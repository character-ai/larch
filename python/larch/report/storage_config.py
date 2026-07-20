"""Storage-root configuration and the initial S3 bucket-list preflight."""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast
from urllib.parse import SplitResult, urlsplit

from larch.core import config, proc
from larch.core.repo_roots import consumer_repo_root

_MIN_URI_PATH_SEGMENT_COUNT: Final = 2
_ASCII_CONTROL_CHARACTER_MAX: Final = 32


class StorageConfigurationError(ValueError):
    """The repository's storage-root configuration is missing or invalid."""


class StoragePreflightError(RuntimeError):
    """The configured storage bucket cannot be used for a startup preflight."""


@dataclass(frozen=True)
class StorageRoot:
    """Validated larch storage root, without credentials or object names."""

    scheme: str
    bucket: str
    prefix: str

    @property
    def uri(self) -> str:
        """Return the canonical configured storage-root URI."""
        return f"{self.scheme}://{self.bucket}/{self.prefix}"

    @property
    def run_logs_uri(self) -> str:
        """Return the deterministic remote root for run archives."""
        return f"{self.uri}/run-logs/"

    @property
    def bucket_uri(self) -> str:
        """Return the provider bucket root used by existence preflights."""
        return f"{self.scheme}://{self.bucket}"


def _validated_bucket(parsed: SplitResult) -> str:
    """Return a plain bucket authority with no credentials or port."""
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise StorageConfigurationError("[logs].uri must not contain credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise StorageConfigurationError("[logs].uri must contain a valid bucket name without a port") from exc
    if not parsed.netloc or port is not None or parsed.hostname != parsed.netloc:
        raise StorageConfigurationError("[logs].uri must contain a plain bucket name without a port")
    if any(character.isspace() for character in parsed.netloc):
        raise StorageConfigurationError("[logs].uri bucket must not contain whitespace")
    return parsed.netloc


def _validated_prefix(path: str) -> str:
    """Return a normalized non-empty storage-root prefix."""
    segments = path.split("/")
    if not path.startswith("/") or len(segments) < _MIN_URI_PATH_SEGMENT_COUNT or not segments[1:]:
        raise StorageConfigurationError("[logs].uri must include a non-empty storage-root prefix")
    prefix_segments = segments[1:]
    if any(not segment or segment in {".", ".."} for segment in prefix_segments):
        raise StorageConfigurationError("[logs].uri prefix must not contain empty, '.' or '..' segments")
    if any(
        any(character.isspace() or ord(character) < _ASCII_CONTROL_CHARACTER_MAX for character in segment)
        for segment in prefix_segments
    ):
        raise StorageConfigurationError("[logs].uri prefix must not contain whitespace or control characters")
    return "/".join(prefix_segments)


def _parse_storage_uri(raw_uri: str) -> StorageRoot:
    if not raw_uri or raw_uri != raw_uri.strip():
        raise StorageConfigurationError("[logs].uri must be a non-empty URI without surrounding whitespace")
    parsed = urlsplit(raw_uri)
    if parsed.scheme not in config.STORAGE_URI_SCHEMES:
        accepted = ", ".join(f"{scheme}://" for scheme in config.STORAGE_URI_SCHEMES)
        raise StorageConfigurationError(f"[logs].uri must use one of: {accepted}")
    if parsed.query or parsed.fragment:
        raise StorageConfigurationError("[logs].uri must not contain a query or fragment")
    return StorageRoot(
        scheme=parsed.scheme,
        bucket=_validated_bucket(parsed),
        prefix=_validated_prefix(parsed.path),
    )


def load_storage_root(*, repo_root: Path, environ: Mapping[str, str] | None = None) -> StorageRoot:
    """Load and validate storage configuration, honoring the environment override."""
    environment = os.environ if environ is None else environ
    override = environment.get(config.ENV_LARCH_LOGS_URI, "")
    if override:
        return _parse_storage_uri(override)
    config_path = repo_root / config.STORAGE_CONFIG_RELPATH
    if config_path.is_symlink() or not config_path.is_file():
        raise StorageConfigurationError(
            f"storage configuration is missing: create {config.STORAGE_CONFIG_RELPATH} at the repository root "
            f"or set {config.ENV_LARCH_LOGS_URI}"
        )
    try:
        with config_path.open("rb") as handle:
            raw_data = cast("dict[str, object]", tomllib.load(handle))
    except tomllib.TOMLDecodeError as exc:
        raise StorageConfigurationError(f"invalid {config.STORAGE_CONFIG_RELPATH}: {exc}") from exc
    raw_logs = raw_data.get("logs")
    if not isinstance(raw_logs, dict):
        raise StorageConfigurationError(f"invalid {config.STORAGE_CONFIG_RELPATH}: missing [logs] table")
    logs = cast("dict[str, object]", raw_logs)
    uri = logs.get("uri")
    if not isinstance(uri, str):
        raise StorageConfigurationError(f"invalid {config.STORAGE_CONFIG_RELPATH}: [logs].uri must be a string")
    return _parse_storage_uri(uri)


def discover_storage_root(*, start: Path | None = None, environ: Mapping[str, str] | None = None) -> StorageRoot:
    """Discover the Git repository root, then load its storage configuration."""
    repo_root = consumer_repo_root(start)
    if repo_root is None:
        location = str(start) if start is not None else str(Path.cwd())
        raise StorageConfigurationError(f"could not discover a Git repository root from {location}")
    return load_storage_root(repo_root=repo_root, environ=environ)


def preflight_s3_bucket(*, storage_root: StorageRoot, runner: proc.Runner | None = None) -> None:
    """Require a successful AWS bucket-root list, without inspecting its output."""
    if storage_root.scheme != "s3":
        raise StoragePreflightError(
            f"S3 startup preflight requires an s3:// storage root, got {storage_root.scheme}://"
        )
    active_runner = proc.ProcRunner() if runner is None else runner
    result = active_runner.run(
        [config.AWS_CLI, "s3", "ls", storage_root.bucket_uri],
        timeout=config.STORAGE_PREFLIGHT_TIMEOUT_SEC,
        check=False,
    )
    if result.returncode == 0:
        return
    if result.returncode == config.AWS_CLI_NOT_FOUND_EXIT_CODE:
        raise StoragePreflightError(
            f"AWS CLI is required for S3 storage preflight; install '{config.AWS_CLI}' and retry"
        )
    raise StoragePreflightError(
        f"S3 bucket-root list failed for {storage_root.bucket_uri} (exit {result.returncode}); "
        "verify normal AWS credential discovery and bucket access"
    )


def storage_preflight_main(argv: list[str]) -> int:
    """Run the configured S3 storage startup preflight."""
    parser = argparse.ArgumentParser(prog="cli.py run-log storage-preflight")
    _ = parser.add_argument("--repo-root", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    start = Path(args.repo_root) if args.repo_root else None
    try:
        storage_root = discover_storage_root(start=start)
        preflight_s3_bucket(storage_root=storage_root)
    except StorageConfigurationError as exc:
        print(f"storage preflight failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except StoragePreflightError as exc:
        print(f"storage preflight failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_PREFLIGHT
    print(f"STORAGE_URI={storage_root.uri}")
    print(f"RUN_LOGS_URI={storage_root.run_logs_uri}")
    print("PREFLIGHT_OK=true")
    return config.EXIT_OK
