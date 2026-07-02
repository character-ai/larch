# pyright: reportUnusedCallResult=false
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_bg_wait_coverage import main

if TYPE_CHECKING:
    import pytest


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_accepts_current_design_and_implement_background_patterns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/design/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**
```bash
"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh
```
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**
```bash
"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-final-summary.sh --outcome "$SUMMARY_OUTCOME"
```
""",
    )
    write(
        tmp_path / "skills/implement/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 15600000`.**
```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4
```
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**
```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-5-review.sh
```
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 21600000`.**
```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-ship.sh
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_rejects_review_background_launch_without_marker_mapping(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/review/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1000`.**
```bash
python3 python/cli.py review core --mode future-background
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/review/SKILL.md:1:" in err
    assert "no bg-wait marker mapping" in err


def test_rejects_unknown_implement_background_launch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/implement/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1000`.**
```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement future-background
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "future-background" in err


def test_accepts_direct_checks_step5_resume(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/implement/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 32700000`.**
```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_accepts_step4_tail_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/design/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 900000`.**
```bash
"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3b-tail.sh
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_rejects_unknown_launch_with_placeholders(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/design/SKILL.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1260000`.**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent launch-review --tool <resolved> --output "$DESIGN_TMPDIR/future-output.txt" --timeout 1200 --timing-task-kind <resolved>-future --prompt "<LANE_PROMPT>"
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "future-output.txt" in err
    assert "no bg-wait marker mapping" in err


def test_accepts_brainstorm_external_launches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/design/references/brainstorm.md",
        """
**Framing** (when the registry-selected tool is external and available):

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1260000`.**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent launch-review --tool <resolved> --output "$DESIGN_TMPDIR/cursor-brainstorm-output.txt" --stderr-sink "$DESIGN_TMPDIR/cursor-brainstorm-launch.failure.log" --timeout 1200 --timing-task-kind <resolved>-brainstorm --prompt "<BRAINSTORM_FRAMING_ASSEMBLED_PROMPT>"
```

**Scope** (when the registry-selected tool is external and available):

**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1260000`.**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent launch-review --tool <resolved> --output "$DESIGN_TMPDIR/codex-brainstorm-output.txt" --stderr-sink "$DESIGN_TMPDIR/codex-brainstorm-launch.failure.log" --timeout 1200 --timing-task-kind <resolved>-brainstorm --prompt "<BRAINSTORM_SCOPE_ASSEMBLED_PROMPT>"
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_ignores_research_background_launches_outside_scope(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path / "skills/research/references/research-phase.md",
        """
**⚠ Immediate-background required — set `run_in_background: true` and `timeout: 1260000`.**
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent launch-review --tool <resolved> --output "$RESEARCH_TMPDIR/future-output.txt" --timeout 1200 --timing-task-kind <resolved>-future --prompt "<LANE_PROMPT>"
```
""",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
