from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_skill_awk_field_refs import main

if TYPE_CHECKING:
    import pytest


def write_skill(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_fails_inline_awk_key_value_fixture(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        "```bash\nvalue=$(printf '%s\\n' \"$out\" | awk -F= '$1==\"KEY\"{print $2}')\n```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:2: bare awk $<digit> field reference" in err


def test_fails_record_reference(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/example/SKILL.md", "```bash\nawk 'index($0, \"KEY=\")==1{print}' file\n```\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md" in err


def test_awk_f_file_source_does_not_treat_positional_files_as_program(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        """```bash
awk -f filter.awk "$1"
```
""",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_multiline_awk_program_is_buffered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        """```bash
awk '
  $1 == "KEY" &&
  $2 == "VALUE" { print }
' file
```
""",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:2: bare awk $<digit> field reference" in err


def test_shell_positional_parameters_are_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        '```bash\ncase "$1" in\n  --repo) REPO="$2" ;;\nesac\n```\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_bootstrap_exception_is_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/implement/SKILL.md",
        "```bash\nCLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p=\"LARCH_CLAUDE_PLUGIN_ROOT=\"} index($0,p)==1{print substr($0,length(p)+1); exit}' \"$IMPLEMENT_TMPDIR/session-env.sh\" 2>/dev/null || true)\n```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_justified_suppression_is_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        "```bash\nawk '$1 == \"KEY\" {print $2}' file # lint-skill-awk-field-ref: ok fixture covers waiver\n```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_empty_suppression_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        "```bash\nawk '$1 == \"KEY\" {print $2}' file # lint-skill-awk-field-ref: ok\n```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "suppression requires a justification" in err


def test_claude_skill_tree_is_scanned(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, ".claude/skills/release/SKILL.md", "```bash\nawk '$1 == \"KEY\" {print $2}' file\n```\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert ".claude/skills/release/SKILL.md" in err


def test_docs_and_reference_files_are_skipped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "docs/SKILL.md", "```bash\nawk '$1 == \"KEY\" {print $2}' file\n```\n")
    write_skill(tmp_path, "skills/example/references/note.md", "```bash\nawk '$1 == \"KEY\" {print $2}' file\n```\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_wrapped_awk_command_is_normalized(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/example/SKILL.md",
        "```bash\nawk -F= \\\n  '$1 == \"KEY\" {print $2}' file\n```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:2: bare awk $<digit> field reference" in err
