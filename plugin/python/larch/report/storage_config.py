"""Repository-owned storage configuration and derived tool namespace."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast
from urllib.parse import SplitResult, urlsplit

from larch.core import config, proc
from larch.core.repo_roots import consumer_repo_root
from larch.report.object_store import ObjectStoreError, object_store_for

_ASCII_CONTROL_CHARACTER_MAX: Final = 32
_ASCII_DELETE: Final = 127
_SHA256_HEX_LENGTH: Final = 64
_GIT_COMMIT_HEX_LENGTH: Final = 40
_TOOL_REPOSITORY_SUFFIX_PARTS: Final = 2
_CLIENT_REPO_RE: Final = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")
_SCP_REMOTE_RE: Final = re.compile(
    r"^(?:(?P<user>[A-Za-z0-9._-]+)@)?(?P<host>[^/:@\s]+):(?P<path>[^:\s]+)$"
)


class StorageConfigurationError(ValueError):
    """The repository's storage configuration or identity is invalid."""


class StoragePreflightError(RuntimeError):
    """The configured tool and repository prefix cannot be listed."""


@dataclass(frozen=True)
class StorageBase:
    """Validated provider, bucket, and optional base prefix."""

    scheme: str
    bucket: str
    prefix: str = ""

    @property
    def uri(self) -> str:
        """Return the canonical configured base URI."""
        suffix: str = f"/{self.prefix}" if self.prefix else ""
        return f"{self.scheme}://{self.bucket}{suffix}"

    @property
    def bucket_uri(self) -> str:
        """Return the provider bucket root."""
        return f"{self.scheme}://{self.bucket}"


@dataclass(frozen=True)
class ToolRepositoryStorage:
    """The fixed larch namespace for one Git-origin-derived repository."""

    base: StorageBase
    client_repo: str

    @property
    def scheme(self) -> str:
        return self.base.scheme

    @property
    def bucket(self) -> str:
        return self.base.bucket

    @property
    def prefix(self) -> str:
        parts: tuple[str, ...] = tuple(
            part
            for part in (self.base.prefix, config.LARCH_TOOL_NAME, self.client_repo)
            if part
        )
        return "/".join(parts)

    @property
    def uri(self) -> str:
        """Return the canonical tool and client-repository root."""
        return f"{self.scheme}://{self.bucket}/{self.prefix}"

    @property
    def storage_origin_id(self) -> str:
        """Bind local mutable state to the complete canonical remote origin."""
        return hashlib.sha256(self.uri.encode("utf-8")).hexdigest()

    def data_uri(self, data_type: str) -> str:
        """Return one validated child data namespace."""
        child: str = _validated_path_component(data_type, label="data type")
        return f"{self.uri}/{child}/"

    @property
    def run_logs_uri(self) -> str:
        """Return the deterministic remote root for run archives."""
        return self.data_uri(config.RUN_LOGS_DATA_TYPE)


@dataclass(frozen=True)
class LegacyMigrationDescriptor:
    """Operator-supplied trust anchor for one historical migration inventory."""

    schema: str
    source_commit: str
    storage_root: str
    inventory_key: str
    inventory_sha256: str


def run_log_reference(*, repo_root: Path | None, skill: str, run_id: str) -> str:
    """Render a provider-neutral run identity for public summaries."""
    provider: str = "unknown"
    if repo_root is not None:
        with contextlib.suppress(StorageConfigurationError):
            provider = load_tool_repository_storage(repo_root=repo_root).scheme
    return f"provider `{provider}`, skill `{skill}`, run ID `{run_id}`"


