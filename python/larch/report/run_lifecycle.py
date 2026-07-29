"""Universal per-skill run lifecycle and terminal archive publication."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tarfile
import uuid
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

from larch import io as larch_io
from larch.core import config, repo_roots
from larch.errors import ShipError
from larch.report import (
    object_store,
    run_log_batch,
    run_log_manifest,
    run_log_publish,
    run_logs,
    storage_config,
)
from larch.report.run_log_publish import (
    ObjectStore,
    PublicationRequest,
    PublicationResult,
)
from larch.report.storage_config import RunLogStorageResolution, ToolRepositoryStorage

LIFECYCLE_SCHEMA_VERSION: Final = 3
LIFECYCLE_CONTEXT_SCHEMA_VERSION: Final = 3
LIFECYCLE_CONTEXT_BASENAME: Final = "context.json"
UNIVERSAL_FINAL_REPORT: Final = "final-report.md"
UNIVERSAL_EXECUTION_ISSUES: Final = "execution-issues.ndjson"
UNIVERSAL_SESSION_TRANSCRIPT: Final = "session-transcript.jsonl"

_ENV_XDG_STATE_HOME: Final = "XDG_STATE_HOME"
_OUTCOME_BY_ACTION: Final = {
    "finalize": "success",
    "failure": "failure",
    "cancel": "cancelled",
    "early-return": "early-return",
}


class RunLifecycleError(RuntimeError):
    """A universal lifecycle state or transition is invalid."""


def _require_lifecycle(condition: bool, message: str) -> None:  # noqa: FBT001 - internal validation pairs predicates with diagnostics
    if not condition:
        raise RunLifecycleError(message)


TERMINAL_EXCEPTIONS: Final = (
    EOFError,
    object_store.ObjectStoreError,
    OSError,
    run_log_publish.PublicationError,
    RunLifecycleError,
    ShipError,
    storage_config.StorageConfigurationError,
    tarfile.TarError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True, init=False)
class LifecycleStart:
    """Validated state created for one skill invocation."""

    repo_root: Path
    storage_resolution: RunLogStorageResolution
    skill: str
    run_id: str
    log_root: Path
    run_dir: Path
    context_file: Path

    def __init__(  # noqa: PLR0913 - compatibility initializer retains the prior enabled-storage seam.
        self,
        repo_root: Path,
        storage_resolution: RunLogStorageResolution | None = None,
        skill: str = "",
        run_id: str = "",
        log_root: Path | None = None,
        run_dir: Path | None = None,
        context_file: Path | None = None,
        *,
        storage_root: ToolRepositoryStorage | None = None,
    ) -> None:
        """Build pinned state while accepting the prior enabled-only test seam."""
        if storage_resolution is not None and storage_root is not None:
            raise ValueError(
                "provide storage_resolution or storage_root, not both"
            )
        resolution: RunLogStorageResolution
        if storage_resolution is not None:
            resolution = storage_resolution
        elif storage_root is not None:
            resolution = storage_config.injected_storage_resolution(storage_root)
        else:
            raise ValueError("lifecycle start requires a storage resolution")
        if log_root is None or run_dir is None or context_file is None:
            raise ValueError("lifecycle start requires staging and context paths")
        object.__setattr__(self, "repo_root", repo_root)
        object.__setattr__(self, "storage_resolution", resolution)
        object.__setattr__(self, "skill", skill)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "log_root", log_root)
        object.__setattr__(self, "run_dir", run_dir)
        object.__setattr__(self, "context_file", context_file)

    @property
    def storage_root(self) -> ToolRepositoryStorage:
        """Return enabled provider storage for storage-dependent consumers."""
        return storage_config.require_enabled_storage(self.storage_resolution)


@dataclass(frozen=True)
class LifecycleTerminal:
    """Verified terminalization result for one skill invocation."""

    outcome: str
    publication: PublicationResult | None
    secret_scrub_violations: int
    storage_mode: storage_config.RunLogStorageMode = "enabled"
    storage_reason: storage_config.RunLogStorageReason = "injected-storage"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validated_repo_root(repo_root: Path) -> Path:
    resolved = repo_roots.consumer_repo_root(repo_root)
    if resolved is None:
        raise RunLifecycleError(
            f"could not discover a Git repository root from {repo_root}"
        )
    return larch_io.validate_trusted_directory(resolved)


def _state_home(environ: Mapping[str, str]) -> Path:
    configured = environ.get(_ENV_XDG_STATE_HOME, "")
    selected = Path(configured) if configured else Path.home() / ".local" / "state"
    if not selected.is_absolute():
        raise RunLifecycleError(f"{_ENV_XDG_STATE_HOME} must be an absolute path")
    return selected


def lifecycle_log_root(
    *,
    repo_root: Path,
    resolution: RunLogStorageResolution,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the durable mutable staging root for universal skill runs."""
    environment = os.environ if environ is None else environ
    _ = _validated_repo_root(repo_root)
    namespace_id: str = (
        resolution.storage.storage_origin_id
        if resolution.storage is not None
        else str(resolution.local_namespace_id)
    )
    namespace_kind: str = (
        "storage-origins" if resolution.storage is not None else "local-repositories"
    )
    return (
        _state_home(environment)
        / "larch"
        / "run-lifecycle"
        / "v3"
        / resolution.client_repo
        / namespace_kind
        / namespace_id
        / "staging"
    )


