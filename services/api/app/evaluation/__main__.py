"""Run the evaluation and write the report.

From services/api:
    ../../venv/Scripts/python -m app.evaluation            # the held-back test sets
    ../../venv/Scripts/python -m app.evaluation --no-ai    # only cached answers, free
"""

import argparse
import json
from dataclasses import asdict
from datetime import date

from app.config import PROJECT_ROOT
from app.db import SessionLocal, check_database
from app.evaluation.report import overall, pct, render
from app.evaluation.runner import CachedReader, evaluate
from app.evaluation.scoring import summarize
from app.evaluation.truth import load_sets
from app.llm import get_extractor

DATASET = PROJECT_ROOT / "data" / "generated"
CACHE = PROJECT_ROOT / "data" / "eval" / "cache"
RESULTS = PROJECT_ROOT / "data" / "eval" / "results.json"
REPORT = PROJECT_ROOT / "docs" / "evaluation.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure accuracy on generated sets.")
    parser.add_argument("--split", choices=["test", "train", "all"], default="test")
    parser.add_argument("--limit", type=int, help="only the first N sets")
    parser.add_argument(
        "--no-ai", action="store_true", help="use cached answers only (no AI calls)"
    )
    args = parser.parse_args()

    sets = load_sets(DATASET, args.split)[: args.limit]
    print(f"Evaluating {len(sets)} sets ({args.split} split)...")
    with SessionLocal() as session:
        reader = CachedReader(
            CACHE,
            extractor=None if args.no_ai else get_extractor(),
            session=session if check_database() else None,
        )
        results = evaluate(DATASET, sets, reader)

    summary = summarize(results)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(summary, args.split, date.today()), encoding="utf-8")
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(
            {
                "mistakes": [asdict(check) for check in summary.mistakes],
                "match_mistakes": summary.match_mistakes,
                "failed": summary.failed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(f"AI calls made:        {reader.ai_calls}")
    print(f"Document type:        {pct(summary.classification)}")
    print(f"Header fields:        {pct(overall(summary.fields))}")
    print(f"Line values:          {pct(overall(summary.line_values))}")
    print(f"3-way match exact:    {pct(summary.sets_exact)}")
    print(f"Could not be read:    {len(summary.failed)}")
    print(f"Report written to {REPORT}")


if __name__ == "__main__":
    main()
