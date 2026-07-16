from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import pytest

from larch import cli
from larch.lint import engine
from larch.lint import lint_complexity_baseline as lcb
from larch.lint import lint_complexity_debt as lcd
from larch.lint.lint_complexity_baseline import BaselineError, Record, RuffResult


SOURCE = """\ndef run(value):\n    if value:\n        return 1\n    return 0\n\nclass ProcRunner:\n    def run(self, value):\n        if value:\n            return 1\n        return 0\n"""


def ruff_item(filename: str, code: str, message: str, row: int) -> dict[str, object]:
    return {
        "filename": filename,
        "code": code,
        "message": message,
        "location": {"row": row, "column": 5},
    }


def base_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "file": "proc.py",
        "code": "PLR0913",
        "qualified_symbol": "ProcRunner.run",
        "metric": 8,
        "added_at": "2026-07-12",
        "history": [],
    }
    record.update(overrides)
    return record


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


def test_load_baseline_accepts_required_and_optional_fields(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "ProcRunner.run",
                    "metric": 8,
                    "added_at": "2026-07-12",
                    "history": [{"date": "2026-07-12", "metric": 8}],
                    "source_issue": 1234,
                    "reason": "urgent fix",
                    "operator_override": {"reason": "known debt", "issue": 1240},
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
            "added_at": "2026-07-12",
            "history": [{"date": "2026-07-12", "metric": 8}],
            "source_issue": 1234,
            "reason": "urgent fix",
            "operator_override": {"reason": "known debt", "issue": 1240},
        }
    ]


def test_load_baseline_accepts_grandfathered_record(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "ProcRunner.run",
                    "metric": 8,
                    "added_at": "legacy",
                    "history": [],
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
            "added_at": "legacy",
            "history": [],
        }
    ]


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("not-a-list", {"records": []}),
        (
            "missing-metric",
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "ProcRunner.run",
                }
            ],
        ),
        (
            "old-four-field-record",
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "ProcRunner.run",
                    "metric": 8,
                }
            ],
        ),
        (
            "unknown-field",
            [base_record(bogus=True)],
        ),
    ],
)
def test_load_baseline_rejects_malformed_shapes(
    tmp_path: Path, name: str, payload: object
) -> None:
    del name
    path = tmp_path / "baseline.json"
    _ = path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BaselineError):
        _ = lcb.load_baseline(path)


def test_load_baseline_rejects_record_missing_history_field(tmp_path: Path) -> None:
    record = base_record()
    del record["history"]
    path = tmp_path / "baseline.json"
    _ = path.write_text(json.dumps([record]), encoding="utf-8")
    with pytest.raises(BaselineError):
        _ = lcb.load_baseline(path)


