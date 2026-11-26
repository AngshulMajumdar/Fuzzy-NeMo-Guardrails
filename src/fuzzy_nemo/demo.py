"""Interactive manual-score demonstration; not a prompt-injection detector."""
from __future__ import annotations
from importlib.resources import files
import gradio as gr
from .engine import FuzzyPolicy

policy = FuzzyPolicy.from_yaml(str(files("fuzzy_nemo").joinpath("default_policy.yaml")))


def evaluate(injection: float, toxicity: float, unsupported: float):
    input_result = policy.evaluate("input", {"injection_risk": injection, "toxicity_risk": toxicity})
    output_result = policy.evaluate("output", {"unsupported_claim_risk": unsupported})
    gated = "BLOCK" if "block" in (input_result.decision, output_result.decision) else (
        "REVIEW" if "review" in (input_result.decision, output_result.decision) else "ALLOW")
    return gated, input_result.to_dict(), output_result.to_dict()


def make_demo():
    with gr.Blocks(title="Fuzzy NeMo Guardrails") as demo:
        gr.Markdown("# Fuzzy NeMo Guardrails\nCPU-only fuzzy decision layer compatible with LLMRails and IORails via adapters.")
        gr.Markdown("**Demo uses manual detector scores.** It does not detect prompt injection, toxicity, or hallucinations from text. Connect real detectors in your application.")
        with gr.Row():
            injection = gr.Slider(0, 1, value=.08, step=.01, label="Input: injection-risk detector score")
            toxicity = gr.Slider(0, 1, value=.10, step=.01, label="Input: toxicity-risk detector score")
            unsupported = gr.Slider(0, 1, value=.08, step=.01, label="Output: unsupported-claim risk detector score")
        evaluate_button = gr.Button("Evaluate fuzzy guardrails", variant="primary")
        decision = gr.Textbox(label="Combined decision")
        with gr.Row():
            input_json = gr.JSON(label="Input rail / rule activations")
            output_json = gr.JSON(label="Output rail / rule activations")
        evaluate_button.click(evaluate, [injection, toxicity, unsupported], [decision, input_json, output_json])
        demo.load(evaluate, [injection, toxicity, unsupported], [decision, input_json, output_json])
    return demo


def main():
    make_demo().launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
