"""Plan-quality library tests retained after #8576 command cutover."""
from __future__ import annotations

from pathlib import Path

from larch.design import plan_quality


def test_parse_optional_metadata_keys_and_values() -> None:
    plan_text = "body\ndiff_added: 1\ndiff_deleted: 2\nmechanical_churn: true\ndiff_lines: 3\n"
    meta = plan_quality.parse_optional_metadata(plan_text)
    assert "diff_added" in meta.keys
    assert "diff_deleted" in meta.keys
    assert "mechanical_churn" in meta.keys
    assert any(v.startswith("diff_added=") for v in meta.values)


def test_parse_optional_metadata_requires_diff_lines() -> None:
    assert not plan_quality.parse_optional_metadata("body\ndiff_added: 1\n").keys


def test_validate_difficulty_metadata(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    _ = plan.write_text("body\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    ok, found = plan_quality.validate_difficulty_metadata(plan.read_text(encoding="utf-8"), require=True)
    assert ok
    assert found == "MODERATE"


def test_validate_optional_trailers_preserved(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    _ = plan.write_text("body\ndiff_added: 1\ndiff_lines: 2\n", encoding="utf-8")
    keys = tmp_path / "keys"
    _ = keys.write_text("diff_added\n", encoding="utf-8")
    values = tmp_path / "keys.values"
    _ = values.write_text("diff_added=1\n", encoding="utf-8")
    assert plan_quality.validate_optional_trailers_preserved(plan_file=plan, values_file=values)


def test_validate_optional_trailers_missing_key(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    _ = plan.write_text("body\ndiff_lines: 2\n", encoding="utf-8")
    keys = tmp_path / "keys"
    _ = keys.write_text("diff_added\n", encoding="utf-8")
    assert not plan_quality.validate_optional_trailers_preserved(plan_file=plan, values_file=keys)
