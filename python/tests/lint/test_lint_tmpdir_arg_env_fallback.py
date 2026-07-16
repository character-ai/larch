"""Coverage for the engine-backed tmpdir-arg-env-fallback rule."""

from __future__ import annotations

import json
from pathlib import Path

from larch.lint import lint_tmpdir_arg_env_fallback as lint
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    SourceFile,
)
from tests.lint.test_lint_engine import (
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
    _write_files,  # type: ignore[reportPrivateUsage]  # importing test-internal helpers from sibling test module
)
from tests.support.lint_repo import (
    make_lint_main_invoker,
    make_python_baseline_rule_invoker,
)

VIOLATING_VALIDATE = (
    "def run(args) -> None:\n"
    "    validate_tmpdir(args.tmpdir)\n"
)

VIOLATING_ATTR_VALIDATE = (
    "def run(args) -> None:\n"
    "    helpers.validate_tmpdir(args.tmpdir)\n"
)

VIOLATING_PATH = (
    "from pathlib import Path\n"
    "def run(args) -> None:\n"
    "    path = Path(args.tmpdir)\n"
)

COMPLIANT_CONFIG = (
    "import os\n"
    "from larch.core import config\n"
    "def run(args) -> None:\n"
    "    validate_tmpdir(args.tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ''))\n"
)

COMPLIANT_LOCAL = (
    "import os\n"
    "from pathlib import Path\n"
    "ENV_IMPLEMENT_TMPDIR = 'IMPLEMENT_TMPDIR'\n"
    "def run(args) -> None:\n"
    "    path = Path(args.tmpdir or os.environ.get(ENV_IMPLEMENT_TMPDIR, ''))\n"
)

BOOL_OP_OTHER = (
    "def run(args) -> None:\n"
    "    validate_tmpdir(args.tmpdir or args.other)\n"
)


def _source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _occurrence_row(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "run",
    pattern_name: str = "validate_tmpdir",
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


_invoke_main = make_lint_main_invoker(lint.main)
_invoke_rule = make_python_baseline_rule_invoker(lint.RULE, lint.BASELINE_FILENAME)


def test_bare_validate_tmpdir_is_flagged() -> None:
    findings = lint.detect(_source("python/larch/mod.py", VIOLATING_VALIDATE))
    assert [(f.pattern_name, f.qualified_symbol, f.occurrence, f.line) for f in findings] == [
        ("validate_tmpdir", "run", 1, 2)
    ]


def test_attribute_validate_tmpdir_is_flagged() -> None:
    findings = lint.detect(_source("python/larch/mod.py", VIOLATING_ATTR_VALIDATE))
    assert [(f.pattern_name, f.qualified_symbol, f.occurrence) for f in findings] == [
        ("validate_tmpdir", "run", 1)
    ]


def test_bare_path_args_tmpdir_is_flagged() -> None:
    findings = lint.detect(_source("python/larch/mod.py", VIOLATING_PATH))
    assert [(f.pattern_name, f.qualified_symbol, f.occurrence, f.line) for f in findings] == [
        ("Path", "run", 1, 3)
    ]


def test_fallback_with_config_constant_passes() -> None:
    assert not lint.detect(_source("python/larch/mod.py", COMPLIANT_CONFIG))


def test_fallback_with_local_env_name_passes() -> None:
    assert not lint.detect(_source("python/larch/mod.py", COMPLIANT_LOCAL))


def test_boolop_without_direct_args_tmpdir_node_is_ignored() -> None:
    assert not lint.detect(_source("python/larch/mod.py", BOOL_OP_OTHER))


def test_path_with_extra_args_is_outside_rule() -> None:
    text = (
        "from pathlib import Path\n"
        "def run(args) -> None:\n"
        "    path = Path(args.tmpdir, 'child')\n"
    )
    assert not lint.detect(_source("python/larch/mod.py", text))


def test_occurrence_stable_across_line_movement() -> None:
    early = (
        "def run(args) -> None:\n"
        "    validate_tmpdir(args.tmpdir)\n"
    )
    late = (
        "def run(args) -> None:\n"
        "    # padding\n"
        "    # more padding\n"
        "    validate_tmpdir(args.tmpdir)\n"
    )
    early_hits = lint.detect(_source("python/larch/mod.py", early))
    late_hits = lint.detect(_source("python/larch/mod.py", late))
    assert [(f.pattern_name, f.occurrence) for f in early_hits] == [
        (f.pattern_name, f.occurrence) for f in late_hits
    ]
    assert early_hits[0].line != late_hits[0].line


def test_production_path_filter_excludes_tests_and_helpers() -> None:
    assert lint.is_production_source_path("python/larch/prod.py")
    assert not lint.is_production_source_path("python/larch/test_mod.py")
    assert not lint.is_production_source_path("python/larch/conftest.py")
    assert not lint.is_production_source_path("python/tests/helper.py")
    assert not lint.is_production_source_path("python/root.py")


def test_reason_bearing_baseline_suppresses(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING_VALIDATE})
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


