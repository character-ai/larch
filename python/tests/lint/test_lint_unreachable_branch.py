"""Coverage for the engine-backed unreachable-branch rule."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from larch.lint import engine as lint_engine
from larch.lint import lint_unreachable_branch as lint
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    ScanError,
    SourceFile,
    render_finding,
)
from larch.lint.unreachable_branch_detector import is_production_source_path
from tests.lint.test_lint_engine import (
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
    _write_files,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
)
from tests.support.lint_repo import (
    make_lint_main_invoker,
    make_python_baseline_rule_invoker,
)

VIOLATING = (
    "def run(flag: bool, value: int) -> int:\n"
    "    if flag:\n"
    "        return value\n"
    "    if flag:\n"
    "        return value\n"
    "    return 0\n"
)

COMPLIANT = "def run() -> int:\n    return 0\n"


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "run",
    occurrence: int = 1,
    normalized_condition: str = "Name('flag', Load())",
    reason: str = "grandfathered",
) -> dict[str, object]:
    return {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "occurrence": occurrence,
        "normalized_condition": normalized_condition,
        "reason": reason,
    }


_invoke_main = make_lint_main_invoker(lint.main)
_invoke_rule = make_python_baseline_rule_invoker(lint.RULE, lint.BASELINE_FILENAME)


def test_repeated_conditional_return_same_value(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(VIOLATING, encoding="utf-8")
    findings = lint.scan_file(path, larch_dir=larch_dir)
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "run"
    assert findings[0].occurrence == 1
    assert findings[0].normalized_condition == "Name('flag', Load())"


def test_different_return_values_not_flagged(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def run(flag: bool) -> int:\n"
        "    if flag:\n"
        "        return 1\n"
        "    if flag:\n"
        "        return 2\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert not lint.scan_file(path, larch_dir=larch_dir)


def test_intervening_assignment_clears_facts(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    flag = not flag\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert not lint.scan_file(path, larch_dir=larch_dir)


def test_final_verdict_shape_regression(tmp_path: Path) -> None:
    """Mirror the #6153 dead second mechanical_verdict branch shape."""
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def _final_verdict(bundle) -> str:\n"
        "    if bundle.mechanical_verdict:\n"
        "        return bundle.mechanical_verdict\n"
        "    # deep path omitted\n"
        "    if bundle.mechanical_verdict:\n"
        "        return bundle.mechanical_verdict\n"
        "    return 'UNKNOWN'\n",
        encoding="utf-8",
    )
    findings = lint.scan_file(path, larch_dir=larch_dir)
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "_final_verdict"


def test_nested_function_isolation(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def outer(flag: bool, value: int) -> int:\n"
        "    def inner(flag: bool, value: int) -> int:\n"
        "        if flag:\n"
        "            return value\n"
        "        if flag:\n"
        "            return value\n"
        "        return 0\n"
        "    return inner(flag, value)\n",
        encoding="utf-8",
    )
    findings = lint.scan_file(path, larch_dir=larch_dir)
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "outer.inner"


def test_nested_functions_under_loop_are_scanned_once(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def outer(items) -> None:\n"
        "    for item in items:\n"
        "        def inner(flag: bool, value: int) -> int:\n"
        "            if flag:\n"
        "                return value\n"
        "            if flag:\n"
        "                return value\n"
        "            return 0\n"
        "        inner(True, 1)\n",
        encoding="utf-8",
    )
    findings = lint.scan_file(path, larch_dir=larch_dir)
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "outer.inner"


def test_elif_preparation_and_unconditional_return_branches_detected(
    tmp_path: Path,
) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        audit = value\n"
        "        return value\n"
        "    elif flag:\n"
        "        return value\n"
        "    return value\n"
        "    if flag:\n"
        "        return value\n",
        encoding="utf-8",
    )
    assert len(lint.scan_file(path, larch_dir=larch_dir)) == 2


