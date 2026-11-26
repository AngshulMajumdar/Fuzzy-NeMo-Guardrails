"""FastAPI evaluation service; does not run a detector or expose unguarded LLM output."""
from __future__ import annotations
import os
from importlib.resources import files
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .engine import FuzzyPolicy


class EvaluationRequest(BaseModel):
    phase: str = Field(default="input")
    scores: dict[str, float]


app = FastAPI(title="Fuzzy NeMo Guardrails", version="0.1.1",
              description="Score-driven fuzzy policy layer for NVIDIA NeMo guardrails")


def get_policy() -> FuzzyPolicy:
    path = os.environ.get("FUZZY_NEMO_POLICY")
    return FuzzyPolicy.from_yaml(path or str(files("fuzzy_nemo").joinpath("default_policy.yaml")))


@app.get("/health")
def health():
    return {"status": "ok", "source": "fuzzy-policy", "detectors": "external"}


@app.get("/config")
def config():
    return {"phases": list(get_policy().phases), "supply_scores_externally": True}


@app.post("/evaluate")
def evaluate(body: EvaluationRequest):
    try:
        return get_policy().evaluate(body.phase, body.scores).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