def _context_file(
    *,
    resolution: RunLogStorageResolution,
    skill: str,
    run_id: str,
    environ: Mapping[str, str],
) -> Path:
    namespace_id: str = (
        resolution.storage.storage_origin_id
        if resolution.storage is not None
        else str(resolution.local_namespace_id)
    )
    namespace_kind: str = (
        "storage-origins"
        if resolution.storage is not None
        else "local-repositories"
    )
    return (
        _state_home(environ)
        / "larch"
        / "run-lifecycle"
        / "v3"
        / resolution.client_repo
        / namespace_kind
        / namespace_id
        / "contexts"
        / skill
        / run_id
        / LIFECYCLE_CONTEXT_BASENAME
    )


def _write_context(*, started: LifecycleStart) -> None:
    resolution: RunLogStorageResolution = started.storage_resolution
    storage: ToolRepositoryStorage | None = resolution.storage
    larch_io.atomic_write(
        started.context_file,
        json.dumps(
            {
                "schema_version": LIFECYCLE_CONTEXT_SCHEMA_VERSION,
                "repo_root": str(started.repo_root),
                "publication_mode": resolution.mode,
                "storage_resolution_reason": resolution.reason,
                "storage_base_uri": storage.base.uri if storage is not None else None,
                "client_repo": resolution.client_repo,
                "tool_repo_uri": storage.uri if storage is not None else None,
                "storage_origin_id": (
                    storage.storage_origin_id if storage is not None else None
                ),
                "local_namespace_id": resolution.local_namespace_id,
                "skill": started.skill,
                "run_id": started.run_id,
                "log_root": str(started.log_root),
                "run_dir": str(started.run_dir),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        mode=0o600,
        nofollow=True,
    )


def _provided_context_resolution(
    *,
    storage_root: ToolRepositoryStorage | None,
    storage_resolution: RunLogStorageResolution | None,
) -> RunLogStorageResolution | None:
    """Return caller-pinned storage state while preserving the legacy seam."""
    if storage_resolution is not None and storage_root is not None:
        raise ValueError("provide storage_resolution or storage_root, not both")
    if storage_resolution is not None:
        return storage_resolution
    if storage_root is not None:
        return storage_config.injected_storage_resolution(storage_root)
    return None


def _active_context_resolution(
    *,
    repo_root: Path,
    environ: Mapping[str, str],
    provided_resolution: RunLogStorageResolution | None,
) -> RunLogStorageResolution:
    """Resolve storage only when the caller has not already pinned it."""
    if provided_resolution is not None:
        return provided_resolution
    return storage_config.resolve_run_log_storage(repo_root=repo_root, environ=environ)


def load_run_context(  # noqa: PLR0913 - preserves the legacy raw-storage seam alongside resolved production storage.
    *,
    repo_root: Path,
    skill: str,
    run_id: str,
    environ: Mapping[str, str] | None = None,
    storage_root: ToolRepositoryStorage | None = None,
    storage_resolution: RunLogStorageResolution | None = None,
) -> LifecycleStart:
    """Rehydrate one lifecycle context without inherited shell state."""
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    run_name = run_log_publish.validated_component(run_id, label="run-id", slug=True)
    provided_resolution = _provided_context_resolution(
        storage_root=storage_root,
        storage_resolution=storage_resolution,
    )
    client_repo: str = (
        provided_resolution.client_repo
        if provided_resolution is not None
        else storage_config.derive_client_repo(repo_root=root)
    )
    local_resolution = RunLogStorageResolution(
        mode="disabled",
        reason="config-file-missing",
        storage=None,
        client_repo=client_repo,
        local_namespace_id=storage_config.local_namespace_id(root),
    )
    disabled_context_file: Path = _context_file(
        resolution=local_resolution,
        skill=skill_name,
        run_id=run_name,
        environ=environment,
    )
    if disabled_context_file.is_symlink():
        raise RunLifecycleError(
            f"lifecycle context is missing or unsafe: {disabled_context_file}"
        )
    disabled_context_exists: bool = disabled_context_file.exists()
    if disabled_context_exists and not disabled_context_file.is_file():
        raise RunLifecycleError(
            f"lifecycle context is missing or unsafe: {disabled_context_file}"
        )

    active_resolution: RunLogStorageResolution
    context_file: Path
    if disabled_context_exists:
        context_file = disabled_context_file
        active_resolution = local_resolution
    else:
        active_resolution = _active_context_resolution(
            repo_root=root,
            environ=environment,
            provided_resolution=provided_resolution,
        )
        context_file = _context_file(
            resolution=active_resolution,
            skill=skill_name,
            run_id=run_name,
            environ=environment,
        )
    _require_lifecycle(
        not context_file.is_symlink() and context_file.is_file(),
        f"lifecycle context is missing or unsafe: {context_file}",
    )
    try:
        larch_io.assert_no_symlink_path_or_ancestors(context_file)
    except OSError as exc:
        raise RunLifecycleError(
            f"lifecycle context is missing or unsafe: {context_file}"
        ) from exc
    raw: object = json.loads(context_file.read_text(encoding="utf-8"))
    _require_lifecycle(isinstance(raw, dict), "lifecycle context must be a JSON object")
    data = cast("dict[str, object]", raw)
    expected: dict[str, object] = {
        "schema_version": LIFECYCLE_CONTEXT_SCHEMA_VERSION,
        "repo_root": str(root),
        "skill": skill_name,
        "run_id": run_name,
    }
    _require_lifecycle(
        all(data.get(key) == value for key, value in expected.items()),
        "lifecycle context identity mismatch",
    )
    publication_mode: object = data.get("publication_mode")
    resolution_reason: object = data.get("storage_resolution_reason")
    context_client_repo: object = data.get("client_repo")
    log_root_raw, run_dir_raw = data.get("log_root"), data.get("run_dir")
    _require_lifecycle(
        publication_mode in {"enabled", "disabled"}
        and isinstance(resolution_reason, str)
        and isinstance(context_client_repo, str)
        and context_client_repo == client_repo
        and isinstance(log_root_raw, str)
        and bool(log_root_raw)
        and isinstance(run_dir_raw, str)
        and bool(run_dir_raw),
        "lifecycle context paths or publication identity are missing",
    )
    if publication_mode == "disabled":
        _require_lifecycle(
            context_file == disabled_context_file
            and resolution_reason in storage_config.DISABLED_STORAGE_REASONS
            and data.get("local_namespace_id")
            == local_resolution.local_namespace_id
            and data.get("tool_repo_uri") is None
            and data.get("storage_origin_id") is None
            and data.get("storage_base_uri") is None,
            "disabled lifecycle context identity mismatch",
        )
        active_resolution = RunLogStorageResolution(
            mode="disabled",
            reason=cast("storage_config.RunLogStorageReason", resolution_reason),
            storage=None,
            client_repo=client_repo,
            local_namespace_id=local_resolution.local_namespace_id,
        )
    else:
        tool_repo_uri: object = data.get("tool_repo_uri")
        storage_origin_id: object = data.get("storage_origin_id")
        storage_base_uri: object = data.get("storage_base_uri")
        _require_lifecycle(
            all(
                isinstance(value, str) and value
                for value in (
                    tool_repo_uri,
                    storage_origin_id,
                    storage_base_uri,
                )
            )
            and data.get("local_namespace_id") is None,
            "enabled lifecycle storage identity is missing",
        )
        context_storage: ToolRepositoryStorage = (
            storage_config.parse_tool_repository_uri(
                str(tool_repo_uri), expected_client_repo=client_repo
            )
        )
        _require_lifecycle(
            active_resolution.mode == "enabled"
            and active_resolution.storage == context_storage
            and active_resolution.reason == resolution_reason
            and context_storage.base.uri == storage_base_uri
            and context_storage.storage_origin_id == storage_origin_id,
            "configured storage or Git origin changed after lifecycle start",
        )
    log_root = Path(str(log_root_raw))
    run_dir = Path(str(run_dir_raw))
    _require_lifecycle(
        log_root.is_absolute() and run_dir == log_root / skill_name / run_name,
        "lifecycle context staging path mismatch",
    )
    return LifecycleStart(
        root,
        active_resolution,
        skill_name,
        run_name,
        log_root,
        run_dir,
        context_file,
    )


def _parent_identity_from_context(
    *,
    repo_root: Path,
    context_file: Path,
    environ: Mapping[str, str],
    resolution: RunLogStorageResolution,
) -> tuple[str, str]:
    _require_lifecycle(
        context_file.is_absolute()
        and not context_file.is_symlink()
        and context_file.is_file(),
        "parent lifecycle context is missing or unsafe",
    )
    raw: object = json.loads(context_file.read_text(encoding="utf-8"))
    _require_lifecycle(
        isinstance(raw, dict), "parent lifecycle context identity is missing"
    )
    data = cast("dict[str, object]", raw)
    _require_lifecycle(
        isinstance(data.get("skill"), str) and isinstance(data.get("run_id"), str),
        "parent lifecycle context identity is missing",
    )
    parent = load_run_context(
        repo_root=repo_root,
        skill=cast("str", data["skill"]),
        run_id=cast("str", data["run_id"]),
        environ=environ,
        storage_resolution=resolution,
    )
    _require_lifecycle(
        parent.context_file == context_file, "parent lifecycle context path mismatch"
    )
    return parent.skill, parent.run_id


def _preflight_storage(storage: ToolRepositoryStorage) -> None:
    storage_config.preflight_tool_repository(storage=storage)


def _validate_parent(*, parent_skill: str, parent_run_id: str) -> None:
    if bool(parent_skill) != bool(parent_run_id):
        raise ValueError("--parent-skill and --parent-run-id must be provided together")
    if parent_skill:
        _ = run_log_publish.validated_component(
            parent_skill, label="parent skill", slug=True
        )
        _ = run_log_publish.validated_component(
            parent_run_id, label="parent run-id", slug=True
        )


def start_run(  # noqa: PLR0913 - lifecycle boundary validates identity, adoption, storage, and parent state together.
    *,
    repo_root: Path,
    skill: str,
    parent_skill: str = "",
    parent_run_id: str = "",
    run_id: str | None = None,
    log_root: Path | None = None,
    issue: str = "",
    adopt_existing: bool = False,
    parent_context: Path | None = None,
    environ: Mapping[str, str] | None = None,
    storage_root: ToolRepositoryStorage | None = None,
    preflight: Callable[[ToolRepositoryStorage], None] = _preflight_storage,
) -> LifecycleStart:
    """Resolve publication, preflight when enabled, and create local staging."""
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    active_resolution: RunLogStorageResolution = (
        storage_config.injected_storage_resolution(storage_root)
        if storage_root is not None
        else storage_config.resolve_run_log_storage(
            repo_root=root, environ=environment
        )
    )
    if parent_context is not None:
        if parent_skill or parent_run_id:
            raise ValueError(
                "parent context cannot be combined with explicit parent identity"
            )
        parent_skill, parent_run_id = _parent_identity_from_context(
            repo_root=root,
            context_file=parent_context,
            environ=environment,
            resolution=active_resolution,
        )
    _validate_parent(parent_skill=parent_skill, parent_run_id=parent_run_id)
    if active_resolution.storage is not None:
        preflight(active_resolution.storage)
    selected_run_id = run_id or str(uuid.uuid4())
    run_name = run_log_publish.validated_component(
        selected_run_id, label="run-id", slug=True
    )
    selected_log_root = log_root or lifecycle_log_root(
        repo_root=root, resolution=active_resolution, environ=environment
    )
    _require_lifecycle(
        selected_log_root.is_absolute(), "lifecycle log root must be absolute"
    )
    init = run_logs.log_init(
        log_root=selected_log_root,
        skill=skill_name,
        run_id=run_name,
        parent=(
            run_logs.RunParent(skill=parent_skill, run_id=parent_run_id)
            if parent_skill and parent_run_id
            else None
        ),
        issue=issue,
    )
    if init.unchanged and not adopt_existing:
        raise RunLifecycleError(f"run ID already exists: {run_name}")
    run_dir = init.path.parent
    manifest = run_log_manifest._read_manifest_v2(init.path)  # noqa: SLF001 - sibling lifecycle owns this manifest transition.
    _require_lifecycle(
        manifest.get("lifecycle_schema_version") in {None, LIFECYCLE_SCHEMA_VERSION},
        "unsupported lifecycle schema version",
    )
    expected_parent_skill = parent_skill or None
    expected_parent_run_id = parent_run_id or None
    _require_lifecycle(
        manifest.get("parent_skill") == expected_parent_skill,
        "existing lifecycle parent skill mismatch",
    )
    _require_lifecycle(
        manifest.get("parent_run_id") == expected_parent_run_id,
        "existing lifecycle parent run ID mismatch",
    )
    _require_lifecycle(
        manifest.get("skill") == skill_name and manifest.get("run_id") == run_name,
        "new lifecycle manifest identity mismatch",
    )
    if manifest.get("lifecycle_schema_version") == LIFECYCLE_SCHEMA_VERSION:
        storage: ToolRepositoryStorage | None = active_resolution.storage
        _require_lifecycle(
            manifest.get("publication_mode") == active_resolution.mode
            and manifest.get("storage_resolution_reason")
            == active_resolution.reason
            and manifest.get("client_repo") == active_resolution.client_repo
            and manifest.get("tool_repo_uri")
            == (storage.uri if storage is not None else None)
            and manifest.get("storage_origin_id")
            == (storage.storage_origin_id if storage is not None else None)
            and manifest.get("storage_base_uri")
            == (storage.base.uri if storage is not None else None)
            and manifest.get("local_namespace_id")
            == active_resolution.local_namespace_id,
            "run-log publication or repository identity changed after lifecycle start",
        )
    else:
        storage = active_resolution.storage
        _ = run_log_manifest._update_manifest_v2(  # noqa: SLF001 - sibling lifecycle owns this manifest transition.
            path=init.path,
            updates={
                "status": config.MANIFEST_STATUS_IN_PROGRESS,
                "lifecycle_schema_version": LIFECYCLE_SCHEMA_VERSION,
                "publication_mode": active_resolution.mode,
                "storage_resolution_reason": active_resolution.reason,
                "storage_base_uri": (
                    storage.base.uri if storage is not None else None
                ),
                "client_repo": active_resolution.client_repo,
                "tool_repo_uri": storage.uri if storage is not None else None,
                "storage_origin_id": (
                    storage.storage_origin_id if storage is not None else None
                ),
                "local_namespace_id": active_resolution.local_namespace_id,
                "terminal_outcome": None,
                "finished_at": None,
            },
        )
    context_file = _context_file(
        resolution=active_resolution,
        skill=skill_name,
        run_id=run_name,
        environ=environment,
    )
    started = LifecycleStart(
        root,
        active_resolution,
        skill_name,
        run_name,
        selected_log_root,
        run_dir,
        context_file,
    )
    if not (run_dir / UNIVERSAL_EXECUTION_ISSUES).is_file():
        run_log_batch.atomic_write_text(
            path=run_dir / UNIVERSAL_EXECUTION_ISSUES, content=""
        )
    if context_file.is_file():
        existing = load_run_context(
            repo_root=root,
            skill=skill_name,
            run_id=run_name,
            environ=environment,
            storage_resolution=active_resolution,
        )
        _require_lifecycle(
            existing == started, "existing lifecycle context does not match adoption"
        )
    else:
        _write_context(started=started)
    return started


def _terminal_manifest(
    *, run_dir: Path, skill: str, run_id: str
) -> tuple[Path, dict[str, object]]:
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RunLifecycleError(
            f"lifecycle manifest is missing or unsafe: {manifest_path}"
        )
    manifest = run_log_manifest._read_manifest_v2(manifest_path)  # noqa: SLF001 - sibling lifecycle validates its own manifest.
    if manifest.get("skill") != skill or manifest.get("run_id") != run_id:
        raise RunLifecycleError("lifecycle manifest identity mismatch")
    if manifest.get("lifecycle_schema_version") != LIFECYCLE_SCHEMA_VERSION:
        raise RunLifecycleError("unsupported or missing lifecycle schema version")
    return manifest_path, manifest


def _render_final_report(*, skill: str, run_id: str, outcome: str) -> str:
    return (
        "# Skill run final report\n\n"
        f"- Skill: `{skill}`\n"
        f"- Run ID: `{run_id}`\n"
        f"- Outcome: `{outcome}`\n"
    )


def _missing_transcript_issue(*, skill: str, run_id: str) -> str:
    return (
        json.dumps(
        {
            "phase": "terminal",
            "step": "run-lifecycle",
            "category": "Warnings",
            "body": (
                f"{UNIVERSAL_SESSION_TRANSCRIPT} was unavailable for {skill} run {run_id}; "
                "the universal final report and lifecycle metadata were preserved."
            ),
        },
        separators=(",", ":"),
        sort_keys=True,
        )
        + "\n"
    )


def _write_terminal_artifacts(  # noqa: PLR0913 - terminal identity inputs stay explicit.
    *,
    run_dir: Path,
    manifest_path: Path,
    manifest: dict[str, object],
    skill: str,
    run_id: str,
    outcome: str,
) -> None:
    existing = manifest.get("terminal_outcome")
    if existing is not None and existing != outcome:
        raise RunLifecycleError(
            f"run already recorded terminal outcome {existing!r}, not {outcome!r}"
        )
    report_path = run_dir / UNIVERSAL_FINAL_REPORT
    report = _render_final_report(skill=skill, run_id=run_id, outcome=outcome)
    if report_path.exists() and report_path.read_text(encoding="utf-8") != report:
        raise RunLifecycleError(
            "existing universal final report does not match terminal outcome"
        )
    run_log_batch.atomic_write_text(
        path=report_path,
        content=report,
    )
    transcript = run_dir / UNIVERSAL_SESSION_TRANSCRIPT
    issues_path = run_dir / UNIVERSAL_EXECUTION_ISSUES
    if not transcript.is_file():
        issue = _missing_transcript_issue(skill=skill, run_id=run_id)
        existing_issues = (
            issues_path.read_text(encoding="utf-8") if issues_path.is_file() else ""
        )
        if issue not in existing_issues:
            run_log_batch.atomic_write_text(
                path=issues_path,
                content=existing_issues + issue,
            )
    _ = run_log_manifest._update_manifest_v2(  # noqa: SLF001 - sibling lifecycle owns this manifest transition.
        path=manifest_path,
        updates={
            "status": config.MANIFEST_STATUS_DONE,
            "terminal_outcome": outcome,
            "finished_at": str(manifest.get("finished_at") or _utc_now()),
        },
    )


def _manifest_matches_resolution(
    *, manifest: Mapping[str, object], resolution: RunLogStorageResolution
) -> bool:
    storage: ToolRepositoryStorage | None = resolution.storage
    publication_identity_matches: bool = (
        manifest.get("publication_mode") == resolution.mode
        and manifest.get("storage_resolution_reason") == resolution.reason
        and manifest.get("client_repo") == resolution.client_repo
        and manifest.get("local_namespace_id") == resolution.local_namespace_id
    )
    storage_identity_matches: bool = (
        manifest.get("tool_repo_uri")
        == (storage.uri if storage is not None else None)
        and manifest.get("storage_origin_id")
        == (storage.storage_origin_id if storage is not None else None)
        and manifest.get("storage_base_uri")
        == (storage.base.uri if storage is not None else None)
    )
    return publication_identity_matches and storage_identity_matches


def finish_run(  # noqa: PLR0913 - publication dependencies stay explicit and injectable.
    *,
    repo_root: Path,
    skill: str,
    run_id: str,
    outcome: str,
    environ: Mapping[str, str] | None = None,
    storage_root: ToolRepositoryStorage | None = None,
    store: ObjectStore | None = None,
    pre_scrub_violations: int = 0,
) -> LifecycleTerminal:
    """Record one terminal outcome and publish only when start pinned storage."""
    if outcome not in frozenset(_OUTCOME_BY_ACTION.values()):
        raise ValueError(f"unsupported lifecycle outcome: {outcome}")
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    run_name = run_log_publish.validated_component(run_id, label="run-id", slug=True)
    started = load_run_context(
        repo_root=root,
        skill=skill_name,
        run_id=run_name,
        environ=environment,
        storage_root=storage_root,
    )
    log_root = started.log_root
    run_dir = started.run_dir
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise RunLifecycleError(
            f"lifecycle run directory is missing or unsafe: {run_dir}"
        )
    manifest_path, manifest = _terminal_manifest(
        run_dir=run_dir, skill=skill_name, run_id=run_name
    )
    resolution: RunLogStorageResolution = started.storage_resolution
    active_storage: ToolRepositoryStorage | None = resolution.storage
    if not _manifest_matches_resolution(
        manifest=manifest, resolution=resolution
    ):
        raise RunLifecycleError(
            "run-log publication or repository identity changed after lifecycle start"
        )
    _write_terminal_artifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        skill=skill_name,
        run_id=run_name,
        outcome=outcome,
    )
    publication: PublicationResult | None = None
    violations: int = pre_scrub_violations
    if active_storage is not None:
        publication, violations = run_log_publish.publish_log_run(
            request=PublicationRequest(
                repo_root=root,
                storage_root=active_storage,
                skill=skill_name,
                run_id=run_name,
                staging_root=None,
            ),
            log_root=log_root,
            pre_scrub_violations=pre_scrub_violations,
            store=store,
            environ=environment,
        )
    if active_storage is None:
        shutil.rmtree(started.context_file.parent)
        _require_lifecycle(
            not started.context_file.parent.exists(),
            "disabled lifecycle context cleanup did not complete",
        )
        shutil.rmtree(run_dir)
        _require_lifecycle(
            not run_dir.exists(),
            "disabled lifecycle staging cleanup did not complete",
        )
    else:
        with suppress(OSError):
            shutil.rmtree(run_dir)
        with suppress(OSError):
            shutil.rmtree(started.context_file.parent)
    return LifecycleTerminal(
        outcome=outcome,
        storage_mode=resolution.mode,
        storage_reason=resolution.reason,
        publication=publication,
        secret_scrub_violations=violations,
    )


def _resolve_cli_repo_root(raw: str) -> Path:
    return _validated_repo_root(Path(raw))


def start_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log lifecycle-start")
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--parent-skill", default="")
    _ = parser.add_argument("--parent-run-id", default="")
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--log-root")
    _ = parser.add_argument("--issue", default="")
    _ = parser.add_argument("--adopt-existing", action="store_true")
    _ = parser.add_argument("--lifecycle-parent-context")
    try:
        args = parser.parse_args(argv)
        result = start_run(
            repo_root=_resolve_cli_repo_root(args.repo_root),
            skill=args.skill,
            parent_skill=args.parent_skill,
            parent_run_id=args.parent_run_id,
            run_id=args.run_id,
            log_root=Path(args.log_root) if args.log_root else None,
            issue=args.issue,
            adopt_existing=args.adopt_existing,
            parent_context=(
                Path(args.lifecycle_parent_context)
                if args.lifecycle_parent_context
                else None
            ),
        )
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    except storage_config.StorageConfigurationError as exc:
        print(f"run lifecycle start failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except (
        object_store.ObjectStoreError,
        OSError,
        RunLifecycleError,
        storage_config.StoragePreflightError,
        ValueError,
    ) as exc:
        print(f"run lifecycle start failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_PREFLIGHT
    print(f"RUN_ID={result.run_id}")
    print(f"SKILL={result.skill}")
    print(f"LOG_ROOT={result.log_root}")
    print(f"RUN_DIR={result.run_dir}")
    print(f"CONTEXT_FILE={result.context_file}")
    resolution: RunLogStorageResolution = result.storage_resolution
    storage: ToolRepositoryStorage | None = resolution.storage
    if storage is None:
        print(
            "**⚠ Run-log publication is disabled "
            f"({resolution.reason}). This skill will run, but no remote run-log "
            "archive or synchronized cache entry will be created.**",
            file=sys.stderr,
        )
    print(f"RUN_LOG_STORAGE={resolution.mode}")
    print(f"RUN_LOG_STORAGE_REASON={resolution.reason}")
    print(f"STORAGE_BASE_URI={storage.base.uri if storage is not None else ''}")
    print(f"CLIENT_REPO={resolution.client_repo}")
    print(f"TOOL_REPO_URI={storage.uri if storage is not None else ''}")
    print(f"RUN_LOGS_URI={storage.run_logs_uri if storage is not None else ''}")
    print(
        f"STORAGE_PREFLIGHT={'ok' if storage is not None else 'skipped-disabled'}"
    )
    print("PREFLIGHT_OK=true")
    print("LIFECYCLE_STARTED=true")
    return config.EXIT_OK


def _terminal_main(argv: Sequence[str], *, action: str) -> int:
    parser = argparse.ArgumentParser(prog=f"cli.py run-log lifecycle-{action}")
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
        result = finish_run(
            repo_root=_resolve_cli_repo_root(args.repo_root),
            skill=args.skill,
            run_id=args.run_id,
            outcome=_OUTCOME_BY_ACTION[action],
        )
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    except storage_config.StorageConfigurationError as exc:
        print("RUN_LOG_PUBLICATION=failed")
        print("LIFECYCLE_FLUSHED=false")
        print("LIFECYCLE_TERMINALIZED=false")
        print(f"run lifecycle {action} failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except TERMINAL_EXCEPTIONS as exc:
        print("RUN_LOG_PUBLICATION=failed")
        print("LIFECYCLE_FLUSHED=false")
        print("LIFECYCLE_TERMINALIZED=false")
        print(f"run lifecycle {action} failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
    print(f"RUN_ID={args.run_id}")
    print(f"SKILL={args.skill}")
    print(f"OUTCOME={result.outcome}")
    print(f"RUN_LOG_STORAGE={result.storage_mode}")
    print(f"RUN_LOG_STORAGE_REASON={result.storage_reason}")
    if result.publication is None:
        print(
            "**⚠ Run-log publication skipped because storage was disabled at "
            f"lifecycle start ({result.storage_reason}).**",
            file=sys.stderr,
        )
        print("RUN_LOG_PUBLICATION=skipped-disabled")
        print("LIFECYCLE_FLUSHED=false")
    else:
        print(f"REMOTE_KEY={result.publication.remote_key}")
        print(f"ARCHIVE_SHA256={result.publication.archive_sha256}")
        print(f"CACHE_DIR={result.publication.cache_dir}")
        print(f"SECRET_SCRUB_VIOLATIONS={result.secret_scrub_violations}")
        print("RUN_LOG_PUBLICATION=published")
        print("LIFECYCLE_FLUSHED=true")
    print("LIFECYCLE_TERMINALIZED=true")
    return config.EXIT_OK


def finalize_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="finalize")


def failure_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="failure")


def cancel_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="cancel")


def early_return_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="early-return")
