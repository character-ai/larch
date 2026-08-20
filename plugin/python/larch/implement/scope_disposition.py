"""Thin Python consumer of the Rust-owned `implement scope-disposition` verb.

Coverage attribution, banding, fingerprinting, artifact validation, and
follow-up filing live in `crates/larch-cli/src/implement_scope_disposition_commands.rs`
(#8612). Everything here either shells out to that owner through
`scripts/larch.sh` or deserializes the artifacts it published. No coverage rule
is reimplemented in Python.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from larch import io as larch_io
from larch.core import config, proc
from larch.core.proc import CommandResult, Runner
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env
from larch.errors import NeedsUserInput, ShipError

CoverageBand = Literal["advisory", "middle", "high"]
Disposition = Literal["proceed-partial", "bail-rescope"]

COVERAGE_JSON = "plan-coverage.json"
COVERAGE_ENV = "plan-coverage.env"
UNTOUCHED_PATHS = "plan-coverage-untouched.txt"
TODOS_LEFT = "plan-coverage-todos-left.txt"
DISPOSITION_JSON = "scope-disposition.json"
DEFERRED_INVENTORY = "deferred-plan-inventory.md"
FALLBACK_PROVENANCE = "scope-fallback-provenance.json"

_VERB = ("implement", "scope-disposition")
_ERROR_PREFIX = "implement scope-disposition: "
_STALE_LIVE_COVERAGE_MISMATCH = "coverage artifact does not match live repository inputs"


@dataclass(frozen=True)
class PlanCoverage:
    total: int
    touched: int
    untouched: int
    untouched_percent: int
    band: CoverageBand
    plan_paths: tuple[str, ...]
    touched_paths: tuple[str, ...]
    untouched_paths: tuple[str, ...]
    todos_left_count: int
    todos_left: tuple[str, ...]
    fingerprint: str
    disposition_required: bool
    plan_fidelity_forced: bool
    coverage_file: str
    untouched_file: str
    todos_file: str


@dataclass(frozen=True)
class DispositionRecord:
    disposition: Disposition
    fingerprint: str
    followup_issue_number: str = ""
    followup_issue_url: str = ""
    coverage_file: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    required: bool
    reason: str = ""
    coverage: PlanCoverage | None = None
    disposition: DispositionRecord | None = None


@dataclass(frozen=True)
class FollowupIssue:
    number: str
    url: str


@dataclass(frozen=True)
class ValidatedImplementContext:
    tmpdir: Path
    manifest_path: Path | None


def coverage_path(tmpdir: Path) -> Path:
    return tmpdir / COVERAGE_JSON


def coverage_env_path(tmpdir: Path) -> Path:
    return tmpdir / COVERAGE_ENV


def disposition_path(tmpdir: Path) -> Path:
    return tmpdir / DISPOSITION_JSON


def _artifact_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _safe_line(value: object, *, limit: int = 300) -> str:
    text = " ".join(str(value).split())
    return text[: limit - 1] + "…" if len(text) > limit else text


def _run(
    action: str,
    *,
    tmpdir: Path,
    paths: Mapping[str, Path | None] | None = None,
    fields: Mapping[str, str] | None = None,
) -> CommandResult:
    """Invoke one Rust-owned action through the verified bootstrap script.

    `paths` and `fields` carry the action's optional `--flag` values; empty and
    `None` entries are omitted so each action sees only the flags it declares.
    The bootstrap always runs through `proc`: a caller's `Runner` doubles that
    caller's own `git`/`gh` argv, and cannot answer for the owning binary.
    """
    argv: list[str] = [*_VERB, action, "--tmpdir", str(tmpdir)]
    for option, value in (paths or {}).items():
        if value is not None:
            argv.extend([option, str(value)])
    for option, text in (fields or {}).items():
        if text:
            argv.extend([option, text])
    root = Path(__file__).resolve().parents[3]
    return proc.run(
        [str(larch_entrypoint(root)), *argv], env=larch_entrypoint_env(root)
    )


def _refusal(result: CommandResult, action: str) -> str:
    """Return the owner's own refusal text, without its command prefix.

    Consumers match exact owner messages (teardown recovers only from the
    canonical stale-live mismatch), so the last diagnostic line wins over the
    frozen-fallback provenance note that may precede it.
    """
    lines = [line.strip() for line in (result.stderr or "").splitlines() if line.strip()]
    detail = lines[-1] if lines else (result.stdout or "").strip()
    cleaned = _safe_line(detail).removeprefix(_ERROR_PREFIX)
    return cleaned or f"implement scope-disposition {action} failed"


def _require(result: CommandResult, action: str) -> CommandResult:
    if result.returncode not in (config.EXIT_OK, config.EXIT_NEEDS_USER_INPUT):
        raise ShipError(_refusal(result, action))
    return result


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        with contextlib.suppress(ValueError):
            return int(value)
    return 0


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.lower() == "true"


def _as_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in cast("list[object]", value))


def _read_json_object(path: Path, *, label: str) -> Mapping[str, object] | None:
    if not _artifact_present(path):
        return None
    try:
        parsed: object = json.loads(
            larch_io.read_trusted_text(path, root=path.parent, errors="replace")
        )
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise ShipError(f"{label} unreadable or malformed: {_safe_line(exc)}") from exc
    if not isinstance(parsed, dict):
        raise ShipError(f"{label} schema-invalid")
    return cast("Mapping[str, object]", parsed)


def load_coverage(tmpdir: Path) -> PlanCoverage | None:
    """Deserialize the coverage artifact the Rust owner published."""
    data = _read_json_object(coverage_path(tmpdir), label="coverage artifact")
    if data is None:
        return None
    return PlanCoverage(
        total=_as_int(data.get("total")),
        touched=_as_int(data.get("touched")),
        untouched=_as_int(data.get("untouched")),
        untouched_percent=_as_int(data.get("untouched_percent")),
        band=cast("CoverageBand", str(data.get("band") or "")),
        plan_paths=_as_tuple(data.get("plan_paths")),
        touched_paths=_as_tuple(data.get("touched_paths")),
        untouched_paths=_as_tuple(data.get("untouched_paths")),
        todos_left_count=_as_int(data.get("todos_left_count")),
        todos_left=_as_tuple(data.get("todos_left")),
        fingerprint=str(data.get("fingerprint") or ""),
        disposition_required=_as_bool(data.get("disposition_required")),
        plan_fidelity_forced=_as_bool(data.get("plan_fidelity_forced")),
        coverage_file=str(data.get("coverage_file") or ""),
        untouched_file=str(data.get("untouched_file") or ""),
        todos_file=str(data.get("todos_file") or ""),
    )


def load_disposition(
    tmpdir: Path, *, coverage: PlanCoverage | None = None
) -> DispositionRecord | None:
    """Deserialize the recorded disposition, binding it to trusted coverage."""
    data = _read_json_object(disposition_path(tmpdir), label="scope disposition")
    if data is None:
        return None
    disposition = str(data.get("disposition") or "")
    if disposition not in {"proceed-partial", "bail-rescope"}:
        raise ShipError("scope disposition has invalid disposition")
    record = DispositionRecord(
        disposition=cast("Disposition", disposition),
        fingerprint=str(data.get("fingerprint") or ""),
        followup_issue_number=str(data.get("followup_issue_number") or ""),
        followup_issue_url=str(data.get("followup_issue_url") or ""),
        coverage_file=str(data.get("coverage_file") or ""),
    )
    if coverage is not None and (
        record.fingerprint != coverage.fingerprint
        or record.coverage_file != coverage.coverage_file
    ):
        raise ShipError("scope disposition does not match trusted coverage")
    return record


def resolve_implement_manifest(
    tmpdir: Path, manifest_path: Path | None = None
) -> Path | None:
    if manifest_path is not None:
        if not _artifact_present(manifest_path):
            raise ShipError("declared implement manifest is missing")
        return manifest_path
    for candidate in (
        tmpdir / "manifest.json",
        tmpdir / "codex-step2-out" / "manifest.json",
    ):
        if _artifact_present(candidate):
            return candidate
    return None


def is_pr_mutation_gate_relevant(
    *, tmpdir: Path, manifest_path: Path | None = None
) -> bool:
    return (
        any(
            _artifact_present(candidate)
            for candidate in (
                tmpdir / "plan.txt",
                coverage_path(tmpdir),
                disposition_path(tmpdir),
            )
        )
        or resolve_implement_manifest(tmpdir, manifest_path) is not None
    )


def _validated_implement_context(
    tmpdir: Path | None, *, manifest_path: Path | None = None
) -> ValidatedImplementContext | None:
    env_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if tmpdir is None and not env_tmpdir and manifest_path is None:
        return None
    effective = tmpdir if tmpdir is not None else (Path(env_tmpdir) if env_tmpdir else None)
    if effective is None:
        raise ShipError("declared implement context requires a trusted tmpdir")
    try:
        trusted = larch_io.validate_trusted_directory(effective)
    except OSError as exc:
        raise ShipError(
            f"declared implement tmpdir is invalid: {_safe_line(exc)}"
        ) from exc
    return ValidatedImplementContext(
        tmpdir=trusted, manifest_path=resolve_implement_manifest(trusted, manifest_path)
    )


def compute_coverage(
    *,
    tmpdir: Path,
    repo_root: Path,
    plan_file: Path | None = None,
    manifest_path: Path | None = None,
) -> PlanCoverage:
    """Recompute and republish plan coverage through the Rust owner.

    The owner publishes the coverage artifact set as one transaction, so this
    reads the result back instead of duplicating the computation.
    """
    result = _run(
        "compute",
        tmpdir=tmpdir,
        paths={
            "--repo-root": repo_root,
            "--plan-file": plan_file,
            "--manifest-path": manifest_path,
        },
    )
    if result.returncode != config.EXIT_OK:
        raise ShipError(_refusal(result, "compute"))
    coverage = load_coverage(tmpdir)
    if coverage is None:
        raise ShipError("plan coverage compute published no coverage artifact")
    return coverage


def compute_and_write_coverage(
    *,
    tmpdir: Path,
    repo_root: Path,
    plan_file: Path | None = None,
    manifest_path: Path | None = None,
) -> PlanCoverage:
    return compute_coverage(
        tmpdir=tmpdir,
        repo_root=repo_root,
        plan_file=plan_file,
        manifest_path=manifest_path,
    )


def _validation(result: CommandResult, tmpdir: Path) -> ValidationResult:
    fields = larch_io.parse_kv(result.stdout, cr_strip="strip")
    coverage: PlanCoverage | None = None
    record: DispositionRecord | None = None
    with contextlib.suppress(ShipError):
        coverage = load_coverage(tmpdir)
        record = load_disposition(tmpdir, coverage=coverage)
    return ValidationResult(
        ok=fields.get("SCOPE_DISPOSITION_VALID") == "true",
        required=fields.get("SCOPE_DISPOSITION_REQUIRED") == "true",
        reason=fields.get("SCOPE_DISPOSITION_REASON", ""),
        coverage=coverage,
        disposition=record,
    )


def validate_disposition_for_ship(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
) -> ValidationResult:
    result = _require(
        _run(
            "validate-ship",
            tmpdir=tmpdir,
            paths={"--repo-root": repo_root, "--manifest-path": manifest_path},
        ),
        "validate-ship",
    )
    return _validation(result, tmpdir)


def invalidate_stale_disposition(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
) -> ValidationResult:
    result = _require(
        _run(
            "invalidate-if-stale",
            tmpdir=tmpdir,
            paths={"--repo-root": repo_root, "--manifest-path": manifest_path},
        ),
        "invalidate-if-stale",
    )
    return _validation(result, tmpdir)


def require_valid_disposition_for_ship(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
) -> None:
    if not validate_disposition_for_ship(
        tmpdir=tmpdir,
        repo_root=repo_root,
        manifest_path=manifest_path,
    ).ok:
        raise NeedsUserInput(config.NEEDS_USER_SCOPE_DISPOSITION)


def require_pr_mutation_scope_disposition(
    *,
    tmpdir: Path | None,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> None:
    """Refuse a PR mutation whose plan scope lacks a valid disposition.

    `runner` stays in the signature for the `gh`/`pr` mutation-gate protocol;
    the gate itself reaches its Rust owner through the verified bootstrap, not
    through the caller's `git`/`gh` runner.
    """
    _ = runner
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None or not is_pr_mutation_gate_relevant(
        tmpdir=context.tmpdir, manifest_path=context.manifest_path
    ):
        return
    require_valid_disposition_for_ship(
        tmpdir=context.tmpdir,
        repo_root=repo_root,
        manifest_path=context.manifest_path,
    )


def record_disposition(  # noqa: PLR0913 - one keyword per recorded wire field
    *,
    tmpdir: Path,
    disposition: Disposition,
    repo_root: Path,
    repo: str = "",
    tracking_issue_number: str = "",
    run_id: str = "",
    coverage: PlanCoverage | None = None,
    manifest_path: Path | None = None,
) -> DispositionRecord:
    """Record the operator's disposition through the Rust owner.

    ``coverage`` is accepted for signature compatibility; the owner always
    revalidates live coverage before it writes, so a caller-supplied snapshot
    cannot widen what gets recorded.
    """
    _ = coverage
    result = _run(
        "record",
        tmpdir=tmpdir,
        paths={"--repo-root": repo_root, "--manifest-path": manifest_path},
        fields={
            "--disposition": disposition,
            "--repo": repo,
            "--tracking-issue": tracking_issue_number,
            "--run-id": run_id,
        },
    )
    if result.returncode != config.EXIT_OK:
        raise ShipError(_refusal(result, "record"))
    record = load_disposition(tmpdir)
    if record is None:
        raise ShipError("scope disposition record published no artifact")
    return record


def _inventory(context: ValidatedImplementContext, repo_root: Path) -> str:
    """Render the deferred inventory, enforcing the owner's integrity gate."""
    result = _run(
        "render-deferred-inventory",
        tmpdir=context.tmpdir,
        paths={"--repo-root": repo_root, "--manifest-path": context.manifest_path},
    )
    if result.returncode != config.EXIT_OK:
        raise ShipError(_refusal(result, "render-deferred-inventory"))
    return result.stdout


