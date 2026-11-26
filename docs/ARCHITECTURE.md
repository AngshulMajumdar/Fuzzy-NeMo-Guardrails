# Architecture

CSFSM is a guardrail runtime. The host supplies the generator and any real tools.
The runtime's control loop is:

1. Receive an untrusted candidate and obtain an evidence symbol for a new input.
2. Update the posterior over latent conversation modes using the previous action.
3. Apply trusted protocol constraints, content validators and action risk limits.
4. Project the reference action distribution onto the admissible action set.
5. Select an action, update counters, and append a hash-linked audit event.
6. Release a checked draft or invoke an explicitly registered tool through its wrapper.

`Policy` holds the stochastic model, utilities, risk profiles and protocol rules.
`Engine` evaluates decisions. `Guardrail` owns the engine, registry and store.
`Session` exposes conversation-scoped APIs. The runtime holds observed protocol
state separately from the latent-mode posterior; user text can influence the
latter but cannot create trusted events or grants.

## State and transactions

MemoryStore provides in-process transactions. SQLiteStore provides durable
single-host transactions across processes, using WAL and BEGIN IMMEDIATE. Each
session binds an owner and a policy digest; incompatible policies are rejected.
State includes a revision, expiry, posterior, trusted protocol state, decision
counter, permissions, execution records and the last 100 audit entries. Checks
accept an expected revision and an idempotency key.

Every conversation must have its own session. API credentials map to a tenant;
session lookup, inspection and mutation all enforce that tenant. Application
authentication and mapping an end user to the right session remain host duties.

The tool path commits a pending reservation before invoking the registered
function, then opens a second transaction for permission revalidation, invocation,
output inspection and result persistence. Permission changes through that store
cannot commit during invocation. A crash leaves a pending reservation: the
runtime will not guess whether an external side effect occurred. Reconcile using
the external system's own idempotency/transaction identifier. This is at-most-once
invocation per successfully reserved execution ID, not distributed exactly-once
delivery. Deleting a session discards that deduplication history.

SQLite uses one writer at a time. Tool invocation holds the write transaction,
so long-running tools block writes to other sessions. Use bounded tool timeouts
and single-host deployment for this backend. A distributed implementation can
implement SessionStore, but must preserve transactional authorization and durable
reservations; replacing it with a non-atomic cache changes the guarantees.
Tools must not re-enter the same Guardrail/store from their callback.

## Extension interfaces

`EvidenceEncoder.encode(text, state) -> Evidence` maps text to a policy alphabet.
`CandidateValidator.validate(candidate, state) -> list[Finding]` supplies hard
content constraints. `RiskProvider.risks(candidate, state) -> ndarray[n,k]`
provides candidate-dependent action risks. Copies of state are passed to these
extensions. Exceptions, impossible evidence, malformed risks or nonzero stop
risk cause a terminal stop; transport errors never mean allow.

The default encoder is a small rule baseline. The engine accepts neural or
external detectors without importing a model framework into its core. Supply
candidate validators or a RiskProvider for semantic inspection of model output;
the output gate does not refilter the user's input a second time.

## Audit and data

Audit records contain timestamps, reasons, actions and SHA-256 digests, not raw
prompts. Hash linking detects modifications only relative to a separately trusted
head hash; a database administrator can rewrite an entire chain. Retaining only
100 records requires saving earlier heads/records externally for long histories.
Hashing predictable text is not anonymization. Tool replay records and HTTP
idempotency responses can contain approved tool results. Protect the database,
encrypt its volume when needed, and apply host retention requirements. Session
expiry prevents access; expired rows are purged on subsequent session creation,
so use an external cleanup schedule if immediate physical deletion is required.
