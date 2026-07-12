"""Paths and model configuration for the eval harness.

The prompt under test is read from the repo's canonical `prompts/<name>/prompt.md`
so evals always exercise the single source of truth, not a copy.
"""
import os

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
EVALS_DIR = os.path.dirname(HARNESS_DIR)
REPO_DIR = os.path.dirname(EVALS_DIR)
CASES_DIR = os.path.join(EVALS_DIR, "cases")
RUNS_DIR = os.path.join(EVALS_DIR, "runs")
PROMPTS_DIR = os.path.join(REPO_DIR, "prompts")

# Default to Opus 4.8 for both roles; override per run with env vars.
RUNNER_MODEL = os.environ.get("EVAL_RUNNER_MODEL", "claude-opus-4-8")
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-opus-4-8")


def prompt_body(name):
    """Return the canonical prompt text for prompt `name`."""
    path = os.path.join(PROMPTS_DIR, name, "prompt.md")
    with open(path, encoding="utf-8") as f:
        return f.read()
