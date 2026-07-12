"""Every checker's --json output must carry a uniform {status, ok} verdict.

PR#5 unified the verdict shape via _paper_spine_utils.verdict_fields. Two
scripts previously emitted no machine-readable verdict at all: artifact_check
(its `ok` @property was dropped by json.dumps(__dict__)) and latex_guard (a bare
findings array with no wrapping object). This guards against regressing either.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "src" / "scripts"


def _json(script: str, *args: str) -> dict:
    res = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return json.loads(res.stdout)


def _assert_verdict(case: unittest.TestCase, data: dict) -> None:
    case.assertIsInstance(data, dict)
    case.assertIn("status", data)
    case.assertIn(data["status"], ("PASS", "FAIL"))
    case.assertIn("ok", data)
    case.assertIsInstance(data["ok"], bool)
    case.assertEqual(data["ok"], data["status"] == "PASS")


class JsonVerdictTests(unittest.TestCase):
    def test_artifact_check_emits_verdict(self) -> None:
        # Regression: ok was a @property excluded from json.dumps(__dict__).
        tmp = Path(tempfile.mkdtemp()) / "paper_rewriting_output"
        tmp.mkdir(parents=True)
        _assert_verdict(self, _json("artifact_check.py", str(tmp)))

    def test_latex_guard_emits_verdict_object(self) -> None:
        # Regression: JSON was a bare array with no verdict wrapper.
        tmp = Path(tempfile.mkdtemp())
        tex = tmp / "main.tex"
        tex.write_text(
            r"\documentclass{article}\begin{document}Hello.\end{document}",
            encoding="utf-8",
        )
        data = _json("latex_guard.py", str(tex))
        _assert_verdict(self, data)
        self.assertIn("findings", data)

    def test_section_economy_emits_verdict(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        tex = tmp / "main.tex"
        tex.write_text(r"\section{One}\section{Two}", encoding="utf-8")
        _assert_verdict(self, _json("section_economy_check.py", str(tex)))

    def test_progress_check_keeps_is_complete_and_adds_verdict(self) -> None:
        tmp = Path(tempfile.mkdtemp()) / "paper_rewriting_output"
        tmp.mkdir(parents=True)
        data = _json("progress_check.py", str(tmp))
        _assert_verdict(self, data)
        self.assertIn("is_complete", data)  # existing consumers still supported
        self.assertEqual(data["ok"], data["is_complete"])


if __name__ == "__main__":
    unittest.main()
