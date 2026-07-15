from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from larch.lint import lint_self_disarmable_gate as lint
from larch.lint import self_disarmable_gate_detector as detector
from larch.lint.engine import Finding, LintRule, ScanError, SourceFile
from larch.lint.lint_self_disarmable_gate import PATHSPECS, _source_filter  # type: ignore[reportPrivateUsage]  # test verifies private filter behaviour directly

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _design_tree(root: Path, *, plan_quality: str, commands: str | None = None) -> Path:
    design = root / "python" / "larch" / "design"
    design.mkdir(parents=True)
    _ = (design / "_plan_quality_commands.py").write_text(
        commands if commands is not None else OPTIONAL_META, encoding="utf-8"
    )
    _ = (design / "plan_quality.py").write_text(plan_quality, encoding="utf-8")
    return design


def _make_source(path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _design_corpus(
    *,
    plan_quality: str,
    commands: str | None = None,
) -> list[SourceFile]:
    """Build an in-memory corpus for the design directory."""
    cmd_text = commands if commands is not None else OPTIONAL_META
    return [
        _make_source("python/larch/design/_plan_quality_commands.py", cmd_text),
        _make_source("python/larch/design/plan_quality.py", plan_quality),
    ]


# ---------------------------------------------------------------------------
# Legacy compatibility tests (scan_file / resolve_optional_metadata)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Corpus-based preparation and detection tests
# ---------------------------------------------------------------------------


def test_corpus_prepare_resolves_metadata_via_reexport() -> None:
    sources = _design_corpus(
        plan_quality="from larch.design._plan_quality_commands import OptionalMetadata\n",
    )
    prepared = detector.prepare_corpus(sources)
    assert "diff_added" in prepared.resolution.fields
    assert "mechanical_churn" in prepared.resolution.fields


def test_corpus_missing_required_fields_fail_closed() -> None:
    sources = _design_corpus(
        plan_quality="from larch.design._plan_quality_commands import OptionalMetadata\n",
        commands=(
            "from dataclasses import dataclass\n"
            "@dataclass(frozen=True)\n"
            "class OptionalMetadata:\n"
            "    diff_added: str | None\n"
        ),
    )
    with pytest.raises(ScanError, match="missing required fields"):
        _ = detector.prepare_corpus(sources)


def test_corpus_preparation_call_order() -> None:
    """Preparation receives the complete corpus once; detect uses only prepared context."""
    pq_text = (
        "from larch.design._plan_quality_commands import OptionalMetadata\n"
        "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
        "    size_diff_raw = hard\n"
        "    if meta.mechanical_churn == 'true':\n"
        "        return False\n"
        "    return size_diff_raw\n"
    )
    sources = _design_corpus(plan_quality=pq_text)
    prepared = detector.prepare_corpus(sources)
    assert "mechanical_churn" in prepared.resolution.fields
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    findings = detector.detect(pq, prepared=prepared)
    assert findings
    assert all(f.path == "python/larch/design/plan_quality.py" for f in findings)


def test_corpus_negated_metadata_early_return_flagged() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    findings = detector.detect(pq, prepared=prepared)
    assert findings
    assert "mechanical_churn" in findings[0].message


def test_corpus_or_combine_and_presentation_softening_compliant() -> None:
    sources = _design_corpus(
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
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    assert not detector.detect(pq, prepared=prepared)


def test_corpus_ternary_replacement_flagged() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = False if meta.mechanical_churn == 'true' else hard\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    findings = detector.detect(pq, prepared=prepared)
    assert any("conditional expression" in f.message for f in findings)


def test_corpus_and_negate_flagged() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard and not meta.diff_added\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    findings = detector.detect(pq, prepared=prepared)
    assert any("AND-negates" in f.message for f in findings)


def test_corpus_suppression_requires_reason() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':  # lint-self-disarmable-gate: ok\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    with pytest.raises(ScanError, match="empty"):
        _ = detector.detect(pq, prepared=prepared)


def test_corpus_suppression_reason_names_gate_owner() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':  # lint-self-disarmable-gate: ok intentional\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    with pytest.raises(ScanError, match="gate owner"):
        _ = detector.detect(pq, prepared=prepared)


def test_corpus_suppression_with_gate_owner_produces_clean_exit() -> None:
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':  # lint-self-disarmable-gate: ok gate owner: plan_quality\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    assert not detector.detect(pq, prepared=prepared)


def test_corpus_malformed_python_raises_scan_error() -> None:
    """Corpus preparation probes python_syntax_error() before AST access."""
    sources = [
        _make_source(
            "python/larch/design/_plan_quality_commands.py",
            "this is not valid python !!!$$$\n",
        ),
        _make_source(
            "python/larch/design/plan_quality.py",
            "from larch.design._plan_quality_commands import OptionalMetadata\n",
        ),
    ]
    with pytest.raises(ScanError, match="cannot parse source"):
        _ = detector.prepare_corpus(sources)


def test_corpus_finding_paths_are_repo_relative() -> None:
    """detect() returns findings with repo-relative paths (no legacy prefix mapping)."""
    sources = _design_corpus(
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata, hard: bool) -> bool:\n"
            "    size_diff_raw = hard\n"
            "    if meta.mechanical_churn == 'true':\n"
            "        return False\n"
            "    return size_diff_raw\n"
        ),
    )
    prepared = detector.prepare_corpus(sources)
    pq = next(s for s in sources if s.path.endswith("plan_quality.py"))
    findings = detector.detect(pq, prepared=prepared)
    assert findings
    assert findings[0].path == "python/larch/design/plan_quality.py"
    assert findings[0].rule_id == detector.SUPPRESSION


