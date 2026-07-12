"""Tests for reviewer_audit_check.py (reviewer-aware audit gate)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "scripts" / "reviewer_audit_check.py"


VALUE_MAP = """## Reviewer Value Map

| Reviewer criterion | What reviewers want | Our evidence | Current weakness | Revision action |
|---|---|---|---|---|
| Novelty | Defensible delta vs closest prior work. | Sec. 1 bullets | Implied not stated | Add one delta sentence. |
| Significance | Evidence the gain matters. | Sec. 4 effect size | Asserted not quantified | Quantify the stakes. |
| Technical soundness | Correct, justified methods. | Sec. 3 derivation | One assumption undefended | Justify each assumption. |
| Evidence sufficiency | Enough ablations/baselines. | Tables 2-3 | Missing one baseline | Add the baseline. |
| Clarity | Readable in one pass. | Section flow | Claim split across sections | Consolidate the claim. |
| Venue fit | Matches the venue. | Target-venue analysis | Framing off-community | Reframe the intro. |
"""

OBJECTION = """## Reviewer Objection Register

| Likely objection | Where triggered | Severity | What the reviewer may say | Preemptive fix | Status |
|---|---|---|---|---|---|
| Contribution overlaps prior work | Sec. 1 | CRITICAL | "This is incremental." | Add delta sentence + Table 1 row. | OPEN |
| Missing baseline | Sec. 4 | MAJOR | "Why no comparison?" | Add the baseline or scope it out. | OPEN |
"""

EDITORIAL = """## Editorial Fit Map

