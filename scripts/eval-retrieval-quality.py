"""
eval-retrieval-quality.py — opt-in retrieval-quality regression harness.

Runs a small hardcoded gold set (query -> expected clause_id) through
clause_search() and reports hit@1 / hit@5. This is a manual/CI smoke gate,
NOT collected by pytest (lives in scripts/, requires a live Mongo + an
indexed corpus).

Prerequisites:
  1. Mongo running:   docker compose -f infra/docker/docker-compose.yml up -d mongo
  2. Corpus indexed:  python scripts/index-foia-corpus.py --upsert --yes
     (creates the foia_precedent collection + text index)

Usage:
  python scripts/eval-retrieval-quality.py
  python scripts/eval-retrieval-quality.py --floor 0.5

Exit codes:
  0  hit@5 >= floor (pass)
  1  hit@5 <  floor (regression)
  2  retrieval infrastructure unavailable (Mongo down / corpus not indexed)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# clause_search lives in the ai-orchestrator service package; add it to the
# path so this standalone script can import it.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_AI_ORCH = _REPO_ROOT / "services" / "ai-orchestrator"
sys.path.insert(0, str(_AI_ORCH))

from app import atlas_retriever  # noqa: E402

# Gold set: query -> expected clause_id (filename stem in data/seed/foia-precedent).
# Pairs are drawn honestly from the seed corpus content, covering both
# far_parts (5 USC 552 and 28 CFR 16).
GOLD_SET: list[tuple[str, str]] = [
    ("twenty working days time limit determination", "5usc552-a6A-time-limits"),
    ("expedited processing compelling need imminent threat", "5usc552-a6E-expedited"),
    ("fee waiver public interest requester category", "5usc552-a4A-fees"),
    ("advance payment fees exceed 250 dollars", "28cfr16-10-fees"),
    ("deliberative process privilege pre-decisional drafts", "exemption-b5-deliberative"),
    ("adverse determination right to appeal OGIS dispute resolution", "28cfr16-5-6-processing"),
]


def _evaluate(floor: float) -> int:
    rows: list[tuple[str, str, bool, bool]] = []
    hit1 = 0
    hit5 = 0

    for query, expected in GOLD_SET:
        hits = atlas_retriever.clause_search(query, top_k=5)
        clause_ids = [h["clause_id"] for h in hits]
        is_hit1 = bool(clause_ids) and clause_ids[0] == expected
        is_hit5 = expected in clause_ids
        hit1 += int(is_hit1)
        hit5 += int(is_hit5)
        rows.append((query, expected, is_hit1, is_hit5))

    n = len(GOLD_SET)
    hit1_rate = hit1 / n
    hit5_rate = hit5 / n

    # Per-query table.
    print(f"{'hit@1':<6}{'hit@5':<6}  expected_clause_id            query")
    print("-" * 90)
    for query, expected, is_hit1, is_hit5 in rows:
        print(
            f"{('Y' if is_hit1 else '.'):<6}"
            f"{('Y' if is_hit5 else '.'):<6}  "
            f"{expected:<28}  {query}"
        )
    print("-" * 90)
    print(f"aggregate: hit@1 = {hit1}/{n} ({hit1_rate:.2f})   "
          f"hit@5 = {hit5}/{n} ({hit5_rate:.2f})   floor = {floor:.2f}")

    if hit5_rate < floor:
        print(f"\nREGRESSION: hit@5 {hit5_rate:.2f} below floor {floor:.2f}",
              file=sys.stderr)
        return 1
    print("\nPASS: retrieval quality at or above floor.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Opt-in FOIA retrieval-quality eval (hit@1 / hit@5)."
    )
    parser.add_argument(
        "--floor",
        type=float,
        default=0.5,
        help="Minimum acceptable hit@5 rate; exit 1 below it (default: 0.5).",
    )
    args = parser.parse_args()

    try:
        return _evaluate(args.floor)
    except atlas_retriever.RetrievalUnavailableError as exc:
        print(
            f"ERROR: retrieval unavailable ({exc}).\n"
            "Mongo not reachable / corpus not indexed — run "
            "scripts/index-foia-corpus.py --upsert --yes first "
            "(and ensure docker-compose mongo is up).",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
