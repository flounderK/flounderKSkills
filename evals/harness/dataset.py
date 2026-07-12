"""Load eval cases from evals/cases/<case-id>/."""
import os
from dataclasses import dataclass
from typing import Optional

import yaml


@dataclass
class Case:
    id: str
    dir: str
    prompt: str
    # True = change contains a real problem to catch; False = clean; None = unlabeled
    # (e.g. freshly harvested — must be labeled before it counts toward metrics).
    should_flag: Optional[bool]
    description: str
    expected_findings: list     # ground-truth findings an ideal review should surface
    diff: str


def load_cases(cases_dir, only=None):
    cases = []
    if not os.path.isdir(cases_dir):
        return cases
    for name in sorted(os.listdir(cases_dir)):
        case_dir = os.path.join(cases_dir, name)
        meta_path = os.path.join(case_dir, "case.yaml")
        if not os.path.isfile(meta_path):
            continue
        if only and name != only:
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        diff = ""
        diff_path = os.path.join(case_dir, "diff.patch")
        if os.path.isfile(diff_path):
            with open(diff_path, encoding="utf-8") as f:
                diff = f.read()
        cases.append(Case(
            id=meta.get("id", name),
            dir=case_dir,
            prompt=meta.get("prompt", "post-change-validation"),
            should_flag=meta.get("should_flag"),  # None when unlabeled; keep tri-state
            description=meta.get("description", ""),
            expected_findings=meta.get("expected_findings") or [],
            diff=diff,
        ))
    return cases
