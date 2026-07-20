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
from larch.report.run_log_publish import ObjectStore, PublicationRequest, PublicationResult
from larch.report.storage_config import StorageRoot

LIFECYCLE_SCHEMA_VERSION: Final = 1
LIFECYCLE_CONTEXT_SCHEMA_VERSION: Final = 1
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


TERMINAL_EXCEPTIONS: Final = (EOFError, object_store.ObjectStoreError, OSError, run_log_publish.PublicationError, RunLifecycleError, ShipError, storage_config.StorageConfigurationError, tarfile.TarError, TypeError, ValueError)


@dataclass(frozen=True)
class LifecycleStart:
    """Validated state created for one skill invocation."""

    repo_root: Path
    storage_root: StorageRoot
    skill: str
    run_id: str
    log_root: Path
    run_dir: Path
    context_file: Path


@dataclass(frozen=True)
class LifecycleTerminal:
    """Verified terminal publication result for one skill invocation."""

    outcome: str
    publication: PublicationResult
    secret_scrub_violations: int


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _validated_repo_root(repo_root: Path) -> Path:
    resolved = repo_roots.consumer_repo_root(repo_root)
    if resolved is None:
        raise RunLifecycleError(f"could not discover a Git repository root from {repo_root}")
    return larch_io.validate_trusted_directory(resolved)


def _state_home(environ: Mapping[str, str]) -> Path:
    configured = environ.get(_ENV_XDG_STATE_HOME, "")
    selected = Path(configured) if configured else Path.home() / ".local" / "state"
    if not selected.is_absolute():
        raise RunLifecycleError(f"{_ENV_XDG_STATE_HOME} must be an absolute path")
    return selected


def lifecycle_log_root(
    *, repo_root: Path, environ: Mapping[str, str] | None = None
) -> Path:
    """Return the durable mutable staging root for universal skill runs."""
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    repo_name = run_log_publish.validated_component(
        root.name, label="repository name", slug=False
    )
    return _state_home(environment) / "larch" / "run-lifecycle" / repo_name / "staging"


def _context_file(*, repo_root: Path, skill: str, run_id: str, environ: Mapping[str, str]) -> Path:
    return _state_home(environ) / "larch" / "run-lifecycle" / run_log_publish.validated_component(repo_root.name, label="repository name", slug=False) / "contexts" / skill / run_id / LIFECYCLE_CONTEXT_BASENAME


def _write_context(*, started: LifecycleStart) -> None:
    larch_io.atomic_write(started.context_file, json.dumps({"schema_version": LIFECYCLE_CONTEXT_SCHEMA_VERSION, "repo_root": str(started.repo_root), "storage_uri": started.storage_root.uri, "skill": started.skill, "run_id": started.run_id, "log_root": str(started.log_root), "run_dir": str(started.run_dir)}, separators=(",", ":"), sort_keys=True) + "\n", mode=0o600, nofollow=True)


def load_run_context(*, repo_root: Path, skill: str, run_id: str, environ: Mapping[str, str] | None = None) -> LifecycleStart:
    """Rehydrate one lifecycle context without inherited shell state."""
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    run_name = run_log_publish.validated_component(run_id, label="run-id", slug=True)
    context_file = _context_file(repo_root=root, skill=skill_name, run_id=run_name, environ=environment)
    _require_lifecycle(not context_file.is_symlink() and context_file.is_file(), f"lifecycle context is missing or unsafe: {context_file}")
    raw: object = json.loads(context_file.read_text(encoding="utf-8"))
    _require_lifecycle(isinstance(raw, dict), "lifecycle context must be a JSON object")
    data = cast("dict[str, object]", raw)
    expected: dict[str, object] = {"schema_version": LIFECYCLE_CONTEXT_SCHEMA_VERSION, "repo_root": str(root), "skill": skill_name, "run_id": run_name}
    _require_lifecycle(all(data.get(key) == value for key, value in expected.items()), "lifecycle context identity mismatch")
    storage_uri, log_root_raw, run_dir_raw = data.get("storage_uri"), data.get("log_root"), data.get("run_dir")
    _require_lifecycle(all(isinstance(value, str) and value for value in (storage_uri, log_root_raw, run_dir_raw)), "lifecycle context paths or storage URI are missing")
    storage_root = storage_config._parse_storage_uri(str(storage_uri))  # pyright: ignore[reportPrivateUsage]  # persisted context reuses canonical parser  # noqa: SLF001 - sibling parser owns validation
    log_root = Path(str(log_root_raw))
    run_dir = Path(str(run_dir_raw))
    _require_lifecycle(log_root.is_absolute() and run_dir == log_root / skill_name / run_name, "lifecycle context staging path mismatch")
    return LifecycleStart(root, storage_root, skill_name, run_name, log_root, run_dir, context_file)


