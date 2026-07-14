"""Offline coverage for the shared scan-only lint engine."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from larch.lint import engine as lint_engine

from larch.core.proc import CommandResult
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    SYNTAX_FAIL_MESSAGE,
    Finding,
    LintRule,
    SourceFile,
    render_finding,
    run_rule,
)


def _empty_responses() -> list[CommandResult]:
    return []


def _empty_calls() -> list[tuple[tuple[str, ...], str | None]]:
    return []


@dataclass
class RecordingRunner:
    """Queue-backed Runner that records argv and cwd for each call."""

    responses: list[CommandResult] = field(default_factory=_empty_responses)
    calls: list[tuple[tuple[str, ...], str | None]] = field(
        default_factory=_empty_calls
    )
    _index: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        argv_tuple = tuple(argv)
        self.calls.append((argv_tuple, cwd))
        if self._index >= len(self.responses):
            msg = f"no queued response for {argv_tuple!r}"
            raise AssertionError(msg)
        result = self.responses[self._index]
        self._index += 1
        return result


def _ok(argv: Sequence[str], stdout: str = "") -> CommandResult:
    return CommandResult(tuple(argv), 0, stdout, "", 0.01)


def _fail(
    argv: Sequence[str], *, returncode: int = 1, stderr: str = "boom"
) -> CommandResult:
    return CommandResult(tuple(argv), returncode, "", stderr, 0.01)


def _write_files(root: Path, files: Mapping[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")


def _git_ok_runner(root: Path, tracked: Sequence[str]) -> RecordingRunner:
    listing = "\0".join(tracked)
    if tracked:
        listing += "\0"
    return RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{root.resolve()}\n"),
            _ok(("git", "ls-files", "--cached", "-z"), listing),
        ]
    )


def _rule(
    *,
    detect: Callable[[SourceFile], list[Finding]] | None = None,
    syntax_policy: str = "fail",
    rule_id: str = "demo-rule",
    pragma: str = "lint-demo",
) -> LintRule:
    def _default_detect(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id=rule_id,
                message="hit",
            )
        ]

    return LintRule(
        rule_id=rule_id,
        description="demo",
        detect=detect or _default_detect,
        syntax_policy=syntax_policy,  # type: ignore[arg-type]
        suppression_token=pragma,
    )


def _invoke(
    rule: LintRule,
    root: Path,
    runner: RecordingRunner,
    paths: Sequence[str] | None = None,
    **kwargs: object,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(rule, root, runner, paths=paths, **kwargs)  # type: ignore[arg-type]
    return code, stdout.getvalue(), stderr.getvalue()


def _run(
    tmp_path: Path,
    *,
    files: Mapping[str, str],
    tracked: Sequence[str] | None = None,
    rule: LintRule | None = None,
    paths: Sequence[str] | None = None,
    runner: RecordingRunner | None = None,
) -> tuple[int, str, str, RecordingRunner]:
    _write_files(tmp_path, files)
    active_tracked = list(tracked) if tracked is not None else list(files)
    active_runner = runner or _git_ok_runner(tmp_path, active_tracked)
    code, out, err = _invoke(rule or _rule(), tmp_path, active_runner, paths=paths)
    return code, out, err, active_runner


def _patch_engine_parse(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    parse_calls = {"n": 0}
    real_parse = lint_engine.ast.parse

    def counting_parse(*args: object, **kwargs: object) -> ast.AST:
        parse_calls["n"] += 1
        return real_parse(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(lint_engine.ast, "parse", counting_parse)
    return parse_calls


def test_missing_root_returns_error(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    runner = RecordingRunner(responses=[])
    code, out, err = _invoke(_rule(), missing, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "does not exist" in err
    assert not runner.calls


def test_non_directory_root_returns_error(tmp_path: Path) -> None:
    file_root = tmp_path / "file"
    _ = file_root.write_text("x", encoding="utf-8")
    runner = RecordingRunner(responses=[])
    code, _out, err = _invoke(_rule(), file_root, runner)
    assert code == EXIT_ERROR
    assert "not a directory" in err
    assert not runner.calls


def test_rev_parse_nonzero_empty_multiline_and_mismatch(tmp_path: Path) -> None:
    cases = [
        (
            [_fail(("git", "rev-parse", "--show-toplevel"), stderr="not a git repo")],
            "failed",
        ),
        ([_ok(("git", "rev-parse", "--show-toplevel"), "")], "malformed"),
        ([_ok(("git", "rev-parse", "--show-toplevel"), "/a\n/b\n")], "malformed"),
        (
            [_ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path}\0\n")],
            "malformed",
        ),
        (
            [
                _ok(
                    ("git", "rev-parse", "--show-toplevel"),
                    f"{tmp_path.resolve() / 'other'}\n",
                )
            ],
            "not the git work-tree",
        ),
    ]
    for responses, needle in cases:
        runner = RecordingRunner(responses=list(responses))
        code, out, err = _invoke(_rule(), tmp_path, runner)
        assert code == EXIT_ERROR
        assert out == ""
        assert needle in err
        assert runner.calls == [
            (("git", "rev-parse", "--show-toplevel"), str(tmp_path.resolve()))
        ]


def test_rev_parse_preserves_significant_trailing_root_whitespace(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo "
    root.mkdir()
    runner = _git_ok_runner(root, [])

    code, out, err = _invoke(_rule(), root, runner)

    assert code == EXIT_CLEAN
    assert out == err == ""


def test_nested_worktree_directory_rejected(tmp_path: Path) -> None:
    nested = tmp_path / "pkg"
    nested.mkdir()
    runner = RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n")
        ]
    )
    code, _out, err = _invoke(_rule(), nested, runner)
    assert code == EXIT_ERROR
    assert "not the git work-tree top-level" in err
    assert runner.calls[0] == (
        ("git", "rev-parse", "--show-toplevel"),
        str(nested.resolve()),
    )


def test_discovery_argv_cwd_tracked_only_and_empty(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n", "ignored.py": "y = 2\n"})
    runner = _git_ok_runner(tmp_path, ["a.py"])
    seen: list[str] = []

    def detect(source: SourceFile) -> list[Finding]:
        seen.append(source.path)
        return []

    code, out, err = _invoke(_rule(detect=detect), tmp_path, runner)
    assert code == EXIT_CLEAN
    assert seen == ["a.py"]
    assert out == err == ""
    assert runner.calls == [
        (("git", "rev-parse", "--show-toplevel"), str(tmp_path.resolve())),
        (("git", "ls-files", "--cached", "-z"), str(tmp_path.resolve())),
    ]

    empty_runner = _git_ok_runner(tmp_path, [])
    code2, out2, err2, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=[],
        rule=_rule(detect=lambda _source: []),
        runner=empty_runner,
    )
    assert code2 == EXIT_CLEAN
    assert out2 == ""
    assert err2 == ""


def test_discovery_rejects_nonzero_and_blank_and_unsafe_paths(tmp_path: Path) -> None:
    _write_files(tmp_path, {"ok.py": "x = 1\n"})
    bad_runners = [
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _fail(("git", "ls-files", "--cached", "-z"), stderr="ls failed"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached", "-z"), "\0"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached", "-z"), "../escape.py\0"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached", "-z"), "/tmp/abs.py\0"),
            ]
        ),
    ]
    for runner in bad_runners:
        code, out, err = _invoke(_rule(), tmp_path, runner)
        assert code == EXIT_ERROR
        assert out == ""
        assert err


def test_discovery_preserves_whitespace_paths_and_rejects_unterminated_records(
    tmp_path: Path,
) -> None:
    filename = " leading and trailing.py "
    _write_files(tmp_path, {filename: "x = 1\n"})
    code, out, err, _ = _run(
        tmp_path,
        files={},
        tracked=[filename],
        rule=_rule(),
    )
    assert code == EXIT_FINDINGS
    assert out == f"{filename}:1: demo-rule hit\n"
    assert err == ""

    runner = RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
            _ok(("git", "ls-files", "--cached", "-z"), "a.py"),
        ]
    )
    code2, out2, err2 = _invoke(_rule(), tmp_path, runner)
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "unterminated" in err2


def test_requested_paths_filter_and_unmatched_clean(tmp_path: Path) -> None:
    files = {
        "pkg/a.py": "x = 1\n",
        "pkg/b.py": "y = 1\n",
        "other.py": "z = 1\n",
    }
    seen: list[str] = []

    def detect(source: SourceFile) -> list[Finding]:
        seen.append(source.path)
        return []

    code, out, err, _ = _run(
        tmp_path,
        files=files,
        tracked=list(files),
        rule=_rule(detect=detect),
        paths=["pkg"],
    )
    assert code == EXIT_CLEAN
    assert seen == ["pkg/a.py", "pkg/b.py"]
    assert out == ""
    assert err == ""

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    code2, out2, err2, _ = _run(
        tmp_path,
        files=files,
        tracked=list(files),
        rule=_rule(detect=lambda _source: []),
        paths=["empty"],
    )
    assert code2 == EXIT_CLEAN
    assert out2 == ""
    assert err2 == ""


def test_requested_path_rejects_outside_traversal_and_symlink(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    outside = tmp_path.parent / "outside.py"
    _ = outside.write_text("x = 1\n", encoding="utf-8")
    link = tmp_path / "link.py"
    link.symlink_to(outside)

    for paths in ([str(outside)], ["../outside.py"], ["link.py"]):
        code, out, err, _ = _run(
            tmp_path,
            files={"a.py": "x = 1\n"},
            tracked=["a.py"],
            paths=paths,
        )
        assert code == EXIT_ERROR
        assert out == ""
        assert err

    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=["a.py"],
        paths=["pkg/../a.py"],
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "must not contain '..'" in err


def test_requested_path_rejects_absolute_path_inside_repository(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})

    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=["a.py"],
        paths=[str(tmp_path / "a.py")],
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "repository-relative" in err


def test_discovered_missing_or_non_regular_rejected(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    (tmp_path / "dir_entry").mkdir()
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=["missing.py"],
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "does not exist" in err

    code2, out2, err2, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=["dir_entry"],
        runner=_git_ok_runner(tmp_path, ["dir_entry"]),
    )
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "not a regular file" in err2


def test_source_loading_utf8_and_undecodable(tmp_path: Path) -> None:
    captured: list[SourceFile] = []

    def detect(source: SourceFile) -> list[Finding]:
        captured.append(source)
        return []

    code, out, err, _ = _run(
        tmp_path,
        files={"ok.py": "alpha\nbeta\n"},
        rule=_rule(detect=detect),
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""
    assert captured[0].path == "ok.py"
    assert captured[0].text == "alpha\nbeta\n"
    assert captured[0].lines == ("alpha", "beta")

    bad = tmp_path / "bad.py"
    _ = bad.write_bytes(b"\xff\xfe")
    code2, out2, err2, _ = _run(
        tmp_path,
        files={},
        tracked=["bad.py"],
        runner=_git_ok_runner(tmp_path, ["bad.py"]),
    )
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "UTF-8" in err2


def test_source_loading_revalidates_and_converts_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "a.py"
    outside = tmp_path.parent / "outside.py"
    _ = outside.write_text("x = 1\n", encoding="utf-8")
    _write_files(tmp_path, {"a.py": "x = 1\n"})

    def swap_after_discovery(_root: Path, _runner: RecordingRunner) -> list[str]:
        source.unlink()
        source.symlink_to(outside)
        return ["a.py"]

    original_discover = lint_engine._discover_tracked_paths  # type: ignore[reportPrivateUsage]
    monkeypatch.setattr(lint_engine, "_discover_tracked_paths", swap_after_discovery)
    runner = RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n")
        ]
    )
    code, out, err = _invoke(_rule(), tmp_path, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "symlink" in err

    source.unlink()
    _ = source.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(lint_engine, "_discover_tracked_paths", original_discover)

    def fail_open(_path: Path, _flags: int) -> int:
        raise OSError("read denied")

    monkeypatch.setattr(lint_engine.os, "open", fail_open)
    code2, out2, err2, _ = _run(
        tmp_path,
        files={},
        tracked=["a.py"],
    )
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "failed to read" in err2


def test_source_loading_rejects_intermediate_symlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"pkg/a.py": "x = 1\n"})
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "a.py").write_text("outside = 1\n", encoding="utf-8")
    real_open = os.open

    def swap_parent(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        raw_path = os.fspath(path)
        if isinstance(raw_path, str) and Path(raw_path) == tmp_path and dir_fd is None:
            _ = (tmp_path / "pkg").rename(tmp_path / "pkg-original")
            (tmp_path / "pkg").symlink_to(outside, target_is_directory=True)
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(lint_engine.os, "open", swap_parent)

    with pytest.raises(lint_engine.ScanError, match=r"failed to read pkg/a\.py"):
        lint_engine._load_source(tmp_path, "pkg/a.py")  # type: ignore[reportUnusedCallResult, reportPrivateUsage]


def test_lazy_ast_parses_once_and_non_python_has_no_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_calls = _patch_engine_parse(monkeypatch)

    def detect(source: SourceFile) -> list[Finding]:
        if source.is_python:
            _ = source.python_ast
            _ = source.python_ast
        return []

    code, out, err, _ = _run(
        tmp_path,
        files={"ok.py": "x = 1\n", "notes.md": "hello\n"},
        tracked=["ok.py", "notes.md"],
        rule=_rule(detect=detect),
    )
    assert code == EXIT_CLEAN
    assert out == err == ""
    assert parse_calls["n"] == 1

    md = SourceFile(path="notes.md", text="hello\n", lines=("hello",))
    with pytest.raises(TypeError, match="non-Python"):
        _ = md.python_ast


def test_non_ast_detector_does_not_reparse_after_policy_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_calls = _patch_engine_parse(monkeypatch)

    code, out, err, _ = _run(
        tmp_path,
        files={"ok.py": "x = 1\n"},
        rule=_rule(detect=lambda _source: []),
    )
    assert code == EXIT_CLEAN
    assert out == err == ""
    assert parse_calls["n"] == 1


def test_cached_syntax_failure_does_not_reparse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parse_calls = _patch_engine_parse(monkeypatch)
    invalid = "def broken(\n"

    def detect(_source: SourceFile) -> list[Finding]:
        raise AssertionError("detect must not run for invalid python under fail")

    code, out, err, _ = _run(
        tmp_path,
        files={"bad.py": invalid},
        rule=_rule(detect=detect, syntax_policy="fail"),
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert SYNTAX_FAIL_MESSAGE in out
    assert parse_calls["n"] == 1

    source = SourceFile(path="bad.py", text=invalid, lines=tuple(invalid.splitlines()))
    with pytest.raises(SyntaxError):
        _ = source.python_ast
    assert parse_calls["n"] == 2
    with pytest.raises(SyntaxError):
        _ = source.python_ast
    assert parse_calls["n"] == 2
    assert source.python_syntax_error() is not None


def test_syntax_policy_fail_and_skip(tmp_path: Path) -> None:
    invalid = "def broken(\n"
    detect_calls = {"n": 0}

    def detect(_source: SourceFile) -> list[Finding]:
        detect_calls["n"] += 1
        return []

    code, out, err, _ = _run(
        tmp_path,
        files={"bad.py": invalid, "ok.py": "x = 1\n"},
        tracked=["bad.py", "ok.py"],
        rule=_rule(detect=detect, syntax_policy="fail"),
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == f"bad.py:1: demo-rule {SYNTAX_FAIL_MESSAGE}\n"
    assert detect_calls["n"] == 1  # only ok.py

    detect_calls["n"] = 0
    code2, out2, err2, _ = _run(
        tmp_path,
        files={"bad.py": invalid, "ok.py": "x = 1\n"},
        tracked=["bad.py", "ok.py"],
        rule=_rule(detect=detect, syntax_policy="skip"),
    )
    assert code2 == EXIT_CLEAN
    assert out2 == ""
    assert err2 == ""
    assert detect_calls["n"] == 1


@pytest.mark.parametrize("lineno", [0, -1, None, 99])
def test_syntax_error_invalid_line_numbers_fall_back_to_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lineno: int | None
) -> None:
    def invalid_parse(*_args: object, **_kwargs: object) -> ast.AST:
        error = SyntaxError("broken")
        error.lineno = lineno
        raise error

    monkeypatch.setattr(lint_engine.ast, "parse", invalid_parse)
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        rule=_rule(detect=lambda _source: []),
    )
    assert code == EXIT_FINDINGS
    assert out == f"a.py:1: demo-rule {SYNTAX_FAIL_MESSAGE}\n"
    assert err == ""


def test_suppression_same_line_reason_and_empty_reason_error(tmp_path: Path) -> None:
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1  # lint-demo: ok deliberate\n"},
        rule=_rule(),
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""

    code2, out2, err2, _ = _run(
        tmp_path,
        files={"a.py": "x = 1  # lint-demo: ok\n"},
        rule=_rule(),
    )
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "non-empty reason" in err2

    code3, out3, err3, _ = _run(
        tmp_path,
        files={"a.py": "x = 1  # lint-demo: ok    \n"},
        rule=_rule(),
    )
    assert code3 == EXIT_ERROR
    assert out3 == ""
    assert err3


def test_suppression_ignores_code_strings_and_adjacent_lines(tmp_path: Path) -> None:
    source = (
        'TOKEN = "lint-demo: ok in-string"\n'
        "x = 1  # adjacent does not count\n"
        "# lint-demo: ok previous-line\n"
        "y = 2\n"
    )

    def detect(src: SourceFile) -> list[Finding]:
        return [
            Finding(path=src.path, line=2, rule_id="demo-rule", message="a"),
            Finding(path=src.path, line=4, rule_id="demo-rule", message="b"),
        ]

    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": source},
        rule=_rule(detect=detect),
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == "a.py:2: demo-rule a\na.py:4: demo-rule b\n"


def test_detector_and_config_validation(tmp_path: Path) -> None:
    bad_rule = LintRule(
        rule_id="",
        description="x",
        detect=lambda _s: [],
        syntax_policy="fail",
        suppression_token="lint-tok",  # noqa: S106 - pragma name, not a secret
    )
    code, out, err = _invoke(bad_rule, tmp_path, _git_ok_runner(tmp_path, []))
    assert code == EXIT_ERROR
    assert out == ""
    assert "rule_id" in err

    def bad_list(_source: SourceFile) -> list[Finding]:
        return "nope"  # type: ignore[return-value]

    code2, out2, err2, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=bad_list)
    )
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "list" in err2

    def bad_member(_source: SourceFile) -> list[Finding]:
        return [object()]  # type: ignore[list-item]

    code3, out3, err3, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=bad_member)
    )
    assert code3 == EXIT_ERROR
    assert out3 == ""
    assert "Finding" in err3

    def mismatch(_source: SourceFile) -> list[Finding]:
        return [Finding(path="other.py", line=1, rule_id="demo-rule", message="x")]

    code4, out4, err4, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=mismatch)
    )
    assert code4 == EXIT_ERROR
    assert out4 == ""
    assert "does not match source" in err4

    def bad_line(source: SourceFile) -> list[Finding]:
        return [Finding(path=source.path, line=0, rule_id="demo-rule", message="x")]

    code5, out5, err5, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=bad_line)
    )
    assert code5 == EXIT_ERROR
    assert out5 == ""
    assert "out of range" in err5 or "positive" in err5

    def boolean_line(source: SourceFile) -> list[Finding]:
        return [Finding(path=source.path, line=True, rule_id="demo-rule", message="x")]

    code_bool_line, out_bool_line, err_bool_line, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=boolean_line)
    )
    assert code_bool_line == EXIT_ERROR
    assert out_bool_line == ""
    assert "out of range" in err_bool_line

    def bad_message(source: SourceFile) -> list[Finding]:
        return [Finding(path=source.path, line=1, rule_id="demo-rule", message="x\ny")]

    code6, out6, err6, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=bad_message)
    )
    assert code6 == EXIT_ERROR
    assert out6 == ""
    assert "message" in err6

    def bad_metric(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="x",
                metric=-1,
            )
        ]

    code7, out7, err7, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=bad_metric)
    )
    assert code7 == EXIT_ERROR
    assert out7 == ""
    assert "metric" in err7

    def boolean_metric(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="x",
                metric=True,
            )
        ]

    code_bool_metric, out_bool_metric, err_bool_metric, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=boolean_metric)
    )
    assert code_bool_metric == EXIT_ERROR
    assert out_bool_metric == ""
    assert "metric" in err_bool_metric

    def boom(_source: SourceFile) -> list[Finding]:
        raise RuntimeError("detector exploded")

    code8, out8, err8, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=boom)
    )
    assert code8 == EXIT_ERROR
    assert out8 == ""
    assert "detector raised" in err8


@pytest.mark.parametrize(
    ("field", "value"),
    [("message", None), ("qualified_symbol", 3), ("path", 3)],
)
def test_detector_fields_must_be_valid_strings(
    tmp_path: Path, field: str, value: object
) -> None:
    def malformed(source: SourceFile) -> list[Finding]:
        values: dict[str, object] = {
            "path": source.path,
            "line": 1,
            "rule_id": "demo-rule",
            "message": "hit",
            "qualified_symbol": None,
        }
        values[field] = value
        return [Finding(**values)]  # type: ignore[arg-type]

    code, out, err, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=malformed)
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert err


def test_detector_rejects_mismatched_rule_id(tmp_path: Path) -> None:
    def mismatch(source: SourceFile) -> list[Finding]:
        return [Finding(path=source.path, line=1, rule_id="other", message="hit")]

    code, out, err, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=mismatch)
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "rule_id" in err


@pytest.mark.parametrize(
    ("rule_id", "suppression_token"),
    [("demo\nrule", "lint-demo"), ("demo-rule", "lint\ndemo")],
)
def test_rule_configuration_rejects_multiline_values(
    tmp_path: Path, rule_id: str, suppression_token: str
) -> None:
    rule = LintRule(
        rule_id=rule_id,
        description="demo",
        detect=lambda _source: [],
        syntax_policy="fail",
        suppression_token=suppression_token,
    )
    code, out, err = _invoke(rule, tmp_path, _git_ok_runner(tmp_path, []))
    assert code == EXIT_ERROR
    assert out == ""
    assert "single-line" in err


@pytest.mark.parametrize("symbol", ["name\nother", ""])
def test_detector_rejects_invalid_qualified_symbol(tmp_path: Path, symbol: str) -> None:
    def malformed(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="hit",
                qualified_symbol=symbol,
            )
        ]

    code, out, err, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=malformed)
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "qualified_symbol" in err


def test_tokenizer_indentation_error_returns_scan_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def invalid_tokens(_readline: object) -> object:
        raise IndentationError("unexpected indent")

    monkeypatch.setattr(lint_engine.tokenize, "generate_tokens", invalid_tokens)
    code, out, err, _ = _run(
        tmp_path,
        files={"notes.md": "notes\n"},
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to tokenize" in err
    assert "notes" not in err


def test_no_partial_stdout_when_later_source_fails(tmp_path: Path) -> None:
    def detect(source: SourceFile) -> list[Finding]:
        if source.path == "b.py":
            raise RuntimeError("late failure")
        return [Finding(path=source.path, line=1, rule_id="demo-rule", message="early")]

    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n", "b.py": "y = 1\n"},
        tracked=["a.py", "b.py"],
        rule=_rule(detect=detect),
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "late failure" in err


def test_dedupe_sort_render_and_optional_fields(tmp_path: Path) -> None:
    def detect(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=2,
                rule_id="demo-rule",
                message="b",
                qualified_symbol="sym",
                metric=3,
            ),
            Finding(path=source.path, line=1, rule_id="demo-rule", message="a"),
            Finding(
                path=source.path,
                line=2,
                rule_id="demo-rule",
                message="b",
                qualified_symbol="other",
                metric=9,
            ),
            Finding(path=source.path, line=1, rule_id="demo-rule", message="a"),
        ]

    code, out, err, _ = _run(
        tmp_path,
        files={"z.py": "a = 1\nb = 2\n", "a.py": "a = 1\nb = 2\n"},
        tracked=["z.py", "a.py"],
        rule=_rule(detect=detect),
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert out == (
        "a.py:1: demo-rule a\n"
        "a.py:2: demo-rule b\n"
        "z.py:1: demo-rule a\n"
        "z.py:2: demo-rule b\n"
    )
    finding = Finding(path="a.py", line=1, rule_id="demo-rule", message="a", metric=1)
    assert render_finding(finding) == "a.py:1: demo-rule a"


def test_exit_codes_and_no_repo_writes(tmp_path: Path) -> None:
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        rule=_rule(detect=lambda _source: []),
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""

    code2, out2, err2, _ = _run(tmp_path, files={"a.py": "x = 1\n"}, rule=_rule())
    assert code2 == EXIT_FINDINGS
    assert out2 == "a.py:1: demo-rule hit\n"
    assert err2 == ""

    code3, out3, err3, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        tracked=["missing.py"],
    )
    assert code3 == EXIT_ERROR
    assert out3 == ""
    assert err3

    after_files = sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    )
    assert after_files == ["a.py"]


def test_duplicate_tracked_paths_are_deduped(tmp_path: Path) -> None:
    seen: list[str] = []

    def detect(source: SourceFile) -> list[Finding]:
        seen.append(source.path)
        return []

    runner = RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
            _ok(("git", "ls-files", "--cached", "-z"), "a.py\0a.py\0"),
        ]
    )
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1\n"},
        rule=_rule(detect=detect),
        runner=runner,
    )
    assert code == EXIT_CLEAN
    assert seen == ["a.py"]
    assert out == err == ""


def test_final_line_without_newline_still_suppresses(tmp_path: Path) -> None:
    code, out, err, _ = _run(
        tmp_path,
        files={"a.py": "x = 1  # lint-demo: ok trailing"},
        rule=_rule(),
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def _baseline_row(
    path: str,
    *,
    line: int = 1,
    message: str = "hit",
    reason: str = "accepted",
) -> dict[str, object]:
    return {
        "path": path,
        "line": line,
        "rule_id": "demo-rule",
        "message": message,
        "reason": reason,
    }


def _write_baseline(path: Path, rows: list[dict[str, object]]) -> None:
    _ = path.write_text(json.dumps(rows), encoding="utf-8")


def test_generic_baseline_match_new_stale_and_strict_stale(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [_baseline_row("a.py"), _baseline_row("removed.py", message="old")],
    )
    runner = _git_ok_runner(tmp_path, ["a.py"])

    code, out, err = _invoke(_rule(), tmp_path, runner, baseline_path="baseline.json")

    assert code == EXIT_CLEAN
    assert out == ""
    assert err == "warning: stale baseline row: removed.py:1: demo-rule old\n"

    strict_runner = _git_ok_runner(tmp_path, ["a.py"])
    strict_code, strict_out, strict_err = _invoke(
        _rule(),
        tmp_path,
        strict_runner,
        baseline_path="baseline.json",
        strict_stale=True,
    )
    assert strict_code == EXIT_ERROR
    assert strict_out == ""
    assert strict_err == (
        "warning: stale baseline row: removed.py:1: demo-rule old\n"
        "strict_stale rejected stale baseline rows\n"
    )


def test_strict_stale_takes_precedence_over_new_findings(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("a.py", message="old")])

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        strict_stale=True,
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert err == (
        "warning: stale baseline row: a.py:1: demo-rule old\n"
        "strict_stale rejected stale baseline rows\n"
    )


def test_baseline_new_finding_and_reason_do_not_change_generic_identity(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("a.py", reason="different reason")])

    code, out, err = _invoke(
        _rule(), tmp_path, _git_ok_runner(tmp_path, ["a.py"]), baseline_path=baseline
    )
    assert code == EXIT_CLEAN
    assert out == err == ""

    _write_baseline(baseline, [_baseline_row("a.py", message="old")])
    changed_code, changed_out, changed_err = _invoke(
        _rule(), tmp_path, _git_ok_runner(tmp_path, ["a.py"]), baseline_path=baseline
    )
    assert changed_code == EXIT_FINDINGS
    assert changed_out == "a.py:1: demo-rule hit\n"
    assert changed_err == "warning: stale baseline row: a.py:1: demo-rule old\n"


def test_symbol_metric_baselines_compare_symbols_without_generic_dedupe(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "one",
                "metric": 1,
                "reason": "known",
            },
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "two",
                "metric": 3,
                "reason": "known",
            },
        ],
    )

    def detect(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="same",
                qualified_symbol="one",
                metric=2,
            ),
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="same",
                qualified_symbol="two",
                metric=4,
            ),
        ]

    code, out, err = _invoke(
        _rule(detect=detect),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )
    assert code == EXIT_FINDINGS
    assert out == "a.py:1: demo-rule same\na.py:1: demo-rule same\n"
    assert err == ""


@pytest.mark.parametrize("metric", [2, 3])
def test_symbol_metric_baseline_accepts_equal_or_reduced_metric(
    tmp_path: Path, metric: int
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "function",
                "metric": 3,
                "reason": "known",
            }
        ],
    )

    def detect(source: SourceFile) -> list[Finding]:
        return [
            Finding(
                path=source.path,
                line=1,
                rule_id="demo-rule",
                message="same",
                qualified_symbol="function",
                metric=metric,
            )
        ]

    code, out, err = _invoke(
        _rule(detect=detect),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )

    assert code == EXIT_CLEAN
    assert out == err == ""


@pytest.mark.parametrize("metric", [-1, True, "3"])
def test_symbol_metric_baseline_rejects_invalid_metric(
    tmp_path: Path, metric: object
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "function",
                "metric": metric,
                "reason": "known",
            }
        ],
    )

    code, out, err = _invoke(
        _rule(), tmp_path, _git_ok_runner(tmp_path, ["a.py"]), baseline_path=baseline
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "invalid metric" in err


def test_symbol_metric_baseline_rejects_duplicate_identity(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    row: dict[str, object] = {
        "path": "a.py",
        "rule_id": "demo-rule",
        "qualified_symbol": "function",
        "metric": 3,
        "reason": "known",
    }
    _write_baseline(baseline, [row, {**row, "metric": 4}])

    code, out, err = _invoke(
        _rule(), tmp_path, _git_ok_runner(tmp_path, ["a.py"]), baseline_path=baseline
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "duplicate baseline identity" in err


def test_baseline_active_duplicate_identity_fails_but_scan_only_dedupes(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [])

    def duplicate(source: SourceFile) -> list[Finding]:
        finding = Finding(path=source.path, line=1, rule_id="demo-rule", message="hit")
        return [finding, finding]

    plain_code, plain_out, plain_err = _invoke(
        _rule(detect=duplicate), tmp_path, _git_ok_runner(tmp_path, ["a.py"])
    )
    assert plain_code == EXIT_FINDINGS
    assert plain_out == "a.py:1: demo-rule hit\n"
    assert plain_err == ""

    baseline_code, baseline_out, baseline_err = _invoke(
        _rule(detect=duplicate),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )
    assert baseline_code == EXIT_ERROR
    assert baseline_out == ""
    assert "duplicate live" in baseline_err


def test_filtered_baseline_check_ignores_out_of_scope_stale_rows(
    tmp_path: Path,
) -> None:
    _write_files(
        tmp_path,
        {"pkg/a.py": "x = 1\n", "other/b.py": "x = 1\n"},
    )
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [_baseline_row("pkg/a.py"), _baseline_row("other/removed.py")],
    )

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["pkg/a.py", "other/b.py"]),
        paths=["pkg"],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_CLEAN
    assert out == err == ""


def test_write_baseline_preserves_reasons_and_refuses_unexplained_findings(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n", "b.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("a.py", reason="keep this")])

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py", "b.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="new finding",
    )
    assert code == EXIT_CLEAN
    assert out == err == ""
    expected_rows = [
        lint_engine.GenericBaselineRow("a.py", 1, "demo-rule", "hit", "keep this"),
        lint_engine.GenericBaselineRow("b.py", 1, "demo-rule", "hit", "new finding"),
    ]
    assert baseline.read_text(encoding="utf-8") == lint_engine._serialized_baseline(  # pyright: ignore[reportPrivateUsage]
        expected_rows
    )

    before = baseline.read_text(encoding="utf-8")
    no_reason_code, no_reason_out, no_reason_err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py", "b.py"]),
        baseline_path=baseline,
        write_baseline=True,
    )
    assert no_reason_code == EXIT_CLEAN
    assert no_reason_out == no_reason_err == ""
    assert baseline.read_text(encoding="utf-8") == before

    _write_baseline(baseline, [_baseline_row("a.py", reason="keep this")])
    missing_code, missing_out, missing_err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py", "b.py"]),
        baseline_path=baseline,
        write_baseline=True,
    )
    assert missing_code == EXIT_ERROR
    assert missing_out == ""
    assert "no baseline reason" in missing_err
    assert json.loads(baseline.read_text(encoding="utf-8")) == [
        _baseline_row("a.py", reason="keep this")
    ]


@pytest.mark.parametrize(
    ("kwargs", "needle"),
    [
        ({"write_baseline": True}, "requires baseline_path"),
        ({"strict_stale": True}, "requires baseline check mode"),
        ({"initial_reason": "why"}, "only valid"),
        (
            {
                "baseline_path": "baseline.json",
                "write_baseline": True,
                "paths": ["a.py"],
            },
            "does not support filtered",
        ),
    ],
)
def test_baseline_flag_combinations_fail_before_scan(
    tmp_path: Path, kwargs: dict[str, object], needle: str
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n", "baseline.json": "[]"})
    supplied_paths = kwargs.pop("paths", None)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        RecordingRunner(responses=[]),
        paths=supplied_paths,  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert needle in err


def test_baseline_path_rejects_escape_symlink_parent_and_directory_target(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    outside = tmp_path.parent / "outside-baselines"
    outside.mkdir(exist_ok=True)
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    (tmp_path / "directory.json").mkdir()

    cases = [
        ("../outside.json", "must not contain"),
        ("linked/baseline.json", "symlinked"),
        ("directory.json", "not a regular file"),
    ]
    for baseline_path, needle in cases:
        code, out, err = _invoke(
            _rule(),
            tmp_path,
            RecordingRunner(
                responses=[
                    _ok(
                        ("git", "rev-parse", "--show-toplevel"),
                        f"{tmp_path.resolve()}\n",
                    )
                ]
            ),
            baseline_path=baseline_path,
        )
        assert code == EXIT_ERROR
        assert out == ""
        assert needle in err


@pytest.mark.parametrize("write_baseline", [False, True])
def test_baseline_component_lstat_errors_return_scan_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, write_baseline: bool
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n", "baseline.json": "[]"})
    baseline = tmp_path / "baseline.json"
    original_lstat = Path.lstat

    def denied(path: Path) -> os.stat_result:
        if path == baseline:
            raise PermissionError("denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", denied)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=write_baseline,
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to inspect baseline path" in err


@pytest.mark.parametrize(
    ("baseline_path", "setup", "needle"),
    [
        ("../outside.json", None, "must not contain"),
        ("missing/baseline.json", None, "parent does not exist"),
        ("not-a-directory/baseline.json", "file", "parent is not a directory"),
        ("linked.json", "symlink", "symlinked"),
        ("linked-parent/baseline.json", "symlink-parent", "symlinked"),
        ("directory.json", "directory", "not a regular file"),
    ],
)
def test_write_baseline_rejects_unsafe_or_invalid_destination(
    tmp_path: Path,
    baseline_path: str,
    setup: str | None,
    needle: str,
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    if setup == "file":
        _ = (tmp_path / "not-a-directory").write_text("x", encoding="utf-8")
    if setup == "symlink":
        target = tmp_path / "target.json"
        _ = target.write_text("[]", encoding="utf-8")
        (tmp_path / "linked.json").symlink_to(target)
    if setup == "symlink-parent":
        target = tmp_path / "target-parent"
        target.mkdir()
        (tmp_path / "linked-parent").symlink_to(target, target_is_directory=True)
    if setup == "directory":
        (tmp_path / "directory.json").mkdir()

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline_path,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert needle in err


def test_write_baseline_creates_empty_destination(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"

    code, out, err = _invoke(
        _rule(detect=lambda _source: []),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_CLEAN
    assert out == err == ""
    assert baseline.read_text(encoding="utf-8") == "[]\n"


def test_write_baseline_cleans_up_temporary_artifact_after_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"

    def fail_fsync(_fd: int) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lint_engine.larch_io.os, "fsync", fail_fsync)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to write baseline" in err
    assert not list(tmp_path.glob(".baseline.json.*.tmp"))


def test_baseline_check_rejects_missing_file(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "missing.json"

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "file does not exist" in err
    assert not baseline.exists()


def test_baseline_rejects_mixed_row_shapes(tmp_path: Path) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        [
            _baseline_row("a.py"),
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "function",
                "metric": 1,
                "reason": "known",
            },
        ],
    )

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "mixed baseline row shapes" in err


@pytest.mark.parametrize(
    ("row", "needle"),
    [
        (
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "metric": 1,
                "reason": "known",
            },
            "unsupported keys",
        ),
        (
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "",
                "metric": 1,
                "reason": "known",
            },
            "invalid qualified_symbol",
        ),
        (
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": "outer\ninner",
                "metric": 1,
                "reason": "known",
            },
            "invalid qualified_symbol",
        ),
        (
            {
                "path": "a.py",
                "rule_id": "demo-rule",
                "qualified_symbol": 1,
                "metric": 1,
                "reason": "known",
            },
            "invalid qualified_symbol",
        ),
    ],
)
def test_symbol_metric_baseline_rejects_malformed_qualified_symbol(
    tmp_path: Path, row: dict[str, object], needle: str
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [row])

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert needle in err


@pytest.mark.parametrize(
    "row",
    [
        {
            "path": "a.py",
            "line": 0,
            "rule_id": "demo-rule",
            "message": "hit",
            "reason": "x",
        },
        {
            "path": "a.py",
            "line": True,
            "rule_id": "demo-rule",
            "message": "hit",
            "reason": "x",
        },
        {
            "path": "a.py",
            "line": 1,
            "rule_id": "demo-rule",
            "message": "hit",
            "reason": "",
        },
    ],
)
def test_malformed_generic_baseline_aborts_before_write(
    tmp_path: Path, row: dict[str, object]
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [row])
    before = baseline.read_text(encoding="utf-8")

    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "invalid" in err
    assert baseline.read_text(encoding="utf-8") == before


def test_write_baseline_readback_mismatch_fails_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("removed.py", reason="old")])
    original_read = lint_engine.larch_io.read_trusted_text
    calls = 0

    def mismatched_read(*args: object, **kwargs: object) -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            return "[]\n"
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(lint_engine.larch_io, "read_trusted_text", mismatched_read)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "read-back bytes differ" in err
    assert baseline.read_text(encoding="utf-8") == lint_engine._serialized_baseline(  # pyright: ignore[reportPrivateUsage]
        [lint_engine.GenericBaselineRow("a.py", 1, "demo-rule", "hit", "known")]
    )


def test_write_baseline_readback_error_fails_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("removed.py", reason="old")])
    original_read = lint_engine.larch_io.read_trusted_text
    calls = 0

    def failing_read(*args: object, **kwargs: object) -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("read-back denied")
        return original_read(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(lint_engine.larch_io, "read_trusted_text", failing_read)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to read back baseline" in err
    assert baseline.read_text(encoding="utf-8") == lint_engine._serialized_baseline(  # pyright: ignore[reportPrivateUsage]
        [lint_engine.GenericBaselineRow("a.py", 1, "demo-rule", "hit", "known")]
    )


def test_write_baseline_readback_parse_failure_fails_without_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"a.py": "x = 1\n"})
    baseline = tmp_path / "baseline.json"
    _write_baseline(baseline, [_baseline_row("removed.py", reason="old")])
    original_parse = lint_engine._parse_baseline_text  # pyright: ignore[reportPrivateUsage]
    calls = 0

    def malformed_parse(*args: object, **kwargs: object) -> list[lint_engine.BaselineRow]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise lint_engine.ScanError("invalid JSON baseline: expected value")
        return original_parse(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(lint_engine, "_parse_baseline_text", malformed_parse)
    code, out, err = _invoke(
        _rule(),
        tmp_path,
        _git_ok_runner(tmp_path, ["a.py"]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="known",
    )

    assert code == EXIT_ERROR
    assert out == ""
    assert "read-back validation failed" in err
    assert baseline.read_text(encoding="utf-8") == lint_engine._serialized_baseline(  # pyright: ignore[reportPrivateUsage]
        [lint_engine.GenericBaselineRow("a.py", 1, "demo-rule", "hit", "known")]
    )
