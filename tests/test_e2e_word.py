from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD_GUARD = ROOT / "src" / "scripts" / "word_guard.py"

MAIN_TEX = r"""\documentclass{article}
\title{A Lightweight Method for Document Conversion Fidelity}
\author{Jane Doe and John Smith}
\begin{document}
\maketitle
\begin{abstract}
We evaluate a lightweight method for document conversion fidelity. The pipeline
is reproducible, inexpensive to run, and produces faithful output across the
evaluated configurations.
\end{abstract}
\section{Introduction}
This report evaluates a lightweight method for document conversion fidelity.
Prior work \cite{devlin2019} established strong baselines for language
understanding, and we build on that foundation in a controlled setting with a
reproducible pipeline and a small, well-documented configuration.
\section{Results}
Our experiments show consistent improvements across the evaluated
configurations, with no regressions observed on the held-out set. The approach
remains simple to reproduce and inexpensive to run end to end.
\bibliographystyle{plain}
\bibliography{references}
\end{document}
"""

# Three authors, so author-date citeproc would render "(Devlin et al. 2019)" —
# a form word_guard.py rejects. Only the numeric CSL keeps it as "[1]".
REFERENCES_BIB = """@article{devlin2019,
  title={BERT: Pre-training of Deep Bidirectional Transformers},
  author={Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton},
  journal={NAACL},
  year={2019}
}
"""

# Mirrors the numeric CSL documented in references/latex.md.
NUMERIC_CSL = """<?xml version="1.0" encoding="utf-8"?>
<style xmlns="http://purl.org/net/xbiblio/csl" class="in-text" version="1.0" default-locale="en-US">
  <info><title>Numeric</title><id>paperspine-numeric</id><updated>2000-01-01T00:00:00+00:00</updated></info>
  <citation collapse="citation-number">
    <sort><key variable="citation-number"/></sort>
    <layout prefix="[" suffix="]" delimiter=",">
      <text variable="citation-number"/>
    </layout>
  </citation>
  <bibliography>
    <sort><key variable="citation-number"/></sort>
    <layout>
      <text variable="citation-number" prefix="[" suffix="] "/>
      <names variable="author" suffix=". "><name delimiter=", " and="text" initialize-with=". "/></names>
      <text variable="title" suffix=". "/>
      <text variable="container-title" suffix=", "/>
      <date variable="issued" suffix="."><date-part name="year"/></date>
    </layout>
  </bibliography>
</style>
"""


def _docx_body_text(docx: Path) -> str:
    xml = zipfile.ZipFile(docx).read("word/document.xml").decode("utf-8")
    return re.sub(r"<[^>]+>", "", xml)


@unittest.skipUnless(shutil.which("pandoc"), "pandoc not installed")
class WordEndToEndTests(unittest.TestCase):
    """End-to-end: LaTeX -> pandoc docx -> word_guard, exercising the real chain.

    The Word build in PaperSpine V4 always runs word_guard with --fix-fonts, which
    normalizes the docx to Times New Roman and black headings (pandoc's default
    theme uses Aptos / colored headings) before validating. This mirrors the real
    pipeline: pandoc produces the docx, then word_guard fixes-and-checks it.
    """

    def test_build_docx_from_latex_and_validate(self) -> None:
        # Regression: pandoc citeproc defaults to author-date, which word_guard
        # rejects; and a thebibliography block drops in-text \cite in the .docx.
        # This exercises the corrected chain (a .bib + a numeric CSL) and
        # asserts the .docx body actually shows a numeric [1] citation.
        with tempfile.TemporaryDirectory() as tmp:
            final_paper = Path(tmp) / "final_paper"
            final_paper.mkdir(parents=True)
            (final_paper / "main.tex").write_text(MAIN_TEX, encoding="utf-8")
            (final_paper / "references.bib").write_text(REFERENCES_BIB, encoding="utf-8")
            (final_paper / "numeric.csl").write_text(NUMERIC_CSL, encoding="utf-8")
            docx = final_paper / "paper.docx"

            pandoc = subprocess.run(
                [
                    "pandoc", "main.tex", "-o", "paper.docx",
                    "--from", "latex", "--to", "docx",
                    "--resource-path=.", "--number-sections",
                    "--citeproc", "--bibliography=references.bib",
                    "--csl=numeric.csl",
                ],
                cwd=final_paper, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(pandoc.returncode, 0, pandoc.stderr)
            self.assertTrue(docx.exists(), "pandoc did not produce paper.docx")
            self.assertGreater(docx.stat().st_size, 0)

            body = _docx_body_text(docx)
            # In-text citation must survive conversion and be numeric, not
            # author-year and not dropped entirely.
            self.assertIn("[1]", body, "numeric in-text citation [1] missing from docx body")
            self.assertNotRegex(
                body, r"\(Devlin et al\.?,? 2019\)",
                "citation rendered author-year instead of numeric",
            )

            guard = subprocess.run(
                [sys.executable, str(WORD_GUARD), str(docx),
                 "--fix-fonts", "--language", "en", "--markdown"],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
            self.assertIn("Status: PASS", guard.stdout)


if __name__ == "__main__":
    unittest.main()
