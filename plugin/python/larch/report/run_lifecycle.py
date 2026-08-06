"""Typed Python consumer for the Rust-owned shared run lifecycle."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.errors import ShipError
from larch.core.repo_roots import larch_entrypoint
from larch.report import object_store, run_log_publish, storage_config
from larch.report.run_log_publish import PublicationResult
from larch.report.storage_config import RunLogStorageResolution, ToolRepositoryStorage

LIFECYCLE_SCHEMA_VERSION = 3
LIFECYCLE_CONTEXT_SCHEMA_VERSION = 3
LIFECYCLE_CONTEXT_BASENAME = "context.json"
UNIVERSAL_FINAL_REPORT = "final-report.md"
UNIVERSAL_EXECUTION_ISSUES = "execution-issues.ndjson"
UNIVERSAL_SESSION_TRANSCRIPT = "session-transcript.jsonl"


class RunLifecycleError(RuntimeError):
    """The Rust lifecycle command rejected a transition or machine envelope."""


TERMINAL_EXCEPTIONS = (
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
    """Validated state returned by the Rust lifecycle start command."""

    repo_root: Path
    storage_resolution: RunLogStorageResolution
    skill: str
    run_id: str
    log_root: Path
    run_dir: Path
    context_file: Path

    def __init__(  # noqa: PLR0913 - fields mirror the persisted lifecycle context.
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
        if storage_resolution is not None and storage_root is not None:
            raise ValueError("provide storage_resolution or storage_root, not both")
        resolution = storage_resolution
        if resolution is None and storage_root is not None:
            resolution = storage_config.injected_storage_resolution(storage_root)
        if (
            resolution is None
            or log_root is None
            or run_dir is None
            or context_file is None
        ):
            raise ValueError("lifecycle start requires resolved storage and paths")
        object.__setattr__(self, "repo_root", repo_root)
        object.__setattr__(self, "storage_resolution", resolution)
        object.__setattr__(self, "skill", skill)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "log_root", log_root)
        object.__setattr__(self, "run_dir", run_dir)
        object.__setattr__(self, "context_file", context_file)

    @property
    def storage_root(self) -> ToolRepositoryStorage:
        """Return enabled storage for compatibility with specialized callers."""
        return storage_config.require_enabled_storage(self.storage_resolution)


@dataclass(frozen=True)
class LifecycleTerminal:
    """Validated result returned by a Rust terminal command."""

    outcome: str
    publication: PublicationResult | None
    secret_scrub_violations: int
    storage_mode: storage_config.RunLogStorageMode = "enabled"
    storage_reason: storage_config.RunLogStorageReason = "injected-storage"


def _invoke(
    arguments: list[str],
    *,
    environ: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    plugin_root = Path(__file__).resolve().parents[3]
    command = [str(larch_entrypoint(plugin_root, use_env=False)), *arguments]
    environment = dict(os.environ if environ is None else environ)
    environment["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    return subprocess.run(
        command,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def _kv(stdout: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            values[key] = value
    return values


def _resolution(
    values: Mapping[str, str], context_file: Path
) -> RunLogStorageResolution:
    mode = values.get("RUN_LOG_STORAGE", "")
    reason = values.get("RUN_LOG_STORAGE_REASON", "")
    client_repo = values.get("CLIENT_REPO", "")
    context: object = json.loads(context_file.read_text(encoding="utf-8"))
    if not isinstance(context, dict):
        raise RunLifecycleError("Rust lifecycle context is not a JSON object")
    context_fields = cast("Mapping[str, object]", context)
    local_namespace = context_fields.get("local_namespace_id")
    if mode == "enabled":
        storage = storage_config.parse_tool_repository_uri(
            values.get("TOOL_REPO_URI", ""), expected_client_repo=client_repo
        )
        return RunLogStorageResolution(
            mode="enabled",
            reason=reason,  # type: ignore[arg-type]  # Rust emits the shared closed token set.
            storage=storage,
            client_repo=client_repo,
            local_namespace_id=None,
        )
    if mode == "disabled" and isinstance(local_namespace, str):
        return RunLogStorageResolution(
            mode="disabled",
            reason=reason,  # type: ignore[arg-type]  # Rust emits the shared closed token set.
            storage=None,
            client_repo=client_repo,
            local_namespace_id=local_namespace,
        )
    raise RunLifecycleError("Rust lifecycle returned an invalid storage state")


def _started(
    *, repo_root: Path, result: subprocess.CompletedProcess[str]
) -> LifecycleStart:
    values = _kv(result.stdout)
    required = (
        "RUN_ID",
        "SKILL",
        "LOG_ROOT",
        "RUN_DIR",
        "CONTEXT_FILE",
        "RUN_LOG_STORAGE",
        "RUN_LOG_STORAGE_REASON",
        "CLIENT_REPO",
        "LIFECYCLE_STARTED",
    )
    if result.returncode != 0 or any(key not in values for key in required):
        detail = result.stderr.strip() or "missing lifecycle start machine envelope"
        raise RunLifecycleError(detail)
    if values["LIFECYCLE_STARTED"] != "true":
        raise RunLifecycleError("Rust lifecycle start did not report success")
    context_file = Path(values["CONTEXT_FILE"])
    return LifecycleStart(
        repo_root=repo_root.resolve(),
        storage_resolution=_resolution(values, context_file),
        skill=values["SKILL"],
        run_id=values["RUN_ID"],
        log_root=Path(values["LOG_ROOT"]),
        run_dir=Path(values["RUN_DIR"]),
        context_file=context_file,
    )


def start_run(  # noqa: PLR0913 - keyword inputs mirror the stable lifecycle-start CLI.
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
    **unsupported: object,
) -> LifecycleStart:
    """Invoke Rust lifecycle start and parse its machine envelope."""
    if storage_root is not None or unsupported:
        raise RunLifecycleError("injected Python lifecycle dependencies were retired")
    arguments = [
        "run-log",
        "lifecycle-start",
        "--repo-root",
        str(repo_root),
        "--skill",
        skill,
    ]
    for flag, value in (
        ("--parent-skill", parent_skill),
        ("--parent-run-id", parent_run_id),
        ("--run-id", run_id or ""),
        ("--log-root", str(log_root) if log_root is not None else ""),
        ("--issue", issue),
        ("--lifecycle-parent-context", str(parent_context) if parent_context else ""),
    ):
        if value:
            arguments.extend([flag, value])
    if adopt_existing:
        arguments.append("--adopt-existing")
    result = _invoke(arguments, environ=environ)
    return _started(repo_root=repo_root, result=result)


def load_run_context(
    *,
    repo_root: Path,
    skill: str,
    run_id: str,
    environ: Mapping[str, str] | None = None,
    **unsupported: object,
) -> LifecycleStart:
    """Rehydrate through idempotent Rust adoption instead of Python state logic."""
    if unsupported:
        raise RunLifecycleError("injected Python lifecycle dependencies were retired")
    result = _invoke(
        [
            "run-log",
            "lifecycle-start",
            "--repo-root",
            str(repo_root),
            "--skill",
            skill,
            "--run-id",
            run_id,
            "--adopt-existing",
            "--rehydrate",
        ],
        environ=environ,
    )
    return _started(repo_root=repo_root, result=result)


def finish_run(  # noqa: PLR0913 - keyword inputs mirror the stable terminal CLI.
    *,
    repo_root: Path,
    skill: str,
    run_id: str,
    outcome: str,
    environ: Mapping[str, str] | None = None,
    pre_scrub_violations: int = 0,
    **unsupported: object,
) -> LifecycleTerminal:
    """Invoke the Rust terminal owner and parse its publication envelope."""
    if unsupported:
        raise RunLifecycleError("injected Python lifecycle dependencies were retired")
    action = {
        "success": "finalize",
        "failure": "failure",
        "cancelled": "cancel",
        "early-return": "early-return",
    }.get(outcome)
    if action is None:
        raise ValueError(f"unsupported lifecycle outcome: {outcome}")
    arguments = [
        "run-log",
        f"lifecycle-{action}",
        "--repo-root",
        str(repo_root),
        "--skill",
        skill,
        "--run-id",
        run_id,
    ]
    if pre_scrub_violations:
        arguments.extend(["--pre-scrub-violations", str(pre_scrub_violations)])
    result = _invoke(arguments, environ=environ)
    values = _kv(result.stdout)
    if result.returncode != 0 or values.get("LIFECYCLE_TERMINALIZED") != "true":
        detail = result.stderr.strip() or "missing lifecycle terminal machine envelope"
        raise RunLifecycleError(detail)
    if (
        result.stderr
        and "publication skipped because storage was disabled" not in result.stderr
    ):
        print(
            result.stderr,
            end="" if result.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )
    mode = values.get("RUN_LOG_STORAGE", "")
    reason = values.get("RUN_LOG_STORAGE_REASON", "")
    publication: PublicationResult | None = None
    violations = int(values.get("SECRET_SCRUB_VIOLATIONS", pre_scrub_violations))
    if values.get("RUN_LOG_PUBLICATION") == "published":
        publication = PublicationResult(
            remote_key=values["REMOTE_KEY"],
            archive_sha256=values["ARCHIVE_SHA256"],
            cache_dir=Path(values["CACHE_DIR"]),
            remote_status=run_log_publish.RemotePublicationStatus.CREATED,
            cache_status=run_log_publish.CachePublicationStatus.PROMOTED,
        )
    elif values.get("RUN_LOG_PUBLICATION") != "skipped-disabled":
        raise RunLifecycleError("Rust lifecycle returned an invalid publication state")
    return LifecycleTerminal(
        outcome=values.get("OUTCOME", outcome),
        publication=publication,
        secret_scrub_violations=violations,
        storage_mode=mode,  # type: ignore[arg-type]  # Rust emits the shared closed token set.
        storage_reason=reason,  # type: ignore[arg-type]  # Rust emits the shared closed token set.
    )
