from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from larch.lint import lint_consecutive_bash
from larch.lint.lint_consecutive_bash import main


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def skill_doc(body: str) -> str:
    return body.strip() + "\n"


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_clean_single_bash_fence(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
echo one
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize(
    "gap",
    [
        "\n",
        "\n<!-- comment -->\n",
        "\nQuick status check.\n",
    ],
)
def test_adjacent_bash_fences_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str], gap: str) -> None:
    write(tmp_path / "skills/foo/SKILL.md", f"```bash\necho one\n```{gap}```bash\necho two\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md:1:" in err
    assert "fences at lines 1 and" in err


@pytest.mark.parametrize(
    "gap",
    [
        "\n## Next step\n",
        "\nThis paragraph is deliberately long enough to be a real Markdown step rather than a short breadcrumb between two prompt-side shell tool calls in the source.\n",
        "\n- Inspect the result before continuing.\n",
    ],
)
def test_substantive_markdown_between_fences_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], gap: str
) -> None:
    write(tmp_path / "skills/foo/SKILL.md", f"```bash\necho one\n```{gap}```bash\necho two\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


@pytest.mark.parametrize("info", ["sh", "shell", "text", ""])
def test_non_bash_fences_do_not_count(tmp_path: Path, capsys: pytest.CaptureFixture[str], info: str) -> None:
    write(tmp_path / "skills/foo/SKILL.md", f"```{info}\necho one\n```\n```bash\necho two\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_wrong_correct_example_pair_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
WRONG:
```bash
echo one
```
CORRECT:
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_wrong_correct_labels_only_in_gap_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
echo one
```
WRONG:
CORRECT:
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_example_word_in_preceding_prose_does_not_suppress(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The documented scope is explicit WRONG/CORRECT examples only. Ordinary
    # prose that happens to contain "example"/"correct"/"wrong" before two
    # adjacent bash fences must not silently exclude them from linting.
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
For example, run the following and confirm the output is correct.
```bash
echo one
```
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "consecutive bash tool-call fences" in err


def test_unclosed_opener_does_not_swallow_following_fences(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # An unclosed opener must not be treated as one fence extending to EOF;
    # doing so swallows later fences and hides real consecutive-bash violations.
    # Here the unindented opener never matches the indented closers, so under the
    # old "closed at EOF" behavior the two indented fences were hidden.
    write(
        tmp_path / "skills/foo/SKILL.md",
        "```bash\necho unterminated\n  ```bash\n  echo one\n  ```\n  ```bash\n  echo two\n  ```\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "consecutive bash tool-call fences" in err


def test_pause_resume_launcher_boundary_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/design/SKILL.md", skill_doc("""
```bash
python3 python/cli.py design driver --action pause --design-tmpdir "$DESIGN_TMPDIR"
```
Resume boundary.
```bash
python3 python/cli.py design driver --action resume --design-tmpdir "$DESIGN_TMPDIR"
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_foreground_recovery_probe_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/implement/SKILL.md", skill_doc("""
```bash
DESIGN_TMPDIR=/tmp/demo; test -f "$DESIGN_TMPDIR/.completed/step-3-terminal"
```
Then parse the sentinel.
```bash
cat "$DESIGN_TMPDIR/.completed/step-3-terminal"
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_task_notification_immediate_background_boundary_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path / "skills/implement/SKILL.md", skill_doc("""
```bash
run_in_background python3 python/cli.py review-and-fix step5
```
<task-notification> fires on completion.
```bash
python3 python/cli.py review-and-fix step5 --parse-result
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_indented_openers_detect_and_suppress(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", "   ```bash\necho one\n   ```\n   ```bash\necho two\n   ```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md:1:" in err
    write(
        tmp_path / "skills/foo/SKILL.md",
        "   ```bash\necho one # lint-consecutive-bash: ok fixture boundary\n   ```\n   ```bash\necho two\n   ```\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_trailing_pragma_on_single_line_launcher_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/implement/SKILL.md", skill_doc("""
```bash
python3 python/cli.py implement step2-dispatch # lint-consecutive-bash: ok intentional dispatch boundary
```
```bash
python3 python/cli.py implement step2-post-dispatch
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_standalone_suppression_as_only_body_line_does_not_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
# lint-consecutive-bash: ok not enough
```
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "consecutive bash tool-call fences" in err


def test_multiline_body_comment_suppression_requires_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
# lint-consecutive-bash: ok intentional boundary
echo one
```
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
# lint-consecutive-bash: ok
echo one
```
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "consecutive bash tool-call fences" in err


def test_trailing_suppression_requires_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", skill_doc("""
```bash
echo one # lint-consecutive-bash: ok
```
```bash
echo two
```
"""))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "consecutive bash tool-call fences" in err


def test_multiple_files_report_deterministically(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/b/SKILL.md", "```bash\necho b\n```\n```bash\necho b2\n```\n")
    write(tmp_path / "skills/a/SKILL.md", "```bash\necho a\n```\n```bash\necho a2\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert err.index("skills/a/SKILL.md") < err.index("skills/b/SKILL.md")


def test_non_utf8_input_returns_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "skills/foo/SKILL.md"
    path.parent.mkdir(parents=True)
    _ = path.write_bytes(b"\xff\xfe")
    rc, err = run(tmp_path, capsys)
    assert rc == 2
    assert "cannot read file" in err


def test_non_git_fixture_enumerates_scoped_patterns(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "skills/foo/SKILL.md", "```bash\necho one\n```\n```bash\necho two\n```\n")
    write(tmp_path / "skills/foo/references/ref.md", "```bash\necho one\n```\n```bash\necho two\n```\n")
    write(tmp_path / ".claude/skills/bar/SKILL.md", "```bash\necho one\n```\n```bash\necho two\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/foo/SKILL.md" in err
    assert "skills/foo/references/ref.md" in err
    assert ".claude/skills/bar/SKILL.md" in err


def test_out_of_scope_markdown_ignored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "docs/out.md", "```bash\necho one\n```\n```bash\necho two\n```\n")
    write(tmp_path / "skills/foo/notes.md", "```bash\necho one\n```\n```bash\necho two\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_git_os_error_raises_lint_error_and_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_git_rooted(root: Path) -> bool:
        return root == tmp_path

    def fake_run(_args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise FileNotFoundError("git: No such file or directory")

    monkeypatch.setattr(lint_consecutive_bash.lint_common, "git_rooted", fake_git_rooted)
    monkeypatch.setattr(lint_consecutive_bash.subprocess, "run", fake_run)
    write(tmp_path / "skills/foo/SKILL.md", "```bash\necho one\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 2
    assert "cannot enumerate markdown files" in err


def test_git_enumeration_uses_all_pathspecs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_git_rooted(root: Path) -> bool:
        return root == tmp_path

    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is True
        stdout = b"skills/foo/SKILL.md\0skills/foo/references/ref.md\0.claude/skills/bar/SKILL.md\0"
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(lint_consecutive_bash.lint_common, "git_rooted", fake_git_rooted)
    monkeypatch.setattr(lint_consecutive_bash.subprocess, "run", fake_run)
    write(tmp_path / "skills/foo/SKILL.md", "```bash\necho one\n```\n")
    write(tmp_path / "skills/foo/references/ref.md", "```bash\necho one\n```\n")
    write(tmp_path / ".claude/skills/bar/SKILL.md", "```bash\necho one\n```\n")
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err
    assert calls == [
        [
            lint_consecutive_bash.GIT,
            "-C",
            str(tmp_path),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            "skills/*/SKILL.md",
            "skills/*/references/*.md",
            ".claude/skills/*/SKILL.md",
        ]
    ]
