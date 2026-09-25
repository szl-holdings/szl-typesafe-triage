# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Source contract for this repository's CI, not a general YAML/policy verifier.

The functional pytest tests and legacy unittest cases must both be collected.
The original setup failure and zero-functional-collection risks must not recur.
"""
from pathlib import Path
import ast
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def workflow() -> str:
    return (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def action_refs(source: str) -> list[str]:
    # Deliberately restricted to the simple block steps in this CI file.
    return re.findall(r"^\s*-\s+uses:\s+([^\s#]+)", source, re.MULTILINE)


class CIContractTests(unittest.TestCase):
    def test_external_actions_have_immutable_full_sha_pins(self):
        refs = action_refs(workflow())
        self.assertEqual(len(refs), 2)
        for ref in refs:
            self.assertRegex(ref, r"^actions/(checkout|setup-python)@[0-9a-f]{40}$")

    def test_original_tag_pins_are_rejected_by_contract(self):
        for ref in ("actions/checkout@v4", "actions/setup-python@v5",
                    "actions/checkout@11d5960", "actions/checkout@main"):
            with self.subTest(ref=ref):
                self.assertNotRegex(ref, r"^actions/(checkout|setup-python)@[0-9a-f]{40}$")

    def test_full_pytest_suite_runs_without_selection_or_failure_masking(self):
        source = workflow()
        self.assertIn("        run: python -m pytest tests -ra\n", source)
        self.assertNotIn("python -m unittest discover", source)
        self.assertNotIn("continue-on-error:", source)
        self.assertNotIn("|| true", source)
        self.assertNotIn("--ignore", source)

    def test_actual_test_runner_is_installed_without_model_extras(self):
        source = workflow()
        self.assertIn("run: python -m pip install -e . pytest==9.0.2\n", source)
        self.assertNotIn(".[model]", source)
        self.assertIn("run: python -m pip check\n", source)

    def test_cli_and_both_original_policy_gates_remain(self):
        source = workflow()
        self.assertIn('run: szl-triage decide "charged twice on invoice INV-2041, want a refund"', source)
        for version in (1, 2):
            self.assertIn(
                f"run: python scripts/export_sft_dataset.py --check --policy policies/triage_policy.v{version}.json\n",
                source,
            )

    def test_bounded_read_only_execution_and_no_persisted_checkout_credentials(self):
        source = workflow()
        self.assertIn("permissions:\n  contents: read\n", source)
        self.assertIn("    timeout-minutes: 15\n", source)
        self.assertIn("          persist-credentials: false\n", source)
        self.assertIn('      PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"\n', source)

    def test_packaged_test_helpers_use_relative_imports(self):
        for name in ("test_doctrine.py", "test_pipeline.py", "test_redteam.py"):
            with self.subTest(path=name):
                tree = ast.parse((ROOT / "tests" / name).read_text(encoding="utf-8"))
                imports = [node for node in ast.walk(tree)
                           if isinstance(node, ast.ImportFrom) and node.module == "conftest"]
                self.assertEqual(len(imports), 1)
                self.assertEqual(imports[0].level, 1)

    def test_native_push_pr_and_merge_group_paths_remain(self):
        source = workflow()
        # A copyright header and nested push filters are part of the committed
        # workflow. The three native events must remain, including merge_group
        # checks_requested. Do not require push to be an empty key.
        self.assertRegex(source, r"(?m)^on:\n")
        self.assertRegex(source, r"(?m)^  push:\n")
        self.assertRegex(source, r"(?m)^  pull_request:\s")
        self.assertRegex(
            source,
            r"(?m)^  merge_group:\n    types:\n    - checks_requested\n",
        )
        self.assertNotIn("pull_request_target:", source)


if __name__ == "__main__":
    unittest.main()
