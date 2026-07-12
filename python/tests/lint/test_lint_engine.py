"""Offline coverage for the shared scan-only lint engine."""

from __future__ import annotations

import ast
import contextlib
import io
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
    listing = "\n".join(tracked)
    if tracked:
        listing += "\n"
    return RecordingRunner(
        responses=[
            _ok(("git", "rev-parse", "--show-toplevel"), f"{root.resolve()}\n"),
            _ok(("git", "ls-files", "--cached"), listing),
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
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(rule, root, runner, paths=paths)
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
    assert runner.calls == []


def test_non_directory_root_returns_error(tmp_path: Path) -> None:
    file_root = tmp_path / "file"
    _ = file_root.write_text("x", encoding="utf-8")
    runner = RecordingRunner(responses=[])
    code, _out, err = _invoke(_rule(), file_root, runner)
    assert code == EXIT_ERROR
    assert "not a directory" in err
    assert runner.calls == []


def test_rev_parse_nonzero_empty_multiline_and_mismatch(tmp_path: Path) -> None:
    cases = [
        (
            [_fail(("git", "rev-parse", "--show-toplevel"), stderr="not a git repo")],
            "failed",
        ),
        ([_ok(("git", "rev-parse", "--show-toplevel"), "")], "malformed"),
        ([_ok(("git", "rev-parse", "--show-toplevel"), "/a\n/b\n")], "malformed"),
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
        (("git", "ls-files", "--cached"), str(tmp_path.resolve())),
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
                _fail(("git", "ls-files", "--cached"), stderr="ls failed"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached"), "\n"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached"), "../escape.py\n"),
            ]
        ),
        RecordingRunner(
            responses=[
                _ok(("git", "rev-parse", "--show-toplevel"), f"{tmp_path.resolve()}\n"),
                _ok(("git", "ls-files", "--cached"), "/tmp/abs.py\n"),
            ]
        ),
    ]
    for runner in bad_runners:
        code, out, err = _invoke(_rule(), tmp_path, runner)
        assert code == EXIT_ERROR
        assert out == ""
        assert err


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

    def boom(_source: SourceFile) -> list[Finding]:
        raise RuntimeError("detector exploded")

    code8, out8, err8, _ = _run(
        tmp_path, files={"a.py": "x = 1\n"}, rule=_rule(detect=boom)
    )
    assert code8 == EXIT_ERROR
    assert out8 == ""
    assert "detector raised" in err8


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
            _ok(("git", "ls-files", "--cached"), "a.py\na.py\n"),
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
