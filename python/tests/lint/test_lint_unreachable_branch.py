from __future__ import annotations

import json
from pathlib import Path


from larch.lint import lint_unreachable_branch as lint


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "run",
    occurrence: int = 1,
    normalized_condition: str = "Name('flag')",
    reason: str = "grandfathered",
) -> dict[str, object]:
    return {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "occurrence": occurrence,
        "normalized_condition": normalized_condition,
        "reason": reason,
    }


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        _ = (python_dir / lint.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")


def test_repeated_conditional_return_same_value(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    path = larch_dir / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n",
        encoding="utf-8",
    )
    findings = lint.scan_file(path, larch_dir=larch_dir)
    assert len(findings) == 1
    assert findings[0].qualified_symbol == "run"


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


def test_elif_preparation_and_unconditional_return_branches_detected(tmp_path: Path) -> None:
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


def test_malformed_source_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": "def broken(\n"}, baseline=[])
    assert lint.main(["--root", str(tmp_path)]) == 2


def test_baseline_schema_and_stale(tmp_path: Path) -> None:
    source = (
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n"
    )
    _write_project(tmp_path, files={"larch/mod.py": source}, baseline=None)
    assert (
        lint.main(
            ["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap"]
        )
        == 0
    )
    assert lint.main(["--root", str(tmp_path)]) == 0

    # Replace source so the baselined finding disappears; stale row must fail.
    _ = (tmp_path / "python" / "larch" / "mod.py").write_text(
        "def run() -> int:\n    return 0\n", encoding="utf-8"
    )
    assert lint.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_rejected(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": "def run() -> int:\n    return 0\n"},
        baseline=[_record(), _record()],
    )
    assert lint.main(["--root", str(tmp_path)]) == 2


def test_new_finding_exits_1(tmp_path: Path) -> None:
    source = (
        "def run(flag: bool, value: int) -> int:\n"
        "    if flag:\n"
        "        return value\n"
        "    if flag:\n"
        "        return value\n"
        "    return 0\n"
    )
    _write_project(tmp_path, files={"larch/mod.py": source}, baseline=[])
    assert lint.main(["--root", str(tmp_path)]) == 1


def test_scope_excludes_tests(tmp_path: Path) -> None:
    larch_dir = tmp_path / "python" / "larch"
    for relpath in ["test_mod.py", "conftest.py", "prod.py"]:
        path = larch_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("x = 1\n", encoding="utf-8")
    assert [p.name for p in lint.iter_source_files(larch_dir)] == ["prod.py"]