def _validated_bucket(parsed: SplitResult) -> str:
    """Return the exact plain bucket authority with no credentials or port."""
    if (
        parsed.username is not None
        or parsed.password is not None
        or "@" in parsed.netloc
    ):
        raise StorageConfigurationError(
            "[larch].storage_base_uri must not contain credentials"
        )
    try:
        port: int | None = parsed.port
    except ValueError as exc:
        raise StorageConfigurationError(
            "[larch].storage_base_uri must contain a plain bucket name without a port"
        ) from exc
    bucket: str = parsed.netloc
    if (
        not bucket
        or port is not None
        or ":" in bucket
        or "\\" in bucket
        or any(
            character.isspace()
            or ord(character) < _ASCII_CONTROL_CHARACTER_MAX
            or ord(character) == _ASCII_DELETE
            for character in bucket
        )
    ):
        raise StorageConfigurationError(
            "[larch].storage_base_uri must contain a plain bucket name without a port"
        )
    return bucket


def _validated_prefix(path: str) -> str:
    """Return an exact optional base prefix."""
    if not path:
        return ""
    if not path.startswith("/") or path.endswith("/"):
        raise StorageConfigurationError(
            "[larch].storage_base_uri must not have a trailing slash"
        )
    prefix_segments: list[str] = path[1:].split("/")
    if any(not segment or segment in {".", ".."} for segment in prefix_segments):
        raise StorageConfigurationError(
            "[larch].storage_base_uri prefix must not contain empty, '.' or '..' segments"
        )
    if any(
        "\\" in segment
        or any(
            character.isspace()
            or ord(character) < _ASCII_CONTROL_CHARACTER_MAX
            or ord(character) == _ASCII_DELETE
            for character in segment
        )
        for segment in prefix_segments
    ):
        raise StorageConfigurationError(
            "[larch].storage_base_uri prefix must not contain whitespace or control characters"
        )
    return "/".join(prefix_segments)


def parse_storage_base_uri(raw_uri: str) -> StorageBase:
    """Validate a base URI without adding the tool or repository namespace."""
    if not raw_uri or raw_uri != raw_uri.strip():
        raise StorageConfigurationError(
            "[larch].storage_base_uri must be a non-empty URI without surrounding whitespace"
        )
    parsed: SplitResult = urlsplit(raw_uri)
    if (
        parsed.scheme not in config.STORAGE_URI_SCHEMES
        or not raw_uri.startswith(f"{parsed.scheme}://")
    ):
        accepted: str = ", ".join(
            f"{scheme}://" for scheme in config.STORAGE_URI_SCHEMES
        )
        raise StorageConfigurationError(
            f"[larch].storage_base_uri must use one of: {accepted}"
        )
    if parsed.query or parsed.fragment:
        raise StorageConfigurationError(
            "[larch].storage_base_uri must not contain a query or fragment"
        )
    return StorageBase(
        scheme=parsed.scheme,
        bucket=_validated_bucket(parsed),
        prefix=_validated_prefix(parsed.path),
    )


def parse_tool_repository_uri(
    raw_uri: str, *, expected_client_repo: str | None = None
) -> ToolRepositoryStorage:
    """Rehydrate a canonical persisted tool-repository URI."""
    parsed: SplitResult = urlsplit(raw_uri)
    if parsed.scheme not in config.STORAGE_URI_SCHEMES:
        raise StorageConfigurationError(
            "persisted tool repository URI has an invalid scheme"
        )
    bucket: str = _validated_bucket(parsed)
    prefix: str = _validated_prefix(parsed.path)
    parts: list[str] = prefix.split("/")
    if (
        len(parts) < _TOOL_REPOSITORY_SUFFIX_PARTS
        or parts[-2] != config.LARCH_TOOL_NAME
    ):
        raise StorageConfigurationError(
            "persisted tool repository URI has an invalid namespace"
        )
    client_repo: str = validate_client_repo(parts[-1])
    if expected_client_repo is not None and client_repo != expected_client_repo:
        raise StorageConfigurationError("persisted tool repository identity changed")
    base_prefix: str = "/".join(parts[:-2])
    storage: ToolRepositoryStorage = ToolRepositoryStorage(
        StorageBase(parsed.scheme, bucket, base_prefix), client_repo
    )
    if storage.uri != raw_uri:
        raise StorageConfigurationError(
            "persisted tool repository URI is not canonical"
        )
    return storage


