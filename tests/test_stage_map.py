"""Drift guard: keep SKILL.md's stage map consistent with progress_check.py.

The PaperSpine pipeline is described in prose (SKILL.md), in a stage map
(orchestrator-branch-map.md), and executably (progress_check.py STAGES). These
tests tie the prose to the executable source of truth so the three cannot
silently diverge again (Translation/Submission order, dead gate names, dead
playbook links, renumbering slips).
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = ROOT / "src" / "skill" / "SKILL.md"
REFERENCES = ROOT / "src" / "skill" / "references"

STAGE_HEADER = re.compile(r"^###\s+Stage\s+(\d+)\s*[—–-]\s*(.+?)\s*$", re.MULTILINE)
GATE_TOKEN = re.compile(r"--gate\s+([a-z_]+)")
REF_LINK = re.compile(r"references/([a-z0-9-]+)\.md")


def _load_progress_check():
    sys.path.insert(0, str(ROOT / "src" / "scripts"))
    try:
        import progress_check
    finally:
        sys.path.remove(str(ROOT / "src" / "scripts"))
    return progress_check


class StageMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.progress_check = _load_progress_check()
        cls.skill_text = SKILL_MD.read_text(encoding="utf-8")
        cls.headers = [
            (int(num), title) for num, title in STAGE_HEADER.findall(cls.skill_text)
        ]
        cls.stage_keys = [s.key for s in cls.progress_check.STAGES]

    def _stage_number(self, needle: str) -> int:
        matches = [num for num, title in self.headers if needle.lower() in title.lower()]
        self.assertEqual(
            len(matches), 1, f"expected exactly one '{needle}' stage, got {matches}"
        )
        return matches[0]

    def test_translation_before_submission_matches_gate_order(self) -> None:
        # The canonical order comes from the executable gate list: whatever order
        # translation/submission appear in STAGES is the order SKILL.md must use.
        keys = self.stage_keys
        self.assertLess(
            keys.index("translation"),
            keys.index("submission"),
            "progress_check STAGES should order translation before submission",
        )
        self.assertLess(
            self._stage_number("Translation"),
            self._stage_number("Submission"),
            "SKILL.md must number Translation before Submission to match STAGES",
        )

    def test_stage_numbers_are_contiguous(self) -> None:
        numbers = sorted(num for num, _ in self.headers)
        self.assertTrue(numbers, "SKILL.md has no '### Stage N' headers")
        self.assertEqual(
            numbers,
            list(range(1, len(numbers) + 1)),
            f"SKILL.md stage numbers must be 1..N with no gaps/dupes, got {numbers}",
        )

    def test_every_gate_in_skill_is_a_real_stage_key(self) -> None:
        valid = set(self.stage_keys)
        used = set(GATE_TOKEN.findall(self.skill_text))
        self.assertTrue(used, "no --gate tokens found in SKILL.md")
        unknown = sorted(used - valid)
        self.assertEqual(unknown, [], f"SKILL.md invokes unknown gates: {unknown}")

    def test_every_reference_link_in_skill_exists(self) -> None:
        linked = sorted(set(REF_LINK.findall(self.skill_text)))
        missing = [name for name in linked if not (REFERENCES / f"{name}.md").exists()]
        self.assertEqual(missing, [], f"SKILL.md links missing playbooks: {missing}")

    def test_stage_playbook_values_resolve_to_files(self) -> None:
        missing = []
        for key, value in self.progress_check.STAGE_PLAYBOOK.items():
            if value is None:
                continue
            if not (REFERENCES / f"{value}.md").exists():
                missing.append((key, value))
        self.assertEqual(
            missing, [], f"STAGE_PLAYBOOK points to missing playbooks: {missing}"
        )


class ReferenceReachabilityTests(unittest.TestCase):
    """Every playbook and agent card must be reachable from SKILL.md.

    PR#4 wired or pruned ~19 orphaned reference files; this guard keeps new
    playbooks from silently joining the skill without a `references/<name>.md`
    link path from the orchestrator (and agent cards without an `agents/<name>`
    mention in a reachable playbook).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL_MD.read_text(encoding="utf-8")

    def test_every_reference_playbook_is_reachable_from_skill(self) -> None:
        all_refs = {p.stem for p in REFERENCES.glob("*.md")}
        seen: set[str] = set()
        frontier = set(REF_LINK.findall(self.skill_text))
        while frontier:
            name = frontier.pop()
            if name in seen or name not in all_refs:
                continue
            seen.add(name)
            text = (REFERENCES / f"{name}.md").read_text(encoding="utf-8")
            frontier |= set(REF_LINK.findall(text)) - seen
        orphans = sorted(all_refs - seen)
        self.assertEqual(
            orphans,
            [],
            "reference playbooks with no references/<name>.md link path from "
            f"SKILL.md — wire them in or delete them: {orphans}",
        )

    def test_every_agent_card_is_referenced_from_a_playbook(self) -> None:
        agents_dir = ROOT / "src" / "skill" / "agents"
        cards = sorted(p.name for p in agents_dir.glob("*.md"))
        self.assertTrue(cards, "no agent role cards found")
        corpus = self.skill_text + "\n".join(
            p.read_text(encoding="utf-8") for p in REFERENCES.glob("*.md")
        )
        unreferenced = [c for c in cards if f"agents/{c}" not in corpus]
        self.assertEqual(
            unreferenced,
            [],
            "agent role cards never mentioned (as agents/<name>) by SKILL.md "
            f"or any playbook: {unreferenced}",
        )


if __name__ == "__main__":
    unittest.main()
