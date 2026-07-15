"""Coverage for the engine-backed markdown-heading-fence-state rule."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

import pytest
from larch.lint import lint_markdown_heading_fence_state as lint
from larch.lint import engine as lint_engine
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    ScanError,
    SourceFile,
    run_rule,
)
from larch.lint.markdown_heading_fence_state_detector import (
    is_production_source_path,
)
from tests.lint.test_lint_engine import (
    RecordingRunner,
    _git_ok_runner,  # type: ignore[reportPrivateUsage]
    _write_files,  # type: ignore[reportPrivateUsage]
)


VIOLATING = """\
import re

HEADING_RE = re.compile(r"^#{1,6}\\s+")

def parse(text: str) -> None:
    for line in text.splitlines():
        if HEADING_RE.match(line):
            pass
"""

COMPLIANT = """\
import re

HEADING_RE = re.compile(r"^#{1,6}\\s+")

def _balanced_fence_line_indices(lines: list[str]) -> set[int]:
    return set()

def parse(text: str) -> None:
    lines = text.splitlines()
    fenced = _balanced_fence_line_indices(lines)
    for index, line in enumerate(lines):
        in_fence = index in fenced
        if not in_fence and HEADING_RE.match(line):
            pass
"""

UNRELATED = """\
import re

TOKEN_RE = re.compile(r"^[A-Z_]+$")

def parse(text: str) -> None:
    for line in text.splitlines():
        if TOKEN_RE.match(line):
            pass