@pytest.mark.parametrize(
    "overrides",
    [
        {"added_at": ""},
        {"added_at": 123},
        {"history": "not-a-list"},
        {"history": [{"date": "", "metric": 1}]},
        {"history": [{"date": "2026-07-12", "metric": -1}]},
        {"history": [{"date": "2026-07-12", "metric": True}]},
        {"history": [{"date": "2026-07-12"}]},
        {"history": [{"date": "2026-07-12", "metric": 1, "bogus": 1}]},
        {"source_issue": 0},
        {"source_issue": True},
        {"source_issue": "1234"},
        {"reason": ""},
        {"reason": 123},
        {"operator_override": {"reason": "", "issue": 1}},
        {"operator_override": {"reason": "ok", "issue": 0}},
        {"operator_override": {"reason": "ok", "issue": True}},
        {"operator_override": {"reason": "ok"}},
        {"operator_override": {"issue": 1}},
        {"operator_override": "not-a-dict"},
    ],
)
def test_load_baseline_rejects_invalid_field_values(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(json.dumps([base_record(**overrides)]), encoding="utf-8")
    with pytest.raises(BaselineError):
        _ = lcb.load_baseline(path)


def test_serialize_baseline_uses_canonical_field_order_regardless_of_input_order() -> (
    None
):
    shuffled: Record = {
        "operator_override": {"issue": 1240, "reason": "known debt"},
        "reason": "urgent",
        "metric": 8,
        "source_issue": 1234,
        "qualified_symbol": "ProcRunner.run",
        "history": [{"metric": 8, "date": "2026-07-12"}],
        "code": "PLR0913",
        "added_at": "2026-07-12",
        "file": "proc.py",
    }
    text = lcb.serialize_baseline([shuffled])
    parsed = json.loads(text)
    assert list(parsed[0].keys()) == [
        "file",
        "code",
        "qualified_symbol",
        "metric",
        "added_at",
        "history",
        "source_issue",
        "reason",
        "operator_override",
    ]


def test_serialize_baseline_omits_absent_optional_fields_without_null() -> None:
    record: Record = {
        "file": "proc.py",
        "code": "PLR0913",
        "qualified_symbol": "run",
        "metric": 5,
        "added_at": "legacy",
        "history": [],
    }
    text = lcb.serialize_baseline([record])
    parsed = json.loads(text)
    assert set(parsed[0].keys()) == {
        "file",
        "code",
        "qualified_symbol",
        "metric",
        "added_at",
        "history",
    }
    assert "null" not in text


def test_migrate_baseline_adds_legacy_metadata_to_four_field_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "run",
                    "metric": 8,
                },
                {
                    "file": "proc.py",
                    "code": "C901",
                    "qualified_symbol": "other",
                    "metric": 11,
                },
            ]
        ),
        encoding="utf-8",
    )
    assert lcb.migrate_baseline(path) == 2
    migrated = lcb.load_baseline(path)
    assert migrated == [
        {
            "file": "proc.py",
            "code": "C901",
            "qualified_symbol": "other",
            "metric": 11,
            "added_at": "legacy",
            "history": [],
        },
        {
            "file": "proc.py",
            "code": "PLR0913",
            "qualified_symbol": "run",
            "metric": 8,
            "added_at": "legacy",
            "history": [],
        },
    ]


def test_migrate_baseline_fills_only_missing_fields_on_partial_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "run",
                    "metric": 8,
                    "added_at": "2026-07-01",
                    "source_issue": 1234,
                },
                {
                    "file": "proc.py",
                    "code": "C901",
                    "qualified_symbol": "other",
                    "metric": 11,
                    "history": [{"date": "2026-07-01", "metric": 11}],
                },
            ]
        ),
        encoding="utf-8",
    )
    assert lcb.migrate_baseline(path) == 2
    migrated = lcb.load_baseline(path)
    assert migrated == [
        {
            "file": "proc.py",
            "code": "C901",
            "qualified_symbol": "other",
            "metric": 11,
            "added_at": "legacy",
            "history": [{"date": "2026-07-01", "metric": 11}],
        },
        {
            "file": "proc.py",
            "code": "PLR0913",
            "qualified_symbol": "run",
            "metric": 8,
            "added_at": "2026-07-01",
            "history": [],
            "source_issue": 1234,
        },
    ]