def disposition_link_kind(
    tmpdir: Path | None = None,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None:
        return "closes"
    if repo_root is None:
        raise ShipError("repository root is required to load scope disposition")
    # The inventory action is the owner's trusted-coverage gate: it refuses a
    # durable disposition without live coverage before anything reads the record.
    _ = _inventory(context, repo_root)
    record = load_disposition(
        context.tmpdir, coverage=load_coverage(context.tmpdir)
    )
    return "part-of" if record and record.disposition == "proceed-partial" else "closes"


def disposition_deferred_inventory(
    tmpdir: Path | None = None,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None:
        return ""
    if repo_root is None:
        raise ShipError("repository root is required to load deferred inventory")
    return _inventory(context, repo_root)


def plan_coverage_summary_line(tmpdir: Path, *, manifest_path: Path | None = None) -> str:
    """Render the final report's optional `- **Plan coverage**:` line body."""
    result = _run(
        "summary-line", tmpdir=tmpdir, paths={"--manifest-path": manifest_path}
    )
    fields = larch_io.parse_kv(result.stdout, cr_strip="strip")
    if result.returncode != config.EXIT_OK:
        raise ShipError(
            fields.get("PLAN_COVERAGE_ERROR") or _refusal(result, "summary-line")
        )
    return fields.get("PLAN_COVERAGE_LINE", "")


def plan_coverage_summary_line_or_empty(
    tmpdir: Path, *, manifest_path: Path | None = None
) -> str:
    """Optional plan-coverage line; the owner already degrades post-merge staleness."""
    return plan_coverage_summary_line(tmpdir, manifest_path=manifest_path)