"""


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _occurrence_row(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "parse",
    pattern_name: str = "HEADING_RE",
    occurrence: int = 1,
    reason: str = "grandfathered",
) -> dict[str, object]:
    return {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "pattern_name": pattern_name,
        "occurrence": occurrence,
        "reason": reason,
    }


def _invoke_main(root: Path, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = lint.main(["--root", str(root), *argv])
    return code, stdout.getvalue(), stderr.getvalue()


def _invoke_rule(
    root: Path,
    runner: RecordingRunner,
    *,
    write_baseline: bool = False,
    initial_reason: str | None = None,
    strict_stale: bool = True,
    baseline_name: str = lint.BASELINE_FILENAME,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(
            lint.RULE,
            root,
            runner,
            paths=None,
            baseline_path=root / "python" / baseline_name,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=strict_stale,
        )
    return code, stdout.getvalue(), stderr.getvalue()


def test_direct_re_compile_without_fence_is_detected() -> None:
    findings = lint.detect(_source("python/larch/mod.py", VIOLATING))
    assert [(f.pattern_name, f.qualified_symbol, f.occurrence) for f in findings] == [
        ("HEADING_RE", "parse", 1)
    ]


def test_fence_helper_gating_is_compliant() -> None:
    assert not lint.detect(_source("python/larch/mod.py", COMPLIANT))


def test_inline_fence_helper_and_continue_skip_are_compliant() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def fence_indices(lines: list[str]) -> set[int]:\n"
        "    return set()\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    for index, line in enumerate(lines):\n"
        "        if index in fence_indices(lines):\n"
        "            continue\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))


def test_unrelated_boolean_does_not_count_as_fence_guard() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        in_fence = False\n"
        "        if not in_fence and HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert [f.pattern_name for f in lint.detect(_source("python/larch/mod.py", text))] == [
        "HEADING_RE"
    ]


def test_unrelated_regex_ignored() -> None:
    assert not lint.detect(_source("python/larch/mod.py", UNRELATED))


def test_search_over_split_lines_detected() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s')\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    for line in lines:\n"
        "        if HEADING_RE.search(line):\n"
        "            pass\n"
    )
    assert [f.pattern_name for f in lint.detect(_source("python/larch/mod.py", text))] == [
        "HEADING_RE"
    ]


def test_enumerated_split_lines_require_fence_guard() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    for index, line in enumerate(text.splitlines()):\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert [f.pattern_name for f in lint.detect(_source("python/larch/mod.py", text))] == [
        "HEADING_RE"
    ]


def test_fence_guard_must_reference_active_loop_value() -> None:
    text = (
        "import re\n"
        "from larch.design.plan_grammar import _balanced_fence_line_indices\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    fenced = _balanced_fence_line_indices(lines)\n"
        "    for index, line in enumerate(lines):\n"
        "        if 0 not in fenced and HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert [f.pattern_name for f in lint.detect(_source("python/larch/mod.py", text))] == [
        "HEADING_RE"
    ]


def test_boolean_fence_guard_and_subscript_line_are_compliant() -> None:
    text = (
        "import re\n"
        "from larch.design.plan_grammar import _balanced_fence_line_indices\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    fenced = _balanced_fence_line_indices(lines)\n"
        "    for index in range(len(lines)):\n"
        "        in_fence = index in fenced\n"
        "        if not in_fence and HEADING_RE.match(lines[index]):\n"
        "            pass\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))


def test_function_local_fence_helper_import_is_compliant() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    from larch.design.plan_grammar import _balanced_fence_line_indices\n"
        "    lines = text.splitlines()\n"
        "    fenced = _balanced_fence_line_indices(lines)\n"
        "    for index, line in enumerate(lines):\n"
        "        if index not in fenced and HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))


def test_nested_symbol_occurrence_numbering() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')\n"
        "class Parser:\n"
        "    def outer(self, text: str) -> None:\n"
        "        def inner(chunk: str) -> None:\n"
        "            for line in chunk.splitlines():\n"
        "                if HEADING_RE.match(line):\n"
        "                    pass\n"
        "        for line in text.splitlines():\n"
        "            if HEADING_RE.match(line):\n"
        "                pass\n"
    )
    findings = lint.detect(_source("python/larch/mod.py", text))
    assert [(f.qualified_symbol, f.occurrence) for f in findings] == [
        ("Parser.outer.inner", 1),
        ("Parser.outer", 1),
    ]


def test_production_path_filter_includes_root_files_and_excludes_tests_support_and_vendor() -> None:
    assert is_production_source_path("python/root.py")
    assert is_production_source_path("python/larch/prod.py")
    assert not is_production_source_path("python/larch/test_mod.py")
    assert not is_production_source_path("python/larch/conftest.py")
    assert not is_production_source_path("python/tests/support/helper.py")
    assert not is_production_source_path("python/larch/.venv/vendor.py")
    assert not is_production_source_path("scripts/tool.py")
    assert not is_production_source_path("skills/demo/helper.py")


def test_valid_suppression_on_regex_declaration() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')  "
        "# lint-markdown-heading-fence-state: ok intentional\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))


def test_empty_declaration_pragma_raises_scan_error() -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')  "
        "# lint-markdown-heading-fence-state: ok\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n"
    )
    with pytest.raises(ScanError, match="empty lint-markdown-heading-fence-state"):
        _ = lint.detect(_source("python/larch/mod.py", text))


def test_empty_declaration_pragma_main_exits_2(tmp_path: Path) -> None:
    text = (
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\s+')  "
        "# lint-markdown-heading-fence-state: ok\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n"
    )
    _write_files(tmp_path, {"python/larch/mod.py": text})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "empty lint-markdown-heading-fence-state" in err


def test_malformed_in_scope_python_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def broken(\n"})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "cannot parse source" in err


def test_excluded_malformed_and_out_of_tree_paths_never_loaded(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {
            "python/larch/prod.py": "x = 1\n",
            "python/larch/test_bad.py": "def broken(\n",
            "python/larch/conftest.py": "def broken(\n",
            "python/tests/support/helper.py": "def broken(\n",
            "scripts/tool.py": "def broken(\n",
            "skills/demo/helper.py": "def broken(\n",
        },
    )
    tracked = [
        "python/larch/prod.py",
        "python/larch/test_bad.py",
        "python/larch/conftest.py",
        "python/tests/support/helper.py",
        "scripts/tool.py",
        "skills/demo/helper.py",
    ]
    runner = _git_ok_runner(tmp_path, tracked)
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""
    # Discovery used rule pathspecs, not the full tracked set.
    assert runner.calls[1][0][:4] == ("git", "ls-files", "--cached", "-z")
    assert "python/**/*.py" in runner.calls[1][0]


def test_excluded_paths_filtered_in_write_mode(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {
            "python/larch/prod.py": "x = 1\n",
            "scripts/tool.py": "def broken(\n",
            "skills/demo/helper.py": VIOLATING,
        },
    )
    tracked = [
        "python/larch/prod.py",
        "scripts/tool.py",
        "skills/demo/helper.py",
    ]
    runner = _git_ok_runner(tmp_path, tracked)
    code, out, _err = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="seed",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    assert baseline.read_text(encoding="utf-8") == "[]\n"


def test_tracked_symlink_is_skipped_in_check_and_write_modes(tmp_path: Path) -> None:
    target = tmp_path / "outside.py"
    _ = target.write_text(VIOLATING, encoding="utf-8")
    link = tmp_path / "python/larch/linked.py"
    link.parent.mkdir(parents=True)
    link.symlink_to(target)

    check_runner = _git_ok_runner(tmp_path, ["python/larch/linked.py"])
    code, out, err = _invoke_rule(tmp_path, check_runner, strict_stale=False)
    assert code == EXIT_CLEAN
    assert out == err == ""

    write_runner = _git_ok_runner(tmp_path, ["python/larch/linked.py"])
    code, out, err = _invoke_rule(
        tmp_path,
        write_runner,
        write_baseline=True,
        initial_reason="seed",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    assert out == err == ""
    assert (tmp_path / "python" / lint.BASELINE_FILENAME).read_text(encoding="utf-8") == "[]\n"


def test_unreadable_in_scope_file_exits_2_with_deterministic_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "x = 1\n"})
    original_open = lint_engine.os.open

    def denied_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(path) == "mod.py" and dir_fd is not None:
            raise PermissionError("read denied")
        if dir_fd is None:
            return original_open(path, flags, mode)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(lint_engine.os, "open", denied_open)
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to read python/larch/mod.py" in err


def test_absent_baseline_clean_scan_exits_0(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def test_absent_baseline_live_findings_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "required baseline missing" in err


def test_check_mode_matches_committed_style_baseline(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_occurrence_row()], indent=2) + "\n",
        encoding="utf-8",
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def test_new_finding_exits_1(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_FINDINGS
    assert "python/larch/mod.py:7: lint-markdown-heading-fence-state" in out
    assert err == ""


def test_stale_baseline_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_occurrence_row()], indent=2) + "\n",
        encoding="utf-8",
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "stale baseline row" in err


def test_malformed_baseline_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("{not-json", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "invalid JSON" in err or "baseline" in err


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_occurrence_row(), _occurrence_row()], indent=2) + "\n",
        encoding="utf-8",
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert out == ""
    assert "duplicate baseline identity" in err


def test_write_requires_initial_reason_for_new_rows(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(
        tmp_path, runner, write_baseline=True, strict_stale=False
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "initial_reason" in err


def test_noop_regeneration_is_byte_identical(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    original = json.dumps([_occurrence_row()], indent=2) + "\n"
    _ = baseline.write_text(original, encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, _err = _invoke_rule(
        tmp_path, runner, write_baseline=True, strict_stale=False
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert baseline.read_text(encoding="utf-8") == original


def test_main_invalid_argument_exits_2() -> None:
    code, out, _err = _invoke_main(Path("/tmp"), ["--no-such-flag"])
    assert code == 2
    assert out == ""


def test_main_empty_initial_reason_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "x = 1\n"})
    code, _out, err = _invoke_main(tmp_path, ["--write", "--initial-reason", "   "])
    assert code == 2
    assert "initial-reason must be non-empty" in err


def test_rule_contract_flags() -> None:
    assert lint.RULE.allow_inline_suppression is False
    assert lint.RULE.occurrence_baseline is True
    assert lint.RULE.syntax_policy == "raise"
    assert lint.RULE.pathspecs == ("python/*.py", "python/**/*.py")
    assert lint.RULE.source_filter is is_production_source_path
