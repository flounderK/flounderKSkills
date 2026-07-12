"""Pairwise-judge two runs to compare open-ended review quality (A/B a prompt change).

Each case is judged twice with the two reviews swapped, to control for position bias:
a run only "wins" a case if it wins both orderings; otherwise the case is a tie.
"""
import json
import os

from . import config
from .dataset import load_cases
from .llm import complete_json

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
        "reason": {"type": "string"},
    },
    "required": ["winner", "reason"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """You compare two code reviews (A and B) of the same change and decide
which is better overall: more correct, catches the real issues, avoids false alarms, and
gives actionable fixes. If they are genuinely equivalent, answer "tie". Judge quality,
not verbosity — a longer review is not automatically better."""


def _judge(case, review_a, review_b):
    user = json.dumps({
        "change_description": case.description,
        "diff": case.diff,
        "review_A": review_a,
        "review_B": review_b,
    }, indent=2)
    return complete_json(JUDGE_SYSTEM, user, VERDICT_SCHEMA, config.JUDGE_MODEL)["winner"]


def _load(run_dir, case_id):
    path = os.path.join(run_dir, case_id + ".json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("findings", [])


def compare_runs(run_a, run_b, only=None):
    cases = load_cases(config.CASES_DIR, only=only)
    dir_a = os.path.join(config.RUNS_DIR, run_a)
    dir_b = os.path.join(config.RUNS_DIR, run_b)
    wins = {run_a: 0, run_b: 0, "tie": 0}
    judged = 0
    print(f"\nPairwise comparison (judge: {config.JUDGE_MODEL}):")
    for case in cases:
        fa, fb = _load(dir_a, case.id), _load(dir_b, case.id)
        if fa is None or fb is None:
            continue
        # Judge both orderings; map each verdict back to the run name.
        first = {"A": run_a, "B": run_b, "tie": "tie"}[_judge(case, fa, fb)]
        second = {"A": run_b, "B": run_a, "tie": "tie"}[_judge(case, fb, fa)]
        if first == second and first != "tie":
            verdict = first
        else:
            verdict = "tie"
        wins[verdict] += 1
        judged += 1
        print(f"  {case.id}: {verdict}")

    print(f"\n{judged} case(s) judged (double-swapped):")
    print(f"  {run_a}: {wins[run_a]} win(s)")
    print(f"  {run_b}: {wins[run_b]} win(s)")
    print(f"  tie: {wins['tie']}")
