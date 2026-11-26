"""Command-line decision checker."""
import argparse
import json
from .engine import FuzzyPolicy


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate normalized detector scores")
    parser.add_argument("--config", default="examples/policy.yaml")
    parser.add_argument("--phase", default="input")
    parser.add_argument("--scores", required=True, help='JSON: {"injection_risk": 0.1, ...}')
    args = parser.parse_args()
    result = FuzzyPolicy.from_yaml(args.config).evaluate(args.phase, json.loads(args.scores))
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
