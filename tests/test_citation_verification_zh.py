"""Tests for citation_verification_zh.py.

This module previously had zero test coverage (its English sibling has a
dedicated file). These cover the offline-parseable surface: DOI extraction
(which must not swallow trailing full-width CJK punctuation) and the Chinese
reference-format heuristics.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "scripts"))
from citation_verification_zh import check_zh_format, has_doi


class DoiExtractionTests(unittest.TestCase):
    def test_doi_does_not_swallow_fullwidth_punctuation(self) -> None:
        # Regression: the DOI body class excluded only ASCII delimiters, so a
        # reference ending with a full-width 。 folded it into the DOI and the
        # malformed DOI failed to resolve (false SUSPICIOUS).
        self.assertEqual(has_doi("张三. 某研究. doi:10.1000/xyz123。"), "10.1000/xyz123")
        self.assertEqual(has_doi("见 https://doi.org/10.1234/abc，后续"), "10.1234/abc")

    def test_plain_ascii_doi_still_extracted(self) -> None:
        self.assertEqual(has_doi("Ref. doi: 10.5555/example.2020"), "10.5555/example.2020")

    def test_no_doi_returns_empty(self) -> None:
        self.assertEqual(has_doi("张三. 某研究. 计算机学报, 2024."), "")


class ChineseFormatTests(unittest.TestCase):
    def test_full_chinese_reference_fields_detected(self) -> None:
        # Journal name uses the 《...》 book-title marks the heuristic expects.
        fields = check_zh_format("张三, 李四. 深度学习综述. 《计算机学报》, 2024, 47(3): 1-20.")
        self.assertTrue(fields["has_author"])
        self.assertTrue(fields["has_journal"])
        self.assertTrue(fields["has_year"])


if __name__ == "__main__":
    unittest.main()
