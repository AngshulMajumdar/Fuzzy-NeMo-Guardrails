# HTTP API

All `/v1` routes require `Authorization: Bearer <key>` unless anonymous development
mode is explicitly enabled. Keys map to `{tenant, role}` in `CSFSM_API_KEYS`.
Use different secrets for client and trusted-authority roles. Keep authority keys
in a trusted backend, never in a chat message, browser or model tool configuration.

| Method and path | Role | Result |
|---|---|---|
| GET /health | Public | Service version and liveness |
| GET /v1/policy | Client | Policy, digest and registered tool schemas |
| POST /v1/sessions | Client | New session and revision |
| GET /v1/sessions/{id} | Client | Tenant-scoped state summary |
| DELETE /v1/sessions/{id} | Client | Remove session and replay history |
| GET /v1/sessions/{id}/audit | Client | Last 100 hash-linked events |
| POST /v1/sessions/{id}/check | Client | Decision for input, output or tool candidate |
| POST /v1/sessions/{id}/events | Authority | Trusted protocol event |
| POST /v1/sessions/{id}/grants | Authority | Single-use argument-bound tool permission |
| POST /v1/sessions/{id}/tools/execute | Client | Enforced registered function execution |

Authority credentials may also use client routes, within the same tenant. The
host must decide which real authenticated end user owns a conversation; a tenant
credential gives access to that tenant's sessions. `events` must follow actual
verification in the host application. The API does not authenticate end users by
their conversational assertions.

```python
from csfsm_guardrails import Candidate
from csfsm_guardrails.client import Client

with Client("http://localhost:8000", api_key="YOUR_CLIENT_KEY") as client:
    session = client.create_session()
    decision = client.check(
        session["id"],
        Candidate(stage="input", text="Explain a state machine"),
        expected_revision=session["revision"],
        idempotency_key="input-001",
    )
    decision.require_allowed()
    draft = your_model("Explain a state machine")
    output = client.check(
        session["id"],
        Candidate(stage="output", text=draft),
        expected_revision=decision.revision,
        idempotency_key="output-001",
    )
    send_to_user(draft if output.allowed else output.message)
```

`AsyncClient` exposes the same operations with async methods. Network errors
raise; never convert a timeout or invalid response into an allowed decision.
The service does not proxy arbitrary user-specified model URLs or execute
user-supplied code. A host model is connected through the SDK or its own backend.

Example check JSON:

```json
{"candidate":{"stage":"output","text":"A proposed response"},"expected_revision":1}
```

Example authority grant JSON:

```json
{"tool":"lookup_record","arguments":{"record_id":"demo-001"},"ttl_seconds":120}
```

Example execution JSON:

```json
{"tool":"lookup_record","arguments":{"record_id":"demo-001"},"execution_id":"application-operation-001"}
```

Use a new operation ID for each intended execution, and reuse it for retries of
that same operation. Checks, grants and events accept `Idempotency-Key`. Reusing
a key with different content returns 409. A cached check is a historical decision,
not a fresh permission. Execution verifies current authorization before releasing
a cached result. Consumed grants are pruned when new grants are issued, so an
older cached result can become unavailable; the operation is still not repeated.

HTTP 401 means invalid credentials, 403 insufficient role, 404 missing/expired or
other-tenant session, 409 revision/idempotency/pending-execution conflict, 413 body
limit, 422 invalid arguments, 429 rate limit, and 503 capacity. A rejected request
must not trigger application fall-through. The default body limit is 64 KiB.
The rate limiter is per tenant per process; put a shared limiter at the ingress
when using multiple workers. Serve over HTTPS behind your deployment's ingress.

OpenAPI is served at `/openapi.json` and `/docs`. The release includes an exported
schema in `docs/openapi.json`.