- Venue fit: Targets venue Y; scope and methods match its typical papers.
- Editor-facing value: A serving-cost reduction an editor can defend to the board.
- Desk-reject risks: Length within limit (resolved); ethics section present (resolved).
"""


def _doc(*parts: str) -> str:
    return "# Reviewer Audit\n\n" + "\n".join(parts)


def _write_audit(text: str | None, encoding: str = "utf-8") -> Path:
    tmp = Path(tempfile.mkdtemp())
    if text is not None:
        (tmp / "reviewer_audit.md").write_bytes(text.encode(encoding))
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


class ReviewerAuditCheckTests(unittest.TestCase):
    def test_complete_audit_passes(self) -> None:
        out = _write_audit(_doc(VALUE_MAP, OBJECTION, EDITORIAL))
        res = _run(out)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Status: PASS", res.stdout)

    def test_missing_file_fails(self) -> None:
        out = _write_audit(None)
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("does not exist", res.stdout)

    def test_missing_editorial_section_fails(self) -> None:
        out = _write_audit(_doc(VALUE_MAP, OBJECTION))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Editorial Fit Map", res.stdout)

    def test_value_map_missing_criterion_fails(self) -> None:
        # Drop the "Venue fit" row -> only five of six criteria present.
        five_row_map = "\n".join(
            ln for ln in VALUE_MAP.splitlines() if not ln.startswith("| Venue fit")
        ) + "\n"
        out = _write_audit(_doc(five_row_map, OBJECTION, EDITORIAL))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("venue fit", res.stdout.lower())

    def test_label_only_value_map_fails(self) -> None:
        # Six criterion rows whose only content is the label -> no real scoring.
        label_only = (
            "## Reviewer Value Map\n\n"
            "| Reviewer criterion | What reviewers want | Our evidence | Current weakness | Revision action |\n"
            "|---|---|---|---|---|\n"
            "| Novelty |  |  |  |  |\n"
            "| Significance |  |  |  |  |\n"
            "| Technical soundness |  |  |  |  |\n"
            "| Evidence sufficiency |  |  |  |  |\n"
            "| Clarity |  |  |  |  |\n"
            "| Venue fit |  |  |  |  |\n"
        )
        out = _write_audit(_doc(label_only, OBJECTION, EDITORIAL))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("label-only", res.stdout.lower())

    def test_placeholder_objection_row_fails(self) -> None:
        # Severity/fix cells present but placeholder ('x' / '-') -> not a real row.
        bad_objection = (
            "## Reviewer Objection Register\n\n"
            "| Likely objection | Where triggered | Severity | Preemptive fix |\n"
            "|---|---|---|---|\n"
            "| Some objection | Sec. 1 | x | - |\n"
        )
        out = _write_audit(_doc(VALUE_MAP, bad_objection, EDITORIAL))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)

    def test_thin_editorial_fit_fails(self) -> None:
        thin_editorial = "## Editorial Fit Map\n\n- ok\n"
        out = _write_audit(_doc(VALUE_MAP, OBJECTION, thin_editorial))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)

    def test_gb18030_chinese_content_passes(self) -> None:
        # Regression: the checker read the artifact with errors="ignore" on utf-8,
        # so a GB18030-encoded audit lost its Chinese content bytes, emptied the
        # content cells, and failed. The shared read_text decodes GB18030.
        value_map_zh = (
            "## Reviewer Value Map\n\n"
            "| Reviewer criterion | What reviewers want | Our evidence | Current weakness | Revision action |\n"
            "|---|---|---|---|---|\n"
            "| Novelty | 相对最接近的先前工作应有可辩护的增量贡献 | 第一节要点给出了方法差异 | 差异被暗示但未明确陈述出来 | 增加一句明确的差异说明句子 |\n"
            "| Significance | 需要证据说明增益为何重要且有意义 | 第四节报告了效应量大小 | 断言了但没有量化其重要性 | 量化该工作的实际影响与价值 |\n"
            "| Technical soundness | 方法应当正确且每步都有充分论证 | 第三节给出了完整推导过程 | 有一个关键假设没有被辩护 | 逐一论证每个建模假设合理性 |\n"
            "| Evidence sufficiency | 应有足够的消融实验与基线比较 | 表二和表三提供了对照结果 | 缺少一个重要的基线方法比较 | 补充缺失的那个基线方法实验 |\n"
            "| Clarity | 论文应当能够在一次阅读中被读懂 | 章节流程整体比较清晰连贯 | 一个论点被拆分到多个章节中 | 把该论点合并到同一章节叙述 |\n"
            "| Venue fit | 论文框架应当匹配目标发表场所 | 做了针对目标期刊的分析比较 | 论文的框架偏离了目标读者群 | 重新构造引言以贴合社区旨趣 |\n"
        )
        objection_zh = (
            "## Reviewer Objection Register\n\n"
            "| Likely objection | Where triggered | Severity | Preemptive fix |\n"
            "|---|---|---|---|\n"
            "| 贡献与已有工作重叠度较高 | 第一节 | CRITICAL | 增加差异说明句并补充对照表格中的一行 |\n"
            "| 缺少一个必要的基线比较 | 第四节 | MAJOR | 补上该基线或明确说明其为何超出范围 |\n"
        )
        editorial_zh = (
            "## Editorial Fit Map\n\n"
            "- 场所匹配：目标期刊的范围与本文的方法学高度契合适配\n"
            "- 面向编辑的价值：一个编辑可以向委员会辩护的服务成本降低\n"
            "- 拒稿风险：篇幅在限制之内已解决，伦理章节也已经补充完整\n"
        )
        out = _write_audit(_doc(value_map_zh, objection_zh, editorial_zh), encoding="gb18030")
        res = _run(out)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Status: PASS", res.stdout)

    def test_objection_without_severity_and_fix_fails(self) -> None:
        # Objection register present but the row carries neither Severity nor fix.
        bad_objection = (
            "## Reviewer Objection Register\n\n"
            "| Likely objection | Where triggered | Severity | Preemptive fix |\n"
            "|---|---|---|---|\n"
            "| Some objection | Sec. 1 |  |  |\n"
        )
        out = _write_audit(_doc(VALUE_MAP, bad_objection, EDITORIAL))
        res = _run(out)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
