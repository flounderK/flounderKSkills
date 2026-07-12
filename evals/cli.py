"""Eval harness CLI. Run from the repo root: `python -m evals.cli <command>`.

Commands:
  run <run_id>            Run the prompt over all cases (single-shot) → evals/runs/<run_id>/
  score <run_id>          Score a run against ground truth (recall + false-positive rate)
  compare <run_a> <run_b> Pairwise-judge two runs (A/B a prompt change)
  harvest <repo>          Grab 1-2 diffs from a git repo into new (unlabeled) cases

The run/score/compare commands call the Anthropic API (needs `anthropic` installed and
ANTHROPIC_API_KEY or an `ant` profile). harvest is offline (git only).
"""
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(prog="evals", description="Prompt eval harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a prompt over all cases (single-shot)")
    p_run.add_argument("run_id", help="Name for this run (a folder under evals/runs/)")
    p_run.add_argument("--only", help="Run only the named case")

    p_score = sub.add_parser("score", help="Score a run against ground truth")
    p_score.add_argument("run_id")
    p_score.add_argument("--only")

    p_cmp = sub.add_parser("compare", help="Pairwise-judge two runs")
    p_cmp.add_argument("run_a")
    p_cmp.add_argument("run_b")
    p_cmp.add_argument("--only")

    p_harvest = sub.add_parser("harvest", help="Grab diffs from a git repo into new cases")
    p_harvest.add_argument("repo", help="Path to a git repository")
    p_harvest.add_argument("--count", type=int, default=1, help="Number of recent commits (default 1)")
    p_harvest.add_argument("--working", action="store_true", help="Capture uncommitted changes instead")
    p_harvest.add_argument("--rev", help="A specific commit SHA/ref instead of recent commits")
    p_harvest.add_argument("--prompt", default="post-change-validation", help="Prompt this case targets")

    args = parser.parse_args(argv)

    # Import lazily so `harvest` and `--help` work without the anthropic package.
    if args.cmd == "run":
        from evals.harness.run import run_prompt
        run_prompt(args.run_id, only=args.only)
    elif args.cmd == "score":
        from evals.harness.score import score_run
        score_run(args.run_id, only=args.only)
    elif args.cmd == "compare":
        from evals.harness.compare import compare_runs
        compare_runs(args.run_a, args.run_b, only=args.only)
    elif args.cmd == "harvest":
        from evals.harness.harvest import harvest
        harvest(args.repo, count=args.count, working=args.working,
                rev=args.rev, prompt=args.prompt)


if __name__ == "__main__":
    main()
