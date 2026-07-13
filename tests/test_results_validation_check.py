"""Tests for results_validation_check.py (Results-as-Validation gate)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "scripts" / "results_validation_check.py"


HEADER = (
    "| Results Unit | Contribution Claim Tested | Result/Evidence | Figure/Table "
    "| Confirmatory Condition | Allowed Interpretation | Interpretation NOT Allowed |\n"
    "|---|---|---|---|---|---|---|\n"
)

GOOD_ROW = (
    "| 4.2 Main accuracy vs SOTA | C1: our method beats prior SOTA on benchmark X "
    "| +3.1 acc over best baseline (88.4 vs 85.3) | Table 2 | X standard split, matched budget "
    "| Improves accuracy under matched-budget training on X | Do NOT claim general superiority |\n"
)

# Same columns but the Contribution Claim Tested cell is empty -> metric-only row.
METRIC_ONLY_ROW = (
    "| 4.2 Main accuracy |  | +3.1 acc over best baseline (88.4 vs 85.3) | Table 2 "
    "| X standard split | Improves accuracy on X | Do NOT claim general superiority |\n"
)

# Cells are non-empty but placeholder text -> must not count as a mapped row.
PLACEHOLDER_CLAIM_ROW = (
    "| 4.2 Main accuracy | TBD | +3.1 acc over best baseline (88.4 vs 85.3) | Table 2 "
    "| X standard split | Improves accuracy on X | Do NOT claim general superiority |\n"
)
SHORT_EVIDENCE_ROW = (
    "| 4.2 Main accuracy | C1: our method beats prior SOTA on benchmark X | - | Table 2 "
    "| X standard split | Improves accuracy on X | Do NOT claim general superiority |\n"
)


def _write_results(text: str | None) -> Path:
    tmp = Path(tempfile.mkdtemp())
    if text is not None:
        (tmp / "results_validation.md").write_text(text, encoding="utf-8")
    return tmp


def _run(out_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(out_dir), "--markdown"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ResultsValidationCheckTests(unittest.TestCase):
    def test_mapped_row_passes(self) -> None:
        out = _write_results("# Results Validation\n\n" + HEADER + GOOD_ROW)
        res = _run(out)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Status: PASS", res.stdout)
        self.assertIn("Rows mapping a claim to evidence: 1", res.stdout)

    def test_metric_only_row_fails(self) -> None:
        out = _write_results("# Results Validation\n\n" + HEADER + METRIC_ONLY_ROW)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Status: FAIL", res.stdout)
        self.assertIn("Contribution Claim Tested", res.stdout)

    def test_placeholder_claim_fails(self) -> None:
        # A non-empty but placeholder claim (TBD) must not satisfy the gate.
        out = _write_results("# Results Validation\n\n" + HEADER + PLACEHOLDER_CLAIM_ROW)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("placeholder", res.stdout.lower())

    def test_short_evidence_fails(self) -> None:
        # A one-character evidence cell ('-') is a placeholder, not a result.
        out = _write_results("# Results Validation\n\n" + HEADER + SHORT_EVIDENCE_ROW)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Result/Evidence", res.stdout)

    def test_terse_concrete_cells_pass(self) -> None:
        # A bare contribution ID + a short concrete number are valid content;
        # the gate must not impose a prose-length floor on them.
        terse_row = (
            "| 4.2 Accuracy | C1 | AUC 0.92 | Table 2 | matched budget "
            "| Improves accuracy on X | Do NOT claim general superiority |\n"
        )
        out = _write_results("# Results Validation\n\n" + HEADER + terse_row)
        res = _run(out)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Status: PASS", res.stdout)

    def test_evidence_column_titled_result_is_resolved(self) -> None:
        # Regression: the bare "result" term substring-matched the "Results
        # Unit" header, so an evidence column titled just "Result" bound to the
        # unit column (index 0) and empty Result cells silently passed.
        header = (
            "| Results Unit | Contribution Claim Tested | Result | Figure/Table "
            "| Confirmatory Condition | Allowed Interpretation "
            "| Interpretation NOT Allowed |\n"
            "|---|---|---|---|---|---|---|\n"
        )
        empty_evidence_row = (
            "| 4.1 Accuracy | C1: beats SOTA |  | Table 2 | matched budget "
            "| Improves accuracy on X | Do NOT claim general superiority |\n"
        )
        out = _write_results("# Results Validation\n\n" + header + empty_evidence_row)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Status: FAIL", res.stdout)

    def test_missing_file_fails(self) -> None:
        out = _write_results(None)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("does not exist", res.stdout)

    def test_no_data_rows_fails(self) -> None:
        out = _write_results("# Results Validation\n\n" + HEADER)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("no data rows", res.stdout)


if __name__ == "__main__":
    unittest.main()
