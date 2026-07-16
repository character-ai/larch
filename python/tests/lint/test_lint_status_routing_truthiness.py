"""Coverage for the status-routing-truthiness lint rule."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from larch import cli as larch_cli
from larch.lint import lint_status_routing_truthiness as lint
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    Finding,
)
from tests.lint.test_lint_engine import (
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
    _write_files,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
)
from tests.support.lint_repo import (
    make_lint_main_invoker,
    make_python_baseline_rule_invoker,
)

VIOLATING = (
    "def route(status: str) -> str:\n"
    "    if status:\n"
    "        return status\n"
    '    if status == "DONE":\n'
    '        return "done"\n'
    '    return "missing"\n'
)

COMPLIANT = (
    "def route(status: str) -> str:\n"
    "    if status in TERMINAL:\n"
    "        return status\n"
    '    return "missing"\n'
)


def _hits(text: str) -> list[Finding]:
    return lint.scan_module(ast.parse(text), path="python/larch/mod.py")


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "route",
    occurrence: int = 1,
    normalized_condition: str = "Name('status', Load())",
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
_invoke_rule = make_python_baseline_rule_invoker(
    lint.RULE, lint.BASELINE_FILENAME, non_strict_when_writing=True
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "def run(status):\n"
            '    if status == "DONE":\n'
            "        pass\n"
            "    if status:\n"
            "        pass\n",
            1,
        ),
        (
            "def run(bundle):\n"
            '    if bundle.mechanical_verdict == "NEEDS_DEEP":\n'
            "        pass\n"
            "    if bundle.mechanical_verdict:\n"
            "        pass\n",
            1,
        ),
        (
            "def run(status):\n"
            '    if status == "DONE":\n'
            "        pass\n"
            "    while status:\n"
            "        break\n"
            '    x = "a" if status else "b"\n'
            "    if status and True:\n"
            "        pass\n"
            "    if False or status:\n"
            "        pass\n"
            "    if not status:\n"
            "        pass\n"
            "    y = bool(status)\n",
            6,
        ),
    ],
)
def test_detector_contexts_and_shapes(source: str, expected: int) -> None:
    assert len(_hits(source)) == expected


def test_dedupe_nested_not() -> None:
    hits = _hits(
        "def run(status):\n"
        '    if status != "X":\n'
        "        pass\n"
        "    if not status:\n"
        "        pass\n"
    )
    assert len(hits) == 1


def test_evidence_shapes_and_exclusions() -> None:
    assert len(
        _hits(
            "def run(status):\n"
            '    if "DONE" == status:\n'
            "        pass\n"
            "    if status:\n"
            "        pass\n"
        )
    ) == 1
    assert len(
        _hits(
            "def run(outcome):\n"
            "    if outcome is Outcome.OK:\n"
            "        pass\n"
            "    if outcome:\n"
            "        pass\n"
        )
    ) == 1
    assert len(
        _hits(
            "def run(status):\n"
            "    if status in TERMINAL_RESULTS:\n"
            "        pass\n"
            "    if status:\n"
            "        pass\n"
        )
    ) == 1
    assert not _hits(
        "def run(status):\n"
        "    if status is None:\n"
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert not _hits(
        "def run(status):\n"
        "    if status == True:\n"
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert not _hits(
        "def run(status):\n"
        "    if status == 1:\n"
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert not _hits(
        "def run(status):\n"
        '    if status == "":\n'
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert not _hits(
        "def run(status):\n"
        "    if status in {}:\n"
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )


def test_explicit_checks_and_optional_without_evidence() -> None:
    assert not _hits(
        "def run(verdict):\n"
        "    if verdict in TERMINAL_VERDICTS:\n"
        "        return verdict\n"
        "    if verdict is None:\n"
        "        return fallback()\n"
        "    if len(verdict):\n"
        "        return verdict\n"
        "    if any(verdict):\n"
        "        return verdict\n"
        "    if all(verdict):\n"
        "        return verdict\n"
    )
    assert not _hits(
        "def run(rendered_result):\n"
        "    if rendered_result:\n"
        "        print(rendered_result)\n"
    )


def test_unstable_candidates_ignored() -> None:
    assert not _hits(
        "def run(items):\n"
        '    if items[0].status == "DONE":\n'
        "        pass\n"
        "    if items[0].status:\n"
        "        pass\n"
        '    if get_status() == "DONE":\n'
        "        pass\n"
        "    if get_status():\n"
        "        pass\n"
    )


def test_regression_6153_first_truthiness_still_fails() -> None:
    hits = _hits(
        "def final_verdict(bundle):\n"
        "    if bundle.mechanical_verdict:\n"
        "        return bundle.mechanical_verdict\n"
        '    if bundle.mechanical_verdict == "NEEDS_DEEP":\n'
        "        return read_deep_verdict(bundle)\n"
        '    return "UNKNOWN"\n'
    )
    assert len(hits) == 1
    assert hits[0].qualified_symbol == "final_verdict"
    assert "mechanical_verdict" in (hits[0].pattern_name or "")


def test_scope_isolation_and_async() -> None:
    hits = _hits(
        "def outer(status):\n"
        "    def inner(status):\n"
        '        if status == "X":\n'
        "            pass\n"
        "        if status:\n"
        "            pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert len(hits) == 1
    assert hits[0].qualified_symbol == "outer.inner"

    sibling = _hits(
        "def a(status):\n"
        '    if status == "X":\n'
        "        pass\n"
        "def b(status):\n"
        "    if status:\n"
        "        pass\n"
    )
    assert not sibling

    async_hits = _hits(
        "async def run(status):\n"
        '    if status == "DONE":\n'
        "        pass\n"
        "    if status:\n"
        "        pass\n"
    )
    assert len(async_hits) == 1
    assert async_hits[0].qualified_symbol == "run"


def test_occurrence_stable_across_line_movement() -> None:
    base = _hits(
        "def run(status):\n"
        '    if status == "DONE":\n'
        "        pass\n"
        "    if status:\n"
        "        pass\n"
        "    if not status:\n"
        "        pass\n"
    )
    moved = _hits(
        "def run(status):\n"
        '    if status == "DONE":\n'
        "        pass\n"
        "    helper = 1\n"
        "    if status:\n"
        "        pass\n"
        "    helper = 2\n"
        "    if not status:\n"
        "        pass\n"
    )
    assert [h.occurrence for h in base] == [1, 2]
    assert [h.occurrence for h in moved] == [1, 2]
    assert base[0].pattern_name == moved[0].pattern_name


def test_pathspecs_include_shallow_and_recursive() -> None:
    assert lint.PATHSPECS == ("python/larch/*.py", "python/larch/**/*.py")
    assert lint.is_production_source_path("python/larch/cli.py")
    assert lint.is_production_source_path("python/larch/core/config.py")
    assert not lint.is_production_source_path("python/larch/test_mod.py")
    assert not lint.is_production_source_path(lint._SELF_MODULE)  # type: ignore[reportPrivateUsage]  # assert self-module exclusion


def test_suppression_reason_via_engine(tmp_path: Path) -> None:
    text = (
        "def run(status):\n"
        '    if status == "DONE":\n'
        "        pass\n"
        "    if status:  # lint-status-routing-truthiness: ok presence check\n"
        "        pass\n"
    )
    _write_files(tmp_path, {"python/larch/mod.py": text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""

    bad = (
        "def run(status):\n"
        '    if status == "DONE":\n'
        "        pass\n"
        "    if status:  # lint-status-routing-truthiness: ok\n"
        "        pass\n"
    )
    _write_files(tmp_path, {"python/larch/mod.py": bad})
    runner2 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code2, out2, err2 = _invoke_rule(tmp_path, runner2, strict_stale=False)
    assert code2 == EXIT_ERROR
    assert out2 == ""
    assert "non-empty reason" in err2


def test_new_finding_fails_matching_warns(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, _err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_FINDINGS
    assert "lint-status-routing-truthiness" in out
    assert "Name('status', Load())" in out

    _ = baseline.write_text(json.dumps([_record()]), encoding="utf-8")
    runner2 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code2, out2, err2 = _invoke_rule(tmp_path, runner2, strict_stale=False)
    assert code2 == EXIT_CLEAN
    assert out2 == ""
    assert "warning: matching baseline finding:" in err2
    assert "python/larch/mod.py:" in err2


def test_missing_baseline_exits_2_even_when_clean(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "does not exist" in err


def test_stale_duplicate_malformed_baseline_rows(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": COMPLIANT})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_record(normalized_condition="Name('gone', Load())")]),
        encoding="utf-8",
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=True)
    assert code == EXIT_ERROR
    assert out == ""
    assert "stale baseline row" in err

    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    _ = baseline.write_text(
        json.dumps([_record(), _record()]),
        encoding="utf-8",
    )
    runner2 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code2, _, err2 = _invoke_rule(tmp_path, runner2, strict_stale=False)
    assert code2 == EXIT_ERROR
    assert "duplicate" in err2.lower() or "invalid" in err2.lower() or "reason" in err2

    _ = baseline.write_text("{not-json", encoding="utf-8")
    runner3 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code3, _, err3 = _invoke_rule(tmp_path, runner3, strict_stale=False)
    assert code3 == EXIT_ERROR
    assert err3


def test_empty_reason_extra_key_unsafe_path_baseline(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    bad_reason = _record(reason="")
    _ = baseline.write_text(json.dumps([bad_reason]), encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert "reason" in err

    extra = _record()
    extra["extra"] = "nope"
    _ = baseline.write_text(json.dumps([extra]), encoding="utf-8")
    runner2 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code2, _, _err2 = _invoke_rule(tmp_path, runner2, strict_stale=False)
    assert code2 == EXIT_ERROR

    unsafe = _record(file="../etc/passwd.py")
    _ = baseline.write_text(json.dumps([unsafe]), encoding="utf-8")
    runner3 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code3, _, err3 = _invoke_rule(tmp_path, runner3, strict_stale=False)
    assert code3 == EXIT_ERROR
    assert "invalid file" in err3 or "file" in err3


def test_write_preserves_reasons_and_rejects_new_without_reason(
    tmp_path: Path,
) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_record(reason="kept-reason")]), encoding="utf-8"
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, _ = _invoke_rule(tmp_path, runner, write_baseline=True)
    assert code == EXIT_CLEAN
    rows = json.loads(baseline.read_text(encoding="utf-8"))
    assert rows[0]["reason"] == "kept-reason"

    dual = (
        "def route(status: str) -> str:\n"
        "    if status:\n"
        "        return status\n"
        '    if status == "DONE":\n'
        '        return "done"\n'
        "    if not status:\n"
        '        return "missing"\n'
        '    return "missing"\n'
    )
    _write_files(tmp_path, {"python/larch/mod.py": dual})
    runner2 = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code2, _, err2 = _invoke_rule(tmp_path, runner2, write_baseline=True)
    assert code2 == EXIT_ERROR
    assert "reason" in err2.lower() or "initial" in err2.lower()


def test_initial_write_accepts_reason(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _, _ = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="pre-existing status truthiness before the status-routing-truthiness ratchet",
    )
    assert code == EXIT_CLEAN
    rows = json.loads(baseline.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["reason"].startswith("pre-existing")
    assert rows[0]["normalized_condition"] == "Name('status', Load())"


def test_syntax_failure_and_cli_registration(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def broken(\n"})
    _ = (tmp_path / "python" / lint.BASELINE_FILENAME).write_text(
        "[]\n", encoding="utf-8"
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert out == ""
    assert "cannot parse source" in err

    assert ("lint", "status-routing-truthiness") in larch_cli._REGISTRY  # type: ignore[reportPrivateUsage]  # accessing _REGISTRY to verify cli dispatch registration
    assert lint.RULE.rule_id == "lint-status-routing-truthiness"


def test_repository_scan_clean_against_committed_baseline() -> None:
    root = Path(__file__).resolve().parents[2].parent
    code, out, err = _invoke_main(root, [])
    assert code == EXIT_CLEAN
    assert out == ""
    # Matching grandfathered rows may warn; stale/new must not appear.
    assert "stale baseline row" not in err
    assert not out