def _load_repository_config(repo_root: Path) -> dict[str, object]:
    config_path: Path = repo_root / config.STORAGE_CONFIG_RELPATH
    repo_label: str = repo_root.name or str(repo_root)
    if config_path.is_symlink():
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: refusing symlink in Git repository {repo_label}"
        )
    if not config_path.is_file():
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: missing required file in Git repository "
            f"{repo_label}; add [larch] with storage_base_uri"
        )
    try:
        with config_path.open("rb") as handle:
            return cast("dict[str, object]", tomllib.load(handle))
    except OSError as exc:
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: cannot read configuration in Git repository "
            f"{repo_label}; add readable [larch] with storage_base_uri"
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: malformed TOML in Git repository {repo_label}"
        ) from exc


def _configured_storage_base(
    *, repo_root: Path, environ: Mapping[str, str]
) -> StorageBase:
    raw_data: dict[str, object] = _load_repository_config(repo_root)
    raw_larch: object = raw_data.get(config.LARCH_TOOL_NAME)
    repo_label: str = repo_root.name or str(repo_root)
    if not isinstance(raw_larch, dict):
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: missing required [larch] table; "
            f"larch cannot run in Git repository {repo_label}; add [larch] with storage_base_uri"
        )
    larch_table: dict[str, object] = cast("dict[str, object]", raw_larch)
    if frozenset(larch_table) != frozenset({config.STORAGE_BASE_URI_FIELD}):
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: [larch] must contain only "
            f"{config.STORAGE_BASE_URI_FIELD}"
        )
    configured: object = larch_table.get(config.STORAGE_BASE_URI_FIELD)
    if not isinstance(configured, str):
        raise StorageConfigurationError(
            f"{config.STORAGE_CONFIG_RELPATH}: "
            f"[larch].{config.STORAGE_BASE_URI_FIELD} must be a string"
        )
    legacy_override: str = environ.get(config.ENV_LARCH_LOGS_URI, "")
    if legacy_override:
        raise StorageConfigurationError(
            f"{config.ENV_LARCH_LOGS_URI} is no longer supported; remove it and use "
            f"{config.ENV_LARCH_STORAGE_BASE_URI} for a base-only override"
        )
    override: str = environ.get(config.ENV_LARCH_STORAGE_BASE_URI, "")
    return parse_storage_base_uri(override or configured)


def validate_client_repo(value: str) -> str:
    """Validate the closed lowercase client-repository slug."""
    if not _CLIENT_REPO_RE.fullmatch(value) or value in {".", ".."}:
        raise StorageConfigurationError(
            "Git remote.origin.url did not yield a valid lowercase repository slug; "
            "set remote.origin.url to a standard HTTPS, SSH, or SCP-like repository URL"
        )
    return value


