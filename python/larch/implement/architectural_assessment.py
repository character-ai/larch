"""Coordinate read-only Step 8 architectural assessments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, Protocol, cast

from larch import io as larch_io
from larch.core import architectural_guidelines, config, external_defaults, logging_util, redact
from larch.implement import ship_guidelines

_AGENT_PROMPT: Final = Path(__file__).parents[3] / "skills/implement/references/architectural-assessment-agent.md"
_PY_CLI: Final = Path(__file__).parents[2] / "cli.py"
_MAX_SANITIZE_DETAIL_BYTES: Final = 8 * 1024
_MAX_ASSESSMENT_CHARS: Final = 12000
_UNAVAILABLE_RECEIPT: Final = "architectural-assessment-unavailable-{kind}.json"
_KIND_ORDER: Final = (config.ASSESSMENT_KIND_INVARIANTS, config.ASSESSMENT_KIND_GUIDELINES)
_DIFF_HEADER_RE: Final = re.compile(r"^diff --git a/(\S+) b/(\S+)$")
_IDENTIFIER_RE: Final = re.compile(r"^#{1,6}\s+((?:I|G)-[A-Za-z0-9-]+-\d+):", re.MULTILINE)
_COMMIT_RE: Final = re.compile(r"^[0-9a-f]{40}$")
_BASE_REF_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_FENCE_OPEN_RE: Final = re.compile(r"^`{3,}[A-Za-z0-9]*$")
_FENCE_CLOSE_RE: Final = re.compile(r"^`{3,}$")
_REAUTHOR_REASONS: Final[frozenset[str]] = frozenset({
    config.ASSESSMENT_REAUTHOR_REASON_INVALID_OUTCOME,
    config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH,
    config.ASSESSMENT_REAUTHOR_REASON_MISSING_METADATA,
})
# A clean-outcome prose mismatch is a formatting defect, not an architectural
# verdict: the lane confirmed `clean` but cited a G-*/I-* identifier in the
# supporting prose. Re-author once with this constraint appended so the retry
# keeps the clean verdict while dropping the identifier reference. See issue #7113.
_CLEAN_PROSE_CONSTRAINT: Final = (
    "\n\nADDITIONAL CONSTRAINT FOR THIS RETRY: A previous attempt marked a result "
    "`clean` while its assessment text cited a `G-*` or `I-*` identifier, which the "
    "coordinator treats as a deviation/violation signal. For every `clean` result, "
    "write the assessment in plain prose that mentions NO `G-*` or `I-*` identifier "
    "anywhere; affirm the clean verdict in one plain sentence and cite `G-*`/`I-*` "
    "identifiers only inside `deviation` or `violation` results."
)


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
class AssessmentLane:
    """One canonical architectural-assessment waterfall lane."""

    tool: str
    model: str


_LANES: Final[dict[str, AssessmentLane]] = {
    "cursor": AssessmentLane("cursor", config.ARCHITECTURAL_ASSESSMENT_CURSOR_MODEL),
    "codex": AssessmentLane("codex", config.ARCHITECTURAL_ASSESSMENT_CODEX_MODEL),
    "claude": AssessmentLane("claude", config.ARCHITECTURAL_ASSESSMENT_CLAUDE_MODEL),
}


@dataclass(frozen=True)
class LaunchRequest:
    """Read-only assessment lane request."""

    lane: AssessmentLane
    repo_root: Path
    prompt: str
    evidence_dir: Path
    output_path: Path


@dataclass(frozen=True)
class LaunchResult:
    """Captured external launcher result."""

    returncode: int
    stdout: str
    stderr: str
    dirty_tree_path: Path | None = None


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


class Launcher(Protocol):
    """Injectable assessment launcher."""

    def launch(self, request: LaunchRequest) -> LaunchResult:
        """Run the assessment process and return captured output."""
        raise NotImplementedError


class DirectClaudeLauncher:
    """Production direct read-only Claude assessment launcher."""

    def launch(self, request: LaunchRequest) -> LaunchResult:
        argv: tuple[str, ...] = (
            "claude",
            "--print",
            "--model",
            request.lane.model,
            "--add-dir",
            str(request.evidence_dir),
            "--allowedTools",
            "Read",
            "--permission-mode",
            "plan",
        )
        try:
            completed = subprocess.run(  # lint-subprocess-via-runner: ok dedicated typed external-agent boundary
                list(argv),
                cwd=request.evidence_dir,
                input=request.prompt,
                text=True,
                capture_output=True,
                check=False,
                timeout=config.ARCHITECTURAL_ASSESSMENT_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired as exc:
            return LaunchResult(config.EXIT_TIMEOUT, str(exc.stdout or ""), str(exc.stderr or "assessment timed out"))
        except OSError as exc:
            return LaunchResult(config.EXIT_INTERNAL_ERROR, "", str(exc))
        return LaunchResult(completed.returncode, completed.stdout, completed.stderr)


class SharedReviewLauncher:
    """Assessment adapter over the shared Codex/Cursor read-only launcher."""

    def launch(self, request: LaunchRequest) -> LaunchResult:
        prompt_path = request.output_path.with_suffix(request.output_path.suffix + ".prompt-input")
        _write_text_atomic(prompt_path, request.prompt)
        argv: list[str] = [
            sys.executable,
            str(_PY_CLI),
            "agent",
            "launch-review",
            "--tool",
            request.lane.tool,
            "--output",
            str(request.output_path),
            "--timeout",
            str(config.ARCHITECTURAL_ASSESSMENT_TIMEOUT_SEC),
            "--prompt-file",
            str(prompt_path),
            "--assessment-contract",
            "--assessment-evidence-dir",
            str(request.evidence_dir),
            "--assessment-repo-root",
            str(request.repo_root),
            "--single-attempt",
            "--site",
            "implement Step 8 architectural assessment",
            "--timing-task-kind",
            f"{request.lane.tool}-architectural-assessment",
        ]
        if request.lane.tool == "cursor":
            argv.extend(("--cursor-model", request.lane.model))
        else:
            argv.extend(("--model-role", "fix", "--default-model", request.lane.model))
        try:
            completed = subprocess.run(  # lint-subprocess-via-runner: ok typed shared-launcher adapter
                argv,
                cwd=request.repo_root,
                text=True,
                capture_output=True,
                check=False,
                timeout=config.ARCHITECTURAL_ASSESSMENT_TIMEOUT_SEC + 60,
            )
        except subprocess.TimeoutExpired as exc:
            return LaunchResult(config.EXIT_TIMEOUT, "", str(exc.stderr or "shared assessment launcher timed out"))
        except OSError as exc:
            return LaunchResult(config.EXIT_INTERNAL_ERROR, "", str(exc))
        launcher_exit = _parse_launcher_exit(completed.stdout, expected_output=request.output_path)
        if launcher_exit is None:
            return LaunchResult(config.EXIT_INTERNAL_ERROR, "", completed.stderr or "malformed shared launcher metadata")
        artifact_error = _shared_launcher_artifact_error(
            output=request.output_path,
            tool=request.lane.tool,
            launcher_exit=launcher_exit,
        )
        if artifact_error:
            return LaunchResult(config.EXIT_INTERNAL_ERROR, "", artifact_error)
        raw_output = ""
        if _regular_file(request.output_path):
            raw_output = request.output_path.read_text(encoding="utf-8", errors="replace")
        diagnostics: list[str] = [completed.stderr] if completed.stderr else []
        for suffix in (".diag", ".sidecar"):
            path = request.output_path.with_suffix(request.output_path.suffix + suffix)
            if _regular_file(path):
                text = path.read_text(encoding="utf-8", errors="replace")
                if text and text not in diagnostics:
                    diagnostics.append(text)
        dirty_tree_path = request.output_path.with_suffix(request.output_path.suffix + ".dirty-tree")
        return LaunchResult(
            launcher_exit,
            raw_output,
            "\n".join(diagnostics),
            dirty_tree_path if request.lane.tool == "cursor" else None,
        )


def _parse_launcher_exit(text: str, *, expected_output: Path) -> int | None:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key not in {"LAUNCHER_EXIT", "OUTPUT"}:
            continue
        if key in values:
            return None
        values[key] = value
    if values.get("OUTPUT") != str(expected_output):
        return None
    try:
        return int(values["LAUNCHER_EXIT"])
    except (KeyError, ValueError):
        return None


def _shared_launcher_artifact_error(*, output: Path, tool: str, launcher_exit: int) -> str:
    done = output.with_suffix(output.suffix + ".done")
    meta = output.with_suffix(output.suffix + ".meta")
    sidecar = output.with_suffix(output.suffix + ".sidecar")
    if not all(_regular_file(path) for path in (done, meta, sidecar)):
        return "shared launcher omitted a required result sidecar"
    try:
        done_exit = int(done.read_text(encoding="utf-8", errors="replace").strip())
        metadata = _read_env_strict(meta, root=output.parent)
    except (OSError, UnicodeDecodeError, ValueError):
        return "shared launcher result sidecar is malformed"
    if done_exit != launcher_exit:
        return "shared launcher exit metadata is inconsistent"
    if metadata.get("TOOL") != tool or metadata.get("OUTPUT_FILE") != str(output):
        return "shared launcher result metadata is inconsistent"
    return ""


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
        # coverage; a re-run must re-author it rather than reuse the stale receipt
        # (_discard_unavailable_coverage clears it before re-materialization).
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


def _discard_unavailable_coverage(kind: str, *, implement_tmpdir: Path) -> None:
    """Invalidate a prior `unavailable` note so a re-run re-authors instead of reusing it."""
    metadata = (
        architectural_guidelines.invariant_durable_note_metadata(implement_tmpdir)
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.durable_note_metadata(implement_tmpdir)
    )
    if metadata.get("NOTE_STATE") != config.NOTE_STATE_UNAVAILABLE:
        return
    invalidator = (
        architectural_guidelines.invalidate_invariant_implement_note
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.invalidate_implement_note
    )
    invalidator(implement_tmpdir)


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


def _copy_evidence(evidences: Sequence[MaterializedEvidence], *, implement_tmpdir: Path) -> tuple[Path, dict[str, tuple[Path, Path]]]:
    evidence_dir = Path(tempfile.mkdtemp(prefix="architectural-assessment-evidence-", dir=implement_tmpdir))
    evidence_dir.chmod(0o700)
    prompt_target = evidence_dir / "agent-contract.md"
    _ = shutil.copyfile(_AGENT_PROMPT, prompt_target)
    copied: dict[str, tuple[Path, Path]] = {}
    for evidence in evidences:
        diff_target = evidence_dir / f"{evidence.kind}-diff.txt"
        knowledge_target = evidence_dir / f"{evidence.kind}-knowledge.md"
        _ = diff_target.write_text(evidence.diff_text, encoding="utf-8")
        _ = shutil.copyfile(evidence.knowledge_path, knowledge_target)
        if _sha256(knowledge_target.read_text(encoding="utf-8")) != evidence.knowledge_sha256:
            raise OSError("knowledge evidence copy verification failed")
        copied[evidence.kind] = (diff_target, knowledge_target)
    return evidence_dir, copied


def _validate_launch_evidence(*, evidence_dir: Path, copied: dict[str, tuple[Path, Path]]) -> None:
    if not evidence_dir.is_dir() or evidence_dir.is_symlink() or not _under(evidence_dir, evidence_dir.parent):
        raise OSError("unsafe evidence directory")
    for diff_path, knowledge_path in copied.values():
        for path in (diff_path, knowledge_path):
            if not _under(path, evidence_dir) or not _regular_file(path):
                raise OSError("unsafe launch evidence artifact")
    contract = evidence_dir / "agent-contract.md"
    if not _under(contract, evidence_dir) or not _regular_file(contract):
        raise OSError("unsafe launch agent contract")


def _launch_prompt(
    evidences: Sequence[MaterializedEvidence],
    copied: dict[str, tuple[Path, Path]],
    *,
    clean_prose_constraint: bool = False,
) -> str:
    requests: list[dict[str, str]] = []
    for evidence in evidences:
        diff_path, knowledge_path = copied[evidence.kind]
        requests.append(
            {
                "kind": evidence.kind,
                "head_sha": evidence.head_sha,
                "base_ref": evidence.base_ref,
                "diff_fingerprint": evidence.diff_fingerprint,
                "knowledge_sha256": evidence.knowledge_sha256,
                "diff_path": str(diff_path),
                "knowledge_path": str(knowledge_path),
            }
        )
    prompt = _AGENT_PROMPT.read_text(encoding="utf-8")
    if clean_prose_constraint:
        # Keep REQUESTS_JSON last: _validate_prompt_evidence_paths parses the
        # suffix after the final REQUESTS_JSON marker, so the constraint precedes it.
        prompt += _CLEAN_PROSE_CONSTRAINT
    return prompt + "\n\nREQUESTS_JSON=" + json.dumps(requests, separators=(",", ":"))


def _validate_prompt_evidence_paths(prompt: str, *, evidence_dir: Path) -> None:
    marker = "\n\nREQUESTS_JSON="
    _prefix, separator, raw = prompt.rpartition(marker)
    if not separator:
        raise ValueError("assessment prompt is missing REQUESTS_JSON")
    try:
        requests: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("assessment prompt REQUESTS_JSON is malformed") from exc
    if not isinstance(requests, list) or not requests:
        raise ValueError("assessment prompt has no requests")
    for raw_item in cast("list[object]", requests):
        if not isinstance(raw_item, dict):
            raise TypeError("assessment prompt request is malformed")
        item = cast("dict[str, object]", raw_item)
        for key in ("diff_path", "knowledge_path"):
            raw_path = item.get(key)
            if not isinstance(raw_path, str) or not _under(Path(raw_path), evidence_dir):
                raise ValueError(f"assessment prompt {key} is outside the evidence directory")


def _parse_result_row(  # noqa: C901 - strict schema validation checks each independent boundary
    item: object, by_kind: dict[str, MaterializedEvidence], seen: set[str]
) -> AssessmentResult:
    if not isinstance(item, dict):
        raise TypeError("assessment result must be an object")
    row: dict[str, object] = cast("dict[str, object]", item)
    allowed_fields: set[str] = {"kind", "state", "assessment", "identifiers", "head_sha", "base_ref", "diff_fingerprint", "knowledge_sha256"}
    if set(row) != allowed_fields:
        raise ValueError("assessment result fields are invalid")
    kind: str = str(row["kind"])
    if kind in seen or kind not in by_kind:
        raise ValueError("assessment result kind is duplicate or unexpected")
    evidence = by_kind[kind]
    state: str = str(row["state"])
    allowed_states = {"clean", "violation"} if kind == config.ASSESSMENT_KIND_INVARIANTS else {"clean", "deviation"}
    if state not in allowed_states:
        raise ValueError("assessment result state is invalid")
    assessment: str = str(row["assessment"])
    if not assessment.strip() or len(assessment) > _MAX_ASSESSMENT_CHARS:
        raise ValueError("assessment text is empty or oversized")
    raw_identifiers: object = row["identifiers"]
    if not isinstance(raw_identifiers, list):
        raise TypeError("assessment identifiers must be an array")
    identifier_items: list[object] = cast("list[object]", raw_identifiers)
    if any(not isinstance(identifier, str) for identifier in identifier_items):
        raise ValueError("assessment identifiers are invalid")
    identifiers: tuple[str, ...] = tuple(cast("list[str]", identifier_items))
    if not set(identifiers).issubset(evidence.identifiers):
        raise ValueError("assessment cites an unknown architectural identifier")
    for key, expected in (("head_sha", evidence.head_sha), ("base_ref", evidence.base_ref), ("diff_fingerprint", evidence.diff_fingerprint), ("knowledge_sha256", evidence.knowledge_sha256)):
        if str(row[key]) != expected:
            raise ValueError(f"assessment identity mismatch: {key}")
    seen.add(kind)
    return AssessmentResult(kind, state, assessment, identifiers, evidence.head_sha, evidence.base_ref, evidence.diff_fingerprint, evidence.knowledge_sha256)


def _strip_json_fence(raw: str) -> str:
    """Strip one optional Markdown code fence wrapping a JSON payload.

    A launcher may enclose its JSON envelope in a Markdown code fence: an
    opening triple-backtick line (optionally tagged json) and a closing
    triple-backtick line. Drop the leading fence line and the matching closing
    fence line, plus any trailing prose after it, so json.loads sees the
    enclosed payload. Input without a leading fence line is returned unchanged,
    so non-fenced prose and truncated objects still fail closed in the caller.
    """
    lines = raw.strip().splitlines()
    if not lines or _FENCE_OPEN_RE.fullmatch(lines[0].strip()) is None:
        return raw
    for index, line in enumerate(lines[1:], start=1):
        if _FENCE_CLOSE_RE.fullmatch(line.strip()) is not None:
            return "\n".join(lines[1:index]).strip()
    return raw


def _parse_results(  # type: ignore[reportUnusedFunction]  # reason: internal helper
    raw: str, evidences: Sequence[MaterializedEvidence]
) -> tuple[AssessmentResult, ...]:
    try:
        decoded: object = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("assessment output is not exactly one JSON object") from exc
    if not isinstance(decoded, dict):
        raise TypeError("assessment output envelope must be an object")
    envelope: dict[str, object] = cast("dict[str, object]", decoded)
    if set(envelope) != {"schema_version", "results"} or str(envelope.get("schema_version")) != "1":
        raise ValueError("assessment output envelope is invalid")
    rows: object = envelope.get("results")
    if not isinstance(rows, list):
        raise TypeError("assessment results must be an array")
    row_items: list[object] = cast("list[object]", rows)
    by_kind: dict[str, MaterializedEvidence] = {evidence.kind: evidence for evidence in evidences}
    seen: set[str] = set()
    parsed: list[AssessmentResult] = [_parse_result_row(item, by_kind, seen) for item in row_items]
    if seen != set(by_kind):
        raise ValueError("assessment result omitted a requested kind")
    return tuple(sorted(parsed, key=lambda result: _KIND_ORDER.index(result.kind)))


def _record_invalid_result_row(
    *,
    kind: str,
    by_kind: Mapping[str, MaterializedEvidence],
    parsed: dict[str, AssessmentResult],
    invalid: dict[str, str],
    detail: str,
) -> None:
    """Keep malformed rows unresolved, including valid rows they invalidate."""
    if kind in by_kind:
        invalid[kind] = detail
        _ = parsed.pop(kind, None)
        return
    parsed.clear()
    for expected_kind in by_kind:
        _ = invalid.setdefault(expected_kind, detail)


def _parse_results_independently(
    raw: str,
    evidences: Sequence[MaterializedEvidence],
) -> tuple[tuple[AssessmentResult, ...], dict[str, str]]:
    """Return valid result rows while isolating malformed or omitted kinds."""
    try:
        decoded: object = json.loads(_strip_json_fence(raw))
        if not isinstance(decoded, dict) or set(cast("dict[str, object]", decoded).keys()) != {"schema_version", "results"} or str(decoded.get("schema_version")) != "1":  # type: ignore[reportUnknownArgumentType, reportUnknownMemberType]  # reason: decoded is object from json.loads
            raise ValueError("assessment output envelope is invalid")
        rows = decoded.get("results")  # type: ignore[reportUnknownMemberType]  # reason: decoded is object from json.loads
        if not isinstance(rows, list):
            raise TypeError("assessment results must be an array")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return (), {evidence.kind: str(exc) for evidence in evidences}
    by_kind = {evidence.kind: evidence for evidence in evidences}
    seen: set[str] = set()
    parsed: dict[str, AssessmentResult] = {}
    invalid: dict[str, str] = {}
    for item in rows:  # type: ignore[reportUnknownVariableType]  # reason: item is object from json.loads
        kind = str(item.get("kind") or "") if isinstance(item, dict) else ""  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]  # reason: item is object from json.loads
        try:
            result = _parse_result_row(item, by_kind, seen)  # type: ignore[reportUnknownArgumentType]  # reason: item is object from json.loads
        except (TypeError, ValueError) as exc:
            _record_invalid_result_row(
                kind=kind,
                by_kind=by_kind,
                parsed=parsed,
                invalid=invalid,
                detail=str(exc),
            )
        else:
            if result.kind not in invalid:
                parsed[result.kind] = result
    for missing_kind in set(by_kind) - set(parsed):
        _ = invalid.setdefault(missing_kind, "assessment result omitted a requested kind")
    return tuple(sorted(parsed.values(), key=lambda result: _KIND_ORDER.index(result.kind))), invalid


def _write_text_atomic(path: Path, text: str) -> None:
    larch_io.trusted_atomic_write(path, text, root=path.parent, mode=0o600)


def _write_json_atomic(path: Path, data: dict[str, object]) -> None:
    _write_text_atomic(path, json.dumps(data, sort_keys=True) + "\n")


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
            note=result.assessment, detail=detail, invariants_status="present", assessment_kind=result.state, note_state=note_state
        )
        _ = ship_guidelines.write_invariant_ship_outcome(
            implement_tmpdir=str(implement_tmpdir), result=gate, head_sha=result.head_sha, base_ref=result.base_ref
        )
    else:
        gate = ship_guidelines.GuidelinesGateResult(
            note=result.assessment, detail=detail, guidelines_status="present", assessment_kind=result.state, note_state=note_state
        )
        _ = ship_guidelines.write_guideline_ship_outcome(
            implement_tmpdir=str(implement_tmpdir), result=gate, head_sha=result.head_sha, base_ref=result.base_ref
        )


def _persist_result(result: AssessmentResult, *, repo_root: Path, implement_tmpdir: Path) -> None:
    current_head: str = _git_read(repo_root, ["rev-parse", "HEAD"])
    if current_head != result.head_sha:
        raise _HeadDrift("HEAD changed after architectural assessment launch")
    if result.kind == config.ASSESSMENT_KIND_INVARIANTS:
        try:
            architectural_guidelines.write_invariant_compose_assessment(
                implement_tmpdir=implement_tmpdir, assessment_text=result.assessment, outcome=result.state, repo_root=repo_root
            )
        except architectural_guidelines.AssessmentReauthorRequired as exc:
            raise _ReauthorRequired(str(exc)) from exc
    else:
        try:
            architectural_guidelines.write_compose_assessment(
                implement_tmpdir=implement_tmpdir, assessment_text=result.assessment, outcome=result.state, repo_root=repo_root
            )
        except architectural_guidelines.AssessmentReauthorRequired as exc:
            raise _ReauthorRequired(str(exc)) from exc
    _write_outcome(result.kind, implement_tmpdir=implement_tmpdir, result=result)
    metadata = (
        architectural_guidelines.invariant_durable_note_metadata(implement_tmpdir)
        if result.kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.durable_note_metadata(implement_tmpdir)
    )
    if not _outcome_valid(result.kind, implement_tmpdir, metadata):
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
    invariant: bool = evidence.kind == config.ASSESSMENT_KIND_INVARIANTS
    architectural_guidelines.write_deterministic_clean_note(
        implement_tmpdir=implement_tmpdir,
        head_sha=evidence.head_sha,
        base_ref=evidence.base_ref,
        diff_text=evidence.diff_text,
        invariant=invariant,
    )
    clean_text: str = architectural_guidelines.CLEAN_INVARIANT_PRESENTATION_NOTE if invariant else architectural_guidelines.CLEAN_PRESENTATION_NOTE
    result = AssessmentResult(evidence.kind, "clean", clean_text, (), evidence.head_sha, evidence.base_ref, evidence.diff_fingerprint, evidence.knowledge_sha256)
    _write_outcome(evidence.kind, implement_tmpdir=implement_tmpdir, result=result, note_state=config.NOTE_STATE_DETERMINISTIC_CLEAN)


def _repair_current_outcome(kind: str, *, repo_root: Path, implement_tmpdir: Path, head_sha: str) -> str:
    """Repair a missing outcome sidecar without replacing a current durable note."""
    if _git_read(repo_root, ["rev-parse", "HEAD"]) != head_sha:
        raise _HeadDrift("HEAD changed before current-outcome repair")
    # A note the repair path cannot certify is stale: invalidate it so the next pass
    # re-materializes and re-authors (mirroring _persist_authored_results), and return
    # a bounded re-author reason the Step 8 adapter grammar accepts, not a bare token
    # that the grammar rejects and hard-stops the run as fail-closed. See #7144.
    invalidator = (
        architectural_guidelines.invalidate_invariant_implement_note
        if kind == config.ASSESSMENT_KIND_INVARIANTS
        else architectural_guidelines.invalidate_implement_note
    )
    metadata = architectural_guidelines.invariant_durable_note_metadata(implement_tmpdir) if kind == config.ASSESSMENT_KIND_INVARIANTS else architectural_guidelines.durable_note_metadata(implement_tmpdir)
    note_path = architectural_guidelines.invariant_durable_note_path(implement_tmpdir) if kind == config.ASSESSMENT_KIND_INVARIANTS else architectural_guidelines.durable_note_path(implement_tmpdir)
    state = metadata.get("ASSESSMENT_KIND", "")
    allowed = {"clean", "violation"} if kind == config.ASSESSMENT_KIND_INVARIANTS else {"clean", "deviation"}
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
        invariant=kind == config.ASSESSMENT_KIND_INVARIANTS,
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


def _persist_unavailable(evidence: MaterializedEvidence, *, repo_root: Path, implement_tmpdir: Path, detail: str) -> None:
    invariant: bool = evidence.kind == config.ASSESSMENT_KIND_INVARIANTS
    if invariant and _preserved_invariant_violation(evidence, repo_root=repo_root, implement_tmpdir=implement_tmpdir):
        return
    architectural_guidelines.write_unavailable_note(
        implement_tmpdir=implement_tmpdir, head_sha=evidence.head_sha, base_ref=evidence.base_ref, invariant=invariant
    )
    safe_detail: str = sanitize_detail(detail, implement_tmpdir=implement_tmpdir)
    result = AssessmentResult(evidence.kind, "clean", "Architectural assessment unavailable.", (), evidence.head_sha, evidence.base_ref, evidence.diff_fingerprint, evidence.knowledge_sha256)
    _write_outcome(
        evidence.kind, implement_tmpdir=implement_tmpdir, result=result, note_state=config.NOTE_STATE_UNAVAILABLE, detail=safe_detail
    )
    note_path = architectural_guidelines.invariant_durable_note_path(implement_tmpdir) if invariant else architectural_guidelines.durable_note_path(implement_tmpdir)
    outcome_path = architectural_guidelines.invariant_ship_outcome_path(implement_tmpdir) if invariant else architectural_guidelines.guideline_ship_outcome_path(implement_tmpdir)
    receipt: dict[str, object] = {
        "schema_version": "1",
        "kind": evidence.kind,
        "head_sha": evidence.head_sha,
        "base_ref": evidence.base_ref,
        "diff_fingerprint": evidence.diff_fingerprint,
        "knowledge_sha256": evidence.knowledge_sha256,
        "note_sha256": _sha256(_read_regular(note_path, root=implement_tmpdir)),
        "outcome_sha256": _sha256(_read_regular(outcome_path, root=implement_tmpdir)),
        "detail": safe_detail,
    }
    _write_json_atomic(implement_tmpdir / _UNAVAILABLE_RECEIPT.format(kind=evidence.kind), receipt)


def _preserved_invariant_violation(evidence: MaterializedEvidence, *, repo_root: Path, implement_tmpdir: Path) -> bool:  # noqa: PLR0911 - preserved-violation gate rejects each non-matching boundary
    if evidence.kind != config.ASSESSMENT_KIND_INVARIANTS:
        return False
    path = architectural_guidelines.invariant_ship_outcome_path(implement_tmpdir)
    try:
        data = _load_json(path, root=implement_tmpdir)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return False
    if architectural_guidelines.validate_invariant_ship_outcome_record(data) is not None or not isinstance(data, dict):
        return False
    metadata = architectural_guidelines.invariant_durable_note_metadata(implement_tmpdir)
    if metadata.get("ASSESSMENT_KIND") != config.ASSESSMENT_OUTCOME_VIOLATION:
        return False
    if not architectural_guidelines.invariant_note_consumable(
        implement_tmpdir=implement_tmpdir,
        head_sha=evidence.head_sha,
        base_ref=evidence.base_ref,
        repo_root=repo_root,
    ) or not _outcome_valid(config.ASSESSMENT_KIND_INVARIANTS, implement_tmpdir, metadata):
        return False
    if not _authored_note_valid(
        config.ASSESSMENT_KIND_INVARIANTS,
        implement_tmpdir=implement_tmpdir,
        outcome=config.ASSESSMENT_OUTCOME_VIOLATION,
    ):
        return False
    return (  # type: ignore[reportUnknownVariableType]  # reason: data is dict from _load_json
        data.get("outcome") == "violation"  # type: ignore[reportUnknownMemberType]  # reason: data is dict from _load_json
        and data.get("assessment_kind") == "violation"  # type: ignore[reportUnknownMemberType]  # reason: data is dict from _load_json
        and data.get("head_sha") == evidence.head_sha  # type: ignore[reportUnknownMemberType]  # reason: data is dict from _load_json
        and data.get("base_ref") == evidence.base_ref  # type: ignore[reportUnknownMemberType]  # reason: data is dict from _load_json
        and _regular_file(architectural_guidelines.invariant_durable_note_path(implement_tmpdir))
    )


def _cursor_dirty_tree_clean(path: Path | None, *, implement_tmpdir: Path) -> tuple[bool, str]:
    if path is None or not _under(path, implement_tmpdir) or not _regular_file(path):
        return False, "Cursor dirty-tree sidecar is missing or unsafe"
    try:
        values = _read_env_strict(path, root=implement_tmpdir)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return False, f"Cursor dirty-tree sidecar is malformed: {exc}"
    status = values.get("STATUS", "")
    if status != "clean":
        return False, f"Cursor dirty-tree status is {status or 'missing'}"
    return True, ""


def _production_launchers() -> dict[str, Launcher]:
    shared = SharedReviewLauncher()
    return {"cursor": shared, "codex": shared, "claude": DirectClaudeLauncher()}


def _lane_availability(implement_tmpdir: Path) -> dict[str, bool]:
    return {
        "cursor": external_defaults.binary_available(name=config.ENV_CURSOR_BINARY_FOUND, implement_tmpdir=implement_tmpdir, binary="cursor"),
        "codex": external_defaults.binary_available(name=config.ENV_CODEX_BINARY_FOUND, implement_tmpdir=implement_tmpdir, binary="codex"),
        "claude": external_defaults.binary_available(name=config.ENV_CLAUDE_BINARY_FOUND, implement_tmpdir=implement_tmpdir, binary="claude"),
    }


def _persist_authored_results(
    results: Sequence[AssessmentResult],
    *,
    evidence_by_kind: Mapping[str, MaterializedEvidence],
    statuses: dict[str, str],
    repo_root: Path,
    implement_tmpdir: Path,
) -> None:
    for result in results:
        try:
            _persist_result(result, repo_root=repo_root, implement_tmpdir=implement_tmpdir)
        except _DeviationLogPending:
            statuses[result.kind] = "log-pending"
        except _ReauthorRequired as exc:
            invalidator = (
                architectural_guidelines.invalidate_invariant_implement_note
                if result.kind == config.ASSESSMENT_KIND_INVARIANTS
                else architectural_guidelines.invalidate_implement_note
            )
            invalidator(implement_tmpdir)
            statuses[result.kind] = _reauthor_status(str(exc))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            _persist_unavailable(
                evidence_by_kind[result.kind],
                repo_root=repo_root,
                implement_tmpdir=implement_tmpdir,
                detail=str(exc),
            )
            statuses[result.kind] = "unavailable"
        else:
            statuses[result.kind] = result.state


@dataclass(frozen=True)
class LaneOutcome:
    """Parsed output from one attempted assessment lane."""

    results: tuple[AssessmentResult, ...] = ()
    invalid_details: tuple[tuple[str, str], ...] = ()
    unavailable_detail: str = ""


@dataclass(frozen=True)
class LaneContext:
    """Stable paths and adapters shared by every lane attempt."""

    copied: dict[str, tuple[Path, Path]]
    evidence_dir: Path
    repo_root: Path
    implement_tmpdir: Path
    launchers: Mapping[str, Launcher]


def _set_latest_detail(
    evidences: Sequence[MaterializedEvidence],
    latest_detail: dict[str, str],
    detail: str,
) -> None:
    for evidence in evidences:
        latest_detail[evidence.kind] = detail


def _lane_output_path(*, tool: str, implement_tmpdir: Path) -> Path:
    output_path = implement_tmpdir / f"architectural-assessment-{tool}-result.json"
    if output_path.is_symlink():
        raise OSError(f"unsafe stale {tool} result artifact")
    if not output_path.exists():
        return output_path
    if not _under(output_path, implement_tmpdir) or not _regular_file(output_path):
        raise OSError(f"unsafe stale {tool} result artifact")
    output_path.unlink()
    return output_path


def _launch_failure_detail(
    tool: str,
    launch_result: LaunchResult,
    *,
    implement_tmpdir: Path,
) -> str:
    if launch_result.returncode != 0:
        return launch_result.stderr or f"{tool} launcher exited {launch_result.returncode}"
    if not launch_result.stdout.strip():
        return launch_result.stderr or f"{tool} assessment launcher returned empty output"
    if tool != "cursor":
        return ""
    clean, detail = _cursor_dirty_tree_clean(
        launch_result.dirty_tree_path,
        implement_tmpdir=implement_tmpdir,
    )
    return "" if clean else detail


def _attempt_lane(
    tool: str,
    unresolved: Sequence[MaterializedEvidence],
    context: LaneContext,
    *,
    clean_prose_constraint: bool = False,
) -> LaneOutcome:
    outcome = LaneOutcome()
    try:
        output_path = _lane_output_path(tool=tool, implement_tmpdir=context.implement_tmpdir)
    except OSError as exc:
        outcome = LaneOutcome(unavailable_detail=str(exc))
    else:
        prompt = _launch_prompt(unresolved, context.copied, clean_prose_constraint=clean_prose_constraint)
        _validate_prompt_evidence_paths(prompt, evidence_dir=context.evidence_dir)
        launcher = context.launchers.get(tool)
        if launcher is None:
            outcome = LaneOutcome(unavailable_detail=f"{tool} assessment adapter is unavailable")
        else:
            launch_result = launcher.launch(
                LaunchRequest(_LANES[tool], context.repo_root, prompt, context.evidence_dir, output_path)
            )
            failure_detail = _launch_failure_detail(
                tool,
                launch_result,
                implement_tmpdir=context.implement_tmpdir,
            )
            if failure_detail:
                outcome = LaneOutcome(unavailable_detail=failure_detail)
            else:
                try:
                    results, invalid_details = _parse_results_independently(
                        launch_result.stdout,
                        unresolved,
                    )
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    outcome = LaneOutcome(unavailable_detail=str(exc))
                else:
                    outcome = LaneOutcome(tuple(results), tuple(sorted(invalid_details.items())))
    return outcome


def _record_unresolved_lane_rows(
    unresolved: Sequence[MaterializedEvidence],
    *,
    outcome: LaneOutcome,
    statuses: dict[str, str],
    latest_detail: dict[str, str],
) -> list[MaterializedEvidence]:
    invalid_details: dict[str, str] = dict(outcome.invalid_details)
    for evidence in unresolved:
        if evidence.kind in statuses:
            continue
        detail = invalid_details.get(
            evidence.kind,
            "assessment result omitted a requested kind",
        )
        latest_detail[evidence.kind] = detail
    return [evidence for evidence in unresolved if evidence.kind not in statuses]


def _clean_mismatch_retry_evidence(
    results: Sequence[AssessmentResult],
    *,
    evidence_by_kind: Mapping[str, MaterializedEvidence],
    statuses: Mapping[str, str],
    retried: set[str],
) -> list[MaterializedEvidence]:
    """Return evidence for clean-outcome-prose-mismatch kinds not yet retried.

    A clean-outcome prose mismatch is a formatting defect (the lane confirmed
    ``clean`` but cited an identifier), so the coordinator re-authors it once with
    the tightened clean-prose prompt instead of terminating the run. Kinds already
    retried are excluded, capping the retry at one per kind. See issue #7113.
    """
    retry: list[MaterializedEvidence] = []
    mismatch_status = _reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH)
    for result in results:
        if result.kind in retried:
            continue
        if statuses.get(result.kind) == mismatch_status:
            retry.append(evidence_by_kind[result.kind])
    return retry


def _run_waterfall(
    pending: Sequence[MaterializedEvidence],
    *,
    repo_root: Path,
    implement_tmpdir: Path,
    launchers: Mapping[str, Launcher],
    availability: Mapping[str, bool],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    evidence_by_kind: dict[str, MaterializedEvidence] = {evidence.kind: evidence for evidence in pending}
    evidence_dir, copied = _copy_evidence(pending, implement_tmpdir=implement_tmpdir)
    _validate_launch_evidence(evidence_dir=evidence_dir, copied=copied)
    context = LaneContext(copied, evidence_dir, repo_root, implement_tmpdir, launchers)
    unresolved: list[MaterializedEvidence] = list(pending)
    attempted: list[str] = []
    clean_retried: set[str] = set()
    latest_detail: dict[str, str] = {evidence.kind: "no assessment lane was available" for evidence in pending}
    while unresolved:
        selection = external_defaults.next_untried_tier(
            config.ARCHITECTURAL_ASSESSMENT_ROLE,
            attempted,
            codex_present=availability.get("codex", False),
            cursor_present=availability.get("cursor", False),
            claude_present=availability.get("claude", False),
        )
        if selection.action != config.FIXER_TIER_ACTION_SELECTED:
            break
        tool = selection.selected_tier
        attempted.append(tool)
        outcome = _attempt_lane(
            tool,
            unresolved,
            context,
        )
        if outcome.unavailable_detail:
            _set_latest_detail(unresolved, latest_detail, outcome.unavailable_detail)
            continue
        _persist_authored_results(
            outcome.results,
            evidence_by_kind=evidence_by_kind,
            statuses=statuses,
            repo_root=repo_root,
            implement_tmpdir=implement_tmpdir,
        )
        retry_evidence = _clean_mismatch_retry_evidence(
            outcome.results,
            evidence_by_kind=evidence_by_kind,
            statuses=statuses,
            retried=clean_retried,
        )
        if retry_evidence:
            # Clean-outcome prose mismatch is a formatting defect; re-author once
            # in-lane with the tightened clean-prose prompt before giving up. See #7113.
            clean_retried.update(evidence.kind for evidence in retry_evidence)
            retry_outcome = _attempt_lane(
                tool,
                retry_evidence,
                context,
                clean_prose_constraint=True,
            )
            if not retry_outcome.unavailable_detail:
                _persist_authored_results(
                    retry_outcome.results,
                    evidence_by_kind=evidence_by_kind,
                    statuses=statuses,
                    repo_root=repo_root,
                    implement_tmpdir=implement_tmpdir,
                )
            # A clean-prose retry that did not resolve the mismatch (launch
            # failure, invalid rows, or another mismatch) must not strand the
            # kind on the re-author-required terminal: drop the stale mismatch
            # status so the kind returns to the waterfall and the remaining
            # lanes each get one attempt. See issue #7143.
            mismatch_status = _reauthor_status(config.ASSESSMENT_REAUTHOR_REASON_CLEAN_MISMATCH)
            for retried in retry_evidence:
                if statuses.get(retried.kind) == mismatch_status:
                    _ = statuses.pop(retried.kind, None)
        unresolved = _record_unresolved_lane_rows(
            unresolved,
            outcome=outcome,
            statuses=statuses,
            latest_detail=latest_detail,
        )
        if statuses.get(config.ASSESSMENT_KIND_INVARIANTS) == config.ASSESSMENT_OUTCOME_VIOLATION:
            break
    for evidence in unresolved:
        _persist_unavailable(
            evidence,
            repo_root=repo_root,
            implement_tmpdir=implement_tmpdir,
            detail=latest_detail[evidence.kind],
        )
        statuses[evidence.kind] = "unavailable"
    return statuses


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
    _discard_unavailable_coverage(kind, implement_tmpdir=implement_tmpdir)
    evidence = _materialize_current(
        kind,
        repo_root=repo_root,
        implement_tmpdir=implement_tmpdir,
        head_sha=head_sha,
    )
    if evidence is None:
        return _repair_current_outcome(
            kind,
            repo_root=repo_root,
            implement_tmpdir=implement_tmpdir,
            head_sha=head_sha,
        ), None
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


def run(
    *,
    kinds: Sequence[str],
    repo_root: Path,
    implement_tmpdir: Path,
    launchers: Mapping[str, Launcher] | None = None,
    availability: Mapping[str, bool] | None = None,
) -> tuple[str, ...]:
    """Run requested assessments and return ordered per-kind statuses."""
    normalized: tuple[str, ...] = normalize_kinds(kinds)
    root: Path = repo_root.resolve(strict=True)
    tmpdir: Path = implement_tmpdir.resolve(strict=True)
    if root.is_symlink() or tmpdir.is_symlink() or not root.is_dir() or not tmpdir.is_dir():
        raise ValueError("repo root and implement tmpdir must be non-symlink directories")
    statuses, pending = _prepare_pending(normalized, repo_root=root, implement_tmpdir=tmpdir)
    if pending:
        try:
            statuses.update(
                _run_waterfall(
                    pending,
                    repo_root=root,
                    implement_tmpdir=tmpdir,
                    launchers=launchers if launchers is not None else _production_launchers(),
                    availability=availability if availability is not None else _lane_availability(tmpdir),
                )
            )
        except _HeadDrift:
            return run(
                kinds=normalized,
                repo_root=root,
                implement_tmpdir=tmpdir,
                launchers=launchers,
                availability=availability,
            )
    return tuple(f"{kind}:{statuses[kind]}" for kind in normalized)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the architectural assessment coordinator."""
    parser = argparse.ArgumentParser(prog="cli.py architectural-assessment run")
    _ = parser.add_argument("--kind", action="append", default=[])
    _ = parser.add_argument("--repo-root", default=os.environ.get(config.ENV_REPO, ""))
    _ = parser.add_argument("--implement-tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    args = parser.parse_args(argv)
    try:
        _ = normalize_kinds(args.kind)
    except ValueError as exc:
        print("ARCHITECTURAL_ASSESSMENT_STATUS=usage-error")
        print(f"ARCHITECTURAL_ASSESSMENT_DETAIL={logging_util.sanitize_diagnostic_line(str(exc))}")
        return config.EXIT_USAGE
    if not args.repo_root or not args.implement_tmpdir:
        print("ARCHITECTURAL_ASSESSMENT_STATUS=usage-error")
        print("ARCHITECTURAL_ASSESSMENT_DETAIL=repo root and implement tmpdir are required")
        return config.EXIT_USAGE
    try:
        statuses = run(kinds=args.kind, repo_root=Path(args.repo_root), implement_tmpdir=Path(args.implement_tmpdir))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print("ARCHITECTURAL_ASSESSMENT_STATUS=failed")
        print(f"ARCHITECTURAL_ASSESSMENT_DETAIL={_safe_detail(str(exc), Path(args.implement_tmpdir))}")
        return config.EXIT_INTERNAL_ERROR
    reauthor_required: bool = any(
        item.split(":", 2)[1] == config.ASSESSMENT_RESULT_REAUTHOR_REQUIRED for item in statuses
    )
    print(
        f"ARCHITECTURAL_ASSESSMENT_STATUS="
        f"{config.ASSESSMENT_STATUS_REAUTHOR_REQUIRED if reauthor_required else 'ok'}"
    )
    print(f"ARCHITECTURAL_ASSESSMENT_RESULTS={','.join(statuses)}")
    return config.EXIT_OK


def sanitize_detail_main(argv: list[str] | None = None) -> int:
    """Sanitize stdin for the Step 8 adapter's diagnostic handoff."""
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