def _parent_identity_from_context(*, repo_root: Path, context_file: Path, environ: Mapping[str, str]) -> tuple[str, str]:
    _require_lifecycle(context_file.is_absolute() and not context_file.is_symlink() and context_file.is_file(), "parent lifecycle context is missing or unsafe")
    raw: object = json.loads(context_file.read_text(encoding="utf-8"))
    _require_lifecycle(isinstance(raw, dict), "parent lifecycle context identity is missing")
    data = cast("dict[str, object]", raw)
    _require_lifecycle(isinstance(data.get("skill"), str) and isinstance(data.get("run_id"), str), "parent lifecycle context identity is missing")
    parent = load_run_context(repo_root=repo_root, skill=cast("str", data["skill"]), run_id=cast("str", data["run_id"]), environ=environ)
    _require_lifecycle(parent.context_file == context_file, "parent lifecycle context path mismatch")
    return parent.skill, parent.run_id


def _preflight_storage(storage_root: StorageRoot) -> None:
    if storage_root.scheme == "s3":
        storage_config.preflight_s3_bucket(storage_root=storage_root)
        return
    object_store.object_store_for(storage_root).preflight_bucket()


def _validate_parent(*, parent_skill: str, parent_run_id: str) -> None:
    if bool(parent_skill) != bool(parent_run_id):
        raise ValueError("--parent-skill and --parent-run-id must be provided together")
    if parent_skill:
        _ = run_log_publish.validated_component(parent_skill, label="parent skill", slug=True)
        _ = run_log_publish.validated_component(parent_run_id, label="parent run-id", slug=True)


def start_run(  # noqa: PLR0913 - lifecycle boundary validates identity, adoption, storage, and parent state together.
    *,
    repo_root: Path,
    skill: str,
    parent_skill: str = "",
    parent_run_id: str = "",
    run_id: str | None = None, log_root: Path | None = None, issue: str = "",
    adopt_existing: bool = False, parent_context: Path | None = None,
    environ: Mapping[str, str] | None = None,
    storage_root: StorageRoot | None = None,
    preflight: Callable[[StorageRoot], None] = _preflight_storage,
) -> LifecycleStart:
    """Preflight storage and create a unique, isolated skill-run staging tree."""
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    if parent_context is not None:
        if parent_skill or parent_run_id:
            raise ValueError("parent context cannot be combined with explicit parent identity")
        parent_skill, parent_run_id = _parent_identity_from_context(repo_root=root, context_file=parent_context, environ=environment)
    _validate_parent(parent_skill=parent_skill, parent_run_id=parent_run_id)
    active_storage = storage_root or storage_config.load_storage_root(
        repo_root=root, environ=environment
    )
    preflight(active_storage)
    selected_run_id = run_id or str(uuid.uuid4())
    run_name = run_log_publish.validated_component(
        selected_run_id, label="run-id", slug=True
    )
    selected_log_root = log_root or lifecycle_log_root(repo_root=root, environ=environment)
    _require_lifecycle(selected_log_root.is_absolute(), "lifecycle log root must be absolute")
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
    _require_lifecycle(manifest.get("lifecycle_schema_version") in {None, LIFECYCLE_SCHEMA_VERSION}, "unsupported lifecycle schema version")
    expected_parent_skill = parent_skill or None
    expected_parent_run_id = parent_run_id or None
    _require_lifecycle(manifest.get("parent_skill") == expected_parent_skill, "existing lifecycle parent skill mismatch")
    _require_lifecycle(manifest.get("parent_run_id") == expected_parent_run_id, "existing lifecycle parent run ID mismatch")
    _require_lifecycle(manifest.get("skill") == skill_name and manifest.get("run_id") == run_name, "new lifecycle manifest identity mismatch")
    if manifest.get("lifecycle_schema_version") == LIFECYCLE_SCHEMA_VERSION:
        _require_lifecycle(manifest.get("storage_uri") == active_storage.uri, "configured storage root changed after lifecycle start")
    else:
        _ = run_log_manifest._update_manifest_v2(  # noqa: SLF001 - sibling lifecycle owns this manifest transition.
            path=init.path,
            updates={"status": config.MANIFEST_STATUS_IN_PROGRESS, "lifecycle_schema_version": LIFECYCLE_SCHEMA_VERSION, "storage_uri": active_storage.uri, "terminal_outcome": None, "finished_at": None},
        )
    context_file = _context_file(repo_root=root, skill=skill_name, run_id=run_name, environ=environment)
    started = LifecycleStart(root, active_storage, skill_name, run_name, selected_log_root, run_dir, context_file)
    if not (run_dir / UNIVERSAL_EXECUTION_ISSUES).is_file():
        run_log_batch.atomic_write_text(path=run_dir / UNIVERSAL_EXECUTION_ISSUES, content="")
    if context_file.is_file():
        existing = load_run_context(repo_root=root, skill=skill_name, run_id=run_name, environ=environment)
        _require_lifecycle(existing == started, "existing lifecycle context does not match adoption")
    else:
        _write_context(started=started)
    return started