def _repository_leaf(remote: str) -> str:
    """Extract the final path component without returning remote text in errors."""
    if (
        not remote
        or remote != remote.strip()
        or any(
            ord(character) < _ASCII_CONTROL_CHARACTER_MAX
            or ord(character) == _ASCII_DELETE
            for character in remote
        )
    ):
        raise StorageConfigurationError(
            "remote.origin.url is missing or malformed; set it to a standard HTTPS, SSH, "
            "or SCP-like repository URL"
        )
    path: str
    if "://" in remote:
        parsed: SplitResult = urlsplit(remote)
        try:
            has_port: bool = parsed.port is not None
        except ValueError:
            has_port = True
        unsupported_shape: bool = (
            parsed.scheme not in {"https", "ssh"}
            or not parsed.netloc
            or not parsed.path.startswith("/")
        )
        credential_bearing: bool = parsed.password is not None or (
            parsed.scheme == "https" and parsed.username is not None
        )
        decorated: bool = has_port or bool(parsed.query) or bool(parsed.fragment)
        if (
            unsupported_shape
            or credential_bearing
            or decorated
        ):
            raise StorageConfigurationError(
                "remote.origin.url uses unsupported or credential-bearing syntax; "
                "set a credential-free standard HTTPS or SSH repository URL"
            )
        path = parsed.path
    else:
        match: re.Match[str] | None = _SCP_REMOTE_RE.fullmatch(remote)
        if match is None:
            raise StorageConfigurationError(
                "remote.origin.url uses unsupported or ambiguous syntax; set a standard "
                "HTTPS, SSH, or SCP-like repository URL"
            )
        path = match.group("path")
    path_segments: list[str] = path.lstrip("/").split("/")
    if (
        path.endswith("/")
        or "//" in path
        or any(not segment or segment in {".", ".."} for segment in path_segments)
    ):
        raise StorageConfigurationError(
            "remote.origin.url has an ambiguous repository path; set a standard repository URL"
    )
    leaf: str = path_segments[-1].removesuffix(".git")
    lowered: str = leaf.lower()
    return validate_client_repo(lowered)


def derive_client_repo(
    *,
    repo_root: Path,
    runner: proc.Runner | None = None,
) -> str:
    """Read the local origin and derive its canonical repository slug."""
    active_runner: proc.Runner = proc.ProcRunner() if runner is None else runner
    try:
        result: proc.CommandResult = active_runner.run(
            [
                "git",
                "-C",
                str(repo_root),
                "config",
                "--local",
                "--get",
                "remote.origin.url",
            ],
            timeout=config.STORAGE_GIT_IDENTITY_TIMEOUT_SEC,
            check=False,
        )
    except OSError as exc:
        raise StorageConfigurationError(
            "could not read local remote.origin.url; configure an origin repository remote"
        ) from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise StorageConfigurationError(
            "local remote.origin.url is missing; configure an origin repository remote"
        )
    return _repository_leaf(result.stdout.strip())


def load_tool_repository_storage(
    *,
    repo_root: Path,
    environ: Mapping[str, str] | None = None,
    runner: proc.Runner | None = None,
) -> ToolRepositoryStorage:
    """Require repository config and derive the fixed larch/client namespace."""
    environment: Mapping[str, str] = os.environ if environ is None else environ
    base: StorageBase = _configured_storage_base(
        repo_root=repo_root, environ=environment
    )
    client_repo: str = derive_client_repo(repo_root=repo_root, runner=runner)
    return ToolRepositoryStorage(base=base, client_repo=client_repo)


def discover_tool_repository_storage(
    *,
    start: Path | None = None,
    environ: Mapping[str, str] | None = None,
    root_resolver: Callable[[Path | None], Path | None] = consumer_repo_root,
    runner: proc.Runner | None = None,
) -> ToolRepositoryStorage:
    """Resolve the startup Git root, then pin config and origin identity."""
    repo_root: Path | None = root_resolver(start)
    if repo_root is None:
        location: str = str(start) if start is not None else str(Path.cwd())
        raise StorageConfigurationError(
            f"could not discover a Git repository root from startup CWD {location}"
        )
    return load_tool_repository_storage(
        repo_root=repo_root, environ=environ, runner=runner
    )


def _validated_path_component(value: str, *, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(
            character.isspace()
            or ord(character) < _ASCII_CONTROL_CHARACTER_MAX
            or ord(character) == _ASCII_DELETE
            for character in value
        )
    ):
        raise StorageConfigurationError(f"invalid {label}")
    return value


