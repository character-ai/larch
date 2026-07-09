from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from larch.lint import lint_monkeypatch_facade_binding as lmfb


def _record(
    *,
    file: str = "test_facade.py",
    qualified_symbol: str = "test_patch",
    facade_module: str = "larch.facade",
    attribute: str = "target",
    defining_module: str = "larch.defs",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "facade_module": facade_module,
        "attribute": attribute,
        "defining_module": defining_module,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None) -> None:
    python_dir = root / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(dedent(source), encoding="utf-8")
    if baseline is not None:
        _ = (python_dir / lmfb.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")


def _base_files(test_source: str, *, facade_source: str = "from larch.defs import target\n") -> dict[str, str]:
    return {
        "larch/defs.py": "def target():\n    return 'real'\n",
        "larch/facade.py": facade_source,
        "test_facade.py": test_source,
    }


def _scan_single(root: Path) -> list[lmfb.Finding]:
    python_dir = root / "python"
    resolver = lmfb.ModuleResolver(python_dir)
    return lmfb.scan_file(python_dir / "test_facade.py", python_dir=python_dir, resolver=resolver)


def test_facade_reexport_patch_is_flagged(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """
        ),
        baseline=[],
    )

    findings = _scan_single(tmp_path)

    assert findings == [
        lmfb.Finding("test_facade.py", "test_patch", "larch.facade", "target", "larch.defs", 1, 5)
    ]


def test_attribute_chain_on_imported_module_is_flagged(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            **_base_files(
                """
                import larch.ship as ship

                def test_patch(monkeypatch):
                    monkeypatch.setattr(ship.facade, "target", lambda: None)
                """
            ),
            "larch/ship.py": "from larch import facade\n",
        },
        baseline=[],
    )

    findings = _scan_single(tmp_path)

    assert findings == [
        lmfb.Finding("test_facade.py", "test_patch", "larch.facade", "target", "larch.defs", 1, 5)
    ]


def test_patching_the_defining_module_is_not_flagged(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import defs

            def test_patch(monkeypatch):
                monkeypatch.setattr(defs, "target", lambda: None)
            """
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path) == []


@pytest.mark.parametrize(
    "facade_source",
    [
        "def target():\n    return 'local'\n",
        "class target:\n    pass\n",
        "target = object()\n",
        "target: object = object()\n",
    ],
)
def test_module_that_defines_the_patched_name_is_not_flagged(tmp_path: Path, facade_source: str) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """,
            facade_source=facade_source,
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path) == []


def test_unrelated_module_level_bindings_do_not_suppress_flag(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """,
            facade_source="""
            from larch.defs import target

            def other():
                return None

            class Other:
                pass

            other_value = 1
            """,
        ),
        baseline=[],
    )

    findings = _scan_single(tmp_path)

    assert len(findings) == 1
    assert findings[0].attribute == "target"


def test_dotted_string_form_is_flagged(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            def test_patch(monkeypatch):
                monkeypatch.setattr("larch.facade.target", lambda: None)
            """
        ),
        baseline=[],
    )

    findings = _scan_single(tmp_path)

    assert findings == [
        lmfb.Finding("test_facade.py", "test_patch", "larch.facade", "target", "larch.defs", 1, 3)
    ]


def test_non_literal_attribute_names_are_skipped(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                name = "target"
                monkeypatch.setattr(facade, name, lambda: None)
            """
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path) == []


def test_non_repo_modules_and_unresolved_chains_are_skipped(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            import os
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(os, "path", object())
                monkeypatch.setattr(facade.missing, "target", object())
            """
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path) == []


def test_same_line_suppression_with_reason_suppresses(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)  # lint-monkeypatch-binding: ok late facade lookup
            """
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path)[0].suppressed is True
    assert lmfb.main(["--root", str(tmp_path)]) == 0


def test_bare_suppression_without_reason_does_not_suppress(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)  # lint-monkeypatch-binding: ok
            """
        ),
        baseline=[],
    )

    assert _scan_single(tmp_path)[0].suppressed is False
    assert lmfb.main(["--root", str(tmp_path)]) == 1


def test_baseline_entries_are_honored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """
        ),
        baseline=[_record()],
    )

    assert lmfb.main(["--root", str(tmp_path)]) == 0
    assert "warning: test_facade.py:5:test_patch patches larch.facade.target" in capsys.readouterr().err


def test_baseline_file_validation_accepts_test_paths(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={},
        baseline=[_record(file="test_top.py"), _record(file="tests/lint/test_nested.py", occurrence=2)],
    )

    assert lmfb.main(["--root", str(tmp_path)]) == 0


@pytest.mark.parametrize(
    "file_name",
    [
        "larch/test_bad.py",
        "tests/helper.py",
        "pkg/test_bad.py",
        "tests/../test_bad.py",
        "python/test_bad.py",
    ],
)
def test_baseline_file_validation_rejects_out_of_scope_paths(tmp_path: Path, file_name: str) -> None:
    _write_project(tmp_path, files={}, baseline=[_record(file=file_name)])

    assert lmfb.main(["--root", str(tmp_path)]) == 2


def test_write_preserves_reasons_and_shrinks_obsolete_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """
        ),
        baseline=[_record(reason="kept"), _record(attribute="other", reason="obsolete")],
    )

    assert lmfb.main(["--root", str(tmp_path), "--write"]) == 0
    rows = json.loads((tmp_path / "python" / lmfb.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="kept")]


@pytest.mark.parametrize(
    "payload",
    [
        [_record(reason="")],
        [
            {
                "file": "test_facade.py",
                "qualified_symbol": "test_patch",
                "facade_module": "larch.facade",
                "attribute": "target",
                "defining_module": "larch.defs",
                "occurrence": 1,
            }
        ],
        [_record(extra="nope")],
    ],
)
def test_malformed_rows_and_missing_reasons_exit_2(tmp_path: Path, payload: object) -> None:
    _write_project(tmp_path, files={}, baseline=payload)

    assert lmfb.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    row = _record()
    _write_project(tmp_path, files={}, baseline=[row, row])

    assert lmfb.main(["--root", str(tmp_path)]) == 2


def test_missing_baseline_in_check_mode_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={}, baseline=None)

    assert lmfb.main(["--root", str(tmp_path)]) == 2


def test_write_fails_when_new_rows_lack_reasons(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """
        ),
        baseline=[],
    )

    assert lmfb.main(["--root", str(tmp_path), "--write"]) == 2


def test_absent_baseline_bootstrap_succeeds(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files=_base_files(
            """
            from larch import facade

            def test_patch(monkeypatch):
                monkeypatch.setattr(facade, "target", lambda: None)
            """
        ),
        baseline=None,
    )

    assert lmfb.main(["--root", str(tmp_path), "--write", "--initial-reason", "bootstrap"]) == 0
    rows = json.loads((tmp_path / "python" / lmfb.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(reason="bootstrap")]
