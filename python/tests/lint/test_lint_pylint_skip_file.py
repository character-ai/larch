"""Coverage for the pylint skip-file / module-level R0801 gate."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest
from larch.lint import lint_pylint_skip_file as lint
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    SYNTAX_FAIL_MESSAGE,
    Finding,
    SourceFile,
    run_rule,
)
from tests.lint.test_lint_engine import (
    RecordingRunner,
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
    _write_files,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
)


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _baseline_row(
    path: str,
    *,
    line: int = 1,
    message: str = lint.SKIP_FILE_MESSAGE,
    reason: str = "deferred module debt",
) -> dict[str, object]:
    return {
        "path": path,
        "line": line,
        "rule_id": lint.RULE_ID,
        "message": message,
        "reason": reason,
    }


def _invoke_skip_file(
    root: Path,
    runner: RecordingRunner,
    *,
    paths: list[str] | None = None,
    baseline_path: str | Path | None = None,
    write_baseline: bool = False,
    initial_reason: str | None = None,
    strict_stale: bool = False,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(
            lint.RULE,
            root,
            runner,
            paths=paths,
            baseline_path=baseline_path,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=strict_stale,
        )
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize(
    "text",
    [
        "# pylint: skip-file\n",
        "# pylint:  skip-file\n",
        "#pylint: skip-file\n",
        "# pylint: skip-file  # deferred\n",
        "# pylint: skip-file; deferred module debt\n",
        '"""doc"""\n# pylint: skip-file\n',
    ],
)
def test_detect_skip_file_variants(text: str) -> None:
    findings = lint.detect(_source("python/larch/mod.py", text))
    assert len(findings) == 1
    assert findings[0].message == lint.SKIP_FILE_MESSAGE
    assert findings[0].rule_id == lint.RULE_ID


@pytest.mark.parametrize(
    "text",
    [
        "# pylint: disable=R0801\n",
        "# pylint: disable=duplicate-code\n",
        "# pylint: disable = R0801,unused-import\n",
        "# pylint: disable R0801\n",
        "# pylint: disable duplicate-code, too-many-lines\n",
        "# pylint: disable=R0801; deferred duplicate-code debt\n",
        "# pylint: disable=unused-import, R0801; reason=keep scanning\n",
        "# pylint: disable=duplicate-code # trailing hash reason\n",
    ],
)
def test_detect_module_level_duplicate_code_disables(text: str) -> None:
    findings = lint.detect(_source("python/larch/mod.py", text))
    assert len(findings) == 1
    assert findings[0].message == lint.DUPLICATE_CODE_MESSAGE


def test_detect_ignores_strings_docstrings_unrelated_and_local() -> None:
    text = (
        'DOC = """# pylint: skip-file"""\n'
        'MSG = "# pylint: disable=R0801"\n'
        "# pylint: disable=unused-import\n"
        "# pylint: disable-next=R0801\n"
        "def run() -> None:\n"
        "    # pylint: disable=R0801\n"
        "    # pylint: skip-file\n"
        "    return None\n"
    )
    findings = lint.detect(_source("python/larch/mod.py", text))
    # Indented skip-file is still a skip-file directive (banned wherever it appears
    # as a comment). Indented disable=R0801 is ignored as local.
    assert [f.message for f in findings] == [lint.SKIP_FILE_MESSAGE]
    assert findings[0].line == 7


def test_detect_ignores_paths_outside_python_larch() -> None:
    text = "# pylint: skip-file\n"
    assert not lint.detect(_source("python/tests/mod.py", text))
    assert not lint.detect(_source("python/other.py", text))
    assert not lint.detect(_source("README.md", text))