def parse_legacy_migration_descriptor(
    raw_descriptor: object, *, storage_root: StorageBase
) -> LegacyMigrationDescriptor:
    """Validate an explicit operator migration descriptor without config discovery."""
    if not isinstance(raw_descriptor, dict):
        raise StorageConfigurationError("legacy migration descriptor must be a table")
    descriptor: dict[str, object] = cast("dict[str, object]", raw_descriptor)
    required: frozenset[str] = frozenset(
        {
            "inventory_key",
            "inventory_sha256",
            "schema",
            "source_commit",
            "storage_root",
        }
    )
    if frozenset(descriptor) != required or not all(
        isinstance(descriptor[key], str) for key in required
    ):
        raise StorageConfigurationError(
            "legacy migration descriptor has invalid fields"
        )
    values: dict[str, str] = cast("dict[str, str]", descriptor)
    digest: str = values["inventory_sha256"]
    commit: str = values["source_commit"]
    inventory_key: str = values["inventory_key"]
    if len(digest) != _SHA256_HEX_LENGTH or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise StorageConfigurationError("legacy inventory SHA-256 is malformed")
    if len(commit) != _GIT_COMMIT_HEX_LENGTH or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise StorageConfigurationError("legacy source commit is malformed")
    key_parts: list[str] = inventory_key.split("/")
    if (
        inventory_key.startswith("/")
        or not inventory_key.endswith(".json")
        or any(not part or part in {".", ".."} for part in key_parts)
    ):
        raise StorageConfigurationError("legacy inventory key is unsafe")
    if values["storage_root"] != storage_root.uri:
        raise StorageConfigurationError(
            "legacy migration descriptor does not match the explicit storage root"
        )
    if not values["schema"]:
        raise StorageConfigurationError("legacy migration schema is empty")
    return LegacyMigrationDescriptor(
        schema=values["schema"],
        source_commit=commit,
        storage_root=values["storage_root"],
        inventory_key=inventory_key,
        inventory_sha256=digest,
    )


def preflight_tool_repository(
    *,
    storage: ToolRepositoryStorage,
    environ: Mapping[str, str] | None = None,
    runner: proc.Runner | None = None,
) -> None:
    """List at most one object under the exact tool/repository prefix."""
    try:
        object_store_for(storage, environ=environ, runner=runner).preflight_prefix()
    except ObjectStoreError as exc:
        if storage.scheme == "gs" and exc.operation == "checkout-build":
            raise StoragePreflightError(
                "GCS storage preflight could not build the local checkout transport; "
                "verify Cargo is installed and the locked larch-cli release build succeeds"
            ) from exc
        if exc.kind.value == "configuration" and storage.scheme in {"s3", "r2"}:
            raise StoragePreflightError(
                f"AWS CLI is required for {storage.scheme.upper()} storage preflight; "
                f"install '{config.AWS_CLI}' and retry"
            ) from exc
        raise StoragePreflightError(
            f"{storage.scheme} prefix preflight failed for the configured larch repository "
            "namespace; verify provider credentials and prefix-scoped list access"
        ) from exc


def storage_preflight_main(argv: Sequence[str]) -> int:
    """Run the configured provider's prefix-scoped startup preflight."""
    parser = argparse.ArgumentParser(prog="cli.py run-log storage-preflight")
    _ = parser.add_argument("--repo-root", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else config.EXIT_USAGE
    start: Path | None = Path(args.repo_root) if args.repo_root else None
    try:
        storage: ToolRepositoryStorage = discover_tool_repository_storage(start=start)
        preflight_tool_repository(storage=storage)
    except StorageConfigurationError as exc:
        print(f"storage preflight failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_CONFIG
    except StoragePreflightError as exc:
        print(f"storage preflight failed: {exc}", file=sys.stderr)
        return config.EXIT_STORAGE_PREFLIGHT
    print(f"STORAGE_BASE_URI={storage.base.uri}")
    print(f"CLIENT_REPO={storage.client_repo}")
    print(f"TOOL_REPO_URI={storage.uri}")
    print(f"RUN_LOGS_URI={storage.run_logs_uri}")
    print("PREFLIGHT_OK=true")
    return config.EXIT_OK
