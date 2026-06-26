from __future__ import annotations

import json
from pathlib import Path

import pytest

import lint_subprocess_via_runner as lsvr


def _record(
    *,
    file: str = "mod.py",
    qualified_symbol: str = "run",
    callee: str = "run",
    occurrence: int = 1,
    reason: str = "grandfathered",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "callee": callee,
        "occurrence": occurrence,
        "reason": reason,
    }
    record.update(extra)
    return record


def _write_project(
    root: Path,
    *,
    files: dict[str, str],
    baseline: object,
    exemptions: object | None = None,
) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    _ = (python_dir / lsvr.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")
    if exemptions is not None:
        _ = (python_dir / lsvr.EXEMPTIONS_FILENAME).write_text(
            json.dumps(exemptions), encoding="utf-8"
        )


def _source(body: str) -> str:
    return "import subprocess\n\ndef run():\n" + body


def test_direct_subprocess_run_is_detected(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    source = _source("    subprocess.run(['true'])\n")
    path = python_dir / "mod.py"
    _ = path.write_text(source, encoding="utf-8")

    assert lsvr.scan_file(path, python_dir=python_dir) == [
        lsvr.Finding("mod.py", "run", "run", 1, 4)
    ]


def test_popen_check_output_and_call_are_detected(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    path = python_dir / "mod.py"
    _ = path.write_text(
        _source(
            "    subprocess.Popen(['true'])\n"
            "    subprocess.check_output(['true'])\n"
            "    subprocess.call(['true'])\n"
        ),
        encoding="utf-8",
    )

    assert [finding.callee for finding in lsvr.scan_file(path, python_dir=python_dir)] == [
        "Popen",
        "check_output",
        "call",
    ]


def test_scope_excludes_proc_tests_helpers_and_scans_nested_modules(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    for relpath in [
        "larch/core/proc.py",
        "test_mod.py",
        "pkg/test_nested.py",
        "conftest.py",
        "pkg/test_support.py",
        "pkg/review_test_support.py",
        "analysis/nested.py",
        ".venv/lib/vendor.py",
        "node_modules/tool/vendor.py",
        "__pycache__/generated.py",
    ]:
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("import subprocess\n", encoding="utf-8")

    assert [path.relative_to(python_dir).as_posix() for path in lsvr.iter_source_files(python_dir)] == [
        "analysis/nested.py"
    ]


def test_occurrences_are_distinct_and_canonical_on_write(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"b.py": _source("    subprocess.run(['b'])\n    subprocess.run(['b2'])\n")},
        baseline=[],
    )

    assert lsvr.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / lsvr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [
        _record(file="b.py", occurrence=1, reason="bootstrap"),
        _record(file="b.py", occurrence=2, reason="bootstrap"),
    ]


def test_occurrence_is_assigned_before_pragma_suppression(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": _source(
                "    subprocess.run(['suppressed'])  # lint-subprocess-via-runner: ok fixture\n"
                "    subprocess.run(['live'])\n"
            )
        },
        baseline=[],
    )

    assert lsvr.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    rows = json.loads((tmp_path / "python" / lsvr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    assert rows == [_record(occurrence=2, reason="bootstrap")]


def test_baseline_suppresses_existing_findings_but_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        files={"mod.py": _source("    subprocess.run(['true'])\n")},
        baseline=[_record()],
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 0
    assert "warning: mod.py:run calls subprocess.run occurrence 1" in capsys.readouterr().err


@pytest.mark.parametrize(
    "payload",
    [
        [_record(reason="")],
        [{"file": "mod.py", "qualified_symbol": "run", "callee": "run", "occurrence": 1}],
        [_record(extra="nope")],
        [_record(file="python/mod.py")],
    ],
)
def test_baseline_shape_or_reason_errors_exit_2(tmp_path: Path, payload: object) -> None:
    _write_project(
        tmp_path,
        files={"mod.py": _source("    subprocess.run(['true'])\n")},
        baseline=payload,
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_identity_exits_2(tmp_path: Path) -> None:
    row = _record()
    _write_project(
        tmp_path,
        files={"mod.py": _source("    subprocess.run(['true'])\n")},
        baseline=[row, row],
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 2


def test_duplicate_live_identity_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_project(tmp_path, files={"mod.py": ""}, baseline=[])
    finding = lsvr.Finding("mod.py", "run", "run", 1, 1)

    def fake_collect_all(_python_dir: Path) -> tuple[list[lsvr.Finding], dict[str, tuple[str, ...]]]:
        return [finding, finding], {"mod.py": ()}

    monkeypatch.setattr(lsvr, "_collect_all", fake_collect_all)
    assert lsvr.main(["--root", str(tmp_path)]) == 2


def test_new_finding_exits_1(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"mod.py": _source("    subprocess.run(['true'])\n")},
        baseline=[],
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 1


def test_write_preserves_matching_reason_and_requires_reason_for_new_rows(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "mod.py": _source("    subprocess.run(['one'])\n    subprocess.call(['two'])\n")
        },
        baseline=[_record(reason="kept")],
    )

    assert lsvr.main(["--root", str(tmp_path), "--write"]) == 2
    assert lsvr.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "new reason",
    ]) == 0
    rows = json.loads((tmp_path / "python" / lsvr.BASELINE_FILENAME).read_text(encoding="utf-8"))
    reasons = {row["callee"]: row["reason"] for row in rows}
    assert reasons == {"call": "new reason", "run": "kept"}


def test_absent_baseline_bootstrap_succeeds(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    _ = (python_dir / "mod.py").write_text(_source("    subprocess.run(['true'])\n"), encoding="utf-8")

    assert lsvr.main([
        "--root",
        str(tmp_path),
        "--write",
        "--initial-reason",
        "bootstrap",
    ]) == 0
    assert json.loads((python_dir / lsvr.BASELINE_FILENAME).read_text(encoding="utf-8"))[0][
        "reason"
    ] == "bootstrap"


@pytest.mark.parametrize(
    "exemptions",
    [[{"file": "", "reason": "x"}], [{"file": "mod.py"}], [{"file": "mod.py", "reason": ""}], [{"file": "mod.py", "reason": "x", "extra": "bad"}]],
)
def test_exemption_shape_errors_exit_2(tmp_path: Path, exemptions: object) -> None:
    _write_project(tmp_path, files={"mod.py": ""}, baseline=[], exemptions=exemptions)

    assert lsvr.main(["--root", str(tmp_path)]) == 2


def test_file_exemption_suppresses_findings(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"mod.py": _source("    subprocess.run(['true'])\n")},
        baseline=[],
        exemptions=[{"file": "mod.py", "reason": "cli glue"}],
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 0


def test_inline_pragma_requires_reason_and_suppresses_only_intended_call(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={
            "ok.py": _source("    subprocess.run(['true'])  # lint-subprocess-via-runner: ok fixture\n"),
            "bad.py": _source("    subprocess.run(['true'])  # lint-subprocess-via-runner: ok\n"),
        },
        baseline=[],
    )

    assert lsvr.main(["--root", str(tmp_path)]) == 1


def test_malformed_json_and_syntax_error_conventions(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    _ = (python_dir / "bad_syntax.py").write_text("def nope(:\n", encoding="utf-8")
    _ = (python_dir / lsvr.BASELINE_FILENAME).write_text("[]", encoding="utf-8")
    assert lsvr.main(["--root", str(tmp_path)]) == 0
    _ = (python_dir / lsvr.BASELINE_FILENAME).write_text("{", encoding="utf-8")
    assert lsvr.main(["--root", str(tmp_path)]) == 2
    _ = (python_dir / lsvr.BASELINE_FILENAME).write_text("[]", encoding="utf-8")
    _ = (python_dir / lsvr.EXEMPTIONS_FILENAME).write_text("{", encoding="utf-8")
    assert lsvr.main(["--root", str(tmp_path)]) == 2