def test_async_function_supported(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "async def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert len(lint.scan_file(path, larch_dir=larch_dir)) == 1


def test_suppression_on_condition_line(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:  # lint-unreachable-branch: ok intentional duplicate\n"
        "        return value\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert not lint.scan_file(path, larch_dir=larch_dir)


def test_suppressed_match_does_not_consume_occurrence() -> None:
    text = (
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:  # lint-unreachable-branch: ok first\n"
        "        return value\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n"
    )
    findings = lint.detect(_source("python/larch/mod.py", text))
    assert len(findings) == 1
    assert findings[0].occurrence == 1
    assert findings[0].pattern_name == "Name('flag', Load())"
    assert findings[0].qualified_symbol == "run"
    rendered = render_finding(findings[0])
    assert rendered.startswith("python/larch/mod.py:")
    assert "lint-unreachable-branch" in rendered
    assert "occurrence 1" in rendered


def test_empty_suppression_reason_raises() -> None:
    text = (
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:  # lint-unreachable-branch: ok\n"
        "        return value\n"
        "    return 0\n"
    )
    with pytest.raises(ScanError, match="empty lint-unreachable-branch"):
        _ = lint.detect(_source("python/larch/mod.py", text))


def test_adapted_findings_pass_occurrence_baseline_validation() -> None:
    findings = lint.detect(_source("python/larch/mod.py", VIOLATING))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.qualified_symbol == "run"
    assert finding.pattern_name == "Name('flag', Load())"
    assert finding.occurrence == 1
    validated = lint_engine._validate_finding(  # type: ignore[reportPrivateUsage]  # accessing private engine internals for round-trip validation
        finding, source=_source("python/larch/mod.py", VIOLATING), rule=lint.RULE
    )
    assert validated.pattern_name == finding.pattern_name
    row = lint_engine.OccurrenceBaselineRow(
        path=validated.path,
        qualified_symbol=validated.qualified_symbol or "",
        pattern_name=validated.pattern_name or "",
        occurrence=validated.occurrence or 0,
        reason="bootstrap",
    )
    serialized = lint_engine._serialized_baseline(  # type: ignore[reportPrivateUsage]  # accessing private engine internals for round-trip validation
        [row], occurrence_pattern_field="normalized_condition"
    )
    assert '"normalized_condition"' in serialized
    assert '"pattern_name"' not in serialized
    parsed = lint_engine._parse_baseline_text(  # type: ignore[reportPrivateUsage]  # accessing private engine internals for round-trip validation
        serialized, source="round-trip"
    )
    assert parsed == [row]


def test_malformed_source_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def broken(\n"})
    _ = (tmp_path / "python" / lint.BASELINE_FILENAME).write_text(
        "[]\n", encoding="utf-8"
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "cannot parse source" in err


def test_scope_excludes_tests(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    for relpath in ["test_mod.py", "conftest.py", "prod.py"]:
        path = larch_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("x = 1\n", encoding="utf-8")
    assert [p.name for p in lint.iter_source_files(larch_dir)] == ["prod.py"]


def test_production_path_filter_and_pathspecs() -> None:
    assert is_production_source_path("python/larch/mod.py")
    assert not is_production_source_path("python/larch/test_mod.py")
    assert not is_production_source_path("python/larch/conftest.py")
    assert not is_production_source_path("python/cli.py")
    assert not is_production_source_path("python/bootstrap.py")
    assert lint.RULE.pathspecs == ("python/larch/*.py", "python/larch/**/*.py")
    assert lint.RULE.source_filter is is_production_source_path


def test_engine_cli_skips_exempt_larch_sources(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {
            "python/larch/prod.py": VIOLATING,
            "python/larch/test_skip.py": VIOLATING,
            "python/larch/conftest.py": VIOLATING,
            "python/cli.py": VIOLATING,
        },
    )
    tracked = [
        "python/larch/prod.py",
        "python/larch/test_skip.py",
        "python/larch/conftest.py",
        "python/cli.py",
    ]
    runner = _git_ok_runner(tmp_path, tracked)
    code, out, _ = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="bootstrap",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    baseline = json.loads(
        (tmp_path / "python" / lint.BASELINE_FILENAME).read_text(encoding="utf-8")
    )
    assert len(baseline) == 1
    assert baseline[0]["file"] == "larch/prod.py"
    assert list(baseline[0]) == [
        "file",
        "qualified_symbol",
        "occurrence",
        "normalized_condition",
        "reason",
    ]


def test_baseline_schema_and_stale(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, _ = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="bootstrap",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    baseline_path = tmp_path / "python" / lint.BASELINE_FILENAME
    original = baseline_path.read_text(encoding="utf-8")
    record = json.loads(original)[0]
    assert list(record) == [
        "file",
        "qualified_symbol",
        "occurrence",
        "normalized_condition",
        "reason",
    ]
    assert record["reason"] == "bootstrap"
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, _ = _invoke_rule(tmp_path, runner)
    assert code == EXIT_CLEAN
    assert out == ""

    _ = (tmp_path / "python" / "larch" / "mod.py").write_text(COMPLIANT, encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert "stale baseline row" in err


def test_duplicate_baseline_rejected(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_record(), _record()], indent=2) + "\n", encoding="utf-8"
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert "duplicate baseline identity" in err


def test_new_finding_exits_1(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, _ = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_FINDINGS
    assert "python/larch/mod.py:" in out
    assert "lint-unreachable-branch" in out


def test_clean_scan_without_baseline_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])

    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)

    assert code == EXIT_ERROR
    assert out == ""
    assert "failed to read baseline" in err


def test_noop_regeneration_is_byte_identical(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    original = json.dumps([_record()], indent=2) + "\n"
    _ = baseline.write_text(original, encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, _ = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="bootstrap",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    assert baseline.read_text(encoding="utf-8") == original


def test_main_empty_initial_reason_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    code, _, err = _invoke_main(tmp_path, ["--write", "--initial-reason", "  "])
    assert code == EXIT_ERROR
    assert "--initial-reason must be non-empty" in err


def test_rule_contract_flags() -> None:
    assert lint.RULE.occurrence_baseline is True
    assert lint.RULE.require_baseline is True
    assert lint.RULE.allow_inline_suppression is False
    assert lint.RULE.occurrence_pattern_field == "normalized_condition"
    assert lint.RULE.syntax_policy == "raise"
    assert lint.RULE.source_filter is is_production_source_path