def _terminal_manifest(*, run_dir: Path, skill: str, run_id: str) -> tuple[Path, dict[str, object]]:
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RunLifecycleError(f"lifecycle manifest is missing or unsafe: {manifest_path}")
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
    return json.dumps(
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
    ) + "\n"


def _write_terminal_artifacts(  # noqa: PLR0913 - terminal identity inputs stay explicit.
    *, run_dir: Path, manifest_path: Path, manifest: dict[str, object], skill: str, run_id: str, outcome: str
) -> None:
    existing = manifest.get("terminal_outcome")
    if existing is not None and existing != outcome:
        raise RunLifecycleError(
            f"run already recorded terminal outcome {existing!r}, not {outcome!r}"
        )
    report_path = run_dir / UNIVERSAL_FINAL_REPORT
    report = _render_final_report(skill=skill, run_id=run_id, outcome=outcome)
    if report_path.exists() and report_path.read_text(encoding="utf-8") != report:
        raise RunLifecycleError("existing universal final report does not match terminal outcome")
    run_log_batch.atomic_write_text(
        path=report_path,
        content=report,
    )
    transcript = run_dir / UNIVERSAL_SESSION_TRANSCRIPT
    issues_path = run_dir / UNIVERSAL_EXECUTION_ISSUES
    if not transcript.is_file():
        issue = _missing_transcript_issue(skill=skill, run_id=run_id)
        existing_issues = issues_path.read_text(encoding="utf-8") if issues_path.is_file() else ""
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


def finish_run(  # noqa: PLR0913 - publication dependencies stay explicit and injectable.
    *,
    repo_root: Path,
    skill: str,
    run_id: str,
    outcome: str,
    environ: Mapping[str, str] | None = None,
    storage_root: StorageRoot | None = None,
    store: ObjectStore | None = None,
    pre_scrub_violations: int = 0,
) -> LifecycleTerminal:
    """Record one terminal outcome and loudly publish its immutable archive."""
    if outcome not in frozenset(_OUTCOME_BY_ACTION.values()):
        raise ValueError(f"unsupported lifecycle outcome: {outcome}")
    environment = os.environ if environ is None else environ
    root = _validated_repo_root(repo_root)
    skill_name = run_log_publish.validated_component(skill, label="skill", slug=True)
    run_name = run_log_publish.validated_component(run_id, label="run-id", slug=True)
    started = load_run_context(repo_root=root, skill=skill_name, run_id=run_name, environ=environment)
    log_root = started.log_root
    run_dir = started.run_dir
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise RunLifecycleError(f"lifecycle run directory is missing or unsafe: {run_dir}")
    manifest_path, manifest = _terminal_manifest(
        run_dir=run_dir, skill=skill_name, run_id=run_name
    )
    _write_terminal_artifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        skill=skill_name,
        run_id=run_name,
        outcome=outcome,
    )
    active_storage = storage_root or storage_config.load_storage_root(
        repo_root=root, environ=environment
    )
    recorded_storage = manifest.get("storage_uri")
    if recorded_storage != active_storage.uri:
        raise RunLifecycleError("configured storage root changed after lifecycle start")
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
    with suppress(OSError):
        shutil.rmtree(run_dir)
    with suppress(OSError):
        shutil.rmtree(started.context_file.parent)
    return LifecycleTerminal(
        outcome=outcome,
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
    _ = parser.add_argument("--parent-context")
    try:
        args = parser.parse_args(argv)
        result = start_run(repo_root=_resolve_cli_repo_root(args.repo_root), skill=args.skill, parent_skill=args.parent_skill, parent_run_id=args.parent_run_id,
            run_id=args.run_id, log_root=Path(args.log_root) if args.log_root else None, issue=args.issue, adopt_existing=args.adopt_existing,
            parent_context=Path(args.parent_context) if args.parent_context else None)
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
    print(f"STORAGE_URI={result.storage_root.uri}")
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
        print("LIFECYCLE_FLUSHED=false")
        print(f"run lifecycle {action} failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except TERMINAL_EXCEPTIONS as exc:
        print("LIFECYCLE_FLUSHED=false")
        print(f"run lifecycle {action} failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
    print(f"RUN_ID={args.run_id}")
    print(f"SKILL={args.skill}")
    print(f"OUTCOME={result.outcome}")
    print(f"REMOTE_KEY={result.publication.remote_key}")
    print(f"ARCHIVE_SHA256={result.publication.archive_sha256}")
    print(f"CACHE_DIR={result.publication.cache_dir}")
    print(f"SECRET_SCRUB_VIOLATIONS={result.secret_scrub_violations}")
    print("LIFECYCLE_FLUSHED=true")
    return config.EXIT_OK


def finalize_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="finalize")


def failure_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="failure")


def cancel_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="cancel")


def early_return_main(argv: Sequence[str]) -> int:
    return _terminal_main(argv, action="early-return")
