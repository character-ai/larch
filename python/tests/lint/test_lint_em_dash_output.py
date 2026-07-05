from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint.lint_em_dash_output import main

if TYPE_CHECKING:
    import pytest


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_clean_python_output_string(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/larch/example.py", 'print("plain status")\n')

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_python_print_em_dash_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/larch/example.py", 'print("bad — text")\n')

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:1: em dash in Python output literal" in err


def test_python_f_string_literal_part_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/larch/example.py", 'name = "x"\nprint(f"bad — {name}")\n')

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:2: em dash in Python output literal" in err


def test_non_output_python_string_is_ignored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/larch/example.py", 'value = "not emitted — ignored"\n')

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_logging_util_output_sinks_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'from larch.core import logging_util\n'
        'logging_util.emit("bad — text")\n'
        'logging_util.diagnostic("bad — diag")\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:2: em dash in Python output literal" in err
    assert "python/larch/example.py:3: em dash in Python output literal" in err


def test_imported_logging_util_output_sinks_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'from larch.core.logging_util import BreadcrumbWriter, diagnostic, emit, emit_kv\n'
        'emit("bad — text")\n'
        'emit_kv(key="KEY", value="bad — value")\n'
        'diagnostic("bad — diag")\n'
        'BreadcrumbWriter().emit("bad — writer")\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:2: em dash in Python output literal" in err
    assert "python/larch/example.py:3: em dash in Python output literal" in err
    assert "python/larch/example.py:4: em dash in Python output literal" in err
    assert "python/larch/example.py:5: em dash in Python output literal" in err


def test_err_sink_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "python/larch/example.py", '_err("bad — text")\n')

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:1: em dash in Python output literal" in err


def test_local_helper_sink_names_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'emit("bad — text")\n'
        '_plain_diagnostic("bad — diag")\n'
        '_emit_kv(key="KEY", value="bad — value")\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:1: em dash in Python output literal" in err
    assert "python/larch/example.py:2: em dash in Python output literal" in err
    assert "python/larch/example.py:3: em dash in Python output literal" in err


def test_breadcrumb_writer_emit_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'from larch.core import logging_util\nlogging_util.BreadcrumbWriter().emit("bad — text")\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:2: em dash in Python output literal" in err


def test_skill_markdown_print_literal_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/example/SKILL.md", "Print: `bad — text`\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:1: em dash in markdown print literal" in err


def test_inline_print_template_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/example/SKILL.md", "If skipped, print `⏩ step — skipped`.\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:1: em dash in markdown print literal" in err


def test_line_leading_status_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "skills/example/SKILL.md", "⏩ step — skipped\n")

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/SKILL.md:1: em dash in markdown status line" in err


def test_quoted_prose_and_fenced_content_are_ignored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "skills/example/SKILL.md",
        "> quoted prose — not output\n"
        "> Print: `quoted — template`\n"
        "```\n"
        "print `⏩ fixture — ignored`\n"
        "⏩ fixture — ignored\n"
        "```\n",
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_breadcrumb_writer_alias_emit_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'from larch.core import logging_util\n'
        'worker = logging_util.BreadcrumbWriter()\n'
        'alias = worker\n'
        'alias.emit("bad — text")\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:4: em dash in Python output literal" in err


def test_suppression_requires_non_empty_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "python/larch/example.py",
        'print("allowed — fixture")  # lint-em-dash-output: ok quoted legacy output\n'
        'print("bad — fixture")  # lint-em-dash-output: ok\n',
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "python/larch/example.py:2: suppression requires a non-empty reason" in err
    assert "python/larch/example.py:2: em dash in Python output literal" in err
