"""Harvest real diffs from a git repo into (unlabeled) eval cases.

Point this at a repo you've been running the prompt on and it captures 1-2 diffs —
recent commits, a specific revision, or the uncommitted working tree — as new cases
under evals/cases/. The diff and context are filled in; you then hand-label
`should_flag` and `expected_findings` (that human step is the point — the labels are
the ground truth the scorer trusts).
"""
import os
import subprocess

import yaml

from . import config


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def _write_case(case_id, prompt, diff, description):
    case_dir = os.path.join(config.CASES_DIR, case_id)
    os.makedirs(case_dir, exist_ok=True)
    meta = {
        "id": case_id,
        "prompt": prompt,
        "source": "harvested",
        # UNLABELED — a human must set these two before the case is usable:
        "should_flag": None,        # true if the change contains a real problem, else false
        "description": description,
        "expected_findings": [],    # list of {location, category, description} to catch
    }
    with open(os.path.join(case_dir, "case.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(meta, f, sort_keys=False, default_flow_style=False)
    with open(os.path.join(case_dir, "diff.patch"), "w", encoding="utf-8") as f:
        f.write(diff)
    return case_dir


def harvest(repo, count=1, working=False, rev=None, prompt="post-change-validation"):
    repo = os.path.abspath(repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit(f"{repo} is not a git repository")
    name = os.path.basename(repo.rstrip("/")) or "repo"
    os.makedirs(config.CASES_DIR, exist_ok=True)

    created = []
    if working:
        diff = _git(repo, "diff", "HEAD")
        if not diff.strip():
            raise SystemExit(f"No uncommitted changes in {repo}")
        created.append(_write_case(
            f"harvest-{name}-working", prompt, diff,
            f"Uncommitted working-tree changes in {name}."))
    else:
        shas = [rev] if rev else _git(repo, "log", f"-{count}", "--format=%H").split()
        for sha in shas:
            short = sha[:8]
            subject = _git(repo, "show", "-s", "--format=%s", sha).strip()
            diff = _git(repo, "show", sha, "--format=", "--no-color")
            created.append(_write_case(
                f"harvest-{name}-{short}", prompt, diff,
                f"{name}@{short}: {subject}"))

    for path in created:
        print("  wrote", path)
    print(f"Harvested {len(created)} case(s). "
          "Now hand-label should_flag and expected_findings in each case.yaml.")
    return created
