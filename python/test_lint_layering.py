from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_layering as ll


def _write_project(
    root: Path,
    *,
    files: dict[str, str],
    baseline: object,
) -> Path:
    python_dir = root / "python"
    (python_dir / "larch").mkdir(parents=True, exist_ok=True)
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    _ = (python_dir / ll.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")
    return python_dir


# ---------------------------------------------------------------------------
# _importer_package
# ---------------------------------------------------------------------------


def test_importer_package_core() -> None:
    assert ll._importer_package("larch/core/proc.py") == "larch.core"  # type: ignore[reportPrivateUsage]


def test_importer_package_domain() -> None:
    assert ll._importer_package("larch/state/session_env.py") == "larch.state"  # type: ignore[reportPrivateUsage]


def test_importer_package_leaf_module() -> None:
    assert ll._importer_package("larch/errors.py") == "larch.errors"  # type: ignore[reportPrivateUsage]


def test_importer_package_cli_module() -> None:
    assert ll._importer_package("larch/cli.py") == "larch.cli"  # type: ignore[reportPrivateUsage]


def test_importer_package_non_larch() -> None:
    assert ll._importer_package("cli.py") is None  # type: ignore[reportPrivateUsage]


def test_importer_package_root_init() -> None:
    assert ll._importer_package("larch/__init__.py") == "larch"  # type: ignore[reportPrivateUsage]


def test_importer_package_subpackage_init() -> None:
    assert ll._importer_package("larch/core/__init__.py") == "larch.core"  # type: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# _package_tier
# ---------------------------------------------------------------------------


def test_tier_leaf() -> None:
    assert ll._package_tier("larch") == 0  # type: ignore[reportPrivateUsage]
    assert ll._package_tier("larch.errors") == 0  # type: ignore[reportPrivateUsage]
    assert ll._package_tier("larch.io") == 0  # type: ignore[reportPrivateUsage]
    assert ll._package_tier("larch.outcomes") == 0  # type: ignore[reportPrivateUsage]


def test_tier_core() -> None:
    assert ll._package_tier("larch.core") == 1  # type: ignore[reportPrivateUsage]


def test_tier_domain() -> None:
    assert ll._package_tier("larch.state") == 2  # type: ignore[reportPrivateUsage]
    assert ll._package_tier("larch.implement") == 2  # type: ignore[reportPrivateUsage]
    assert ll._package_tier("larch.git") == 2  # type: ignore[reportPrivateUsage]


def test_tier_cli() -> None:
    assert ll._package_tier("larch.cli") == 3  # type: ignore[reportPrivateUsage]


def test_tier_unknown_larch_defaults_to_domain() -> None:
    assert ll._package_tier("larch.newpkg") == 2  # type: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# scan_file — violation detection
# ---------------------------------------------------------------------------


def test_core_importing_domain_is_violation(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from larch.state import session_env\n"
    path = larch_core / "bad.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert len(findings) == 1
    assert findings[0].imported_package == "larch.state"
    assert findings[0].qualified_symbol == "<module>"
    assert findings[0].occurrence == 1


def test_domain_importing_core_is_ok(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_state = python_dir / "larch" / "state"
    larch_state.mkdir(parents=True)
    source = "from larch.core import proc\n"
    path = larch_state / "foo.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.state", importer_tier=2
    )
    assert not findings


def test_domain_importing_cli_is_violation(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_state = python_dir / "larch" / "state"
    larch_state.mkdir(parents=True)
    source = "from larch.cli import COMMANDS\n"
    path = larch_state / "bad.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.state", importer_tier=2
    )
    assert len(findings) == 1
    assert findings[0].imported_package == "larch.cli"


def test_core_importing_leaf_is_ok(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from larch.outcomes import Outcome\n"
    path = larch_core / "config.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert not findings


def test_same_package_import_is_ok(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from larch.core import config\n"
    path = larch_core / "proc.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert not findings


def test_occurrence_counter_per_package(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = (
        "from larch.state import A\n"
        "from larch.state import B\n"
    )
    path = larch_core / "multi.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert len(findings) == 2
    assert findings[0].occurrence == 1
    assert findings[1].occurrence == 2


def test_import_inside_function_is_detected(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "def f():\n    from larch.state import X\n"
    path = larch_core / "lazy.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "f"


def test_barrel_import_unknown_subpackage_is_violation(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from larch import newpkg\n"
    path = larch_core / "barrel.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert len(findings) == 1
    assert findings[0].imported_package == "larch.newpkg"


def test_relative_imports_same_package_ok(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from . import config\n"
    path = larch_core / "relative.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert not findings


def test_relative_import_upward_is_violation(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from ..state import session_env\n"
    path = larch_core / "relative.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    assert len(findings) == 1
    assert findings[0].imported_package == "larch.state"


# ---------------------------------------------------------------------------
# Inline pragma suppression
# ---------------------------------------------------------------------------


def test_inline_pragma_suppresses_violation(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    source = "from larch.state import X  # lint-layering: ok architectural dep\n"
    path = larch_core / "pragmatest.py"
    _ = path.write_text(source, encoding="utf-8")

    findings = ll.scan_file(
        path, python_dir=python_dir, importer_pkg="larch.core", importer_tier=1
    )
    # finding is still emitted by scan_file; suppression happens in _filter_suppressed
    assert len(findings) == 1
    source_lines: dict[str, tuple[str, ...]] = {
        "larch/core/pragmatest.py": tuple(source.splitlines())
    }
    suppressed = ll._filter_suppressed(findings, source_lines_by_file=source_lines)  # type: ignore[reportPrivateUsage]
    assert not suppressed


# ---------------------------------------------------------------------------
# Baseline load / validate
# ---------------------------------------------------------------------------


def test_load_baseline_valid(tmp_path: Path) -> None:
    data = [
        {
            "file": "larch/core/foo.py",
            "qualified_symbol": "<module>",
            "imported_package": "larch.state",
            "occurrence": 1,
            "reason": "grandfathered",
        }
    ]
    baseline_path = tmp_path / ll.BASELINE_FILENAME
    _ = baseline_path.write_text(json.dumps(data), encoding="utf-8")
    records = ll.load_baseline(baseline_path)
    assert len(records) == 1
    assert records[0]["imported_package"] == "larch.state"


def test_load_baseline_rejects_extra_keys(tmp_path: Path) -> None:
    data = [
        {
            "file": "larch/core/foo.py",
            "qualified_symbol": "<module>",
            "imported_package": "larch.state",
            "occurrence": 1,
            "reason": "r",
            "extra": "bad",
        }
    ]
    baseline_path = tmp_path / ll.BASELINE_FILENAME
    _ = baseline_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ll.BaselineError, match="must have exactly"):
        _ = ll.load_baseline(baseline_path)


def test_load_baseline_rejects_duplicate(tmp_path: Path) -> None:
    row = {
        "file": "larch/core/foo.py",
        "qualified_symbol": "<module>",
        "imported_package": "larch.state",
        "occurrence": 1,
        "reason": "r",
    }
    baseline_path = tmp_path / ll.BASELINE_FILENAME
    _ = baseline_path.write_text(json.dumps([row, row]), encoding="utf-8")
    with pytest.raises(ll.BaselineError, match="duplicate"):
        _ = ll.load_baseline(baseline_path)


def test_load_baseline_rejects_empty_reason(tmp_path: Path) -> None:
    data = [
        {
            "file": "larch/core/foo.py",
            "qualified_symbol": "<module>",
            "imported_package": "larch.state",
            "occurrence": 1,
            "reason": "   ",
        }
    ]
    baseline_path = tmp_path / ll.BASELINE_FILENAME
    _ = baseline_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ll.BaselineError, match="invalid reason"):
        _ = ll.load_baseline(baseline_path)


def test_load_baseline_rejects_invalid_imported_package(tmp_path: Path) -> None:
    data = [
        {
            "file": "larch/core/foo.py",
            "qualified_symbol": "<module>",
            "imported_package": "not_larch",
            "occurrence": 1,
            "reason": "r",
        }
    ]
    baseline_path = tmp_path / ll.BASELINE_FILENAME
    _ = baseline_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ll.BaselineError, match="invalid imported_package"):
        _ = ll.load_baseline(baseline_path)


# ---------------------------------------------------------------------------
# End-to-end main() — check mode
# ---------------------------------------------------------------------------


def test_main_check_passes_when_baselined(tmp_path: Path) -> None:
    baseline = [
        {
            "file": "larch/core/bad.py",
            "qualified_symbol": "<module>",
            "imported_package": "larch.state",
            "occurrence": 1,
            "reason": "test",
        }
    ]
    _ = _write_project(
        tmp_path,
        files={"larch/core/bad.py": "from larch.state import X\n"},
        baseline=baseline,
    )
    rc = ll.main(["--root", str(tmp_path)])
    assert rc == 0


def test_main_check_fails_on_new_violation(tmp_path: Path) -> None:
    _ = _write_project(
        tmp_path,
        files={"larch/core/bad.py": "from larch.state import X\n"},
        baseline=[],
    )
    rc = ll.main(["--root", str(tmp_path)])
    assert rc == 1


def test_main_write_generates_baseline(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    larch_core = python_dir / "larch" / "core"
    larch_core.mkdir(parents=True)
    _ = (python_dir / "larch" / "core" / "bad.py").write_text(
        "from larch.state import X\n", encoding="utf-8"
    )
    rc = ll.main([
        "--root", str(tmp_path),
        "--write",
        "--initial-reason", "test reason",
    ])
    assert rc == 0
    baseline_path = python_dir / ll.BASELINE_FILENAME
    assert baseline_path.is_file()
    records = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["reason"] == "test reason"
    assert records[0]["imported_package"] == "larch.state"


def test_main_check_no_baseline_exits_tool_failure(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    (python_dir / "larch").mkdir(parents=True)
    rc = ll.main(["--root", str(tmp_path)])
    assert rc == ll.TOOL_FAILURE_EXIT


def test_main_check_no_violations_exits_zero(tmp_path: Path) -> None:
    _ = _write_project(
        tmp_path,
        files={"larch/core/clean.py": "from larch.core import config\n"},
        baseline=[],
    )
    rc = ll.main(["--root", str(tmp_path)])
    assert rc == 0