def test_run_rule_new_finding_exits_one(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "# pylint: skip-file\nx = 1\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel, f"python/{lint.BASELINE_FILENAME}"]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == f"{rel}:1: {lint.RULE_ID} {lint.SKIP_FILE_MESSAGE}\n"


def test_run_rule_baselined_finding_exits_zero(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "# pylint: skip-file\nx = 1\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps([_baseline_row(rel)], indent=2) + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def test_run_rule_stale_row_exits_two(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "x = 1\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps([_baseline_row(rel)], indent=2) + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "stale baseline row" in err


def test_run_rule_invalid_baseline_exits_two(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "# pylint: skip-file\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps(
            [
                {
                    "path": rel,
                    "line": 1,
                    "rule_id": lint.RULE_ID,
                    "message": lint.SKIP_FILE_MESSAGE,
                    "reason": "",
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "invalid reason" in err


def test_run_rule_malformed_python_fail_closed_exit_one(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "def broken(\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == f"{rel}:1: {lint.RULE_ID} {SYNTAX_FAIL_MESSAGE}\n"


def test_run_rule_unreadable_tracked_file_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "# pylint: skip-file\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")

    def fail_open(*_args: object, **_kwargs: object) -> int:
        raise OSError("read denied")

    monkeypatch.setattr("larch.lint.engine.os.open", fail_open)
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to read" in err


def test_run_rule_cannot_bypass_with_inline_pragma(tmp_path: Path) -> None:
    rel = "python/larch/mod.py"
    text = f"# pylint: skip-file  # {lint.SUPPRESSION_TOKEN}: ok deliberate\n"
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == f"{rel}:1: {lint.RULE_ID} {lint.SKIP_FILE_MESSAGE}\n"


def test_write_preserves_reasons_and_refuses_new_without_reason(tmp_path: Path) -> None:
    kept = "python/larch/kept.py"
    novel = "python/larch/novel.py"
    _write_files(
        tmp_path,
        {
            kept: "# pylint: skip-file\n",
            novel: "# pylint: skip-file\n",
        },
    )
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps(
            [_baseline_row(kept, reason="preserve-me")],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [kept, novel]),
        baseline_path=baseline,
        write_baseline=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "initial_reason" in err

    code2, out2, err2 = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [kept, novel]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="bootstrap novel debt",
    )
    assert code2 == EXIT_CLEAN
    assert out2 == ""
    assert err2 == ""
    rows = json.loads(baseline.read_text(encoding="utf-8"))
    by_path = {row["path"]: row for row in rows}
    assert by_path[kept]["reason"] == "preserve-me"
    assert by_path[novel]["reason"] == "bootstrap novel debt"


def test_paths_outside_scope_are_excluded_even_when_tracked(tmp_path: Path) -> None:
    outside = "python/tests/mod.py"
    inside = "python/larch/mod.py"
    _write_files(
        tmp_path,
        {
            outside: "# pylint: skip-file\n",
            inside: "x = 1\n",
        },
    )
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, out, err = _invoke_skip_file(
        tmp_path,
        _git_ok_runner(tmp_path, [outside, inside]),
        paths=["python/larch"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def test_main_check_and_invalid_initial_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rel = "python/larch/mod.py"
    _write_files(tmp_path, {rel: "# pylint: skip-file\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps([_baseline_row(rel)], indent=2) + "\n",
        encoding="utf-8",
    )

    runner = _git_ok_runner(tmp_path, [rel])
    monkeypatch.setattr(lint.proc, "ProcRunner", lambda: runner)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = lint.main(["--root", str(tmp_path)])
    assert code == EXIT_CLEAN
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code2 = lint.main(["--root", str(tmp_path), "--write", "--initial-reason", "  "])
    assert code2 == EXIT_ERROR
    assert "initial-reason must be non-empty" in stderr.getvalue()


def test_finding_text_and_identity_are_stable() -> None:
    finding = Finding(
        path="python/larch/mod.py",
        line=3,
        rule_id=lint.RULE_ID,
        message=lint.SKIP_FILE_MESSAGE,
    )
    assert finding.rule_id == "pylint-skip-file"
    assert finding.message == "banned pylint skip-file directive"
    assert lint.DUPLICATE_CODE_MESSAGE == (
        "banned module-level pylint disable of duplicate-code"
    )


def test_detect_disable_next_and_indented_disable_ignored() -> None:
    text = (
        "# pylint: disable-next=R0801\n"
        "x = 1\n"
        "def f() -> None:\n"
        "    # pylint: disable=duplicate-code\n"
        "    return None\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))
