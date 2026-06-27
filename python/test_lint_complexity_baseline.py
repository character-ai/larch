from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_complexity_baseline as lcb
from larch.lint.lint_complexity_baseline import BaselineError, RuffResult


SOURCE = """\ndef run(value):\n    if value:\n        return 1\n    return 0\n\nclass ProcRunner:\n    def run(self, value):\n        if value:\n            return 1\n        return 0\n"""


def ruff_item(filename: str, code: str, message: str, row: int) -> dict[str, object]:
    return {
        "filename": filename,
        "code": code,
        "message": message,
        "location": {"row": row, "column": 5},
    }


def write_project(
    root: Path, *, source: str = SOURCE, baseline: list[dict[str, object]] | object
) -> None:
    python_dir = root / "python"
    python_dir.mkdir()
    _ = (python_dir / "proc.py").write_text(source, encoding="utf-8")
    _ = (python_dir / "ruff-complexity-audit.toml").write_text(
        "target-version = 'py311'\n", encoding="utf-8"
    )
    _ = (python_dir / "complexity-baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )


def patch_ruff(
    monkeypatch: pytest.MonkeyPatch,
    items: list[object],
    returncode: int = 1,
    stdout: str | None = None,
) -> None:
    def fake_run_ruff(_python_dir: Path) -> RuffResult:
        return RuffResult(
            returncode=returncode,
            stdout=json.dumps(items) if stdout is None else stdout,
            stderr="boom",
        )

    monkeypatch.setattr(lcb, "_run_ruff", fake_run_ruff)


def test_normalize_file_path_collapses_python_cwd_variants() -> None:
    assert lcb.normalize_file_path("./ship.py") == "ship.py"
    assert lcb.normalize_file_path("python/ship.py") == "ship.py"
    assert lcb.normalize_file_path("ship.py") == "ship.py"
    assert lcb.normalize_file_path("/tmp/repo/python/ship.py") == "ship.py"


def test_load_baseline_accepts_top_level_array(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "ProcRunner.run",
                    "metric": 8,
                }
            ]
        ),
        encoding="utf-8",
    )
    assert lcb.load_baseline(path) == [
        {
            "file": "proc.py",
            "code": "PLR0913",
            "qualified_symbol": "ProcRunner.run",
            "metric": 8,
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"records": []},
        [{"file": "proc.py", "code": "PLR0913", "qualified_symbol": "ProcRunner.run"}],
    ],
)
def test_load_baseline_rejects_malformed_shapes(
    tmp_path: Path, payload: object
) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BaselineError):
        _ = lcb.load_baseline(path)


def test_main_passes_when_live_records_match_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(
        tmp_path,
        baseline=[
            {
                "file": "proc.py",
                "code": "PLR0911",
                "qualified_symbol": "run",
                "metric": 18,
            }
        ],
    )
    patch_ruff(
        monkeypatch,
        [ruff_item("./proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_main_fails_on_new_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch, [ruff_item("proc.py", "PLR0912", "Too many branches (13 > 12)", 2)]
    )
    assert lcb.main(["--root", str(tmp_path)]) == 1
    assert "proc.py:run PLR0912 (new)" in capsys.readouterr().err


def test_main_fails_on_metric_growth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(
        tmp_path,
        baseline=[
            {
                "file": "proc.py",
                "code": "PLR0915",
                "qualified_symbol": "run",
                "metric": 51,
            }
        ],
    )
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0915", "Too many statements (52 > 50)", 2)],
    )
    assert lcb.main(["--root", str(tmp_path)]) == 1
    assert "proc.py:run PLR0915 metric 52 > baseline 51" in capsys.readouterr().err


def test_plr_message_without_symbol_uses_ast_symbol() -> None:
    item = ruff_item(
        "python/proc.py",
        "PLR0913",
        "Too many arguments in function definition (8 > 5)",
        8,
    )
    assert lcb.parse_violation_record(item, file_source=SOURCE) == {
        "file": "proc.py",
        "code": "PLR0913",
        "qualified_symbol": "ProcRunner.run",
        "metric": 8,
    }


def test_same_simple_name_resolves_to_distinct_qualified_symbols() -> None:
    module_record = lcb.parse_violation_record(
        ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2),
        file_source=SOURCE,
    )
    method_record = lcb.parse_violation_record(
        ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 8),
        file_source=SOURCE,
    )
    assert module_record is not None
    assert method_record is not None
    assert module_record["qualified_symbol"] == "run"
    assert method_record["qualified_symbol"] == "ProcRunner.run"


