"""Shared release asset naming and identity helpers for remaining Python callers."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_SEMVER_RE: Final = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_COMMIT_RE: Final = re.compile(r"[0-9a-f]{40}")


class AssetError(ValueError):
    """A release asset violates the fail-closed contract."""


@dataclass(frozen=True)
class PlatformContract:
    kind: str
    version: str

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "version": self.version}


@dataclass(frozen=True)
class ReleaseIdentity:
    version: str
    tag: str
    source_commit: str


TARGETS: Final[tuple[str, ...]] = (
    "aarch64-apple-darwin",
    "x86_64-apple-darwin",
    "aarch64-unknown-linux-gnu",
    "x86_64-unknown-linux-gnu",
)
TARGET_CONTRACTS: Final[dict[str, PlatformContract]] = {
    "aarch64-apple-darwin": PlatformContract("macos", "11.0"),
    "x86_64-apple-darwin": PlatformContract("macos", "10.12"),
    "aarch64-unknown-linux-gnu": PlatformContract("glibc", "2.17"),
    "x86_64-unknown-linux-gnu": PlatformContract("glibc", "2.17"),
}


def _identity(version: str, tag: str, source_commit: str) -> ReleaseIdentity:
    if _SEMVER_RE.fullmatch(version) is None:
        raise AssetError(f"invalid plugin version: {version}")
    if tag != f"v{version}":
        raise AssetError(f"tag {tag} does not match plugin version {version}")
    if _COMMIT_RE.fullmatch(source_commit) is None:
        raise AssetError("source commit must be a lowercase 40-character Git object ID")
    return ReleaseIdentity(version=version, tag=tag, source_commit=source_commit)


def release_identity(version: str, tag: str, source_commit: str) -> ReleaseIdentity:
    """Validate and construct the shared release identity."""
    return _identity(version, tag, source_commit)


def _archive_name(identity: ReleaseIdentity, target: str) -> str:
    return f"larch-v{identity.version}-{target}.tar.gz"


def _manifest_name(identity: ReleaseIdentity) -> str:
    return f"larch-v{identity.version}-manifest.json"


def _checksums_name(identity: ReleaseIdentity) -> str:
    return f"larch-v{identity.version}-SHA256SUMS"


def expected_asset_names(identity: ReleaseIdentity) -> tuple[str, ...]:
    """Return the canonical final Release asset allowlist in stable order."""
    archives = tuple(_archive_name(identity, target) for target in TARGETS)
    return (*archives, _manifest_name(identity), _checksums_name(identity))


def _require_regular(path: Path, label: str, *, nonempty: bool = True) -> os.stat_result:
    if path.is_symlink():
        raise AssetError(f"{label} must not be a symlink: {path.name}")
    try:
        metadata = path.stat()
    except OSError as error:
        raise AssetError(f"{label} is not readable: {path.name}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise AssetError(f"{label} must be a regular file: {path.name}")
    if nonempty and metadata.st_size == 0:
        raise AssetError(f"{label} must not be empty: {path.name}")
    return metadata


def sha256_file(path: Path) -> str:
    """Hash a validated regular release asset."""
    _ = _require_regular(path, "release asset")
    return hashlib.sha256(path.read_bytes()).hexdigest()
