# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false
"""Read-only manifest compatibility parsing and state readers for larch run-logs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from larch.core import architectural_guidelines, config, rust_runtime
from larch.core.rust_runtime import RunLogRefreshOutput as RefreshSkip
from larch.core.run_context import RunContext
from larch.report import exec_issue_detail

from larch.report.run_log_batch import (
    _EXECUTION_ISSUE_CATEGORIES,
    _LARCH_LOG_BATCHES,
    _read_state_kv,
    _resolve_log_root,
    validate_run_id_slug,
)
from larch.report.run_log_tolerance import terminal_bail_skip_signal

_MANIFEST_SCHEMA_VERSION = 2

_V2_CORE_KEYS = frozenset({"status", "schema_version", "run_id", "steps_ran", "started_at", "updated_at"})
_V2_RESERVED_KEYS = frozenset({
    "skill",
    "operator_cwd",
    "operator_repo_root",
    "parent_skill",
    "parent_run_id",
    "issue_number",
    "larch_version",
    "model_roster",
    "effort",
    "attempt",
    "superseded_by",
    "stalled_at_step",
    "flags",
    "pr_number",
})
_V2_PARSE_EXCLUDED_KEYS = _V2_CORE_KEYS | _V2_RESERVED_KEYS


def _empty_manifest_reserved() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class Manifest:
    status: str
    version: str
    run_id: str
    steps_ran: dict[str, Any]
    created_at: str = ""
    updated_at: str = ""
    extra: dict[str, Any] | None = None
    # Reserved v2 metadata remains separate from extension keys so Python's
    # compatibility readers can preserve the Rust-owned schema distinctions.
    reserved: dict[str, Any] = field(default_factory=_empty_manifest_reserved)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> Manifest:
        steps_raw = data.get("steps_ran", {})
        steps = dict(cast("dict[str, Any]", steps_raw)) if isinstance(steps_raw, dict) else {}
        if data.get("schema_version") == _MANIFEST_SCHEMA_VERSION:
            reserved: dict[str, Any] = {key: data[key] for key in _V2_RESERVED_KEYS if key in data}
            extra = {key: value for key, value in data.items() if key not in _V2_PARSE_EXCLUDED_KEYS}
            return cls(
                status=str(data.get("status", config.MANIFEST_STATUS_PARTIAL)),
                version="2",
                run_id=str(data.get("run_id", "")),
                steps_ran=steps,
                created_at=str(data.get("started_at", "")),
                updated_at=str(data.get("updated_at", "")),
                extra=extra or None,
                reserved=dict(reserved),
            )
        extra = {
            key: value
            for key, value in data.items()
            if key not in {"status", "version", "run_id", "steps_ran", "created_at", "updated_at"}
        }
        return cls(
            status=str(data.get("status", config.MANIFEST_STATUS_PARTIAL)),
            version=str(data.get("version", "1")),
            run_id=str(data.get("run_id", "")),
            steps_ran=steps,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            extra=extra or None,
        )


@dataclass(frozen=True)
class RequiredArtifact:
    slug: str
    relative_path: str
    skill: str
    condition: str


@dataclass(frozen=True)
class _CommittedIssue:
    category: str
    body: str


@dataclass(frozen=True)
class _ReachabilityContext:
    run_dir: Path
    manifest_data: Manifest
    manifest_status: str
    manifest_pr_number: str


REFRESH_SKIP_RECOVERY_FAILED = "manifest-recovery-failed"


@dataclass(frozen=True)
class ResumeCounters:
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int


@dataclass(frozen=True)
class DurableFlags:
    repo_unavailable: bool
    forked_target: bool
    forked: bool
    merge: bool
    draft: bool


def _read_manifest_v2(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("manifest must be a JSON object")
    return cast("dict[str, Any]", data)


def _manifest_field(*, manifest: Manifest, key: str) -> str:
    value = manifest.reserved.get(key) if key in _V2_RESERVED_KEYS else None
    if value is None and manifest.extra:
        value = manifest.extra.get(key)
    if key == "pr_number":
        if isinstance(value, bool):
            return ""
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""
    if key == "status":
        return manifest.status
    return ""


def _manifest_steps_ran_empty(manifest: Manifest) -> bool:
    return len(manifest.steps_ran) == 0


def _manifest_read_data(manifest: Manifest) -> dict[str, Any]:
    """Project parsed compatibility fields for read-only predicates."""
    data = dict(manifest.extra or {})
    data.update(manifest.reserved)
    data.update({
        "status": manifest.status,
        "run_id": manifest.run_id,
        "steps_ran": dict(manifest.steps_ran),
    })
    if manifest.version == "2":
        data["schema_version"] = _MANIFEST_SCHEMA_VERSION
        data["started_at"] = manifest.created_at
        data["updated_at"] = manifest.updated_at
    else:
        data["version"] = manifest.version
        data["created_at"] = manifest.created_at
        data["updated_at"] = manifest.updated_at
    return data


def _final_summary_bail_signal_without_pr_evidence(
    *,
    run_dir: Path,
    manifest_pr_number: str,
    manifest_data: Manifest | None = None,
) -> bool:
    manifest_obj: object | None = _manifest_read_data(manifest_data) if manifest_data is not None else None
    if manifest_obj is None and manifest_pr_number.strip().isdigit():
        manifest_obj = {"pr_number": int(manifest_pr_number)}
    pr = int(manifest_pr_number) if manifest_pr_number.strip().isdigit() else 0
    return terminal_bail_skip_signal(run_dir=run_dir, manifest=manifest_obj, pr=pr)


def _verify_has_file(*, run_dir: Path, relative_path: str) -> bool:
    return (run_dir / relative_path).is_file()


def _step5_reached(ctx: _ReachabilityContext) -> bool:
    return (
        _verify_has_file(run_dir=ctx.run_dir, relative_path="code-review-tally.json")
        or _verify_has_file(run_dir=ctx.run_dir, relative_path="review-findings-full.jsonl")
        or _condition_reached(ctx=ctx, condition="step7a")
    )


def _step7a_reached(ctx: _ReachabilityContext) -> bool:
    has_step7a_file = (
        _verify_has_file(run_dir=ctx.run_dir, relative_path="token-report.json")
        or _verify_has_file(run_dir=ctx.run_dir, relative_path="timing-report.json")
        or _verify_has_file(run_dir=ctx.run_dir, relative_path="execution-issues.ndjson")
        or _verify_has_file(run_dir=ctx.run_dir, relative_path="session-transcript.jsonl")
    )
    if (
        _manifest_steps_ran_empty(ctx.manifest_data)
        and _final_summary_bail_signal_without_pr_evidence(
            run_dir=ctx.run_dir,
            manifest_pr_number=ctx.manifest_pr_number,
            manifest_data=ctx.manifest_data,
        )
        and not has_step7a_file
    ):
        return False
    return has_step7a_file or _condition_reached(ctx=ctx, condition="step8")


def _step8_reached(ctx: _ReachabilityContext) -> bool:
    has_version_bump = _verify_has_file(run_dir=ctx.run_dir, relative_path="version-bump-reasoning.md")
    if (
        _manifest_steps_ran_empty(ctx.manifest_data)
        and _final_summary_bail_signal_without_pr_evidence(
            run_dir=ctx.run_dir,
            manifest_pr_number=ctx.manifest_pr_number,
            manifest_data=ctx.manifest_data,
        )
        and not has_version_bump
    ):
        return False
    return (
        has_version_bump
        or _verify_has_file(run_dir=ctx.run_dir, relative_path="final-summary.md")
        or _condition_reached(ctx=ctx, condition="step9a1", chain=True)
    )


def _step18_reached(ctx: _ReachabilityContext) -> bool:
    return ctx.manifest_data.steps_ran.get("step18") is True


def _step9a1_bail_skip(ctx: _ReachabilityContext) -> bool:
    return _final_summary_bail_signal_without_pr_evidence(
        run_dir=ctx.run_dir,
        manifest_pr_number=ctx.manifest_pr_number,
        manifest_data=ctx.manifest_data,
    )


def _step9a1_reached(ctx: _ReachabilityContext, *, chain: bool) -> bool:
    has_stats = _verify_has_file(run_dir=ctx.run_dir, relative_path="run-statistics.md")
    if _manifest_step9a1_explicitly_skipped(ctx.manifest_data):
        return False
    if _manifest_step9a1_explicitly_ran(ctx.manifest_data):
        return True
    if _manifest_steps_ran_empty(ctx.manifest_data) and _step9a1_bail_skip(ctx) and not has_stats:
        return False
    if _step9a1_bail_skip(ctx) and not has_stats and _manifest_steps_ran_nonempty_without_step9a1(ctx.manifest_data):
        return False
    return has_stats if chain else True


def _execution_issue_text(run_dir: Path) -> str:
    path = run_dir / "execution-issues.ndjson"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _condition_reached(ctx: _ReachabilityContext, *, condition: str, chain: bool = False) -> bool:
    reached: bool | None = None
    if condition == "always":
        reached = True
    elif condition == "step5":
        reached = _step5_reached(ctx)
    elif condition == "step7a":
        reached = _step7a_reached(ctx)
    elif condition == "step8":
        reached = _step8_reached(ctx)
    elif condition == "step18":
        reached = _step18_reached(ctx)
    elif condition == "step9a1":
        reached = _step9a1_reached(ctx, chain=chain)
    elif condition == "exn-agg-validate-fail":
        reached = "merged output failed validation" in _execution_issue_text(ctx.run_dir)
    elif condition == "exn-agg-dispatch-fail":
        text = _execution_issue_text(ctx.run_dir)
        reached = any(
            needle in text
            for needle in (
                "dispatch-with-waterfall exited non-zero",
                "agent dispatch-waterfall exited non-zero",
                "DISPATCH_OK=false",
            )
        )
    if reached is not None:
        return reached
    msg = f"unsupported manifest condition: {condition}"
    raise ValueError(msg)


def _verify_condition_reached(  # noqa: PLR0913 - shared wrapper preserves the existing verify-completeness call shape.
    *,
    condition: str,
    run_dir: Path,
    manifest_data: Manifest,
    manifest_status: str,
    manifest_pr_number: str,
    chain: bool = False,
) -> bool:
    ctx = _ReachabilityContext(
        run_dir=run_dir,
        manifest_data=manifest_data,
        manifest_status=manifest_status,
        manifest_pr_number=manifest_pr_number,
    )
    return _condition_reached(ctx=ctx, condition=condition, chain=chain)


def _design_plan_review_round_dirs(run_dir: Path) -> list[Path]:
    root = run_dir / "plan-review"
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob("round-*") if path.is_dir())


def _design_plan_review_reached(run_dir: Path) -> bool:
    return bool(_design_plan_review_round_dirs(run_dir))


def _design_publish_reached(run_dir: Path) -> bool:
    if not (run_dir / "manifest.json").is_file():
        return False
    return any(
        (run_dir / name).is_file()
        for name in (
            "final-summary.md",
            "version-bump-reasoning.md",
        )
    )


def _design_transcript_capture_reached(run_dir: Path) -> bool:
    return _design_publish_reached(run_dir) or (run_dir / "session-transcript.jsonl").is_file()


def _implement_code_review_voting_reached(run_dir: Path) -> bool:
    return _verify_has_file(run_dir=run_dir, relative_path="code-review-tally.json")


def implement_step8_reachable(run_dir: Path, manifest: object | None) -> bool:
    """Return whether a compatible implement manifest reached Step 8 artifacts."""
    if not isinstance(manifest, Mapping):
        return False
    manifest_mapping = cast("Mapping[str, Any]", manifest)
    raw_steps = manifest_mapping.get("steps_ran")
    if isinstance(raw_steps, Mapping) and cast("Mapping[str, Any]", raw_steps).get("step8") is False:
        return False
    # The retired audit helper treated a malformed ``steps_ran`` value as
    # nonempty: it must not activate the terminal-bail shortcut and hide a
    # reachable artifact. Keep that compatibility boundary before parsing it
    # into the typed compatibility model, which otherwise normalizes it to {}.
    if raw_steps is not None and not isinstance(raw_steps, Mapping):
        return any(
            _verify_has_file(run_dir=run_dir, relative_path=relative_path)
            for relative_path in (
                "version-bump-reasoning.md",
                "final-summary.md",
                "run-statistics.md",
            )
        )
    typed = Manifest.from_json(manifest_mapping)
    return _verify_condition_reached(
        condition="step8",
        run_dir=run_dir,
        manifest_data=typed,
        manifest_status=_manifest_field(manifest=typed, key="status"),
        manifest_pr_number=_manifest_field(manifest=typed, key="pr_number"),
    )


def _load_run_manifest(run_dir: Path) -> Manifest | None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        return Manifest.from_json(_read_manifest_v2(manifest_path))
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _required_implement_artifacts(*, run_dir: Path, manifest: Manifest) -> list[RequiredArtifact]:
    manifest_status = _manifest_field(manifest=manifest, key="status")
    manifest_pr_number = _manifest_field(manifest=manifest, key="pr_number")
    rows: list[RequiredArtifact] = []
    if _verify_condition_reached(
        condition="step18",
        run_dir=run_dir,
        manifest_data=manifest,
        manifest_status=manifest_status,
        manifest_pr_number=manifest_pr_number,
    ):
        rows.extend(
            [
                RequiredArtifact(
                    slug="final-summary", relative_path="final-summary.md", skill="implement", condition="step18"
                ),
                RequiredArtifact(
                    slug=config.RUN_LOG_BATCH_TOKEN_REPORT,
                    relative_path="token-report.json",
                    skill="implement",
                    condition="step18",
                ),
                RequiredArtifact(
                    slug=config.RUN_LOG_BATCH_TIMING_REPORT,
                    relative_path="timing-report.json",
                    skill="implement",
                    condition="step18",
                ),
                RequiredArtifact(
                    slug="execution-issues",
                    relative_path="execution-issues.ndjson",
                    skill="implement",
                    condition="step18",
                ),
                RequiredArtifact(
                    slug=config.RUN_LOG_BATCH_SESSION_TRANSCRIPT,
                    relative_path="session-transcript.jsonl",
                    skill="implement",
                    condition="step18",
                ),
            ]
        )
    if _implement_code_review_voting_reached(run_dir):
        rows.append(RequiredArtifact(
            slug="review-findings-full",
            relative_path="review-findings-full.jsonl",
            skill="implement",
            condition="code-review-vote",
        ))
    return rows


def _design_run_approved(run_dir: Path) -> bool:
    summary = run_dir / "final-summary.md"
    if not summary.is_file() or summary.is_symlink():
        return False
    try:
        for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("## /design run ") or ":" not in line:
                continue
            outcome = line.rsplit(":", 1)[1].strip()
            return outcome in {"approved", "approved-partition"}
    except OSError:
        return False
    return False


def _derive_consumer_repo_root_from_run_dir(run_dir: Path) -> Path | None:
    try:
        if run_dir.parent.name != "design":
            return None
        log_root = run_dir.parent.parent
        if log_root.name != "larch-logs":
            return None
        return log_root.parent
    except IndexError:
        return None


def _invariant_assessment_required(*, run_dir: Path, repo_root: Path | None) -> bool:
    if not _design_run_approved(run_dir):
        return False
    resolved_repo_root = repo_root or _derive_consumer_repo_root_from_run_dir(run_dir)
    if resolved_repo_root is None:
        return False
    result = rust_runtime.architectural_knowledge_read(
        kind=config.ASSESSMENT_KIND_INVARIANTS,
        repo_root=resolved_repo_root,
    )
    return result.status == "present" and result.has_entries


def _guideline_assessment_required(*, run_dir: Path, repo_root: Path | None) -> bool:
    if not _design_run_approved(run_dir):
        return False
    resolved_repo_root = repo_root or _derive_consumer_repo_root_from_run_dir(run_dir)
    if resolved_repo_root is None:
        return False
    return (
        rust_runtime.architectural_knowledge_read(
            kind=config.ASSESSMENT_KIND_GUIDELINES,
            repo_root=resolved_repo_root,
        ).status
        == "present"
    )


def _required_design_artifacts(run_dir: Path, *, repo_root: Path | None = None) -> list[RequiredArtifact]:
    rows: list[RequiredArtifact] = []
    if _design_publish_reached(run_dir):
        rows.append(RequiredArtifact(
            slug="final-summary",
            relative_path="final-summary.md",
            skill="design",
            condition="design-publish",
        ))
    if _design_transcript_capture_reached(run_dir):
        rows.append(RequiredArtifact(
            slug=config.RUN_LOG_BATCH_SESSION_TRANSCRIPT,
            relative_path="session-transcript.jsonl",
            skill="design",
            condition="design-transcript",
        ))
    if _design_plan_review_reached(run_dir):
        for round_dir in _design_plan_review_round_dirs(run_dir):
            relative_path = (round_dir / "findings-classification.tsv").relative_to(run_dir).as_posix()
            rows.append(RequiredArtifact(
                slug=f"plan-review-{round_dir.name}",
                relative_path=relative_path,
                skill="design",
                condition="design-plan-review",
            ))
    if _invariant_assessment_required(run_dir=run_dir, repo_root=repo_root):
        rows.append(RequiredArtifact(
            slug="invariant-assessment",
            relative_path=architectural_guidelines.INVARIANT_DESIGN_ASSESSMENT,
            skill="design",
            condition="design-invariant-assessment",
        ))
    if _guideline_assessment_required(run_dir=run_dir, repo_root=repo_root):
        rows.append(RequiredArtifact(
            slug="guideline-assessment",
            relative_path=architectural_guidelines.DESIGN_ASSESSMENT,
            skill="design",
            condition="design-guideline-assessment",
        ))
    return rows


def required_artifacts_for_run(
    *,
    run_dir: Path,
    skill: str,
    manifest: Manifest,
    repo_root: Path | None = None,
) -> list[RequiredArtifact]:
    artifacts: list[RequiredArtifact] = []
    if manifest.extra and manifest.extra.get("lifecycle_schema_version") in {1, 2, 3}:
        artifacts.extend([
            RequiredArtifact(
                slug="final-report",
                relative_path="final-report.md",
                skill=skill,
                condition="universal-terminal",
            ),
            RequiredArtifact(
                slug=config.RUN_LOG_BATCH_SESSION_TRANSCRIPT,
                relative_path="session-transcript.jsonl",
                skill=skill,
                condition="universal-terminal",
            ),
        ])
    if skill == "implement":
        artifacts.extend(_required_implement_artifacts(run_dir=run_dir, manifest=manifest))
    elif skill == "design":
        artifacts.extend(_required_design_artifacts(run_dir, repo_root=repo_root))
    return artifacts


def _committed_execution_issues_path(
    run_dir: Path, skill: str, *, universal: bool = False
) -> Path:
    if universal:
        return run_dir / "execution-issues.ndjson"
    if skill == "design":
        return run_dir / "execution-issues.md"
    return run_dir / "execution-issues.ndjson"


def _flush_markdown_issue(
    *,
    issues: list[_CommittedIssue],
    category: str,
    body_lines: list[str],
) -> None:
    body = "\n".join(body_lines).strip()
    if category in _EXECUTION_ISSUE_CATEGORIES and body:
        issues.append(_CommittedIssue(category=category, body=body))


def _load_committed_markdown_execution_issues(path: Path) -> tuple[_CommittedIssue, ...]:
    issues: list[_CommittedIssue] = []
    category = ""
    body_lines: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("### "):
            _flush_markdown_issue(issues=issues, category=category, body_lines=body_lines)
            category = line.removeprefix("### ").strip()
            body_lines = []
            continue
        body_lines.append(line)
    _flush_markdown_issue(issues=issues, category=category, body_lines=body_lines)
    return tuple(issues)


def _load_committed_ndjson_execution_issues(path: Path) -> tuple[_CommittedIssue, ...]:
    issues: list[_CommittedIssue] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row_obj: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row_obj, dict):
            continue
        row = cast("dict[str, object]", row_obj)
        category_obj = row.get("category")
        body_obj = row.get("body")
        if isinstance(category_obj, str) and isinstance(body_obj, str):
            issues.append(_CommittedIssue(category=category_obj, body=body_obj))
    return tuple(issues)


def _load_committed_execution_issues(path: Path) -> tuple[_CommittedIssue, ...]:
    if not path.is_file():
        return ()
    if path.suffix == ".md":
        return _load_committed_markdown_execution_issues(path)
    return _load_committed_ndjson_execution_issues(path)


def _artifact_match_tokens(artifact: RequiredArtifact) -> tuple[str, ...]:
    tokens: list[str] = [artifact.relative_path]
    if artifact.slug:
        tokens.append(artifact.slug)
    if "plan-review/round-" not in artifact.relative_path:
        tokens.append(Path(artifact.relative_path).name)
        batch = _LARCH_LOG_BATCHES.get(artifact.slug)
        if batch is not None:
            tokens.append(f"{artifact.slug}{batch.extension}")
    return tuple(dict.fromkeys(token.lower() for token in tokens if token))


def _issue_body_names_artifact(*, category: str, body: str, artifact: RequiredArtifact) -> bool:
    tokens = _artifact_match_tokens(artifact)
    text_parts = [body]
    text_parts.extend(exec_issue_detail.structured_body_dedupe_keys(body, category))
    normalized = "\n".join(text_parts).lower()
    return any(token in normalized for token in tokens)


def artifact_present_or_waived(*, run_dir: Path, artifact: RequiredArtifact, execution_issues_path: Path) -> bool:
    if _verify_has_file(run_dir=run_dir, relative_path=artifact.relative_path):
        return True
    if execution_issues_path.parent.resolve(strict=False) != run_dir.resolve(strict=False):
        return False
    if execution_issues_path.name not in {"execution-issues.md", "execution-issues.ndjson"}:
        return False
    for issue in _load_committed_execution_issues(execution_issues_path):
        if issue.category not in _EXECUTION_ISSUE_CATEGORIES:
            continue
        if _issue_body_names_artifact(category=issue.category, body=issue.body, artifact=artifact):
            return True
    return False


def verify_run_log_completeness(
    *,
    run_dir: Path,
    skill: str,
    repo_root: Path | None = None,
) -> tuple[bool, list[str]]:
    manifest = _load_run_manifest(run_dir)
    if manifest is None:
        return False, ["manifest.json"]
    universal = bool(
        manifest.extra and manifest.extra.get("lifecycle_schema_version") in {1, 2, 3}
    )
    execution_issues_path = _committed_execution_issues_path(
        run_dir, skill, universal=universal
    )
    missing = [
        f"{artifact.slug}:{artifact.relative_path}"
        for artifact in required_artifacts_for_run(
            run_dir=run_dir,
            skill=skill,
            manifest=manifest,
            repo_root=repo_root,
        )
        if not artifact_present_or_waived(
            run_dir=run_dir,
            artifact=artifact,
            execution_issues_path=execution_issues_path,
        )
    ]
    return not missing, missing


def _parse_nonnegative_int(raw: str) -> int:
    text = raw.strip()
    if not re.fullmatch(r"[0-9]+", text):
        return 0
    return int(text)


def _parse_positive_int(raw: str) -> int | None:
    text = raw.strip()
    if not re.fullmatch(r"[0-9]+", text):
        return None
    value = int(text)
    return value if value > 0 else None


def read_state_kv(*, state_file: str | None, key: str) -> str:
    """Read a single KEY=value from an implement state file."""
    return _read_state_kv(state_file=state_file, key=key)


def read_resume_counters(state_file: str | None) -> ResumeCounters:
    """Read persisted CI-loop counters without raising on corrupt state."""
    if not state_file:
        return ResumeCounters(0, 0, 0, 0)
    return ResumeCounters(
        iteration=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="ITERATION")),
        rebase_count=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="REBASE_COUNT")),
        fix_attempts=_parse_nonnegative_int(_read_state_kv(state_file=state_file, key="FIX_ATTEMPTS")),
        transient_retries=_parse_nonnegative_int(
            _read_state_kv(state_file=state_file, key="TRANSIENT_RETRIES"),
        ),
    )


def _state_bool_or_default(raw: str, *, default: bool) -> bool:
    text = raw.strip()
    if text == "true":
        return True
    if text == "false":
        return False
    return default


def read_durable_flags(*, state_file: str | None, ctx: RunContext) -> DurableFlags:
    """Read durable mode flags state-first, falling back to the run context."""
    if not state_file:
        return DurableFlags(
            repo_unavailable=ctx.repo_unavailable,
            forked_target=ctx.forked_target,
            forked=ctx.forked,
            merge=ctx.merge,
            draft=ctx.draft,
        )
    raw_forked_target = _read_state_kv(state_file=state_file, key="FORKED_TARGET")
    forked_target = _state_bool_or_default(raw_forked_target, default=ctx.forked_target)
    forked = forked_target if raw_forked_target.strip() in {"true", "false"} else ctx.forked
    return DurableFlags(
        repo_unavailable=_state_bool_or_default(
            _read_state_kv(state_file=state_file, key="REPO_UNAVAILABLE"),
            default=ctx.repo_unavailable,
        ),
        forked_target=forked_target,
        forked=forked,
        merge=_state_bool_or_default(_read_state_kv(state_file=state_file, key="MERGE"), default=ctx.merge),
        draft=_state_bool_or_default(_read_state_kv(state_file=state_file, key="DRAFT"), default=ctx.draft),
    )


def parse_pr_number(*, state_file: str | None, ctx_pr_number: int | str | None) -> int | None:
    """Parse the persisted PR number; ignore stale context when state exists."""
    if not state_file:
        return None
    raw = _read_state_kv(state_file=state_file, key="PR_NUMBER")
    if raw.strip():
        return _parse_positive_int(raw)
    _ = ctx_pr_number
    return None


def manifest_status(ctx: RunContext) -> str:
    """Return the run-log manifest status without initializing or recovering it."""
    run_id = effective_run_id(ctx)
    if not run_id:
        return ""
    path = Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id / "manifest.json"
    if not path.is_file():
        return ""
    try:
        return Manifest.from_json(_read_manifest_v2(path)).status
    except (OSError, json.JSONDecodeError, TypeError):
        return ""


def effective_run_id(ctx: RunContext) -> str:
    """Prefer validated state-file RUN_ID over ctx.run_id for log paths."""
    state_run_id = _read_state_kv(state_file=ctx.state_file, key="RUN_ID")
    if state_run_id and validate_run_id_slug(state_run_id):
        return state_run_id
    if validate_run_id_slug(ctx.run_id):
        return ctx.run_id
    return ""


def _manifest_step9a1_explicitly_skipped(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is False


def _manifest_step9a1_explicitly_ran(manifest: Manifest) -> bool:
    return manifest.steps_ran.get("step9a1") is True


def _manifest_steps_ran_nonempty_without_step9a1(manifest: Manifest) -> bool:
    return bool(manifest.steps_ran) and "step9a1" not in manifest.steps_ran


# Expose _resolve_log_root for callers that import it via this module
__all__ = [
    "REFRESH_SKIP_RECOVERY_FAILED",
    "_MANIFEST_SCHEMA_VERSION",
    "_V2_RESERVED_KEYS",
    "DurableFlags",
    "Manifest",
    "RefreshSkip",
    "ResumeCounters",
    "_manifest_step9a1_explicitly_ran",
    "_manifest_step9a1_explicitly_skipped",
    "_manifest_steps_ran_nonempty_without_step9a1",
    "_read_manifest_v2",
    "_read_state_kv",
    "_resolve_log_root",
    "effective_run_id",
    "implement_step8_reachable",
    "manifest_status",
    "parse_pr_number",
    "read_durable_flags",
    "read_resume_counters",
    "read_state_kv",
]
