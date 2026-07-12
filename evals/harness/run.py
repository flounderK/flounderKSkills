"""Run a prompt over the cases (single-shot) and record its findings.

NOTE: this is a single-shot *proxy* for the real prompt. The production prompt runs
as a tool-using agent (reads the repo, runs tests/linters, edits files); here the
model sees only the diff and returns findings as JSON. That isolates the review
*reasoning* — which is what prompt-tuning targets — but does not exercise tool use.
"""
import json
import os

from . import config
from .dataset import load_cases
from .llm import complete_json

FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "category": {"type": "string"},
                    "problem": {"type": "string"},
                    "fix": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                },
                "required": ["location", "category", "problem", "fix", "severity"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

EVAL_INSTRUCTION = """

---
EVAL MODE: You are reviewing a single code change presented as a unified diff below.
You cannot run tools, tests, or linters in this mode — base your review solely on the
diff and its visible context. Report only genuine problems in the changed code; if the
change is clean, return an empty findings list. Emit every finding in the required JSON
schema.
"""


def run_prompt(run_id, only=None):
    cases = load_cases(config.CASES_DIR, only=only)
    if not cases:
        raise SystemExit(f"No cases found in {config.CASES_DIR}")
    out_dir = os.path.join(config.RUNS_DIR, run_id)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Running prompt over {len(cases)} case(s) with model {config.RUNNER_MODEL}")
    for case in cases:
        system = config.prompt_body(case.prompt) + EVAL_INSTRUCTION
        user = f"Change under review ({case.description}):\n\n```diff\n{case.diff}\n```"
        data = complete_json(system, user, FINDINGS_SCHEMA, config.RUNNER_MODEL)
        findings = data.get("findings", [])
        with open(os.path.join(out_dir, case.id + ".json"), "w", encoding="utf-8") as f:
            json.dump({"case": case.id, "findings": findings}, f, indent=2)
        print(f"  {case.id}: {len(findings)} finding(s)")
    print(f"Run '{run_id}' written to {out_dir}")
