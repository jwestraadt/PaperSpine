"""Tests for progress_check.py gate logic (V4 fixed gate bugs)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "scripts" / "progress_check.py"


def _mkdir(config: dict | None = None, files: dict | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "paper_rewriting_output"
    tmp.mkdir(parents=True)
    if config is not None:
        (tmp / "paper_spine_config.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
    for name, content in (files or {}).items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


def _gate(out_dir: Path, gate: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(out_dir), "--gate", gate, *extra],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ProgressGateTests(unittest.TestCase):
    def test_word_require_with_word_output_none_fails(self) -> None:
        # The fixed bug: --gate word --require must NOT pass just because
        # word_output is disabled; --require forces the docx/report pair.
        out = _mkdir(config={"word_output": "none"})
        res = _gate(out, "word", "--require")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("GATE FAILED", res.stdout)
        self.assertIn("paper.docx", res.stdout)

    def test_word_none_without_require_passes_optout(self) -> None:
        # Without --require, word_output=none is a legitimate opt-out.
        out = _mkdir(config={"word_output": "none"})
        res = _gate(out, "word")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_integrity_audit_status_fail_fails(self) -> None:
        out = _mkdir(
            config={"word_output": "none"},
            files={
                "artifact_check.md": "# Artifact Check\n\nStatus: PASS\n",
                "integrity_audit.md": "# Integrity Audit\n\nStatus: FAIL\n",
            },
        )
        res = _gate(out, "integrity_audit")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("FAIL/BLOCKED", res.stdout)

    def test_integrity_audit_healthy_passes(self) -> None:
        out = _mkdir(
            config={"word_output": "none"},
            files={
                "artifact_check.md": "# Artifact Check\n\nStatus: PASS\n",
                "integrity_audit.md": "# Integrity Audit\n\nStatus: PASS\n",
            },
        )
        res = _gate(out, "integrity_audit")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("GATE PASSED", res.stdout)

    def test_final_audit_invokes_methodology_checks(self) -> None:
        # final_audit must drive contribution, reviewer, and (for journal scenes)
        # results-validation checks. With those artifacts absent, the gate fails
        # and names each failing script.
        out = _mkdir(config={"scene": "journal", "word_output": "none"})
        res = _gate(out, "final_audit")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("contribution_check.py", res.stdout)
        self.assertIn("reviewer_audit_check.py", res.stdout)
        self.assertIn("results_validation_check.py", res.stdout)

    def test_final_audit_skips_results_for_nonevidence_scene(self) -> None:
        # results_validation only applies to evidence-bearing scenes.
        out = _mkdir(config={"scene": "report", "word_output": "none"})
        res = _gate(out, "final_audit")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertNotIn("results_validation_check.py", res.stdout)
        self.assertIn("contribution_check.py", res.stdout)


class FinalAuditOfflineTests(unittest.TestCase):
    def test_citation_quality_audit_runs_structural_only(self) -> None:
        # The completion gate must be passable offline: citation_quality_audit
        # is invoked with --no-api (structural analysis). Live DOI resolution
        # belongs to the citation stage (citation_verification_en.py), not the
        # final gate, which would otherwise fail every run without network.
        from unittest import mock

        sys.path.insert(0, str(ROOT / "src" / "scripts"))
        try:
            import progress_check
        finally:
            sys.path.remove(str(ROOT / "src" / "scripts"))

        calls: list[tuple[str, list[str]]] = []

        def fake_run(scripts_dir: Path, script_name: str, args: list[str]):
            calls.append((script_name, args))
            return 0, "", ""

        out = _mkdir(config={"scene": "report", "word_output": "none"})
        with mock.patch.object(progress_check, "_run_script", side_effect=fake_run):
            ok, message, failures = progress_check._run_final_audit_gate(
                out, {"scene": "report", "word_output": "none"}
            )
        self.assertTrue(ok, message)
        self.assertEqual(failures, [])
        cqa_calls = [args for name, args in calls if name == "citation_quality_audit.py"]
        self.assertEqual(len(cqa_calls), 1, calls)
        self.assertIn("--no-api", cqa_calls[0])


class ProgressScanTests(unittest.TestCase):
    def test_missing_output_dir_reports_intake(self) -> None:
        tmp = Path(tempfile.mkdtemp()) / "does_not_exist"
        res = subprocess.run(
            [sys.executable, str(SCRIPT), str(tmp), "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["next_stage"], "intake")
        self.assertFalse(data["is_complete"])


if __name__ == "__main__":
    unittest.main()
