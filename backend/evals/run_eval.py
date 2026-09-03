from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def score_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status")
    if case.get("expect_clarification"):
        passed = status == "waiting_for_clarification"
    elif case.get("expect_rejection"):
        passed = status == "failed"
    else:
        columns = set(result.get("columns", []))
        passed = status == "completed" and set(case.get("required_columns", [])) <= columns
    return {"id": case["id"], "passed": passed, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser(description="Score saved DataPilot evaluation results")
    parser.add_argument("results", type=Path, help="JSON map from case id to query result")
    args = parser.parse_args()
    cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    results = json.loads(args.results.read_text(encoding="utf-8"))
    scores = [score_case(case, results.get(case["id"], {})) for case in cases]
    print(
        json.dumps(
            {
                "passed": sum(item["passed"] for item in scores),
                "total": len(scores),
                "cases": scores,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
