"""Optional tests against the exact NVIDIA v0.25.0 source ZIP supplied by user.

Set NEMO_V025_SOURCE_ZIP=/path/to/Guardrails-0.25.0.zip.
Static source contracts are *not* substitutes for importing/running NeMo.
"""
import ast
import os
import zipfile
import pytest


@pytest.fixture(scope="module")
def nemo_source():
    path = os.environ.get("NEMO_V025_SOURCE_ZIP")
    if not path or not os.path.exists(path):
        pytest.skip("Set NEMO_V025_SOURCE_ZIP to official NVIDIA v0.25.0 source archive")
    with zipfile.ZipFile(path) as z:
        def load(short):
            match = [n for n in z.namelist() if n.endswith("/nemoguardrails/" + short)]
            assert len(match) == 1, (short, match)
            return ast.parse(z.read(match[0]).decode("utf-8"))
        return {
            "legacy": load("rails/llm/llmrails.py"),
            "io": load("guardrails/iorails.py"),
            "facade": load("guardrails/guardrails.py"),
            "options": load("rails/llm/options.py"),
        }


def _class(module, name):
    return next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == name)


def _method(cls, name):
    return next((n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)


@pytest.mark.parametrize("engine,name", [("legacy", "LLMRails"), ("io", "IORails"), ("facade", "Guardrails")])
def test_source_025_check_and_generation_signatures(nemo_source, engine, name):
    cls = _class(nemo_source[engine], name)
    for method in ("check_async", "generate_async"):
        fn = _method(cls, method)
        assert isinstance(fn, ast.AsyncFunctionDef), f"{name}.{method} missing"
        assert "messages" in [a.arg for a in fn.args.args]
    check = _method(cls, "check_async")
    assert "rail_types" in [a.arg for a in check.args.args]


def test_source_025_action_registration_only_legacy(nemo_source):
    assert _method(_class(nemo_source["legacy"], "LLMRails"), "register_action")
    assert _method(_class(nemo_source["facade"], "Guardrails"), "register_action")
    assert _method(_class(nemo_source["io"], "IORails"), "register_action") is None


def test_source_025_facade_can_force_iorails(nemo_source):
    init = _method(_class(nemo_source["facade"], "Guardrails"), "__init__")
    assert "require_iorails" in [a.arg for a in init.args.kwonlyargs]
    assert "use_iorails" in [a.arg for a in init.args.kwonlyargs]


def test_source_025_railstatus_contract(nemo_source):
    cls = _class(nemo_source["options"], "RailStatus")
    vals = {n.targets[0].id: n.value.value for n in cls.body
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
    assert vals == {"PASSED": "passed", "MODIFIED": "modified", "BLOCKED": "blocked"}
