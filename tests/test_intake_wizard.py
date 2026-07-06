from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def isolated_env(output_dir: Path) -> dict[str, str]:
    """Env that never reads the developer's real ~/.paperspine/config.json.

    Without PAPERSPINE_CONFIG_HOME the wizard falls back to Path.home(), so a
    real global config with ui_language 'zh' would flip the default UI away
    from the 'en' these tests assert. Pin it to an isolated dir under the temp
    output so the deterministic default (en) is used.
    """
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PAPERSPINE_CONFIG_HOME"] = str(output_dir / ".paperspine_home")
    return env


def run_wizard(stdin: str, output_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "src/scripts/intake_wizard.py", "--output-dir", str(output_dir)],
        cwd=ROOT,
        env=isolated_env(output_dir),
        text=True,
        encoding="utf-8",
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class IntakeWizardTests(unittest.TestCase):
    def test_no_interactive_uses_flags_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--no-interactive",
                    "--workflow",
                    "build_from_materials",
                    "--scene",
                    "report_review",
                    "--tier",
                    "pro",
                    "--target-name",
                    "Course Report",
                    "--materials-dir",
                    "materials",
                    "--official-url",
                    "https://example.org/rubric",
                    "--reference-mode",
                    "specified_paths",
                    "--reference-path",
                    "local_refs",
                    "--citation-target-count",
                    "24",
                    "--special-requirement",
                    "Keep figures",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env=isolated_env(output_dir),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            data = json.loads((output_dir / "paper_spine_config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["workflow"], "build_from_materials")
            self.assertEqual(data["scene"], "report_review")
            self.assertEqual(data["tier"], "pro")
            self.assertEqual(data["output_language"], "en")
            self.assertEqual(data["target_name"], "Course Report")
            self.assertEqual(data["materials_dir"], "materials")
            self.assertEqual(data["official_urls"], ["https://example.org/rubric"])
            self.assertEqual(data["reference_mode"], "specified_paths")
            self.assertEqual(data["reference_paths"], ["local_refs"])
            self.assertEqual(data["citation_target_count"], 24)
            self.assertEqual(data["special_requirements"], ["Keep figures"])
            # V4: --word-output defaults to "docx" (Word deliverable on by default);
            # only an explicit choice of "none" (interactive option 1 or --word-output none)
            # disables it.
            self.assertEqual(data["word_output"], "docx")
            self.assertEqual(data["translation_package"], "none")

    def test_flash_journal_english_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_wizard(
                "\n".join(
                    [
                        "1",
                        "1",
                        "1",
                        "1",
                        "1",
                        "1",
                        "Target Journal",
                        "draft.tex",
                        "A clear motivation",
                        "https://example.org/guidelines",
                        "1",
                        ".",
                        "20",
                        "Keep claims evidence-bound",
                        "",
                    ]
                ),
                output_dir,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            data = json.loads((output_dir / "paper_spine_config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["workflow"], "rewrite_existing")
            self.assertEqual(data["scene"], "journal")
            self.assertEqual(data["tier"], "flash")
            self.assertEqual(data["output_language"], "en")
            self.assertEqual(data["draft_path"], "draft.tex")
            self.assertEqual(data["official_urls"], ["https://example.org/guidelines"])
            self.assertEqual(data["reference_mode"], "local_first")
            self.assertEqual(data["reference_paths"], ["."])
            self.assertEqual(data["citation_target_count"], 20)
            self.assertEqual(data["word_output"], "none")
            self.assertEqual(data["translation_package"], "none")

    def test_pro_competition_chinese_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_wizard(
                "\n".join(
                    [
                        "2",
                        "4",
                        "2",
                        "2",
                        "1",
                        "Target Competition",
                        "materials",
                        "A contest motivation",
                        "https://example.org/rules",
                        "1",
                        ".",
                        "20",
                        "Use Chinese; keep figures",
                        "",
                    ]
                ),
                output_dir,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            data = json.loads((output_dir / "paper_spine_config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["workflow"], "build_from_materials")
            self.assertEqual(data["scene"], "competition")
            self.assertEqual(data["tier"], "pro")
            self.assertEqual(data["output_language"], "zh")
            self.assertEqual(data["materials_dir"], "materials")
            self.assertIn("Use Chinese", data["special_requirements"])
            self.assertIn("keep figures", data["special_requirements"])
            self.assertEqual(data["word_output"], "none")
            self.assertEqual(data["translation_package"], "none")

    def test_english_can_request_word_and_translation_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--no-interactive",
                    "--workflow",
                    "rewrite_existing",
                    "--scene",
                    "journal",
                    "--tier",
                    "flash",
                    "--output-language",
                    "en",
                    "--word-output",
                    "docx",
                    "--translation-package",
                    "zh",
                    "--reference-path",
                    "references",
                    "--citation-target-count",
                    "30",
                    "--draft-path",
                    "paper.tex",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env={**os.environ, "PYTHONUTF8": "1"},
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            data = json.loads((output_dir / "paper_spine_config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["word_output"], "docx")
            self.assertEqual(data["translation_package"], "zh")
            self.assertEqual(data["reference_paths"], ["references"])
            self.assertEqual(data["citation_target_count"], 30)

    def test_interactive_wizard_displays_menu_review_and_edit_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_wizard(
                "\n".join(
                    [
                        "1",
                        "1",
                        "1",
                        "1",
                        "1",
                        "2",
                        "Target Journal",
                        "draft.tex",
                        "A clear motivation",
                        "https://example.org/guidelines",
                        "1",
                        ".",
                        "20",
                        "Keep claims evidence-bound",
                        "",
                    ]
                ),
                output_dir,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("PaperSpine", result.stdout)
            self.assertIn("Welcome back!", result.stdout)
            # English is the default UI language.
            self.assertIn("Learn the target scene", result.stdout)
            self.assertIn("Workflow", result.stdout)
            self.assertIn("Review configuration", result.stdout)
            self.assertIn("translation_package: zh", result.stdout)
            data = json.loads((output_dir / "paper_spine_config.json").read_text(encoding="utf-8"))
            self.assertEqual(data["translation_package"], "zh")

    def test_setup_global_writes_ui_language_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            config_home = Path(tmp) / "global"
            env = os.environ.copy()
            env["PAPERSPINE_CONFIG_HOME"] = str(config_home)
            env["PYTHONUTF8"] = "1"
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--setup-global",
                    "--no-interactive",
                    "--ui-language",
                    "en",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            saved = json.loads((config_home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["ui_language"], "en")

    def test_keyboard_frame_preview_is_clean_and_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--preview-keyboard-frame",
                    "--preview-width",
                    "118",
                    "--workflow",
                    "build_from_materials",
                    "--scene",
                    "competition",
                    "--tier",
                    "pro",
                ],
                cwd=ROOT,
                env=isolated_env(Path(tmp)),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("PaperSpine", result.stdout)
        # English is the default UI language.
        self.assertIn("Configuration Wizard", result.stdout)
        self.assertIn("Workflow", result.stdout)
        self.assertIn("Current value", result.stdout)
        self.assertIn("Use Up/Down for fields", result.stdout)

    def test_chinese_ui_renders_when_opted_in(self) -> None:
        # Chinese is no longer the default but must still work when explicitly
        # requested via --ui-language zh (or a saved global config).
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--preview-keyboard-frame",
                    "--preview-width", "118",
                    "--ui-language", "zh",
                    "--workflow", "build_from_materials",
                    "--scene", "competition",
                    "--tier", "pro",
                ],
                cwd=ROOT,
                env=isolated_env(Path(tmp)),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("配置向导", result.stdout)
        self.assertIn("工作流", result.stdout)
        self.assertIn("当前值", result.stdout)
        self.assertIn("上下切换字段", result.stdout)
        # No mojibake in the Chinese frame.
        self.assertNotIn("锟", result.stdout)
        self.assertNotIn("鐩", result.stdout)

    def test_preview_frame_has_no_raw_ansi_escapes(self) -> None:
        # color=False preview must not leak escape codes (legacy-console safety).
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/intake_wizard.py",
                    "--preview-keyboard-frame",
                    "--preview-width",
                    "118",
                    "--workflow",
                    "build_from_materials",
                    "--scene",
                    "competition",
                    "--tier",
                    "pro",
                ],
                cwd=ROOT,
                env=isolated_env(Path(tmp)),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertNotIn("\x1b[", result.stdout)


class ConsoleSetupTests(unittest.TestCase):
    def _import(self):
        sys.path.insert(0, str(ROOT / "src" / "scripts"))
        import intake_wizard  # noqa: PLC0415

        return intake_wizard

    def test_configure_console_never_raises(self) -> None:
        wizard = self._import()
        # No-op on non-Windows / non-tty; must not raise on any platform.
        wizard.configure_windows_console()
        self.assertTrue(hasattr(wizard, "_enable_windows_vt"))

    def test_ansi_respects_disabled_flag(self) -> None:
        wizard = self._import()
        original = wizard._ANSI_ENABLED
        try:
            wizard._ANSI_ENABLED = False
            self.assertEqual(wizard.ansi("hi", "31"), "hi")
        finally:
            wizard._ANSI_ENABLED = original

    def test_read_key_unix_decodes_arrow_without_crashing(self) -> None:
        # Regression: the POSIX key reader indexed attrs[5] (ospeed, an int)
        # instead of attrs[6] (the cc list) when arming a non-blocking read
        # for the ESC sequence, so every arrow/ESC key raised TypeError and
        # crashed the wizard. Inject fake termios/tty so the path runs on any
        # platform, feeding the "up arrow" sequence ESC [ A.
        import types

        wizard = self._import()

        fake_termios = types.ModuleType("termios")
        fake_termios.TCSANOW = 0
        fake_termios.VMIN = 6
        fake_termios.VTIME = 5
        # tcgetattr returns [iflag, oflag, cflag, lflag, ispeed, ospeed, cc];
        # index 5 (ospeed) is an int, index 6 (cc) is a mutable list.
        fake_termios.tcgetattr = lambda fd: [0, 0, 0, 0, 9600, 9600, [0] * 32]
        fake_termios.tcsetattr = lambda fd, when, attrs: None
        fake_tty = types.ModuleType("tty")
        fake_tty.setraw = lambda fd: None

        chars = iter("\x1b[A")

        class _FakeStdin:
            def fileno(self) -> int:
                return 0

            def read(self, n: int) -> str:
                return next(chars, "")

        old_modules = {k: sys.modules.get(k) for k in ("termios", "tty")}
        old_stdin = wizard.sys.stdin
        sys.modules["termios"] = fake_termios
        sys.modules["tty"] = fake_tty
        wizard.sys.stdin = _FakeStdin()
        try:
            self.assertEqual(wizard._read_key_unix(), "up")
        finally:
            wizard.sys.stdin = old_stdin
            for k, v in old_modules.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v


if __name__ == "__main__":
    unittest.main()
