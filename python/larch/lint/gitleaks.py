"""Install and run the repository's checksum-pinned Gitleaks release binary."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import io
import os
import platform
import sys
import tarfile
import tempfile
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from larch.core import proc

GITLEAKS_VERSION: Final = "8.18.4"
_DOWNLOAD_MAX_BYTES: Final = 16 * 1024 * 1024
_BINARY_MAX_BYTES: Final = 32 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS: Final = 30.0
_VERSION_TIMEOUT_SECONDS: Final = 10.0
_DOWNLOAD_RETRY_DELAYS_SECONDS: Final = (1.0, 2.0, 4.0, 8.0)
_RELEASE_ROOT: Final = f"https://github.com/gitleaks/gitleaks/releases/download/v{GITLEAKS_VERSION}"


@dataclass(frozen=True)
class ReleaseArtifact:
    """Pinned archive and extracted-binary identities for one platform."""

    filename: str
    archive_sha256: str
    binary_sha256: str


_ARTIFACTS: Final[dict[tuple[str, str], ReleaseArtifact]] = {
    ("darwin", "arm64"): ReleaseArtifact(
        filename=f"gitleaks_{GITLEAKS_VERSION}_darwin_arm64.tar.gz",
        archive_sha256="a480d8593acd8215b22402cf0f3f88b01dcd3610c63b5391db640f7767e62104",
        binary_sha256="a86787a498e702f8820fc73c219ca44ecdf1f415eed8daf922888ffd6c4cf680",
    ),
    ("darwin", "x64"): ReleaseArtifact(
        filename=f"gitleaks_{GITLEAKS_VERSION}_darwin_x64.tar.gz",
        archive_sha256="1a69e5666b13cd374889cbcb1939ed1573b63b551251283d5d2329a53cf58e2f",
        binary_sha256="3f83ea726b8f10c16dfa7ea08c73d1474ddbfe24db4a00e6764ec9abac05e19e",
    ),
    ("linux", "arm64"): ReleaseArtifact(
        filename=f"gitleaks_{GITLEAKS_VERSION}_linux_arm64.tar.gz",
        archive_sha256="bf5f7f466ebfade1296c8bd32cf7d3f592c2aa78836aa9980ffbe2cadca7a861",
        binary_sha256="fc286fab02c3a0ba80670fc9f8cb1b495a2f62eb953d26113cfa3562f76b340b",
    ),
    ("linux", "x64"): ReleaseArtifact(
        filename=f"gitleaks_{GITLEAKS_VERSION}_linux_x64.tar.gz",
        archive_sha256="ba6dbb656933921c775ee5a2d1c13a91046e7952e9d919f9bac4cec61d628e7d",
        binary_sha256="46a05260e7cce527f132cb618de59d22262b8b5eb47f66c288447b95c7a98b7e",
    ),
}

Fetcher = Callable[[str], bytes]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _platform_key(system: str, machine: str) -> tuple[str, str]:
    normalized_system = system.strip().lower()
    normalized_machine = machine.strip().lower()
    machine_aliases: dict[str, str] = {
        "aarch64": "arm64",
        "amd64": "x64",
        "arm64": "arm64",
        "x86_64": "x64",
    }
    architecture = machine_aliases.get(normalized_machine, normalized_machine)
    key = (normalized_system, architecture)
    if key not in _ARTIFACTS:
        raise ValueError(f"unsupported gitleaks platform: {system}/{machine}")
    return key


def _default_cache_root() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(xdg_cache).expanduser() if xdg_cache else Path.home() / ".cache"
    return base / "larch" / "tools" / "gitleaks"


def _fetch_release(url: str) -> bytes:
    request = urllib.request.Request(  # noqa: S310 - caller constructs a fixed HTTPS release URL
        url,
        headers={"User-Agent": "larch-gitleaks-bootstrap"},
    )
    for attempt in range(len(_DOWNLOAD_RETRY_DELAYS_SECONDS) + 1):
        try:
            with urllib.request.urlopen(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed HTTPS release root plus pinned checksum
                payload = response.read(_DOWNLOAD_MAX_BYTES + 1)
        except (http.client.HTTPException, OSError):
            if attempt >= len(_DOWNLOAD_RETRY_DELAYS_SECONDS):
                raise
            time.sleep(_DOWNLOAD_RETRY_DELAYS_SECONDS[attempt])
            continue
        if len(payload) > _DOWNLOAD_MAX_BYTES:
            raise ValueError(f"gitleaks release archive exceeds {_DOWNLOAD_MAX_BYTES} bytes")
        return payload
    raise AssertionError("download retry loop exhausted without returning or raising")


def _extract_binary(archive: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        try:
            member = bundle.getmember("gitleaks")
        except KeyError as exc:
            raise ValueError("gitleaks release archive has no gitleaks binary") from exc
        if not member.isfile() or member.size <= 0 or member.size > _BINARY_MAX_BYTES:
            raise ValueError("gitleaks release archive has an invalid binary member")
        stream = bundle.extractfile(member)
        if stream is None:
            raise ValueError("gitleaks release binary could not be read")
        binary = stream.read(_BINARY_MAX_BYTES + 1)
    if len(binary) != member.size or len(binary) > _BINARY_MAX_BYTES:
        raise ValueError("gitleaks release binary size does not match its archive member")
    return binary


def ensure_gitleaks_binary(
    *,
    cache_root: Path,
    system: str,
    machine: str,
    fetcher: Fetcher = _fetch_release,
) -> Path:
    """Return an identity-verified release binary, downloading it when needed."""
    platform_key = _platform_key(system, machine)
    artifact = _ARTIFACTS[platform_key]
    destination = cache_root / GITLEAKS_VERSION / "-".join(platform_key) / "gitleaks"
    if (
        destination.is_file()
        and not destination.is_symlink()
        and _sha256_path(destination) == artifact.binary_sha256
    ):
        _ = destination.chmod(0o755)
        return destination

    archive = fetcher(f"{_RELEASE_ROOT}/{artifact.filename}")
    if _sha256(archive) != artifact.archive_sha256:
        raise ValueError(f"checksum mismatch for {artifact.filename}")
    binary = _extract_binary(archive)
    if _sha256(binary) != artifact.binary_sha256:
        raise ValueError(f"extracted binary checksum mismatch for {artifact.filename}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="install-", dir=destination.parent) as temp_dir:
        staged = Path(temp_dir) / "gitleaks"
        _ = staged.write_bytes(binary)
        _ = staged.chmod(0o755)
        _ = staged.replace(destination)
    return destination


def _emit_result(result: proc.CommandResult) -> None:
    if result.stdout:
        _ = sys.stdout.write(result.stdout)
    if result.stderr:
        _ = sys.stderr.write(result.stderr)


def _scanner_argv(
    *,
    binary: Path,
    mode: str,
    config_path: Path,
    log_opts: str | None,
) -> tuple[str, ...]:
    base = (
        str(binary),
        "detect",
        "--source",
        ".",
        "--config",
        str(config_path),
        "--redact",
        "--no-banner",
    )
    if mode == "working-tree":
        return (*base, "--no-git")
    if mode == "history":
        if not log_opts:
            raise ValueError("--log-opts is required for a history scan")
        return (*base, "--log-opts", log_opts)
    raise ValueError(f"unsupported gitleaks scan mode: {mode}")


def gitleaks_main(
    argv: Sequence[str] | None = None,
    *,
    runner: proc.Runner | None = None,
    fetcher: Fetcher = _fetch_release,
    system: str | None = None,
    machine: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="cli.py checks gitleaks")
    _ = parser.add_argument("--mode", choices=("verify", "working-tree", "history"), required=True)
    _ = parser.add_argument("--log-opts")
    _ = parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    _ = parser.add_argument("--cache-dir", type=Path, default=_default_cache_root())
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    config_path = repo_root / ".gitleaks.toml"
    if not config_path.is_file() or config_path.is_symlink():
        print(f"ERROR: required gitleaks config is not a regular file: {config_path}", file=sys.stderr)
        return 2

    active_runner = runner or proc.ProcRunner()
    try:
        binary = ensure_gitleaks_binary(
            cache_root=args.cache_dir.resolve(),
            system=system or platform.system(),
            machine=machine or platform.machine(),
            fetcher=fetcher,
        )
        version_result = active_runner.run((str(binary), "version"), timeout=_VERSION_TIMEOUT_SECONDS)
        if version_result.returncode != 0 or version_result.stdout.strip() != GITLEAKS_VERSION:
            _emit_result(version_result)
            print(f"ERROR: expected gitleaks version {GITLEAKS_VERSION}", file=sys.stderr)
            return 2
        if args.mode == "verify":
            _emit_result(version_result)
            return 0
        scanner_argv = _scanner_argv(
            binary=binary,
            mode=args.mode,
            config_path=config_path,
            log_opts=args.log_opts,
        )
    except (http.client.HTTPException, OSError, tarfile.TarError, ValueError) as exc:
        print(f"ERROR: could not prepare gitleaks {GITLEAKS_VERSION}: {exc}", file=sys.stderr)
        return 2

    scan_result = active_runner.run(scanner_argv, cwd=str(repo_root), stdout=1, stderr=2)
    _emit_result(scan_result)
    return scan_result.returncode
