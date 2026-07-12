"""Score a run against ground truth: bug-catch recall + false-positive rate.

An LLM judge decides, per expected finding, whether the review covered it (recall),
and whether the review flagged a real problem on changes that should be clean
(false-positive rate). Reference-based, so it measures the objective signal you can
trust; use `compare` for open-ended quality between two prompt variants.
"""
import json
import os

from . import config
from .dataset import load_cases
from .llm import complete_json

COVERAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "covered_expected_indexes": {"type": "array", "items": {"type": "integer"}},
        "flagged_a_real_problem": {"type": "boolean"},
        "notes": {"type": "string"},
    },
    "required": ["covered_expected_indexes", "flagged_a_real_problem", "notes"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """You are grading a code review against a known-correct answer key.
You are given a code change, a list of EXPECTED findings (the ground truth an ideal
review should surface), and the findings a REVIEW actually produced.

For each expected finding, decide whether the review covered it — same underlying issue,
even if worded differently — and return its index in covered_expected_indexes. Be strict:
a vague or generic comment does NOT cover a specific expected finding.

Also set flagged_a_real_problem to true if the review reported at least one genuine,
substantive problem in the change (used to measure false positives on clean changes)."""


def _score_case(case, findings):
    user = json.dumps({
        "change_description": case.description,
        "diff": case.diff,
        "expected_findings": [
            {"index": i, **(e if isinstance(e, dict) else {"description": e})}
            for i, e in enumerate(case.expected_findings)
        ],
        "review_findings": findings,
    }, indent=2)
    verdict = complete_json(JUDGE_SYSTEM, user, COVERAGE_SCHEMA, config.JUDGE_MODEL)
    n = len(case.expected_findings)
    covered = sorted({i for i in verdict["covered_expected_indexes"] if 0 <= i < n})
    return covered, verdict


def score_run(run_id, only=None):
    cases = load_cases(config.CASES_DIR, only=only)
    run_dir = os.path.join(config.RUNS_DIR, run_id)
    if not os.path.isdir(run_dir):
        raise SystemExit(f"No run at {run_dir} — `python -m evals.cli run {run_id}` first")

    recall_num = recall_den = 0
    clean_total = clean_fp = 0
    unlabeled = []
    rows = []
    for case in cases:
        path = os.path.join(run_dir, case.id + ".json")
        if not os.path.isfile(path):
            continue
        # Unlabeled cases (should_flag is None) have no ground truth — skip them from
        # metrics so a freshly harvested case can't silently distort recall/FP rate.
        if case.should_flag is None and not case.expected_findings:
            unlabeled.append(case.id)
            continue
        with open(path, encoding="utf-8") as f:
            findings = json.load(f).get("findings", [])
        covered, verdict = _score_case(case, findings)
        n = len(case.expected_findings)
        row = {"case": case.id, "expected": n, "covered": len(covered),
               "reported": len(findings), "fp": None}
        if n:
            recall_num += len(covered)
            recall_den += n
        if case.should_flag is False:
            clean_total += 1
            fp = bool(verdict.get("flagged_a_real_problem"))
            clean_fp += 1 if fp else 0
            row["fp"] = fp
        rows.append(row)

    print(f"\nScores for run '{run_id}' (judge: {config.JUDGE_MODEL}):\n")
    print(f"{'case':32} {'expected':>8} {'covered':>8} {'reported':>8} {'false-pos':>10}")
    for r in rows:
        fp = "" if r["fp"] is None else ("YES" if r["fp"] else "no")
        print(f"{r['case']:32} {r['expected']:>8} {r['covered']:>8} {r['reported']:>8} {fp:>10}")
    print()
    if recall_den:
        print(f"Bug-catch recall (covered/expected): "
              f"{recall_num}/{recall_den} = {recall_num / recall_den:.0%}")
    else:
        print("Bug-catch recall: n/a (no cases with expected findings)")
    if clean_total:
        print(f"False-positive rate on clean changes: "
              f"{clean_fp}/{clean_total} = {clean_fp / clean_total:.0%}")
    else:
        print("False-positive rate: n/a (no clean cases)")
    if unlabeled:
        print(f"\nSkipped {len(unlabeled)} unlabeled case(s) — label should_flag/"
              f"expected_findings to include them: {', '.join(unlabeled)}")