def test_migrate_baseline_is_idempotent_on_fully_migrated_records(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    fully_migrated = [
        {
            "file": "proc.py",
            "code": "PLR0913",
            "qualified_symbol": "run",
            "metric": 8,
            "added_at": "2026-07-01",
            "history": [{"date": "2026-07-01", "metric": 8}],
        }
    ]
    _ = path.write_text(json.dumps(fully_migrated), encoding="utf-8")
    assert lcb.migrate_baseline(path) == 0
    assert lcb.load_baseline(path) == fully_migrated


def test_migrate_baseline_preserves_identity_metric_projection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    original = [
        {"file": "proc.py", "code": "PLR0913", "qualified_symbol": "run", "metric": 8},
        {"file": "proc.py", "code": "C901", "qualified_symbol": "other", "metric": 11},
    ]
    _ = path.write_text(json.dumps(original), encoding="utf-8")
    _ = lcb.migrate_baseline(path)
    migrated = lcb.load_baseline(path)
    projection = {
        (record["file"], record["code"], record["qualified_symbol"]): record["metric"]
        for record in migrated
    }
    assert projection == {
        ("proc.py", "PLR0913", "run"): 8,
        ("proc.py", "C901", "other"): 11,
    }


def test_migrate_baseline_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps(
            [
                {
                    "file": "proc.py",
                    "code": "PLR0913",
                    "qualified_symbol": "run",
                    "metric": 8,
                    "bogus": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(BaselineError):
        _ = lcb.migrate_baseline(path)


def test_migrate_baseline_rejects_missing_identity_field(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    _ = path.write_text(
        json.dumps([{"file": "proc.py", "code": "PLR0913", "metric": 8}]),
        encoding="utf-8",
    )
    with pytest.raises(BaselineError):
        _ = lcb.migrate_baseline(path)


def test_migrate_cli_reports_migrated_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(
        tmp_path,
        baseline=[
            {
                "file": "proc.py",
                "code": "PLR0913",
                "qualified_symbol": "ProcRunner.run",
                "metric": 8,
            }
        ],
    )
    assert lcb.main(["--root", str(tmp_path), "--migrate"]) == 0, capsys.readouterr().err
    err = capsys.readouterr().err
    assert "migrated 1" in err
    migrated = lcb.load_baseline(tmp_path / "python" / "complexity-baseline.json")
    assert migrated == [
        {
            "file": "proc.py",
            "code": "PLR0913",
            "qualified_symbol": "ProcRunner.run",
            "metric": 8,
            "added_at": "legacy",
            "history": [],
        }
    ]


def test_checked_in_baseline_strict_loads_and_serializes_byte_stable() -> None:
    baseline_path = Path(__file__).resolve().parents[2] / "complexity-baseline.json"
    records = engine.load_complexity_baseline(
        baseline_path, root=baseline_path.parents[1]
    )
    assert not engine.complexity_duplicate_identities(records)
    assert engine.serialize_complexity_baseline(records) == baseline_path.read_text(
        encoding="utf-8"
    )


def test_engine_write_preserves_unchanged_complexity_baseline_bytes(
    tmp_path: Path,
) -> None:
    source_path = Path(__file__).resolve().parents[2] / "complexity-baseline.json"
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    baseline_path = python_dir / "complexity-baseline.json"
    original = source_path.read_text(encoding="utf-8")
    _ = baseline_path.write_text(original, encoding="utf-8")
    rows = engine.load_complexity_baseline(baseline_path, root=tmp_path)
    _ = engine.write_complexity_baseline(baseline_path, root=tmp_path, rows=rows)
    assert baseline_path.read_text(encoding="utf-8") == original


def test_engine_rejects_symlinked_complexity_baseline(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    python_dir.mkdir()
    target = tmp_path / "target.json"
    _ = target.write_text("[]\n", encoding="utf-8")
    baseline_path = python_dir / "complexity-baseline.json"
    baseline_path.symlink_to(target)
    with pytest.raises(engine.ScanError, match="symlinked"):
        _ = engine.load_complexity_baseline(baseline_path, root=tmp_path)


def test_engine_write_fails_closed_when_read_back_bytes_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mismatched_read(*_args: object, **_kwargs: object) -> str:
        return "[]\n"

    python_dir = tmp_path / "python"
    python_dir.mkdir()
    baseline_path = python_dir / "complexity-baseline.json"
    rows = engine.parse_complexity_baseline(
        json.dumps([base_record()]), source="test", today=date(2026, 7, 14)
    )
    monkeypatch.setattr(
        engine.larch_io,
        "read_trusted_text",
        mismatched_read,
    )
    with pytest.raises(engine.ScanError, match="read-back bytes differ"):
        _ = engine.write_complexity_baseline(
            baseline_path, root=tmp_path, rows=rows, today=date(2026, 7, 14)
        )


def test_engine_merge_records_one_deterministic_growth_event() -> None:
    stored = engine.parse_complexity_baseline(
        json.dumps([base_record(metric=17, history=[{"date": "2026-07-01", "metric": 17}])]),
        source="test",
        today=date(2026, 7, 14),
    )
    live = [engine.ComplexityLiveRow("proc.py", "PLR0913", "ProcRunner.run", 18)]
    merged = engine.merge_complexity_baseline(
        live_rows=live, stored_rows=stored, reason="growth", today=date(2026, 7, 14)
    )
    assert merged[0].history[-1] == engine.ComplexityHistoryEntry("2026-07-14", 18)
    assert merged[0].reason == "growth"


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
                "added_at": "legacy",
                "history": [],
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
                "added_at": "legacy",
                "history": [],
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
            {
                "file": "proc.py",
                "code": "C901",
                "qualified_symbol": "run",
                "metric": 11,
                "added_at": "legacy",
                "history": [],
            }
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
    duplicate: dict[str, object] = {
        "file": "proc.py",
        "code": "PLR0911",
        "qualified_symbol": "run",
        "metric": 18,
        "added_at": "legacy",
        "history": [],
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
                "added_at": "legacy",
                "history": [],
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
    assert lcb.main(["--root", str(tmp_path), "--write", "--reason", "new debt"]) == 0, capsys.readouterr().err
    baseline_file = tmp_path / "python" / "complexity-baseline.json"
    written = json.loads(baseline_file.read_text(encoding="utf-8"))
    assert written == [
        {
            "file": "proc.py", "code": "PLR0911", "qualified_symbol": "run", "metric": 18,
            "added_at": lcb.utc_today().isoformat(), "history": [{"date": lcb.utc_today().isoformat(), "metric": 18}], "reason": "new debt",
        },
        {
            "file": "proc.py",
            "code": "PLR0915",
            "qualified_symbol": "ProcRunner.run",
            "metric": 52,
            "added_at": lcb.utc_today().isoformat(),
            "history": [{"date": lcb.utc_today().isoformat(), "metric": 52}],
            "reason": "new debt",
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
    assert lcb.main(["--root", str(tmp_path), "--write", "--reason", "new debt"]) == 0, capsys.readouterr().err
    baseline_path = tmp_path / "python" / "complexity-baseline.json"
    assert lcb.load_baseline(baseline_path)
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_write_mode_allows_empty_array_bootstrap_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    assert lcb.main(["--root", str(tmp_path), "--write", "--reason", "new debt"]) == 0, capsys.readouterr().err


def test_write_mode_preserves_migrated_baseline_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    migrated: list[dict[str, object]] = [
        {
            "file": "proc.py",
            "code": "PLR0911",
            "qualified_symbol": "run",
            "metric": 18,
            "added_at": "legacy",
            "history": [],
        }
    ]
    write_project(tmp_path, baseline=migrated)
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    baseline_path = tmp_path / "python" / "complexity-baseline.json"
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 0, capsys.readouterr().err
    assert json.loads(baseline_path.read_text(encoding="utf-8")) == migrated
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_write_mode_refuses_partially_migrated_baseline_with_any_extended_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    partially_migrated = [
        {
            "file": "proc.py",
            "code": "PLR0911",
            "qualified_symbol": "run",
            "metric": 18,
            "added_at": "legacy",
            # "history" intentionally omitted: strict loading rejects this fixture.
        }
    ]
    write_project(tmp_path, baseline=partially_migrated)
    baseline_path = tmp_path / "python" / "complexity-baseline.json"
    with pytest.raises(BaselineError):
        _ = lcb.load_baseline(baseline_path)
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    before = baseline_path.read_text(encoding="utf-8")
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 2
    assert baseline_path.read_text(encoding="utf-8") == before


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


def test_write_requires_nonblank_reason_for_new_or_growing_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, baseline=[])
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0911", "Too many return statements (18 > 6)", 2)],
    )
    assert lcb.main(["--root", str(tmp_path), "--write"]) == 2
    assert "--reason is required" in capsys.readouterr().err
    assert lcb.main(["--root", str(tmp_path), "--write", "--reason", "   "]) == 2


def test_write_growth_appends_history_and_preserves_manual_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stored = [
        base_record(
            metric=17,
            history=[{"date": "2026-07-01", "metric": 17}],
            reason="first growth",
            source_issue=7156,
            operator_override={"reason": "approved exception", "issue": 9001},
        )
    ]
    write_project(tmp_path, baseline=stored)
    patch_ruff(
        monkeypatch,
        [ruff_item("proc.py", "PLR0913", "Too many arguments (18 > 5)", 8)],
    )
    assert lcb.main(["--root", str(tmp_path), "--write", "--reason", "urgent API"]) == 0
    written = lcb.load_baseline(tmp_path / "python" / "complexity-baseline.json")
    written_record = written[0]
    assert written_record.get("added_at") == "2026-07-12"
    history = written_record.get("history")
    assert isinstance(history, list)
    assert history[-1] == {"date": lcb.utc_today().isoformat(), "metric": 18}
    assert written_record.get("reason") == "urgent API"
    assert written_record.get("source_issue") == 7156
    assert written_record.get("operator_override") == {
        "reason": "approved exception",
        "issue": 9001,
    }
    assert capsys.readouterr().err


def test_repeat_gate_uses_cross_code_events_and_only_later_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline = [
        base_record(
            code="PLR0911",
            added_at="legacy",
            history=[{"date": "2026-07-01", "metric": 9}],
        ),
        base_record(
            code="PLR0912",
            added_at="legacy",
            history=[{"date": "2026-07-13", "metric": 10}],
        ),
    ]
    write_project(tmp_path, baseline=baseline)
    patch_ruff(monkeypatch, [])
    assert lcb.main(["--root", str(tmp_path)]) == 1
    assert "[PLR0911]" in capsys.readouterr().err
    baseline[1]["operator_override"] = {"reason": "operator approved", "issue": 7156}
    _ = (tmp_path / "python" / "complexity-baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    assert lcb.main(["--root", str(tmp_path)]) == 0, capsys.readouterr().err


def test_dated_seed_is_not_a_bump_and_equal_dates_are_deterministic() -> None:
    records = [
        base_record(
            code="PLR0911",
            added_at="2026-07-01",
            history=[
                {"date": "2026-07-01", "metric": 8},
                {"date": "2026-07-10", "metric": 9},
            ],
        ),
        base_record(
            code="PLR0912",
            added_at="legacy",
            history=[{"date": "2026-07-10", "metric": 11}],
        ),
    ]
    validated: list[Record] = records
    failures = lcb.repeat_bump_failures(validated)
    assert len(failures) == 1
    assert "[PLR0911] metric 9; 2026-07-10 [PLR0912] metric 11" in failures[0]


def test_debt_report_has_all_sections_and_cli_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(
        tmp_path,
        baseline=[
                base_record(
                    metric=22,
                    added_at="legacy",
                    history=[
                    {"date": "2026-07-01", "metric": 20},
                    {"date": "2026-07-10", "metric": 22},
                ],
                operator_override={"reason": "tracked debt", "issue": 7156},
            )
        ],
    )
    monkeypatch.setattr(lcd, "_utc_today", lambda: date(2026, 7, 14))
    assert cli.main(["lint", "complexity-debt", "--root", str(tmp_path), "--report"]) == 0
    report = capsys.readouterr().out
    assert "Total entries: 1" in report
    assert "Age buckets:" in report
    assert "Top 10 by metric:" in report
    assert "Symbols with at least two bumps in the last 30 days:" in report
    assert "Active operator overrides:" in report
    assert "2026-07-01 [PLR0913] metric 20; 2026-07-10 [PLR0913] metric 22" in report
    assert "issue #7156: tracked debt" in report
    assert cli.main(["lint", "complexity-debt", "--root", str(tmp_path)]) == 2


def test_debt_report_golden_output_keeps_long_labels_untruncated() -> None:
    records: list[Record] = [
        {
            "file": "a/path/that/is/intentionally/longer/than/the/report/column/expectation.py",
            "code": "PLR0915",
            "qualified_symbol": "DeeplyNestedClassName.WithAnExtremelyLongMethodName.run",
            "metric": 55,
            "added_at": "legacy",
            "history": [],
        }
    ]
    assert lcd.render_report(records, today=date(2026, 7, 14)) == (
        "Complexity debt report\n"
        "Total entries: 1\n"
        "\n"
        "Age buckets:\n"
        "  under 14 days: 0\n"
        "  14 through 90 days: 0\n"
        "  over 90 days: 0\n"
        "  legacy: 1\n"
        "\n"
        "Top 10 by metric:\n"
        "  55 | a/path/that/is/intentionally/longer/than/the/report/column/expectation.py | PLR0915 | DeeplyNestedClassName.WithAnExtremelyLongMethodName.run\n"
        "\n"
        "Symbols with at least two bumps in the last 30 days:\n"
        "  (none)\n"
        "\n"
        "Active operator overrides:\n"
        "  (none)\n"
    )
