"""Equivalence harness: detector outputs → engine Finding mapping.

Test-only surface. Golden fixtures under fixtures/lint_engine_equivalence/
materialize synthetic repositories below tmp_path. The markdown adapter calls
``lint_markdown_heading_fence_state.detect`` directly on SourceFile values;
unreachable-branch and self-disarmable-gate still use their legacy scan_file
APIs until those ports land.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

import pytest

from larch.lint import lint_markdown_heading_fence_state as lint_md
from larch.lint import lint_self_disarmable_gate as lint_sd
from larch.lint import lint_unreachable_branch as lint_ub
from larch.lint import self_disarmable_gate_detector as _sd_detector
from larch.lint.engine import Finding, SourceFile, render_finding
from larch.lint.engine import (
    OccurrenceBaselineRow,
    _occurrence_json_file,  # type: ignore[reportPrivateUsage]  # accessing internal helpers for test assertion
    _project_finding,  # type: ignore[reportPrivateUsage]  # accessing internal helpers for test assertion
)
from larch.lint.markdown_heading_fence_state_detector import is_production_source_path

FIXTURE_DIR: Final[Path] = (
    Path(__file__).resolve().parent / "fixtures" / "lint_engine_equivalence"
)

EXPECTED_FIXTURE_FILENAMES: Final[frozenset[str]] = frozenset(
    {
        "markdown_heading_fence_state.json",
        "unreachable_branch.json",
        "self_disarmable_gate.json",
    }
)

FindingIdentity = tuple[str, int, str, str]
AdapterFn = Callable[[Path], list[Finding]]


@dataclass(frozen=True)
class ExpectedFindingRecord:
    """One golden finding: identity fields plus rendered engine line."""

    path: str
    line: int
    rule_id: str
    message: str
    qualified_symbol: str | None
    rendered: str

    def to_finding(self) -> Finding:
        return Finding(
            path=self.path,
            line=self.line,
            rule_id=self.rule_id,
            message=self.message,
            qualified_symbol=self.qualified_symbol,
        )

    def identity(self) -> FindingIdentity:
        return (self.path, self.line, self.rule_id, self.message)


@dataclass(frozen=True)
class EquivalenceCase:
    """One labeled synthetic-repo case inside a fixture file."""

    label: str
    sources: Mapping[str, str]
    expected: tuple[ExpectedFindingRecord, ...]


@dataclass(frozen=True)
class EquivalenceFixture:
    """Decoded fixture: rule id plus labeled cases."""

    path: Path
    rule: str
    cases: tuple[EquivalenceCase, ...]


def _normalize_repo_relative_posix(path: str) -> str:
    """Normalize a repository-relative path to POSIX form."""
    normalized: str = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def finding_identity(finding: Finding) -> FindingIdentity:
    """Engine dedupe/sort identity: (path, line, rule_id, message)."""
    return (
        _normalize_repo_relative_posix(finding.path),
        finding.line,
        finding.rule_id,
        finding.message,
    )


def _validate_source_relpath(
    relpath: object, *, fixture_path: Path, case_label: str
) -> str:
    if not isinstance(relpath, str) or not relpath:
        msg = f"{fixture_path}: case {case_label!r} has invalid source path {relpath!r}"
        raise AssertionError(msg)
    normalized: str = relpath.replace("\\", "/")
    if normalized != relpath:
        msg = f"{fixture_path}: case {case_label!r} source path must use POSIX separators: {relpath!r}"
        raise AssertionError(msg)
    if normalized.startswith(("/", "~")):
        msg = f"{fixture_path}: case {case_label!r} source path must be relative: {relpath!r}"
        raise AssertionError(msg)
    if len(normalized) >= 2 and normalized[0].isalpha() and normalized[1] == ":":
        msg = f"{fixture_path}: case {case_label!r} source path must not be drive-qualified: {relpath!r}"
        raise AssertionError(msg)
    parts: list[str] = normalized.split("/")
    if "" in parts or "." in parts or ".." in parts:
        msg = f"{fixture_path}: case {case_label!r} source path is unsafe: {relpath!r}"
        raise AssertionError(msg)
    if not normalized.endswith(".py"):
        msg = f"{fixture_path}: case {case_label!r} source path must end with .py: {relpath!r}"
        raise AssertionError(msg)
    return normalized


def _parse_expected_finding(
    raw: object, *, fixture_path: Path, case_label: str, index: int
) -> ExpectedFindingRecord:
    assert isinstance(raw, dict), (
        f"{fixture_path}: case {case_label!r} expected[{index}] must be an object"
    )
    record: dict[str, object] = cast("dict[str, object]", raw)
    path_raw: object = record.get("path")
    line_raw: object = record.get("line")
    rule_id_raw: object = record.get("rule_id")
    message_raw: object = record.get("message")
    rendered_raw: object = record.get("rendered")
    symbol_raw: object = record.get("qualified_symbol")
    if not isinstance(path_raw, str) or not path_raw:
        msg = f"{fixture_path}: case {case_label!r} expected[{index}] has invalid path"
        raise AssertionError(msg)
    if not isinstance(line_raw, int) or isinstance(line_raw, bool) or line_raw < 1:
        msg = f"{fixture_path}: case {case_label!r} expected[{index}] has invalid line"
        raise AssertionError(msg)
    if not isinstance(rule_id_raw, str) or not rule_id_raw:
        msg = (
            f"{fixture_path}: case {case_label!r} expected[{index}] has invalid rule_id"
        )
        raise AssertionError(msg)
    if not isinstance(message_raw, str) or not message_raw:
        msg = (
            f"{fixture_path}: case {case_label!r} expected[{index}] has invalid message"
        )
        raise AssertionError(msg)
    if not isinstance(rendered_raw, str) or not rendered_raw:
        msg = f"{fixture_path}: case {case_label!r} expected[{index}] has invalid rendered"
        raise AssertionError(msg)
    if symbol_raw is not None and not isinstance(symbol_raw, str):
        msg = f"{fixture_path}: case {case_label!r} expected[{index}] has invalid qualified_symbol"
        raise AssertionError(msg)
    path: str = _normalize_repo_relative_posix(path_raw)
    if path != path_raw or path.startswith("/") or ".." in path.split("/"):
        msg = f"{fixture_path}: case {case_label!r} expected[{index}] path must be repo-relative POSIX"
        raise AssertionError(msg)
    if not path.startswith("python/"):
        msg = (
            f"{fixture_path}: case {case_label!r} expected[{index}] path must start with python/: "
            f"{path!r}"
        )
        raise AssertionError(msg)
    qualified_symbol: str | None = symbol_raw if isinstance(symbol_raw, str) else None
    return ExpectedFindingRecord(
        path=path,
        line=line_raw,
        rule_id=rule_id_raw,
        message=message_raw,
        qualified_symbol=qualified_symbol,
        rendered=rendered_raw,
    )


def _parse_case(raw: object, *, fixture_path: Path, index: int) -> EquivalenceCase:
    assert isinstance(raw, dict), f"{fixture_path}: cases[{index}] must be an object"
    case_obj: dict[str, object] = cast("dict[str, object]", raw)
    label_raw: object = case_obj.get("label")
    sources_raw: object = case_obj.get("sources")
    expected_raw: object = case_obj.get("expected")
    if not isinstance(label_raw, str) or not label_raw:
        msg = f"{fixture_path}: cases[{index}] has invalid label"
        raise AssertionError(msg)
    if not isinstance(sources_raw, dict) or not sources_raw:
        msg = f"{fixture_path}: case {label_raw!r} sources must be a non-empty object"
        raise AssertionError(msg)
    sources_obj: dict[str, object] = cast("dict[str, object]", sources_raw)
    assert isinstance(expected_raw, list), (
        f"{fixture_path}: case {label_raw!r} expected must be an array"
    )
    expected_items: list[object] = cast("list[object]", expected_raw)
    sources: dict[str, str] = {}
    for key, value in sources_obj.items():
        relpath: str = _validate_source_relpath(
            key, fixture_path=fixture_path, case_label=label_raw
        )
        assert isinstance(value, str), (
            f"{fixture_path}: case {label_raw!r} source {relpath!r} must be a string"
        )
        if relpath in sources:
            msg = (
                f"{fixture_path}: case {label_raw!r} duplicate source path {relpath!r}"
            )
            raise AssertionError(msg)
        sources[relpath] = value
    expected: list[ExpectedFindingRecord] = [
        _parse_expected_finding(
            item, fixture_path=fixture_path, case_label=label_raw, index=i
        )
        for i, item in enumerate(expected_items)
    ]
    return EquivalenceCase(
        label=label_raw,
        sources=sources,
        expected=tuple(expected),
    )


def load_equivalence_fixture(path: Path) -> EquivalenceFixture:
    """Load and validate one equivalence fixture JSON file."""
    try:
        raw_text: str = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"{path}: cannot read fixture: {exc}"
        raise AssertionError(msg) from exc
    try:
        decoded: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        msg = f"{path}: invalid JSON: {exc}"
        raise AssertionError(msg) from exc
    assert isinstance(decoded, dict), f"{path}: fixture root must be an object"
    root: dict[str, object] = cast("dict[str, object]", decoded)
    rule_raw: object = root.get("rule")
    cases_raw: object = root.get("cases")
    if not isinstance(rule_raw, str) or not rule_raw:
        msg = f"{path}: rule must be a non-empty string"
        raise AssertionError(msg)
    if rule_raw not in ADAPTER_REGISTRY:
        msg = f"{path}: unsupported rule {rule_raw!r}"
        raise AssertionError(msg)
    if not isinstance(cases_raw, list) or not cases_raw:
        msg = f"{path}: cases must be a non-empty array"
        raise AssertionError(msg)
    case_items: list[object] = cast("list[object]", cases_raw)
    cases: list[EquivalenceCase] = []
    seen_labels: set[str] = set()
    for index, item in enumerate(case_items):
        case: EquivalenceCase = _parse_case(item, fixture_path=path, index=index)
        if case.label in seen_labels:
            msg = f"{path}: duplicate case label {case.label!r}"
            raise AssertionError(msg)
        seen_labels.add(case.label)
        for finding in case.expected:
            if finding.rule_id != rule_raw:
                msg = (
                    f"{path}: case {case.label!r} expected rule_id {finding.rule_id!r} "
                    f"does not match fixture rule {rule_raw!r}"
                )
                raise AssertionError(msg)
        cases.append(case)
    return EquivalenceFixture(path=path, rule=rule_raw, cases=tuple(cases))


def materialize_sources(repo_root: Path, sources: Mapping[str, str]) -> Path:
    """Write fixture sources under repo_root/python/ and return that python/ dir."""
    python_dir: Path = repo_root / "python"
    for relpath, text in sources.items():
        target: Path = python_dir / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(text, encoding="utf-8")
    return python_dir


def adapt_markdown_heading_fence_state(repo_root: Path) -> list[Finding]:
    """Scan synthetic python/ sources directly via detect (no git discovery)."""
    python_dir: Path = repo_root / "python"
    findings: list[Finding] = []
    for path in sorted(python_dir.rglob("*.py")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if not is_production_source_path(rel):
            continue
        text = path.read_text(encoding="utf-8")
        source = SourceFile(path=rel, text=text, lines=tuple(text.splitlines()))
        findings.extend(lint_md.detect(source))
    return findings


def _map_unreachable_finding(legacy: lint_ub.Finding) -> Finding:
    return Finding(
        path=_normalize_repo_relative_posix(f"python/{legacy.file}"),
        line=legacy.lineno,
        rule_id=lint_ub.SUPPRESSION,
        message=(
            f"unreachable branch occurrence {legacy.occurrence} "
            f"cond={legacy.normalized_condition}"
        ),
        qualified_symbol=legacy.qualified_symbol,
    )


def adapt_unreachable_branch(repo_root: Path) -> list[Finding]:
    """Scan synthetic python/larch with the unreachable-branch detector."""
    larch_dir: Path = repo_root / "python" / "larch"
    findings: list[Finding] = []
    for path in lint_ub.iter_source_files(larch_dir):
        findings.extend(
            _map_unreachable_finding(item)
            for item in lint_ub.scan_file(path, larch_dir=larch_dir)
        )
    return findings


def adapt_self_disarmable_gate(repo_root: Path) -> list[Finding]:
    """Build SourceFile corpus from design dir; prepare once then detect each source."""
    design_dir: Path = repo_root / "python" / "larch" / "design"
    sources: list[SourceFile] = []
    for path in sorted(design_dir.glob("*.py")):
        if not path.is_file() or path.is_symlink() or path.name.startswith("test_"):
            continue
        text: str = path.read_text(encoding="utf-8")
        rel: str = path.relative_to(repo_root).as_posix()
        sources.append(SourceFile(path=rel, text=text, lines=tuple(text.splitlines())))
    prepared = _sd_detector.prepare_corpus(sources)
    findings: list[Finding] = []
    for source in sources:
        findings.extend(_sd_detector.detect(source, prepared=prepared))
    return findings


def test_markdown_adapter_preserves_repo_relative_paths_and_occurrence_codec(
    tmp_path: Path,
) -> None:
    """Direct fixture adaptation keeps repo-relative Finding.path values."""
    repo_root = tmp_path / "repo"
    _ = materialize_sources(
        repo_root,
        {
            "larch/mod.py": (
                "import re\n\n"
                'HEADING_RE = re.compile(r"^#{1,6}\\s+")\n\n'
                "def parse(text: str) -> None:\n"
                "    for line in text.splitlines():\n"
                "        if HEADING_RE.match(line):\n"
                "            pass\n"
            )
        },
    )
    findings = adapt_markdown_heading_fence_state(repo_root)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.path == "python/larch/mod.py"
    assert finding.pattern_name == "HEADING_RE"
    assert finding.occurrence == 1
    row = _project_finding(finding)
    assert isinstance(row, OccurrenceBaselineRow)
    assert _occurrence_json_file(row.path) == "larch/mod.py"


ADAPTER_REGISTRY: Final[dict[str, AdapterFn]] = {
    lint_md.SUPPRESSION: adapt_markdown_heading_fence_state,
    lint_ub.SUPPRESSION: adapt_unreachable_branch,
    lint_sd.SUPPRESSION: adapt_self_disarmable_gate,
}


def assert_equivalent_findings(
    actual: Sequence[Finding],
    expected: Sequence[Finding],
    *,
    expected_rendered: Sequence[str] | None = None,
) -> None:
    """Compare sorted identities and sorted render_finding lines."""
    actual_normalized: list[Finding] = [
        Finding(
            path=_normalize_repo_relative_posix(item.path),
            line=item.line,
            rule_id=item.rule_id,
            message=item.message,
            qualified_symbol=item.qualified_symbol,
            metric=item.metric,
        )
        for item in actual
    ]
    expected_normalized: list[Finding] = [
        Finding(
            path=_normalize_repo_relative_posix(item.path),
            line=item.line,
            rule_id=item.rule_id,
            message=item.message,
            qualified_symbol=item.qualified_symbol,
            metric=item.metric,
        )
        for item in expected
    ]
    actual_ids: list[FindingIdentity] = sorted(
        finding_identity(item) for item in actual_normalized
    )
    expected_ids: list[FindingIdentity] = sorted(
        finding_identity(item) for item in expected_normalized
    )
    assert actual_ids == expected_ids, (
        f"finding identities differ\nactual={actual_ids!r}\nexpected={expected_ids!r}"
    )
    actual_rendered: list[str] = sorted(
        render_finding(item) for item in actual_normalized
    )
    if expected_rendered is None:
        expected_lines: list[str] = sorted(
            render_finding(item) for item in expected_normalized
        )
    else:
        expected_lines = sorted(expected_rendered)
    assert actual_rendered == expected_lines, (
        f"rendered findings differ\nactual={actual_rendered!r}\nexpected={expected_lines!r}"
    )


def discover_fixture_paths() -> list[Path]:
    """Return sorted fixture JSON paths under the golden directory."""
    if not FIXTURE_DIR.is_dir():
        msg = f"equivalence fixture directory missing: {FIXTURE_DIR}"
        raise AssertionError(msg)
    return sorted(path for path in FIXTURE_DIR.glob("*.json") if path.is_file())


def _param_id(fixture_path: Path, case: EquivalenceCase) -> str:
    return f"{fixture_path.stem}::{case.label}"


def _case_parameters() -> list[tuple[Path, EquivalenceCase]]:
    params: list[tuple[Path, EquivalenceCase]] = []
    for fixture_path in discover_fixture_paths():
        fixture: EquivalenceFixture = load_equivalence_fixture(fixture_path)
        for case in fixture.cases:
            params.append((fixture_path, case))
    return params


@pytest.mark.parametrize(
    ("fixture_path", "case"),
    _case_parameters(),
    ids=[_param_id(path, case) for path, case in _case_parameters()],
)
def test_legacy_adapter_matches_golden_fixture(
    fixture_path: Path, case: EquivalenceCase, tmp_path: Path
) -> None:
    fixture: EquivalenceFixture = load_equivalence_fixture(fixture_path)
    adapter: AdapterFn = ADAPTER_REGISTRY[fixture.rule]
    repo_root: Path = tmp_path / "repo"
    _ = materialize_sources(repo_root, case.sources)
    actual: list[Finding] = adapter(repo_root)
    expected_findings: list[Finding] = [record.to_finding() for record in case.expected]
    assert_equivalent_findings(
        actual,
        expected_findings,
        expected_rendered=[record.rendered for record in case.expected],
    )
    for record, finding in zip(
        sorted(case.expected, key=lambda item: item.identity()),
        sorted(actual, key=finding_identity),
        strict=True,
    ):
        if record.qualified_symbol is not None:
            assert finding.qualified_symbol == record.qualified_symbol


def test_fixture_registry_and_suppression_completeness() -> None:
    """Fixture files, adapter registry, and SUPPRESSION constants must agree."""
    on_disk: frozenset[str] = frozenset(path.name for path in discover_fixture_paths())
    assert on_disk == EXPECTED_FIXTURE_FILENAMES, (
        f"fixture filenames mismatch\non_disk={sorted(on_disk)!r}\n"
        f"expected={sorted(EXPECTED_FIXTURE_FILENAMES)!r}"
    )
    suppression_ids: frozenset[str] = frozenset(
        {lint_md.SUPPRESSION, lint_ub.SUPPRESSION, lint_sd.SUPPRESSION}
    )
    registry_ids: frozenset[str] = frozenset(ADAPTER_REGISTRY)
    assert registry_ids == suppression_ids, (
        f"adapter registry must match SUPPRESSION constants\n"
        f"registry={sorted(registry_ids)!r}\nsuppressions={sorted(suppression_ids)!r}"
    )
    fixture_rules: set[str] = set()
    for fixture_path in discover_fixture_paths():
        fixture: EquivalenceFixture = load_equivalence_fixture(fixture_path)
        fixture_rules.add(fixture.rule)
        assert fixture.rule in ADAPTER_REGISTRY
        assert fixture_path.name in EXPECTED_FIXTURE_FILENAMES
    assert frozenset(fixture_rules) == registry_ids, (
        f"fixture rules must cover the registry exactly\n"
        f"fixture_rules={sorted(fixture_rules)!r}\nregistry={sorted(registry_ids)!r}"
    )
    exercised: set[str] = {path.stem for path, _case in _case_parameters()}
    assert exercised == {
        name.removesuffix(".json") for name in EXPECTED_FIXTURE_FILENAMES
    }


def test_load_rejects_unsupported_rule(tmp_path: Path) -> None:
    path: Path = tmp_path / "bad.json"
    _ = path.write_text(
        json.dumps(
            {
                "rule": "lint-not-a-real-rule",
                "cases": [
                    {
                        "label": "x",
                        "sources": {"larch/mod.py": "x = 1\n"},
                        "expected": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="unsupported rule"):
        _ = load_equivalence_fixture(path)


def test_load_rejects_duplicate_case_labels(tmp_path: Path) -> None:
    path: Path = tmp_path / "dup.json"
    case: dict[str, object] = {
        "label": "same",
        "sources": {"larch/mod.py": "x = 1\n"},
        "expected": [],
    }
    _ = path.write_text(
        json.dumps({"rule": lint_md.SUPPRESSION, "cases": [case, case]}),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="duplicate case label"):
        _ = load_equivalence_fixture(path)


def test_load_rejects_empty_sources(tmp_path: Path) -> None:
    path: Path = tmp_path / "empty.json"
    _ = path.write_text(
        json.dumps(
            {
                "rule": lint_md.SUPPRESSION,
                "cases": [{"label": "x", "sources": {}, "expected": []}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="sources must be a non-empty object"):
        _ = load_equivalence_fixture(path)


def test_load_rejects_absolute_source_path(tmp_path: Path) -> None:
    path: Path = tmp_path / "abs.json"
    _ = path.write_text(
        json.dumps(
            {
                "rule": lint_md.SUPPRESSION,
                "cases": [
                    {
                        "label": "x",
                        "sources": {"/tmp/evil.py": "x = 1\n"},
                        "expected": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="must be relative"):
        _ = load_equivalence_fixture(path)


def test_load_rejects_drive_qualified_source_path(tmp_path: Path) -> None:
    path: Path = tmp_path / "drive.json"
    _ = path.write_text(
        json.dumps(
            {
                "rule": lint_md.SUPPRESSION,
                "cases": [
                    {
                        "label": "x",
                        "sources": {"C:/outside.py": "x = 1\n"},
                        "expected": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="must not be drive-qualified"):
        _ = load_equivalence_fixture(path)


def test_load_rejects_parent_escape_source_path(tmp_path: Path) -> None:
    path: Path = tmp_path / "escape.json"
    _ = path.write_text(
        json.dumps(
            {
                "rule": lint_md.SUPPRESSION,
                "cases": [
                    {
                        "label": "x",
                        "sources": {"../outside.py": "x = 1\n"},
                        "expected": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="unsafe"):
        _ = load_equivalence_fixture(path)
