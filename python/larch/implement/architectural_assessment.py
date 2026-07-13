"""Materialize and persist Step 8 architectural assessments.

A read-only assessment subagent (``agents/arch-assessor.md``) authors the
``/implement`` Step 8 ``invariants``/``guidelines`` notes. This module keeps
that flow deterministic: evidence materialization, identity fingerprints,
durable persistence, and a fail-closed submit gate. It owns no model lanes and
spawns nothing; the orchestrator spawns the subagent and passes file paths only.

``materialize`` validates or refreshes materialization for the requested kinds
and prints the evidence paths the subagent needs. ``submit`` revalidates
identity fail-closed and persists one authored note. ``deterministic_out_of_scope``
plus ``write_deterministic_clean_note`` run inside ``materialize`` so docs-only
diffs never reach the subagent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, cast

from larch.core import architectural_guidelines, config, logging_util, redact
from larch.core.assessment_kind import AssessmentKind, GUIDELINES, INVARIANTS
from larch.implement import ship_guidelines

_MAX_SANITIZE_DETAIL_BYTES: Final = 8 * 1024
_MAX_ASSESSMENT_CHARS: Final = 12000
_KIND_ORDER: Final = (config.ASSESSMENT_KIND_INVARIANTS, config.ASSESSMENT_KIND_GUIDELINES)
_DIFF_HEADER_RE: Final = re.compile(r"^diff --git a/(\S+) b/(\S+)$")
_IDENTIFIER_RE: Final = re.compile(r"^#{1,6}\s+((?:I|G)-[A-Za-z0-9-]+-\d+):", re.MULTILINE)
_COMMIT_RE: Final = re.compile(r"^[0-9a-f]{40}$")
_BASE_REF_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
# submit exits with this code only when HEAD moved between materialize and
# submit. The orchestrator treats it as "re-materialize and spawn a fresh
# assessor", bounded at two attempts per kind (issue #7193 item 5).
_EXIT_HEAD_DRIFT: Final = 10
_REAUTHOR_REASONS: Final[frozenset[str]] = frozenset({
    config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME,
    config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH,
    config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA,
})


@dataclass(frozen=True)
class MaterializedEvidence:
    """Validated evidence identity for one requested kind."""

    kind: str
    head_sha: str
    base_ref: str
    diff_path: Path
    diff_text: str
    diff_fingerprint: str
    knowledge_path: Path
    knowledge_sha256: str
    identifiers: frozenset[str]


@dataclass(frozen=True)
class AssessmentResult:
    """Validated result for one kind."""

    kind: str
    state: str
    assessment: str
    identifiers: tuple[str, ...]
    head_sha: str
    base_ref: str
    diff_fingerprint: str
    knowledge_sha256: str


class _HeadDrift(RuntimeError):
    """Signal that an assessment must be rematerialized for a new HEAD."""


class _DeviationLogPending(OSError):
    """Signal that a durable deviation awaits its retryable warning-log append."""


class _ReauthorRequired(ValueError):
    """The assessment must be revised before durable persistence."""


def _reauthor_status(reason: str) -> str:
    """Encode a bounded reassessment reason in a coordinator result."""
    bounded_reason = reason if reason in _REAUTHOR_REASONS else config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA
    return f"{config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED}:{bounded_reason}"


def _descriptor_for_kind(kind: str) -> AssessmentKind:
    return INVARIANTS if kind == config.ASSESSMENT_KIND_INVARIANTS else GUIDELINES


def normalize_kinds(raw_kinds: Sequence[str]) -> tuple[str, ...]:
    """Validate, deduplicate, and order requested assessment kinds."""
    requested: set[str] = set(raw_kinds)
    supported: set[str] = set(_KIND_ORDER)
    if not requested:
        raise ValueError("at least one --kind is required")
    unknown: set[str] = requested - supported
    if unknown:
        raise ValueError(f"unsupported assessment kind: {sorted(unknown)[0]}")
    return tuple(kind for kind in _KIND_ORDER if kind in requested)


def _regular_file(path: Path) -> bool:
    try:
        mode: int = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and not path.is_symlink()


def _under(path: Path, root: Path) -> bool:
    try:
        _ = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _read_regular(path: Path, *, root: Path) -> str:
    if not _under(path, root) or not _regular_file(path):
        raise ValueError(f"invalid evidence file: {path.name}")
    return path.read_text(encoding="utf-8")


def _read_env_strict(path: Path, *, root: Path) -> dict[str, str]:
    text: str = _read_regular(path, root=root)
    values: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        key, separator, value = line.partition("=")
        if not separator or not key or key in values:
            raise ValueError(f"malformed or duplicate materialization field: {key or '<empty>'}")
        values[key] = value
    return values


def _git_read(repo_root: Path, argv: Sequence[str]) -> str:
    completed = subprocess.run(  # lint-subprocess-via-runner: ok read-only git identity validation
        ["/usr/bin/git", *argv], cwd=repo_root, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(logging_util.sanitize_diagnostic_line(completed.stderr or "git validation failed"))
    return completed.stdout.strip()


def _validate_recorded_identity(*, head_sha: str, base_ref: str) -> None:
    if _COMMIT_RE.fullmatch(head_sha) is None:
        raise ValueError("materialization HEAD_SHA is invalid")
    if _BASE_REF_RE.fullmatch(base_ref) is None or base_ref.startswith("-") or "/" not in base_ref:
        raise ValueError("materialization BASE_REF is invalid")


def _recorded_diff(*, repo_root: Path, head_sha: str, base_ref: str) -> str:
    _validate_recorded_identity(head_sha=head_sha, base_ref=base_ref)
    remote, ref = base_ref.split("/", 1)
    return architectural_guidelines._materialize_implementation_diff_for_head(  # noqa: SLF001 - frozen snapshot validator needs the exact historical diff helper  # pyright: ignore[reportPrivateUsage]  # exact historical diff helper is intentionally private
        repo_root, head_sha=head_sha, base_remote=remote, base_ref=ref
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _kind_paths(kind: str, implement_tmpdir: Path, repo_root: Path) -> tuple[Path, Path, Path]:
    if kind == config.ASSESSMENT_KIND_INVARIANTS:
        return (
            implement_tmpdir / architectural_guidelines.INVARIANT_MATERIALIZE_ENV,
            implement_tmpdir / architectural_guidelines.INVARIANT_MATERIALIZED_DIFF,
            repo_root / architectural_guidelines.INVARIANTS_FILENAME,
        )
    return (
        implement_tmpdir / architectural_guidelines.MATERIALIZE_ENV,
        implement_tmpdir / architectural_guidelines.MATERIALIZED_DIFF,
        repo_root / architectural_guidelines.GUIDELINES_FILENAME,
    )


def validate_materialization(*, kind: str, repo_root: Path, implement_tmpdir: Path) -> MaterializedEvidence:
    """Validate a recorded materialization against the covered snapshot identity."""
    metadata_path, expected_diff_path, expected_knowledge_path = _kind_paths(kind, implement_tmpdir, repo_root)
    metadata: dict[str, str] = _read_env_strict(metadata_path, root=implement_tmpdir)
    status_key: str = "INVARIANTS_STATUS" if kind == config.ASSESSMENT_KIND_INVARIANTS else "GUIDELINES_STATUS"
    knowledge_key: str = "INVARIANTS_PATH" if kind == config.ASSESSMENT_KIND_INVARIANTS else "GUIDELINES_PATH"
    required: tuple[str, ...] = ("STATUS", "HEAD_SHA", "BASE_REF", "DIFF_FINGERPRINT", "DIFF_SNAPSHOT", status_key, knowledge_key)
    if any(not metadata.get(key, "") for key in required) or metadata["STATUS"] != "present" or metadata[status_key] != "present":
        raise ValueError(f"incomplete {kind} materialization metadata")
    head_sha: str = metadata["HEAD_SHA"]
    base_ref: str = metadata["BASE_REF"]
    _validate_recorded_identity(head_sha=head_sha, base_ref=base_ref)
    resolved_head: str = _git_read(repo_root, ["rev-parse", "--verify", f"{head_sha}^{{commit}}"])
    if resolved_head != head_sha:
        raise ValueError(f"{kind} covered HEAD is not canonical")
    _ = _git_read(repo_root, ["rev-parse", "--verify", f"{base_ref}^{{commit}}"])
    diff_path = Path(metadata["DIFF_SNAPSHOT"])
    if diff_path.resolve() != expected_diff_path.resolve():
        raise ValueError(f"{kind} diff snapshot path mismatch")
    knowledge_path = Path(metadata[knowledge_key])
    if knowledge_path.resolve() != expected_knowledge_path.resolve():
        raise ValueError(f"{kind} knowledge path mismatch")
    diff_text: str = _read_regular(diff_path, root=implement_tmpdir)
    if architectural_guidelines.diff_fingerprint(diff_text) != metadata["DIFF_FINGERPRINT"]:
        raise ValueError(f"{kind} frozen diff fingerprint mismatch")
    if _recorded_diff(repo_root=repo_root, head_sha=head_sha, base_ref=base_ref) != diff_text:
        raise ValueError(f"{kind} frozen diff does not match covered snapshot")
    knowledge_text: str = _read_regular(knowledge_path, root=repo_root)
    identifiers: frozenset[str] = frozenset(_IDENTIFIER_RE.findall(knowledge_text))
    return MaterializedEvidence(
        kind=kind,
        head_sha=head_sha,
        base_ref=base_ref,
        diff_path=diff_path,
        diff_text=diff_text,
        diff_fingerprint=metadata["DIFF_FINGERPRINT"],
        knowledge_path=knowledge_path,
        knowledge_sha256=_sha256(knowledge_text),
        identifiers=identifiers,
    )


def _diff_paths(diff_text: str) -> tuple[str, ...] | None:
    if not diff_text.strip():
        return ()
    paths: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith(("Binary files ", "GIT binary patch", "rename from ", "rename to ")):
            return None
        if not line.startswith("diff --git "):
            continue
        match = _DIFF_HEADER_RE.fullmatch(line)
        if match is None or match.group(1) != match.group(2):
            return None
        path: str = match.group(1)
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or candidate.as_posix() != path or any(part in {"", ".", ".."} for part in candidate.parts):
            return None
        paths.append(path)
    return tuple(paths) if paths else None


def deterministic_out_of_scope(diff_text: str) -> bool:
    """Return true only when every changed path is proven outside scope."""
    paths: tuple[str, ...] | None = _diff_paths(diff_text)
    if not paths:
        return False
    return all(
        (path.startswith("docs/") and path.endswith(".md")) or path.startswith("larch-logs/")
        for path in paths
    )


def _load_json(path: Path, *, root: Path) -> object:
    return json.loads(_read_regular(path, root=root))


def _outcome_valid(kind: str, implement_tmpdir: Path, metadata: dict[str, str]) -> bool:
    path = (
        architectural_guidelines.invariant_ship_outcome_path(implement_tmpdir)
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.guideline_ship_outcome_path(implement_tmpdir)
    )
    try:
        data: object = _load_json(path, root=implement_tmpdir)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return False
    validator = (
        architectural_guidelines.validate_invariant_ship_outcome_record
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.validate_guideline_ship_outcome_record
    )
    if validator(data) is not None or not isinstance(data, dict):
        return False
    record: dict[str, object] = cast("dict[str, object]", data)
    return str(record.get("base_ref") or "") == metadata.get("BASE_REF", "") and str(record.get("head_sha") or "") == (metadata.get("ASSESSED_HEAD_SHA", "") or metadata.get("HEAD_SHA", ""))


def _authored_note_valid(kind: str, *, implement_tmpdir: Path, outcome: str) -> bool:
    note_path = (
        architectural_guidelines.invariant_durable_note_path(implement_tmpdir)
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.durable_note_path(implement_tmpdir)
    )
    try:
        note = _read_regular(note_path, root=implement_tmpdir)
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return architectural_guidelines.authored_outcome_valid(
        note=note,
        outcome=outcome,
        invariant=kind == config.ASSESSMENT_KIND_INVARIANTS,
    )


def _already_handled(kind: str, *, repo_root: Path, implement_tmpdir: Path, head_sha: str) -> bool:
    metadata = (
        architectural_guidelines.invariant_durable_note_metadata(implement_tmpdir)
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.durable_note_metadata(implement_tmpdir)
    )
    base_ref: str = metadata.get("BASE_REF", "")
    note_state: str = metadata.get("NOTE_STATE", config.NOTE_STATE_AUTHORED)
    allowed: frozenset[str] = (
        config.INVARIANT_ASSESSMENT_OUTCOMES
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else config.GUIDELINE_ASSESSMENT_OUTCOMES
    )
    if note_state == config.NOTE_STATE_AUTHORED:
        outcome = metadata.get("ASSESSMENT_KIND", "")
        if outcome not in allowed or not _authored_note_valid(kind, implement_tmpdir=implement_tmpdir, outcome=outcome):
            return False
    consumer = architectural_guidelines.invariant_note_consumable if kind == config.ASSESSMENT_KIND_INVARIANTS else architectural_guidelines.note_consumable
    if not (base_ref and consumer(implement_tmpdir=implement_tmpdir, head_sha=head_sha, base_ref=base_ref, repo_root=repo_root) and _outcome_valid(kind, implement_tmpdir, metadata)):
        return False
    if metadata.get("NOTE_STATE") == config.NOTE_STATE_UNAVAILABLE:
        # A prior `unavailable` note records a transient capture failure, not durable
        # coverage; a re-run must re-author it rather than reuse the stale receipt.
        # The /implement subagent path never produces this state; it remains as a
        # defensive refusal for any /design-shared or historical unavailable note.
        return False
    if kind == config.ASSESSMENT_KIND_GUIDELINES and metadata.get("ASSESSMENT_KIND") == "deviation":
        note_path = architectural_guidelines.durable_note_path(implement_tmpdir)
        try:
            append_status = architectural_guidelines.append_deviation_note(
                implement_tmpdir, _read_regular(note_path, root=implement_tmpdir)
            )
        except (OSError, UnicodeDecodeError, ValueError):
            return False
        return append_status in {"ok", "duplicate"}
    return True


def _materialize_current(kind: str, *, repo_root: Path, implement_tmpdir: Path, head_sha: str) -> MaterializedEvidence | None:
    if kind == config.ASSESSMENT_KIND_INVARIANTS:
        result = architectural_guidelines.prepare_invariant_compose_assessment(
            implement_tmpdir=implement_tmpdir, repo_root=repo_root, expected_head_sha=head_sha, forked_target=False
        )
    else:
        result = architectural_guidelines.prepare_compose_assessment(
            implement_tmpdir=implement_tmpdir, repo_root=repo_root, expected_head_sha=head_sha, forked_target=False
        )
    if result.status == "current":
        return None
    if result.status != "assessment-required":
        raise ValueError(result.warning or f"{kind} materialization was not produced")
    return validate_materialization(kind=kind, repo_root=repo_root, implement_tmpdir=implement_tmpdir)


def _write_outcome(
    kind: str,
    *,
    implement_tmpdir: Path,
    result: AssessmentResult,
    note_state: str = config.NOTE_STATE_AUTHORED,
    detail: str = "",
) -> None:
    if kind == config.ASSESSMENT_KIND_INVARIANTS:
        gate = ship_guidelines.InvariantsGateResult(
            note=result.assessment, detail=detail, invariants_status="present",
            assessment_kind=result.state, note_state=note_state,
        )
        _ = ship_guidelines.write_invariant_ship_outcome(
            implement_tmpdir=str(implement_tmpdir), result=gate,
            head_sha=result.head_sha, base_ref=result.base_ref,
        )
    else:
        gate = ship_guidelines.GuidelinesGateResult(
            note=result.assessment, detail=detail, guidelines_status="present",
            assessment_kind=result.state, note_state=note_state,
        )
        _ = ship_guidelines.write_guideline_ship_outcome(
            implement_tmpdir=str(implement_tmpdir), result=gate,
            head_sha=result.head_sha, base_ref=result.base_ref,
        )


def _persist_result(result: AssessmentResult, *, repo_root: Path, implement_tmpdir: Path) -> None:
    current_head: str = _git_read(repo_root, ["rev-parse", "HEAD"])
    if current_head != result.head_sha:
        raise _HeadDrift("HEAD changed after architectural assessment launch")
    descriptor = _descriptor_for_kind(result.kind)
    write_compose = (
        architectural_guidelines.write_invariant_compose_assessment
        if descriptor.is_invariant
        else architectural_guidelines.write_compose_assessment
    )
    try:
        write_compose(
            implement_tmpdir=implement_tmpdir,
            assessment_text=result.assessment,
            outcome=result.state,
            repo_root=repo_root,
        )
    except architectural_guidelines.AssessmentReauthorRequired as exc:
        raise _ReauthorRequired(str(exc)) from exc
    _write_outcome(result.kind, implement_tmpdir=implement_tmpdir, result=result)
    metadata_reader = (
        architectural_guidelines.invariant_durable_note_metadata
        if descriptor.is_invariant
        else architectural_guidelines.durable_note_metadata
    )
    if not _outcome_valid(result.kind, implement_tmpdir, metadata_reader(implement_tmpdir)):
        raise _ReauthorRequired(config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA)
    if (
        result.kind == config.ASSESSMENT_KIND_GUIDELINES
        and result.state == "deviation"
        and architectural_guidelines.append_deviation_note(implement_tmpdir, result.assessment) not in {"ok", "duplicate"}
    ):
        raise _DeviationLogPending("guideline deviation log append failed")


def _persist_clean(evidence: MaterializedEvidence, *, repo_root: Path, implement_tmpdir: Path) -> None:
    if _git_read(repo_root, ["rev-parse", "HEAD"]) != evidence.head_sha:
        raise _HeadDrift("HEAD changed before deterministic-clean persistence")
    descriptor = _descriptor_for_kind(evidence.kind)
    architectural_guidelines.write_deterministic_clean_note(
        implement_tmpdir=implement_tmpdir,
        head_sha=evidence.head_sha,
        base_ref=evidence.base_ref,
        diff_text=evidence.diff_text,
        kind=descriptor,
    )
    clean_text: str = descriptor.clean_presentation_note
    result = AssessmentResult(evidence.kind, "clean", clean_text, (), evidence.head_sha, evidence.base_ref, evidence.diff_fingerprint, evidence.knowledge_sha256)
    _write_outcome(evidence.kind, implement_tmpdir=implement_tmpdir, result=result, note_state=config.NOTE_STATE_DETERMINISTIC_CLEAN)


def _repair_current_outcome(kind: str, *, repo_root: Path, implement_tmpdir: Path, head_sha: str) -> str:
    """Repair a missing outcome sidecar without replacing a current durable note."""
    if _git_read(repo_root, ["rev-parse", "HEAD"]) != head_sha:
        raise _HeadDrift("HEAD changed before current-outcome repair")
    descriptor = _descriptor_for_kind(kind)
    invalidator = (
        architectural_guidelines.invalidate_invariant_implement_note
        if descriptor.is_invariant
        else architectural_guidelines.invalidate_implement_note
    )
    metadata = (
        architectural_guidelines.invariant_durable_note_metadata
        if descriptor.is_invariant
        else architectural_guidelines.durable_note_metadata
    )(implement_tmpdir)
    note_path = (
        architectural_guidelines.invariant_durable_note_path
        if descriptor.is_invariant
        else architectural_guidelines.durable_note_path
    )(implement_tmpdir)
    state = metadata.get("ASSESSMENT_KIND", "")
    allowed = {config.ASSESSMENT_OUTCOME_CLEAN, descriptor.non_clean_authored_outcome}
    if state not in allowed:
        invalidator(implement_tmpdir)
        return _reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME)
    try:
        note = _read_regular(note_path, root=implement_tmpdir)
    except (OSError, UnicodeDecodeError, ValueError):
        invalidator(implement_tmpdir)
        return _reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA)
    if not architectural_guidelines.authored_outcome_valid(
        note=note,
        outcome=state,
        invariant=descriptor.is_invariant,
    ):
        invalidator(implement_tmpdir)
        return _reauthor_status(
            config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH
            if state == "clean"
            else config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME
        )
    if not _outcome_valid(kind, implement_tmpdir, metadata):
        result = AssessmentResult(kind, state, note, (), head_sha, metadata["BASE_REF"], "", "")
        _write_outcome(kind, implement_tmpdir=implement_tmpdir, result=result)
        if not _outcome_valid(kind, implement_tmpdir, metadata):
            raise OSError("architectural outcome repair postcondition failed")
    if kind == config.ASSESSMENT_KIND_GUIDELINES and state == "deviation":
        append_status = architectural_guidelines.append_deviation_note(implement_tmpdir, _read_regular(note_path, root=implement_tmpdir))
        return "handled" if append_status in {"ok", "duplicate"} else "log-pending"
    return "handled"


def _safe_detail(text: str, implement_tmpdir: Path) -> str:
    redacted: str = redact.redact_outbound(text).replace(str(implement_tmpdir), "<implement-tmpdir>")
    flattened: str = "".join(character if character >= " " and character != "\x7f" else " " for character in redacted)
    return logging_util.sanitize_diagnostic_line(flattened).strip()[:500]


def sanitize_detail(text: str, *, implement_tmpdir: Path) -> str:
    """Return one bounded diagnostic safe for a line-oriented handoff."""
    return _safe_detail(text, implement_tmpdir)


def _prepare_kind(
    kind: str,
    *,
    repo_root: Path,
    implement_tmpdir: Path,
    head_sha: str,
) -> tuple[str, MaterializedEvidence | None]:
    if _already_handled(
        kind,
        repo_root=repo_root,
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
    ):
        return "handled", None
    evidence = _materialize_current(
        kind,
        repo_root=repo_root,
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
    )
    if evidence is None:
        repair = _repair_current_outcome(
            kind,
            repo_root=repo_root,
            implement_tmpdir=implement_tmpdir,
            head_sha=head_sha,
        )
        if repair in {"handled", "log-pending"}:
            return repair, None
        # An invalid current note (re-author-required) is re-assessed by the
        # subagent against the current materialization rather than terminalized.
        evidence = validate_materialization(kind=kind, repo_root=repo_root, implement_tmpdir=implement_tmpdir)
    if deterministic_out_of_scope(evidence.diff_text):
        _persist_clean(evidence, repo_root=repo_root, implement_tmpdir=implement_tmpdir)
        return "deterministic-clean", None
    return "", evidence


def _prepare_pending(
    normalized: Sequence[str],
    *,
    repo_root: Path,
    implement_tmpdir: Path,
) -> tuple[dict[str, str], list[MaterializedEvidence]]:
    for _attempt in range(3):
        statuses: dict[str, str] = {}
        pending: list[MaterializedEvidence] = []
        head_sha = _git_read(repo_root, ["rev-parse", "HEAD"])
        try:
            for kind in normalized:
                status, evidence = _prepare_kind(
                    kind,
                    repo_root=repo_root,
                    implement_tmpdir=implement_tmpdir,
                    head_sha=head_sha,
                )
                if status:
                    statuses[kind] = status
                elif evidence is not None:
                    pending.append(evidence)
        except _HeadDrift:
            continue
        return statuses, pending
    raise ValueError("HEAD changed repeatedly during architectural assessment setup")


def _durable_note_path(kind: str, implement_tmpdir: Path) -> Path:
    descriptor = _descriptor_for_kind(kind)
    return (
        architectural_guidelines.invariant_durable_note_path(implement_tmpdir)
        if descriptor.is_invariant
        else architectural_guidelines.durable_note_path(implement_tmpdir)
    )


def materialize(
    *,
    kinds: Sequence[str],
    repo_root: Path,
    implement_tmpdir: Path,
) -> tuple[dict[str, str], list[MaterializedEvidence]]:
    """Materialize evidence for requested kinds; return statuses and pending evidence."""
    normalized: tuple[str, ...] = normalize_kinds(kinds)
    root: Path = repo_root.resolve(strict=True)
    tmpdir: Path = implement_tmpdir.resolve(strict=True)
    if root.is_symlink() or tmpdir.is_symlink() or not root.is_dir() or not tmpdir.is_dir():
        raise ValueError("repo root and implement tmpdir must be non-symlink directories")
    return _prepare_pending(normalized, repo_root=root, implement_tmpdir=tmpdir)


def submit(
    *,
    kind: str,
    state: str,
    note: str,
    repo_root: Path,
    implement_tmpdir: Path,
) -> AssessmentResult:
    """Revalidate identity fail-closed and persist one authored assessment note."""
    normalized = normalize_kinds([kind])
    single = normalized[0]
    descriptor = _descriptor_for_kind(single)
    allowed_states = {"clean", "violation"} if descriptor.is_invariant else {"clean", "deviation"}
    if state not in allowed_states:
        raise ValueError(f"unsupported {single} assessment state: {state}")
    if not note.strip() or len(note) > _MAX_ASSESSMENT_CHARS:
        raise ValueError("assessment note is empty or oversized")
    root: Path = repo_root.resolve(strict=True)
    tmpdir: Path = implement_tmpdir.resolve(strict=True)
    if root.is_symlink() or tmpdir.is_symlink() or not root.is_dir() or not tmpdir.is_dir():
        raise ValueError("repo root and implement tmpdir must be non-symlink directories")
    evidence = validate_materialization(kind=single, repo_root=root, implement_tmpdir=tmpdir)
    if _git_read(root, ["rev-parse", "HEAD"]) != evidence.head_sha:
        raise _HeadDrift("HEAD changed between architectural assessment materialize and submit")
    redacted_note = redact.redact_outbound(note)
    result = AssessmentResult(
        single, state, redacted_note, (), evidence.head_sha, evidence.base_ref,
        evidence.diff_fingerprint, evidence.knowledge_sha256,
    )
    _persist_result(result, repo_root=root, implement_tmpdir=tmpdir)
    return result


def materialize_main(argv: list[str] | None = None) -> int:
    """CLI entry point: materialize evidence and print per-kind paths for the subagent."""
    parser = argparse.ArgumentParser(prog="cli.py architectural-assessment materialize")
    _ = parser.add_argument("--kind", action="append", default=[])
    _ = parser.add_argument("--repo-root", default=os.environ.get(config.ENV_REPO, ""))
    _ = parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    try:
        normalized = normalize_kinds(args.kind)
    except ValueError as exc:
        print("ASSESSMENT_MATERIALIZE_STATUS=usage-error")
        print(f"ASSESSMENT_DETAIL={logging_util.sanitize_diagnostic_line(str(exc))}")
        return config.EXIT_USAGE
    if not args.repo_root or not args.implement_tmpdir:
        print("ASSESSMENT_MATERIALIZE_STATUS=usage-error")
        print("ASSESSMENT_DETAIL=repo root and implement tmpdir are required")
        return config.EXIT_USAGE
    try:
        statuses, pending = materialize(
            kinds=args.kind, repo_root=Path(args.repo_root), implement_tmpdir=Path(args.implement_tmpdir),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print("ASSESSMENT_MATERIALIZE_STATUS=failed")
        print(f"ASSESSMENT_DETAIL={_safe_detail(str(exc), Path(args.implement_tmpdir))}")
        return config.EXIT_INTERNAL_ERROR
    pending_kinds = [evidence.kind for evidence in pending]
    deterministic_kinds = [kind for kind in normalized if statuses.get(kind)]
    print("ASSESSMENT_MATERIALIZE_STATUS=ok")
    print(f"ASSESSMENT_REQUESTED_KINDS={','.join(normalized)}")
    print(f"ASSESSMENT_PENDING_KINDS={','.join(pending_kinds)}")
    print(f"ASSESSMENT_DETERMINISTIC_KINDS={','.join(deterministic_kinds)}")
    for evidence in pending:
        upper = evidence.kind.upper()
        prior = _durable_note_path(evidence.kind, Path(args.implement_tmpdir))
        prior_value = str(prior) if _regular_file(prior) and _under(prior, Path(args.implement_tmpdir)) else ""
        print(f"ASSESSMENT_KIND_{upper}_DIFF_PATH={evidence.diff_path}")
        print(f"ASSESSMENT_KIND_{upper}_KNOWLEDGE_PATH={evidence.knowledge_path}")
        print(f"ASSESSMENT_KIND_{upper}_PRIOR_NOTE_PATH={prior_value}")
        print(f"ASSESSMENT_KIND_{upper}_HEAD_SHA={evidence.head_sha}")
        print(f"ASSESSMENT_KIND_{upper}_BASE_REF={evidence.base_ref}")
        print(f"ASSESSMENT_KIND_{upper}_DIFF_FINGERPRINT={evidence.diff_fingerprint}")
    return config.EXIT_OK


def submit_main(argv: list[str] | None = None) -> int:
    """CLI entry point: fail-closed persistence of one subagent-authored note."""
    parser = argparse.ArgumentParser(prog="cli.py architectural-assessment submit")
    _ = parser.add_argument("--kind", required=True)
    _ = parser.add_argument("--state", required=True)
    _ = parser.add_argument("--note-file", required=True)
    _ = parser.add_argument("--repo-root", default=os.environ.get(config.ENV_REPO, ""))
    _ = parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    if not args.repo_root or not args.implement_tmpdir:
        print("ASSESSMENT_STATUS=usage-error")
        print("ASSESSMENT_DETAIL=repo root and implement tmpdir are required")
        return config.EXIT_USAGE
    implement_tmpdir = Path(args.implement_tmpdir)
    note_path = Path(args.note_file)
    try:
        normalized = normalize_kinds([args.kind])
        note = _read_regular(note_path, root=implement_tmpdir)
    except ValueError as exc:
        print("ASSESSMENT_STATUS=usage-error")
        print(f"ASSESSMENT_DETAIL={_safe_detail(str(exc), implement_tmpdir)}")
        return config.EXIT_USAGE
    try:
        result = submit(
            kind=normalized[0],
            state=args.state,
            note=note,
            repo_root=Path(args.repo_root),
            implement_tmpdir=implement_tmpdir,
        )
    except _HeadDrift as exc:
        print("ASSESSMENT_STATUS=head-drift")
        print(f"ASSESSMENT_DETAIL={_safe_detail(str(exc), implement_tmpdir)}")
        return _EXIT_HEAD_DRIFT
    except (_ReauthorRequired, _DeviationLogPending, OSError, RuntimeError, TypeError, ValueError) as exc:
        status = (
            "invalid-note" if isinstance(exc, _ReauthorRequired)
            else "log-pending" if isinstance(exc, _DeviationLogPending)
            else "failed"
        )
        print(f"ASSESSMENT_STATUS={status}")
        print(f"ASSESSMENT_DETAIL={_safe_detail(str(exc), implement_tmpdir)}")
        return config.EXIT_INTERNAL_ERROR
    print("ASSESSMENT_STATUS=complete")
    print(f"ASSESSMENT_KIND={result.kind}")
    print(f"ASSESSMENT_STATE={result.state}")
    print(f"ASSESSMENT_RESULTS={result.kind}:{result.state}")
    print(f"ASSESSMENT_HEAD_SHA={result.head_sha}")
    print(f"ASSESSMENT_BASE_REF={result.base_ref}")
    print(f"ASSESSMENT_DIFF_FINGERPRINT={result.diff_fingerprint}")
    return config.EXIT_OK


def sanitize_detail_main(argv: list[str] | None = None) -> int:
    """Sanitize stdin for an assessor diagnostic handoff."""
    parser = argparse.ArgumentParser(prog="cli.py architectural-assessment sanitize-detail")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = Path(args.implement_tmpdir)
    if not implement_tmpdir.is_dir() or implement_tmpdir.is_symlink():
        print("architectural-assessment sanitize-detail: invalid implement tmpdir", file=sys.stderr)
        return config.EXIT_USAGE
    stdin_bytes = getattr(sys.stdin, "buffer", sys.stdin)
    diagnostic = stdin_bytes.read(_MAX_SANITIZE_DETAIL_BYTES)
    if isinstance(diagnostic, bytes):
        diagnostic = diagnostic.decode("utf-8", errors="replace")
    print(sanitize_detail(diagnostic, implement_tmpdir=implement_tmpdir))
    return config.EXIT_OK
