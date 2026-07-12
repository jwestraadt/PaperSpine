"""Tests for _paper_spine_utils.py."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "scripts"))
from _paper_spine_utils import (
    MIN_CELL_CHARS,
    SHORT_OK_MIN_CHARS,
    CanonParagraph,
    canonical,
    is_placeholder,
    is_separator_row,
    make_canon,
    markdown_tables,
    normalize_markdown,
    normalize_tex,
    preview,
    read_config,
    read_text,
    similarity_canon,
    split_paragraphs,
    split_table_line,
    strip_tex_comments,
    table_rows,
    year_from_row,
)


class IsPlaceholderTests(unittest.TestCase):
    def test_empty_and_whitespace_are_placeholders(self) -> None:
        self.assertTrue(is_placeholder(""))
        self.assertTrue(is_placeholder("   "))

    def test_template_tokens_are_placeholders(self) -> None:
        for token in ("TODO", "tbd", "N/A", "-", "...", "[fill]", "<x>", "待定"):
            self.assertTrue(is_placeholder(token), token)

    def test_short_content_is_placeholder_by_default(self) -> None:
        # Below MIN_CELL_CHARS real characters -> placeholder.
        self.assertTrue(is_placeholder("x"))
        self.assertTrue(is_placeholder("too short"))  # 9 < 12

    def test_short_ok_min_lets_labels_through(self) -> None:
        # Category labels pass the lower floor but empty/placeholder still fails.
        self.assertFalse(is_placeholder("MAJOR", SHORT_OK_MIN_CHARS))
        self.assertTrue(is_placeholder("x", SHORT_OK_MIN_CHARS))

    def test_real_prose_passes(self) -> None:
        self.assertFalse(is_placeholder("a concrete, filled-in decision cell"))

    def test_markdown_emphasis_stripped_before_measuring(self) -> None:
        # `**x**` has only one real char after stripping emphasis -> placeholder.
        self.assertTrue(is_placeholder("**x**"))
        self.assertGreater(MIN_CELL_CHARS, SHORT_OK_MIN_CHARS)


class ReadConfigTests(unittest.TestCase):
    def _dir_with_config(self, raw: bytes) -> Path:
        out = Path(tempfile.mkdtemp()) / "paper_rewriting_output"
        out.mkdir(parents=True)
        (out / "paper_spine_config.json").write_bytes(raw)
        return out

    def test_bom_config_parses(self) -> None:
        # Regression: integrity_audit/citation_quality_audit read the config
        # as plain utf-8 and crashed with a JSONDecodeError on a Notepad-saved
        # (BOM-prefixed) config inside the final-audit gate.
        out = self._dir_with_config(b'\xef\xbb\xbf{"scene": "journal"}')
        self.assertEqual(read_config(out), {"scene": "journal"})

    def test_malformed_config_returns_empty(self) -> None:
        out = self._dir_with_config(b'{"scene": "journal"')
        self.assertEqual(read_config(out), {})

    def test_non_dict_config_returns_empty(self) -> None:
        out = self._dir_with_config(b'["not", "a", "config"]')
        self.assertEqual(read_config(out), {})

    def test_missing_config_returns_empty(self) -> None:
        out = Path(tempfile.mkdtemp()) / "paper_rewriting_output"
        out.mkdir(parents=True)
        self.assertEqual(read_config(out), {})

    def test_search_parent_falls_back(self) -> None:
        out = self._dir_with_config(b'{"scene": "journal"}')
        nested = out / "submission_package"
        nested.mkdir()
        self.assertEqual(read_config(nested), {})
        self.assertEqual(read_config(nested, search_parent=True), {"scene": "journal"})


class YearFromRowTests(unittest.TestCase):
    def test_year_glued_to_cjk_is_found(self) -> None:
        # Regression: \b after the final digit fails when a CJK char follows
        # (CJK ideographs are word chars), so "2024年" yielded no year.
        self.assertEqual(year_from_row(["C1", "张三. 某研究. 2024年"]), 2024)

    def test_plain_year_still_found(self) -> None:
        self.assertEqual(year_from_row(["C1", "Smith et al. 2023."]), 2023)

    def test_year_glued_to_more_digits_is_ignored(self) -> None:
        self.assertIsNone(year_from_row(["C1", "identifier 20245 code"]))


class SharedUtilsTests(unittest.TestCase):
    def test_read_text_utf8(self) -> None:
        try:
            fd, name = tempfile.mkstemp(suffix=".txt")
            import os as _os
            _os.write(fd, b"Hello World")
            _os.close(fd)
            self.assertEqual(read_text(Path(name)), "Hello World")
        finally:
            Path(name).unlink(missing_ok=True)

    def test_strip_tex_comments(self) -> None:
        self.assertEqual(strip_tex_comments("text % comment\nmore"), "text \nmore")
        self.assertIn(r"\%", strip_tex_comments(r"a\%b % comment"))

    def test_normalize_tex_removes_commands(self) -> None:
        result = normalize_tex(r"\section{Intro}\cite{key} text")
        self.assertIn("Intro", result)
        self.assertIn("REF", result)
        self.assertIn("text", result)

    def test_normalize_markdown_removes_code(self) -> None:
        result = normalize_markdown("`code` and [link](url) and ![img](u)")
        self.assertNotIn("`", result)
        self.assertIn("link", result)
        self.assertNotIn("img", result)

    def test_split_paragraphs_filters_short(self) -> None:
        text = "Short\n\nA longer paragraph with enough words to pass the eight word minimum threshold"
        paras = split_paragraphs(text)
        self.assertEqual(len(paras), 1)

    def test_canonical_normalizes(self) -> None:
        result = canonical("Hello [World] 123!")
        self.assertIn("hello", result)
        self.assertIn("123", result)
        self.assertNotIn("[", result)

    def test_make_canon_creates_paragraph(self) -> None:
        cp = make_canon("Hello World test")
        self.assertIsInstance(cp, CanonParagraph)
        self.assertTrue(cp.tokens)

    def test_similarity_canon_identical(self) -> None:
        a = make_canon("The quick brown fox jumps over the lazy dog")
        b = make_canon("The quick brown fox jumps over the lazy dog")
        self.assertGreaterEqual(similarity_canon(a, b), 0.95)

    def test_similarity_canon_different(self) -> None:
        a = make_canon("The quick brown fox")
        b = make_canon("A completely different sentence here")
        self.assertLess(similarity_canon(a, b), 0.5)

    def test_similarity_canon_empty(self) -> None:
        self.assertEqual(similarity_canon(make_canon(""), make_canon("")), 0.0)

    def test_preview_truncates(self) -> None:
        self.assertEqual(preview("short"), "short")
        long_text = "x" * 200
        self.assertTrue(preview(long_text).endswith("..."))

    def test_split_table_line(self) -> None:
        cells = split_table_line("| a | b | c |")
        self.assertEqual(cells, ["a", "b", "c"])

    def test_is_separator_row_true(self) -> None:
        self.assertTrue(is_separator_row(["---", ":---:", "---"]))
        self.assertTrue(is_separator_row(["-", "--- "]))

    def test_is_separator_row_false(self) -> None:
        self.assertFalse(is_separator_row([]))
        self.assertFalse(is_separator_row(["data"]))

    def test_table_rows_single(self) -> None:
        text = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        header, rows = table_rows(text)
        self.assertEqual(header, ["A", "B"])
        self.assertEqual(len(rows), 2)

    def test_table_rows_empty(self) -> None:
        header, rows = table_rows("no table here")
        self.assertEqual(header, [])
        self.assertEqual(rows, [])

    def test_markdown_tables_multi(self) -> None:
        text = "| A |\n|---|\n| 1 |\n\ntext\n\n| B |\n|---|\n| 2 |"
        tables = markdown_tables(text)
        self.assertEqual(len(tables), 2)

    def test_year_from_row_with_year(self) -> None:
        self.assertEqual(year_from_row(["foo", "2024", "bar"]), 2024)

    def test_year_from_row_no_year(self) -> None:
        self.assertIsNone(year_from_row(["foo", "bar"]))

    def test_year_from_row_max(self) -> None:
        self.assertEqual(year_from_row(["2020", "2023"]), 2023)


if __name__ == "__main__":
    unittest.main()