def test_current_plan_quality_compliant_via_corpus() -> None:
    """The live design corpus produces no self-disarmable gate violations."""
    root = Path(__file__).resolve().parents[3]
    design_dir = root / "python" / "larch" / "design"
    if not design_dir.is_dir():
        pytest.skip("design directory not found")
    sources: list[SourceFile] = []
    for path in sorted(design_dir.glob("*.py")):
        if not path.is_file() or path.is_symlink() or path.name.startswith("test_"):
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        sources.append(SourceFile(path=rel, text=text, lines=tuple(text.splitlines())))
    prepared = detector.prepare_corpus(sources)
    all_findings: list[Finding] = []
    for source in sources:
        all_findings.extend(detector.detect(source, prepared=prepared))
    assert not all_findings


# ---------------------------------------------------------------------------
# Rule config and CLI tests
# ---------------------------------------------------------------------------


def test_source_filter_excludes_test_modules() -> None:
    """_source_filter rejects test_*.py directly under the design prefix."""
    assert _source_filter("python/larch/design/plan_quality.py")
    assert not _source_filter("python/larch/design/test_plan_quality.py")


def test_source_filter_excludes_subdirectories() -> None:
    """_source_filter rejects nested paths."""
    assert not _source_filter("python/larch/design/sub/plan_quality.py")


def test_rule_config_values() -> None:
    """SUPPRESSION constant and PATHSPECS are correctly exported."""
    assert lint.SUPPRESSION == "lint-self-disarmable-gate"
    assert "python/larch/design/*.py" in PATHSPECS


def test_main_returns_2_when_piece1_absent() -> None:
    """main() fails closed when LintRule.prepare_corpus is absent."""
    if any(f.name == "prepare_corpus" for f in dataclasses.fields(LintRule)):
        pytest.skip("Piece 1 already landed; dependency check not applicable")
    assert lint.main(["--root", "."]) == 2


def test_cli_exit_codes(tmp_path: Path) -> None:
    """With Piece 1 absent, main returns 2 for all roots."""
    if any(f.name == "prepare_corpus" for f in dataclasses.fields(LintRule)):
        pytest.skip("Piece 1 already landed; test via engine path instead")
    _ = _design_tree(
        tmp_path,
        plan_quality=(
            "from larch.design._plan_quality_commands import OptionalMetadata\n"
            "def assess(meta: OptionalMetadata) -> bool:\n"
            "    return True\n"
        ),
    )
    assert lint.main(["--root", str(tmp_path)]) == 2
