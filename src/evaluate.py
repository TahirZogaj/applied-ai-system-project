"""
Evaluation harness for the AI music recommender.

Runs a fixed set of plain-English requests through the pipeline and measures:
  - hit@1        top pick has an expected genre or mood
  - precision@k  share of picks with an expected genre or mood
  - energy fit   average pick energy falls in the expected range
  - grounded     the model never recommended a song outside the retrieved set
  - weak-match   out-of-catalog requests are flagged as weak matches
  - consistency  repeated runs return the same top-3 songs
  - fallbacks    how often the LLM failed and a fallback was used

It always evaluates the offline baseline (keyword parser + rule-based scorer) and,
when GEMINI_API_KEY is set, the Gemini RAG pipeline, so the two can be compared.

Run from the project root:
    python -m src.evaluate              # baseline + Gemini (if key set)
    python -m src.evaluate --offline    # baseline only
    python -m src.evaluate --runs 3     # more runs per case for consistency
"""

import argparse
import json
import logging
import os
from statistics import mean
from typing import Any, Dict, List

try:
    from src.assistant import recommend_from_text
    from src.main import CATALOG_PATH, make_llm, setup_logging
    from src.recommender import load_songs
except ImportError:
    from assistant import recommend_from_text
    from main import CATALOG_PATH, make_llm, setup_logging
    from recommender import load_songs

REPORT_PATH = os.path.join("logs", "eval_report.json")
K = 5

EVAL_CASES: List[Dict[str, Any]] = [
    {"request": "upbeat happy pop for a road trip",
     "genres": {"pop", "indie pop"}, "moods": {"happy"}, "energy": (0.6, 1.0)},
    {"request": "chill lofi beats to study to",
     "genres": {"lofi"}, "moods": {"chill", "focused"}, "energy": (0.0, 0.6)},
    {"request": "something intense and loud for the gym",
     "genres": {"rock", "metal", "edm"}, "moods": {"intense", "angry", "energetic"}, "energy": (0.7, 1.0)},
    {"request": "calm piano music to fall asleep to",
     "genres": {"classical", "ambient"}, "moods": {"peaceful", "chill"}, "energy": (0.0, 0.5)},
    {"request": "sad acoustic songs for a rainy day",
     "genres": {"folk", "blues"}, "moods": {"sad", "melancholic"}, "energy": (0.0, 0.6)},
    {"request": "romantic slow jams for date night",
     "genres": {"r&b", "jazz"}, "moods": {"romantic", "relaxed"}, "energy": (0.0, 0.7)},
    {"request": "party music to dance to",
     "genres": {"edm", "latin", "pop"}, "moods": {"energetic", "festive", "happy"}, "energy": (0.65, 1.0)},
    {"request": "nostalgic country tunes for a long drive",
     "genres": {"country"}, "moods": {"nostalgic"}, "energy": (0.0, 1.0)},
    {"request": "smooth jazz to unwind after work",
     "genres": {"jazz"}, "moods": {"relaxed"}, "energy": (0.0, 0.6)},
    {"request": "k-pop for a euphoric mood",
     "genres": set(), "moods": set(), "energy": (0.0, 1.0), "expect_weak": True},
]


def _matches(song: Dict[str, Any], case: Dict[str, Any]) -> bool:
    return song["genre"].lower() in case["genres"] or song["mood"].lower() in case["moods"]


def score_case(result, case: Dict[str, Any]) -> Dict[str, Any]:
    """Scores one pipeline result against a case's expectations."""
    songs = [p.song for p in result.picks]
    expect_weak = case.get("expect_weak", False)
    lo, hi = case["energy"]
    avg_energy = mean(s["energy"] for s in songs) if songs else 0.0
    row = {
        "request": case["request"],
        "profile": result.profile,
        "picks": [s["id"] for s in songs],
        "grounded": not result.dropped_ids,
        "weak_flag_ok": result.weak_match == expect_weak if expect_weak else True,
        "energy_ok": lo <= avg_energy <= hi,
        "avg_energy": round(avg_energy, 2),
        "fallback": result.profile_source != "llm" or result.answer_source != "llm",
    }
    if expect_weak:
        row["hit1"] = row["precision"] = None  # nothing in the catalog can match
    else:
        row["hit1"] = bool(songs) and _matches(songs[0], case)
        row["precision"] = round(sum(_matches(s, case) for s in songs) / len(songs), 2) if songs else 0.0
    return row


def evaluate(songs, llm, runs: int) -> Dict[str, Any]:
    """Runs every case `runs` times and aggregates the metrics."""
    rows, consistent = [], []
    for case in EVAL_CASES:
        run_rows = []
        for _ in range(runs):
            result = recommend_from_text(case["request"], songs, llm=llm, k=K)
            run_rows.append(score_case(result, case))
        rows.append(run_rows[0])
        consistent.append(len({tuple(r["picks"][:3]) for r in run_rows}) == 1)
        # Count a fallback if any run fell back.
        rows[-1]["fallback"] = any(r["fallback"] for r in run_rows)

    scored = [r for r in rows if r["hit1"] is not None]
    summary = {
        "cases": len(rows),
        "runs_per_case": runs,
        "hit_at_1": round(mean(r["hit1"] for r in scored), 2),
        "precision_at_k": round(mean(r["precision"] for r in scored), 2),
        "energy_fit": round(mean(r["energy_ok"] for r in rows), 2),
        "grounded": round(mean(r["grounded"] for r in rows), 2),
        "weak_match_flagged": round(mean(r["weak_flag_ok"] for r in rows), 2),
        "consistency": round(mean(consistent), 2),
        "fallback_rate": round(mean(r["fallback"] for r in rows), 2),
    }
    return {"summary": summary, "cases": rows}


def print_report(name: str, report: Dict[str, Any]) -> None:
    print(f"\n=== {name} ===")
    print(f"{'request':<42} {'hit@1':>5} {'prec':>5} {'energy':>6} {'grnd':>4} {'fb':>3}")
    for r in report["cases"]:
        hit = "-" if r["hit1"] is None else ("Y" if r["hit1"] else "N")
        prec = "-" if r["precision"] is None else f"{r['precision']:.2f}"
        print(
            f"{r['request'][:42]:<42} {hit:>5} {prec:>5} {('Y' if r['energy_ok'] else 'N'):>6} "
            f"{('Y' if r['grounded'] else 'N'):>4} {('Y' if r['fallback'] else '-'):>3}"
        )
    print("summary:", json.dumps(report["summary"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the AI music recommender.")
    parser.add_argument("--offline", action="store_true", help="evaluate only the offline baseline")
    parser.add_argument("--runs", type=int, default=2, help="runs per case (for the consistency metric)")
    args = parser.parse_args()

    setup_logging()
    songs = load_songs(CATALOG_PATH)
    reports = {"baseline (offline)": evaluate(songs, None, 1)}

    llm = make_llm(args.offline)
    if llm is not None:
        reports["gemini RAG"] = evaluate(songs, llm, max(args.runs, 1))
    elif not args.offline:
        logging.getLogger("music_assistant").warning("No Gemini client; only the baseline was evaluated.")

    for name, report in reports.items():
        print_report(name, report)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=list)
    print(f"\nFull report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
