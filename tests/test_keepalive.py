"""Offline regression checks for the scheduled Renovate keepalive."""

from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


class KeepaliveTests(unittest.TestCase):
    def setUp(self):
        workflow = (ROOT / ".github/workflows/renovate.yml").read_text()
        match = re.search(r"(?ms)^  keepalive:\n(.*?)(?=^  \w+:|\Z)", workflow)
        self.assertIsNotNone(match, "Missing independent keepalive job")
        self.job = match.group(1)

    def test_isolated_scheduled_job(self):
        self.assertIn("if: github.event_name == 'schedule'", self.job)
        self.assertIn("runs-on: ubuntu-latest", self.job)
        self.assertIn("timeout-minutes: 2", self.job)
        self.assertNotIn("needs:", self.job)
        self.assertNotIn("uses:", self.job)
        self.assertNotIn("secrets.", self.job)
        permissions = re.search(
            r"(?m)^    permissions:\n((?:      .+\n)+)", self.job
        )
        self.assertIsNotNone(permissions)
        self.assertEqual(permissions.group(1).strip(), "actions: write")
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.job)
        self.assertIn("GH_REPO: ${{ github.repository }}", self.job)

    def test_existing_schedule_and_manual_options(self):
        workflow = (ROOT / ".github/workflows/renovate.yml").read_text()
        self.assertIn('- cron: "0 6 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("options: [info, debug]", workflow)
        self.assertRegex(workflow, r"dryRun:\n(?: +.*\n)*?        default: false")
        renovate = workflow.split("  renovate:\n", 1)[1]
        self.assertIn("token: ${{ secrets.RENOVATE_TOKEN }}", renovate)
        self.assertIn("LOG_LEVEL: ${{ inputs.logLevel || 'info' }}", renovate)
        self.assertIn("RENOVATE_DRY_RUN: ${{ inputs.dryRun && 'full' || '' }}", renovate)
        self.assertNotIn("actions: write", renovate)

    def test_enable_request_and_api_failure(self):
        match = re.search(r"(?m)^        run: \|\n((?:          .+\n?)+)", self.job)
        self.assertIsNotNone(match)
        script = textwrap.dedent(match.group(1))
        with tempfile.TemporaryDirectory(prefix="renovate-keepalive-") as temp:
            directory = Path(temp)
            fake_gh = directory / "gh"
            fake_gh.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$CALLS"\nexit "$API_EXIT"\n'
            )
            fake_gh.chmod(0o755)
            environment = {
                "PATH": f"{directory}:/usr/bin:/bin",
                "GH_TOKEN": "offline-test-token",
                "GH_REPO": "example/renovate-config",
                "CALLS": str(directory / "calls"),
            }
            for status in (0, 1):
                with self.subTest(api_exit=status):
                    result = subprocess.run(
                        [
                            "/bin/bash", "--noprofile", "--norc",
                            "-e", "-o", "pipefail", "-c", script,
                        ],
                        env={**environment, "API_EXIT": str(status)},
                        capture_output=True,
                        text=True,
                        cwd=temp,
                    )
                    self.assertEqual(result.returncode, status)
                    self.assertEqual(
                        (directory / "calls").read_text().splitlines(),
                        [
                            "api", "--method", "PUT",
                            "repos/example/renovate-config/actions/workflows/renovate.yml/enable",
                        ],
                    )
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
