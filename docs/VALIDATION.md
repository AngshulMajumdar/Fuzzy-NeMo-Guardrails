# Release validation

Version: 0.1.0. Run date: 22 November 2026.

The local suite passed **50 tests**, including 300 generated numerical examples
across three Hypothesis property tests. Statement coverage was approximately
88% overall, 92% for the decision engine, and 94% for the enforcing SDK and session
stores. These are implementation tests, not a benchmark of language safety.

Verified behaviors:

- Factorized and general joint posterior updates agree on equivalent models.
- Probabilities normalize; forbidden actions retain exactly zero probability.
- The TV risk bound dominates the exact two-state worst case.
- Impossible evidence, failing validators and malformed risk providers stop.
- Input blocks prevent generator invocation; output and buffered streaming gates
  withhold protected candidates without leaking prefixes.
- JSON-formatted and plain-text tool results pass output validation.
- Tool authorization requires trusted state and exact argument-bound grants.
- Used/expired/revoked permissions cannot authorize another execution.
- Concurrent duplicate execution requests invoke the function at most once.
- Revocation between reservation and invocation prevents execution.
- SQLite restart preserves state and pending executions are not blindly rerun.
- Tenant isolation, role separation, idempotency, revisions, request-size limits
  and rate limits hold for the tested API scenarios.
- LangChain synchronous/async execution and buffered output, LangGraph gating,
  and Gradio session isolation use the same engine.

The running FastAPI service and running Gradio app were additionally exercised
over local HTTP, including Gradio reset, input/output checks, tool denial,
authorization, successful execution and denial after consuming the grant.
The wheel was built and installed into a separate target directory. The generated
Space was copied outside the source checkout and its app constructed successfully.
Ruff lint and formatting checks passed.

Local environment: Linux, Python 3.12.14, NumPy 2.3.5, Pydantic 2.13.4,
FastAPI 0.141.1, Gradio 6.32.0, LangChain Core 1.8.4 and LangGraph 1.2.24.
CI is configured for Python 3.11 and 3.12; remote CI execution is pending a push.
The environment emitted one third-party AnyIO/pytest deprecation warning.

Docker configuration is included but was not built in this environment. No
GitHub repository or Hugging Face Space was published during this validation:
browser publishing requires sign-in and the connected HF credentials lack write
scope. Publication scripts and a self-contained Space directory are included.

Run the checks again with:

```bash
pip install -e '.[api,space,dev,langchain,langgraph]'
pytest --cov=csfsm_guardrails
ruff check .
ruff format --check .
python scripts/smoke_http.py
python -m build
python scripts/build_space.py --output build/hf-space
```

This release's default encoder, transition/emission parameters and risk profiles
are hand-configured. No general safety-classification accuracy, jailbreak
resistance or calibrated conditional violation guarantee has been established.