def test_line_shift_inside_same_function_still_matches_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_project(
        tmp_path,
        baseline=[
            {"file": "proc.py", "code": "C901", "qualified_symbol": "run", "metric": 11}
        ],
    )
    patch_ruff(
        monkeypatch, [ruff_item("proc.py", "C901", "`run` is too complex (11 > 10)", 4)]
    )
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_duplicate_live_identity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_project(tmp_path, baseline=[])
    item = ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)
    patch_ruff(monkeypatch, [item, item])
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "duplicate live complexity identities" in capsys.readouterr().err


def test_duplicate_baseline_identity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    duplicate = {
        "file": "proc.py",
        "code": "PLR0911",
        "qualified_symbol": "run",
        "metric": 18,
    }
    write_project(tmp_path, baseline=[duplicate, duplicate])
    patch_ruff(monkeypatch, [])
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "duplicate baseline complexity identities" in capsys.readouterr().err


def test_exempt_test_file_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    _ = (tmp_path / "python" / "test_proc.py").write_text(SOURCE, encoding="utf-8")
    patch_ruff(
        monkeypatch,
        [
            ruff_item(
                "test_proc.py", "PLR0911", "Too many return statements (18 > 6)", 2
            )
        ],
    )
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_malformed_baseline_in_main_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_project(tmp_path, baseline={"records": []})
    patch_ruff(monkeypatch, [])
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "top-level JSON array" in capsys.readouterr().err


def test_missing_baseline_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    _ = (python_dir / "proc.py").write_text(SOURCE, encoding="utf-8")
    patch_ruff(monkeypatch, [])
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "cannot load baseline" in capsys.readouterr().err


@pytest.mark.parametrize(
    "item",
    [
        ruff_item("proc.py", "PLR0911", "Too many return statements", 2),
        ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 1),
    ],
)
def test_unparseable_violation_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    item: dict[str, object],
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(monkeypatch, [item])
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "cannot parse violation" in capsys.readouterr().err


def test_ruff_exit_one_with_valid_json_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_project(
        tmp_path,
        baseline=[
            {
                "file": "proc.py",
                "code": "PLR0911",
                "qualified_symbol": "run",
                "metric": 18,
            }
        ],
    )
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
        returncode=1,
    )
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


@pytest.mark.parametrize(
    ("returncode", "stdout"), [(2, "[]"), (0, ""), (0, "not json")]
)
def test_ruff_tool_failures_return_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    returncode: int,
    stdout: str,
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(monkeypatch, [], returncode=returncode, stdout=stdout)
    assert lcb.main(["--root", str(tmp_path)]) == 2
    assert "lint-complexity-baseline" in capsys.readouterr().err


def test_write_mode_regenerates_baseline_from_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch,
        [
            ruff_item("proc.py", "PLR0915", "Too many statements (52 > 50)", 8),
            ruff_item("./proc.py", "PLR0911", "Too many return statements (18 > 6)", 2),
        ],
    )
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 0, capsys.readouterr().err
    baseline_file = tmp_path / "python" / "complexity-baseline.json"
    written = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert written == [
        {"file": "proc.py", "code": "PLR0911", "qualified_symbol": "run", "metric": 18},
        {
            "file": "proc.py",
            "code": "PLR0915",
            "qualified_symbol": "ProcRunner.run",
            "metric": 52,
        },
    ]
    text = baseline_file.read_text(encoding="utf-8")
    assert text.startswith('[\n  {\n    "file": "proc.py",')
    assert text.endswith("\n")


def test_write_then_check_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 0, capsys.readouterr().err
    # The regenerated baseline must check clean against the same live findings.
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_write_mode_fails_closed_on_duplicate_live_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sentinel = [
        {"file": "proc.py", "code": "C901", "qualified_symbol": "run", "metric": 11}
    ]
    write_project(tmp_path, baseline=sentinel)
    item = ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)
    patch_ruff(monkeypatch, [item, item])
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 2
    assert "duplicate live complexity identities" in capsys.readouterr().err
    preserved = json.loads(
        (tmp_path / "python" / "complexity-baseline.json").read_text(encoding="utf-8")
    )
    assert preserved == sentinel


def test_write_mode_fails_closed_on_unparseable_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements", 2)],
    )
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 2
    assert "cannot parse violation" in capsys.readouterr().err