def test_missing_reason_on_write_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING_VALIDATE})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(
        tmp_path, runner, write_baseline=True, strict_stale=False
    )
    assert code == EXIT_ERROR
    assert "reason" in err.lower() or "missing" in err.lower()


def test_duplicate_baseline_rows_fail(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING_VALIDATE})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    row = _occurrence_row()
    _ = baseline.write_text(json.dumps([row, row], indent=2) + "\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert "duplicate" in err.lower()


def test_malformed_baseline_json_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def run() -> None:\n    return None\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("{not-json", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert "json" in err.lower() or "invalid" in err.lower()


def test_unreadable_baseline_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def run() -> None:\n    return None\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.symlink_to(tmp_path / "missing-baseline.json")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert err


def test_stale_baseline_row_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def run() -> None:\n    return None\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text(
        json.dumps([_occurrence_row()], indent=2) + "\n",
        encoding="utf-8",
    )
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(tmp_path, runner)
    assert code == EXIT_ERROR
    assert "stale baseline row" in err


def test_new_finding_without_baseline_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING_PATH})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, out, _err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_FINDINGS
    assert "Path" in out
    assert "mod.py" in out


def test_malformed_python_exits_2(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def broken(\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    _ = baseline.write_text("[]\n", encoding="utf-8")
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, err = _invoke_rule(tmp_path, runner, strict_stale=False)
    assert code == EXIT_ERROR
    assert err


def test_live_tree_baseline_only_documents_bgjob_site() -> None:
    repo = Path(__file__).resolve().parents[2]
    baseline: list[dict[str, object]] = json.loads(
        (repo / "tmpdir-arg-env-fallback-baseline.json").read_text(encoding="utf-8")
    )
    assert len(baseline) == 1
    row = baseline[0]
    assert row["file"] == "larch/bgjob/cli.py"
    assert row["qualified_symbol"] == "_build_spec"
    assert row["pattern_name"] == "Path"
    assert row["occurrence"] == 1
    assert str(row["reason"]).strip()


def test_main_empty_initial_reason_fails(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": "def run() -> None:\n    return None\n"})
    code, _out, err = _invoke_main(tmp_path, ["--write", "--initial-reason", "   "])
    assert code == EXIT_ERROR
    assert "initial-reason" in err


def test_write_with_initial_reason_succeeds(tmp_path: Path) -> None:
    _write_files(tmp_path, {"python/larch/mod.py": VIOLATING_VALIDATE})
    runner = _git_ok_runner(tmp_path, ["python/larch/mod.py"])
    code, _out, _err = _invoke_rule(
        tmp_path,
        runner,
        write_baseline=True,
        initial_reason="grandfathered for test",
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    baseline = json.loads(
        (tmp_path / "python" / lint.BASELINE_FILENAME).read_text(encoding="utf-8")
    )
    assert baseline[0]["reason"] == "grandfathered for test"
    assert baseline[0]["pattern_name"] == "validate_tmpdir"


def test_rule_contract_flags() -> None:
    assert lint.RULE.occurrence_baseline is True
    assert lint.RULE.require_baseline is True
    assert lint.RULE.stale_baseline_on_clean_scan is True
    assert lint.RULE.allow_inline_suppression is False
