from __future__ import annotations

from pathlib import Path

import pytest

from larch.lint import lint_self_disarmable_gate as lint


OPTIONAL_META = """\
from dataclasses import dataclass

@dataclass(frozen=True)
class OptionalMetadata:
    metadata_trailer_lines: int
    diff_added: str | None
    diff_deleted: str | None
    mechanical_churn: str
    oversize_override: str | None
    keys: tuple[str, ...]
    values: tuple[str, ...]
"""


def _design_tree(root: Path, *, plan_quality: str, commands: str | None = None) -> Path:
    design = root / "python" / "larch" / "design"
    design.mkdir(parents=True)
    _ = (design / "_plan_quality_commands.py").write_text(
        commands if commands is not None else OPTIONAL_META, encoding="utf-8"
    )
    _ = (design / "plan_quality.py").write_text(plan_quality, encoding="utf-8")
    return design


def test_resolve_optional_metadata_via_reexport(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def check() -> None:\n"
            "    pass\n"
        ),
    )
    resolution = lint.resolve_optional_metadata(design)
    assert "diff_added" in resolution.fields
    assert "mechanical_churn" in resolution.fields


def test_missing_required_fields_fail_closed(tmp_path: Path) -> None:
    design = tmp_path / "python" / "larch" / "design"
    design.mkdir(parents=True)
    _ = (design / "_plan_quality_commands.py").write_text(
        "from dataclasses import dataclass\n"
        "@dataclass(frozen=True)\n"
        "class OptionalMetadata:\n"
        "    diff_added: str | None\n",
        encoding="utf-8",
    )
    _ = (design / "plan_quality.py").write_text(
        "from larch.design._plan_quality_commands import OptionalMetadata\n",
        encoding="utf-8",
    )
    with pytest.raises(lint.ScanError, match="missing required fields"):
        _ = lint.resolve_optional_metadata(design)


def test_negated_metadata_early_return_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    larch_dir = tmp_path / "python" / "larch"
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=larch_dir,
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert findings
    assert "mechanical_churn" in findings[0].message


def test_or_combine_and_presentation_softening_compliant(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def _size_trigger_assessment(meta: OptionalMetadata, diff_lines: int) -> tuple[bool, bool]:\n"
            "    size_diff_added = meta.diff_added is not None and int(meta.diff_added) > 10\n"
            "    size_diff_lines = diff_lines > 10\n"
            "    size_diff_raw = size_diff_added or size_diff_lines\n"
            "    soft = meta.mechanical_churn == 'true' and size_diff_raw\n"
            "    return size_diff_raw, soft\n"
        ),
    )
    larch_dir = tmp_path / "python" / "larch"
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=larch_dir,
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert not findings


def test_ternary_replacement_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = False if meta.mechanical_churn == 'true' else hard\n"
            "    return size_diff_raw\n"
        ),
    )
    larch_dir = tmp_path / "python" / "larch"
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=larch_dir,
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert any("conditional expression" in f.message for f in findings)


def test_and_negate_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard and not meta.diff_added\n"
            "    return size_diff_raw\n"
        ),
    )
    larch_dir = tmp_path / "python" / "larch"
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=larch_dir,
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert any("AND-negates" in f.message for f in findings)


def test_validation_not_in_is_not_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def check(meta: OptionalMetadata) -> int:\n"
            "    if meta.mechanical_churn not in {'true', 'false'}:\n"
            "        return 2\n"
            "    return 0\n"
        ),
    )
    larch_dir = tmp_path / "python" / "larch"
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=larch_dir,
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert not findings


def test_metadata_only_early_return_without_hard_trigger_is_not_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def check(meta: OptionalMetadata) -> int:\n"
            "    if meta.mechanical_churn == 'true':\n"
            "        return 0\n"
            "    return 1\n"
        ),
    )
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=tmp_path / "python" / "larch",
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert not findings


def test_or_metadata_early_return_with_hard_trigger_is_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, size_diff_raw: bool) -> bool:\n"
            "    if meta.mechanical_churn == 'true' or size_diff_raw:\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=tmp_path / "python" / "larch",
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert len(findings) == 1


def test_nested_metadata_early_return_with_prior_hard_trigger_is_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, size_diff_raw: bool, enabled: bool) -> bool:\n"
            "    hard_trigger = size_diff_raw\n"
            "    if enabled:\n"
            "        if meta.mechanical_churn == 'true':\n"
            "            return False\n"
            "    return hard_trigger\n"
        ),
    )
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=tmp_path / "python" / "larch",
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert len(findings) == 1


def test_inline_plan_size_or_metadata_return_is_flagged(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, diff_lines: int) -> bool:\n"
            "    if meta.mechanical_churn == 'true' or diff_lines > 100:\n"
            "        return False\n"
            "    return True\n"
        ),
    )
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=tmp_path / "python" / "larch",
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert len(findings) == 1


def test_later_hard_trigger_does_not_flag_prior_metadata_return(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata) -> bool:\n"
            "    if meta.mechanical_churn == 'true':\n"
            "        return False\n"
            "    hard_trigger = True\n"
            "    return hard_trigger\n"
        ),
    )
    findings = lint.scan_file(
        design / "plan_quality.py",
        larch_dir=tmp_path / "python" / "larch",
        meta_fields=frozenset({"diff_added", "mechanical_churn"}),
    )
    assert not findings


def test_current_plan_quality_size_trigger_compliant() -> None:
    root = Path(__file__).resolve().parents[3]
    assert lint.main(["--root", str(root)]) == 0


def test_suppression_requires_reason(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':  # lint-self-disarmable-gate: ok\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    with pytest.raises(lint.ScanError, match="empty"):
        _ = lint.scan_file(
            design / "plan_quality.py",
            larch_dir=tmp_path / "python" / "larch",
            meta_fields=frozenset({"diff_added", "mechanical_churn"}),
        )


def test_suppression_reason_names_gate_owner(tmp_path: Path) -> None:
    design = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':  # lint-self-disarmable-gate: ok intentional\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    with pytest.raises(lint.ScanError, match="gate owner"):
        _ = lint.scan_file(
            design / "plan_quality.py",
            larch_dir=tmp_path / "python" / "larch",
            meta_fields=frozenset({"diff_added", "mechanical_churn"}),
        )


def test_cli_exit_codes(tmp_path: Path) -> None:
    _ = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata) -> bool:\n"
            "    return True\n"
        ),
    )
    assert lint.main(["--root", str(tmp_path)]) == 0
