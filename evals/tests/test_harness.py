"""Offline tests for the eval harness — no Anthropic API, no network.

Covers the pure/offline paths: JSON extraction, tri-state case loading, and
harvesting a diff from a real (temporary) git repo. Run from the repo root:

    python -m unittest discover -s evals/tests
"""
import os
import subprocess
import tempfile
import textwrap
import unittest

from evals.harness import config, dataset, harvest
from evals.harness.llm import _extract_json


class ExtractJsonTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_extract_json('{"a": 1}'), {"a": 1})

    def test_fenced_with_lang(self):
        self.assertEqual(_extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_fenced_no_lang(self):
        self.assertEqual(_extract_json('```\n{"a": 1}\n```'), {"a": 1})

    def test_embedded_in_prose(self):
        self.assertEqual(_extract_json('Sure, here: {"a": 1} — done.'), {"a": 1})

    def test_surrounding_whitespace(self):
        self.assertEqual(_extract_json('\n   {"a": 1}\n'), {"a": 1})


def _write_case(root, name, meta_yaml, diff="--- a/x\n+++ b/x\n"):
    case_dir = os.path.join(root, name)
    os.makedirs(case_dir)
    with open(os.path.join(case_dir, "case.yaml"), "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(meta_yaml))
    with open(os.path.join(case_dir, "diff.patch"), "w", encoding="utf-8") as f:
        f.write(diff)


class LoadCasesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _write_case(self.tmp, "bug", "id: bug\nshould_flag: true\nexpected_findings:\n  - x\n")
        _write_case(self.tmp, "clean", "id: clean\nshould_flag: false\n")
        _write_case(self.tmp, "unlabeled", "id: unlabeled\nshould_flag: null\n")

    def test_tristate_should_flag(self):
        cases = {c.id: c for c in dataset.load_cases(self.tmp)}
        self.assertIs(cases["bug"].should_flag, True)
        self.assertIs(cases["clean"].should_flag, False)
        self.assertIsNone(cases["unlabeled"].should_flag)  # not collapsed to False

    def test_defaults_and_only_filter(self):
        cases = dataset.load_cases(self.tmp, only="clean")
        self.assertEqual([c.id for c in cases], ["clean"])
        self.assertEqual(cases[0].prompt, "post-change-validation")  # default
        self.assertEqual(cases[0].expected_findings, [])             # default


class HarvestTests(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.cases = tempfile.mkdtemp()
        self._git("init")
        self._git("commit", "--allow-empty", "-m", "root")
        with open(os.path.join(self.repo, "f.txt"), "w", encoding="utf-8") as f:
            f.write("hello\n")
        self._git("add", "f.txt")
        self._git("commit", "-m", "add f")
        self._orig_cases = config.CASES_DIR
        config.CASES_DIR = self.cases  # harvest writes here

    def tearDown(self):
        config.CASES_DIR = self._orig_cases

    def _git(self, *args):
        subprocess.run(
            ["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True,
        )

    def test_harvest_writes_unlabeled_case(self):
        created = harvest.harvest(self.repo, count=1)
        self.assertEqual(len(created), 1)
        case = dataset.load_cases(self.cases)[0]
        self.assertIsNone(case.should_flag)          # harvested → unlabeled
        self.assertEqual(case.expected_findings, [])
        self.assertIn("f.txt", case.diff)            # captured the real diff

    def test_harvest_rejects_non_repo(self):
        with self.assertRaises(SystemExit):
            harvest.harvest(tempfile.mkdtemp(), count=1)


if __name__ == "__main__":
    unittest.main()
