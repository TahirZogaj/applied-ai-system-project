"""
Evaluation harness for the AI music recommender.

Runs a fixed set of plain-English requests through the pipeline and measures:
  - hit@1        top pick has an expected genre or mood
  - precision    share of returned picks with an expected genre or mood
  - avg picks    how many songs were returned (the LLM may return fewer than k)
  - energy fit   average pick energy falls in the expected range
  - grounded     the model never recommended a song outside the retrieved set
  - weak-match   out-of-catalog requests are flagged as weak matches
  - consistency  repeated runs return the same top-3 songs
  - confidence   the LLM's self-rated confidence, split by picks that fit vs. did not fit
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
    from src.knowledge import GUIDE_PATH, load_guide
    from src.main import CATALOG_PATH, make_llm, setup_logging
    from src.recommender import load_songs
except ImportError:
    from assistant import recommend_from_text
    from knowledge import GUIDE_PATH, load_guide
    from main import CATALOG_PATH, make_llm, setup_logging
    from recommender import load_songs

REPORT_PATH = os.path.join("logs", "eval_report.json")
MARKDOWN_PATH = os.path.join("docs", "evaluation_results.md")
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
    # No genre or mood words: these depend on understanding the activity or setting.
    {"request": "background music while coding",
     "genres": {"lofi", "ambient"}, "moods": {"focused", "chill"}, "energy": (0.0, 0.6)},
    {"request": "beach party vibes",
     "genres": {"reggae", "latin", "pop", "indie pop"}, "moods": {"uplifting", "festive", "happy"}, "energy": (0.55, 1.0)},
    {"request": "late night drive through the city",
     "genres": {"synthwave"}, "moods": {"moody"}, "energy": (0.5, 1.0)},
    # Genres that are not in the catalog: the system should flag them, not pretend.
    {"request": "k-pop for a euphoric mood",
     "genres": set(), "moods": set(), "energy": (0.0, 1.0), "expect_weak": True},
    {"request": "afrobeats for a summer cookout",
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
        "fallback": result.profile_source != "llm" or result.answer_source not in ("llm", "llm_no_match"),
        "confidences": [p.confidence for p in result.picks],
        "pick_fits": [_matches(s_, case) for s_ in songs] if not expect_weak else [],
    }
    if expect_weak:
        row["hit1"] = row["precision"] = None  # nothing in the catalog can match
        row["passed"] = row["grounded"] and result.weak_match
    else:
        row["hit1"] = bool(songs) and _matches(songs[0], case)
        row["precision"] = round(sum(_matches(s, case) for s in songs) / len(songs), 2) if songs else 0.0
        row["passed"] = row["hit1"] and row["energy_ok"] and row["grounded"]
    return row


def evaluate(songs, llm, runs: int, guide=None) -> Dict[str, Any]:
    """Runs every case `runs` times and aggregates the metrics."""
    rows, consistent = [], []
    for case in EVAL_CASES:
        run_rows = []
        for _ in range(runs):
            result = recommend_from_text(case["request"], songs, llm=llm, k=K, guide=guide)
            run_rows.append(score_case(result, case))
        rows.append(run_rows[0])
        consistent.append(len({tuple(r["picks"][:3]) for r in run_rows}) == 1)
        # Count a fallback if any run fell back.
        rows[-1]["fallback"] = any(r["fallback"] for r in run_rows)
        rows[-1]["passed"] = all(r["passed"] for r in run_rows)

    scored = [r for r in rows if r["hit1"] is not None]
    conf_fit, conf_miss, conf_all = [], [], []
    for r in rows:
        for i, c in enumerate(r["confidences"]):
            if c is None:
                continue
            conf_all.append(c)
            if r["pick_fits"]:
                (conf_fit if r["pick_fits"][i] else conf_miss).append(c)
    summary = {
        "passed": f"{sum(r['passed'] for r in rows)}/{len(rows)}",
        "cases": len(rows),
        "runs_per_case": runs,
        "hit_at_1": round(mean(r["hit1"] for r in scored), 2),
        "precision": round(mean(r["precision"] for r in scored), 2),
        "avg_picks": round(mean(len(r["picks"]) for r in rows), 1),
        "energy_fit": round(mean(r["energy_ok"] for r in rows), 2),
        "grounded": round(mean(r["grounded"] for r in rows), 2),
        "weak_match_flagged": round(mean(r["weak_flag_ok"] for r in rows), 2),
        "consistency": round(mean(consistent), 2),
        "fallback_rate": round(mean(r["fallback"] for r in rows), 2),
        "avg_confidence": round(mean(conf_all), 2) if conf_all else None,
        "confidence_when_fit": round(mean(conf_fit), 2) if conf_fit else None,
        "confidence_when_not_fit": round(mean(conf_miss), 2) if conf_miss else None,
    }
    return {"summary": summary, "cases": rows}


def print_report(name: str, report: Dict[str, Any]) -> None:
    print(f"\n=== {name} ===")
    print(f"{'request':<42} {'hit@1':>5} {'prec':>5} {'n':>2} {'energy':>6} {'grnd':>4} {'fb':>3} {'result':>6}")
    for r in report["cases"]:
        hit = "-" if r["hit1"] is None else ("Y" if r["hit1"] else "N")
        prec = "-" if r["precision"] is None else f"{r['precision']:.2f}"
        print(
            f"{r['request'][:42]:<42} {hit:>5} {prec:>5} {len(r['picks']):>2} {('Y' if r['energy_ok'] else 'N'):>6} "
            f"{('Y' if r['grounded'] else 'N'):>4} {('Y' if r['fallback'] else '-'):>3} {('PASS' if r['passed'] else 'FAIL'):>6}"
        )
    print(f"PASSED {report['summary']['passed']}")
    print("summary:", json.dumps(report["summary"]))


def _yn(value) -> str:
    return "-" if value is None else ("Pass" if value else "Fail")


def write_markdown(reports: Dict[str, Any], path: str = MARKDOWN_PATH) -> None:
    """Writes a parseable markdown version of the evaluation results."""
    lines = ["# Evaluation Results", "", "Generated by `python -m src.evaluate`. "
             "A case passes when the top pick fits, energy is in range, and every pick was retrieved "
             "(out-of-catalog cases pass when flagged as a weak match). Each configuration is run with "
             "and without the genre guide (data/genre_guide.md) to show what the second retrieval source adds.", ""]
    case_by_request = {c["request"]: c for c in EVAL_CASES}
    for name, report in reports.items():
        sm = report["summary"]
        lines += [f"## {name}", "", "| Metric | Value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in sm.items()]
        lines += ["", "| Test input | Evaluation criteria | Picks | Precision | Confidence | Result |",
                  "|---|---|---|---|---|---|"]
        for r in report["cases"]:
            case = case_by_request[r["request"]]
            if case.get("expect_weak"):
                criteria = "Genre not in catalog: flagged as weak match, no invented songs"
            else:
                criteria = (f"genre in {sorted(case['genres'])} or mood in {sorted(case['moods'])}; "
                            f"energy {case['energy'][0]}-{case['energy'][1]}")

            confs = [c for c in r["confidences"] if c is not None]
            conf = f"{mean(confs):.2f}" if confs else "-"
            prec = "-" if r["precision"] is None else f"{r['precision']:.2f}"
            note = " (fallback used)" if r["fallback"] and not name.startswith("baseline") else ""
            lines.append(f"| \"{r['request']}\" | {criteria} | {len(r['picks'])} | {prec} | {conf} | {_yn(r['passed'])}{note} |")
        lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the AI music recommender.")
    parser.add_argument("--offline", action="store_true", help="evaluate only the offline baseline")
    parser.add_argument("--runs", type=int, default=2, help="runs per case (for the consistency metric)")
    args = parser.parse_args()

    setup_logging()
    songs = load_songs(CATALOG_PATH)
    guide = load_guide(GUIDE_PATH)
    reports = {
        "baseline (offline), songs only": evaluate(songs, None, 1),
        "baseline (offline), songs + guide": evaluate(songs, None, 1, guide),
    }

    llm = make_llm(args.offline)
    if llm is not None:
        runs = max(args.runs, 1)
        reports["gemini RAG, songs only"] = evaluate(songs, llm, runs)
        reports["gemini RAG, songs + guide"] = evaluate(songs, llm, runs, guide)
    elif not args.offline:
        logging.getLogger("music_assistant").warning("No Gemini client; only the baseline was evaluated.")

    for name, report in reports.items():
        print_report(name, report)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=list)
    write_markdown(reports)
    print(f"\nFull report saved to {REPORT_PATH} and {MARKDOWN_PATH}")


if __name__ == "__main__":
    main()
