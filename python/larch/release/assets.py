"""Build and validate the initial Rust release asset set."""

from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import tempfile
import tomllib
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from larch.core import proc

SCHEMA_VERSION: Final = 1
FRAGMENT_SCHEMA_VERSION: Final = 1
BINARY_PATH: Final = "larch"
LICENSE_PATH: Final = "LICENSE"
_SEMVER_RE: Final = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_COMMIT_RE: Final = re.compile(r"[0-9a-f]{40}")
_SHA256_RE: Final = re.compile(r"[0-9a-f]{64}")
_GZIP_HEADER: Final = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff"

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class AssetError(ValueError):
    """A release asset violates the fail-closed contract."""


@dataclass(frozen=True)
class PlatformContract:
    kind: str
    version: str

    def to_json(self) -> dict[str, JsonValue]:
        return {"kind": self.kind, "version": self.version}


@dataclass(frozen=True)
class ReleaseIdentity:
    version: str
    tag: str
    source_commit: str


@dataclass(frozen=True)
class AssetRecord:
    target: str
    archive: str
    byte_size: int
    sha256: str
    binary_path: str
    minimum_os_or_libc: PlatformContract

    def to_json(self) -> dict[str, JsonValue]:
        return {
            "target": self.target,
            "archive": self.archive,
            "byte_size": self.byte_size,
            "sha256": self.sha256,
            "binary_path": self.binary_path,
            "minimum_os_or_libc": self.minimum_os_or_libc.to_json(),
        }


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
_DEFAULT_RUNNER: Final[proc.Runner] = proc.ProcRunner()


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


def _load_json(path: Path) -> JsonValue:
    _ = _require_regular(path, "JSON file")
    try:
        return cast("JsonValue", json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssetError(f"invalid JSON in {path.name}: {error}") from error


def _object(value: JsonValue, label: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssetError(f"{label} must be a JSON object")
    return value


def _exact_keys(value: dict[str, JsonValue], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise AssetError(f"{label} keys mismatch: missing={missing}, unexpected={unexpected}")


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


def validate_candidate(repo_root: Path, tag: str, source_commit: str) -> ReleaseIdentity:
    root = repo_root.resolve(strict=True)
    plugin_path = root / ".claude-plugin" / "plugin.json"
    cargo_path = root / "Cargo.toml"
    plugin = _object(_load_json(plugin_path), "plugin manifest")
    plugin_version = plugin.get("version")
    if not isinstance(plugin_version, str):
        raise AssetError("plugin manifest version must be a string")
    try:
        cargo = tomllib.loads(cargo_path.read_text(encoding="utf-8"))
        cargo_version = cargo["workspace"]["package"]["version"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        raise AssetError("Cargo.toml has no valid workspace package version") from error
    if not isinstance(cargo_version, str):
        raise AssetError("Cargo workspace version must be a string")
    if cargo_version != plugin_version:
        raise AssetError(
            f"Cargo workspace version {cargo_version} does not match plugin version {plugin_version}"
        )
    return _identity(plugin_version, tag, source_commit)


def _archive_name(identity: ReleaseIdentity, target: str) -> str:
    return f"larch-v{identity.version}-{target}.tar.gz"


def _fragment_name(identity: ReleaseIdentity, target: str) -> str:
    return f"larch-v{identity.version}-{target}.asset.json"


def _manifest_name(identity: ReleaseIdentity) -> str:
    return f"larch-v{identity.version}-manifest.json"


def _checksums_name(identity: ReleaseIdentity) -> str:
    return f"larch-v{identity.version}-SHA256SUMS"


def expected_asset_names(identity: ReleaseIdentity) -> tuple[str, ...]:
    """Return the canonical final Release asset allowlist in stable order."""
    archives = tuple(_archive_name(identity, target) for target in TARGETS)
    return (*archives, _manifest_name(identity), _checksums_name(identity))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a validated regular release asset."""
    _ = _require_regular(path, "release asset")
    return _sha256(path.read_bytes())


def _atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary_name = handle.name
            _ = handle.write(data)
            handle.flush()
            _ = os.fsync(handle.fileno())
        temporary_path = Path(temporary_name)
        temporary_path.chmod(mode)
        _ = temporary_path.replace(path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            with contextlib.suppress(FileNotFoundError):
                Path(temporary_name).unlink()
    written = path.read_bytes()
    if written != data:
        raise AssetError(f"post-write verification failed for {path.name}")


def _tar_info(name: str, size: int, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.type = tarfile.REGTYPE
    return info


def _deterministic_archive(binary: bytes, license_text: bytes) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        _ = archive.addfile(_tar_info(BINARY_PATH, len(binary), 0o755), io.BytesIO(binary))
        _ = archive.addfile(_tar_info(LICENSE_PATH, len(license_text), 0o644), io.BytesIO(license_text))
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=gzip_buffer, mtime=0) as output:
        _ = output.write(tar_buffer.getvalue())
    return gzip_buffer.getvalue()


def _read_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    extracted = archive.extractfile(member)
    if extracted is None:
        raise AssetError(f"archive member is not a file: {member.name}")
    with extracted:
        return extracted.read()


def _validate_archive(path: Path, license_text: bytes) -> None:
    _ = _require_regular(path, "archive")
    data = path.read_bytes()
    tar_data = _decompress_archive(data, path.name)
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r:") as archive:
            members = archive.getmembers()
            if [member.name for member in members] != [BINARY_PATH, LICENSE_PATH]:
                raise AssetError(f"archive member allowlist mismatch: {path.name}")
            expected_modes = (0o755, 0o644)
            for member, expected_mode in zip(members, expected_modes, strict=True):
                if not member.isfile():
                    raise AssetError(f"archive member is not regular: {member.name}")
                if not _member_metadata_is_deterministic(member, expected_mode):
                    raise AssetError(f"archive member metadata is not deterministic: {member.name}")
            binary = _read_member(archive, members[0])
            archived_license = _read_member(archive, members[1])
            content_end = members[-1].offset_data + _tar_padded_size(members[-1].size)
        trailing_tar_data = tar_data[content_end:]
        if len(trailing_tar_data) < tarfile.BLOCKSIZE * 2 or any(trailing_tar_data):
            raise AssetError(f"archive tar padding is not deterministic: {path.name}")
    except (OSError, tarfile.TarError, EOFError) as error:
        raise AssetError(f"invalid archive {path.name}: {error}") from error
    if not binary:
        raise AssetError(f"archive executable is empty: {path.name}")
    if archived_license != license_text:
        raise AssetError(f"archive license does not match repository LICENSE: {path.name}")


def _decompress_archive(data: bytes, name: str) -> bytes:
    if not data.startswith(_GZIP_HEADER):
        raise AssetError(f"archive gzip metadata is not deterministic: {name}")
    try:
        decompressor = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)
        tar_data = decompressor.decompress(data) + decompressor.flush()
    except zlib.error as error:
        raise AssetError(f"invalid archive {name}: {error}") from error
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        raise AssetError(f"archive has trailing or incomplete gzip data: {name}")
    return tar_data


def _member_metadata_is_deterministic(member: tarfile.TarInfo, expected_mode: int) -> bool:
    owner_is_normalized = member.uid == 0 and member.gid == 0
    names_are_empty = member.uname == "" and member.gname == ""
    mode_and_time_are_normalized = member.mtime == 0 and member.mode == expected_mode
    return owner_is_normalized and names_are_empty and mode_and_time_are_normalized and not member.pax_headers


def _tar_padded_size(size: int) -> int:
    blocks = (size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE
    return blocks * tarfile.BLOCKSIZE


def _check_binary_version(
    binary: Path,
    version: str,
    runner: proc.Runner = _DEFAULT_RUNNER,
) -> None:
    metadata = _require_regular(binary, "release executable")
    if metadata.st_mode & 0o111 == 0:
        raise AssetError("release executable is not executable")
    result = runner.run([str(binary), "--version"], cwd=str(binary.parent), timeout=30)
    expected = f"larch {version}\n"
    if result.returncode != 0 or result.stdout != expected or result.stderr != "":
        raise AssetError("release executable did not report the requested version")


def package_asset(
    *,
    binary: Path,
    license_path: Path,
    output_dir: Path,
    identity: ReleaseIdentity,
    target: str,
) -> tuple[Path, Path]:
    if target not in TARGET_CONTRACTS:
        raise AssetError(f"unsupported release target: {target}")
    resolved_binary = binary.resolve(strict=True)
    resolved_license = license_path.resolve(strict=True)
    _check_binary_version(resolved_binary, identity.version)
    _ = _require_regular(resolved_license, "license")
    binary_data = resolved_binary.read_bytes()
    license_text = resolved_license.read_bytes()
    archive_data = _deterministic_archive(binary_data, license_text)
    archive_path = output_dir / _archive_name(identity, target)
    _atomic_write(archive_path, archive_data)
    _validate_archive(archive_path, license_text)
    record = AssetRecord(
        target=target,
        archive=archive_path.name,
        byte_size=len(archive_data),
        sha256=_sha256(archive_data),
        binary_path=BINARY_PATH,
        minimum_os_or_libc=TARGET_CONTRACTS[target],
    )
    fragment: dict[str, JsonValue] = {
        "fragment_schema_version": FRAGMENT_SCHEMA_VERSION,
        "plugin_version": identity.version,
        "tag": identity.tag,
        "source_commit": identity.source_commit,
        "asset": record.to_json(),
    }
    fragment_path = output_dir / _fragment_name(identity, target)
    fragment_data = (json.dumps(fragment, indent=2) + "\n").encode()
    _atomic_write(fragment_path, fragment_data)
    return archive_path, fragment_path


def _parse_contract(value: JsonValue, label: str) -> PlatformContract:
    contract = _object(value, label)
    _exact_keys(contract, {"kind", "version"}, label)
    kind = contract["kind"]
    version = contract["version"]
    if not isinstance(kind, str) or not isinstance(version, str):
        raise AssetError(f"{label} fields must be strings")
    return PlatformContract(kind=kind, version=version)


def _parse_record(value: JsonValue, label: str) -> AssetRecord:
    record = _object(value, label)
    _exact_keys(
        record,
        {"target", "archive", "byte_size", "sha256", "binary_path", "minimum_os_or_libc"},
        label,
    )
    target = record["target"]
    archive = record["archive"]
    byte_size = record["byte_size"]
    sha256 = record["sha256"]
    binary_path = record["binary_path"]
    if not isinstance(target, str) or target not in TARGET_CONTRACTS:
        raise AssetError(f"{label} has an unsupported target")
    if not isinstance(archive, str) or Path(archive).name != archive:
        raise AssetError(f"{label} archive must be a basename")
    if not isinstance(byte_size, int) or isinstance(byte_size, bool) or byte_size <= 0:
        raise AssetError(f"{label} byte_size must be a positive integer")
    if not isinstance(sha256, str) or _SHA256_RE.fullmatch(sha256) is None:
        raise AssetError(f"{label} sha256 is invalid")
    if binary_path != BINARY_PATH:
        raise AssetError(f"{label} binary_path must be {BINARY_PATH}")
    contract = _parse_contract(record["minimum_os_or_libc"], f"{label} minimum contract")
    return AssetRecord(target, archive, byte_size, sha256, BINARY_PATH, contract)


def _expected_input_names(identity: ReleaseIdentity) -> set[str]:
    names: set[str] = set()
    for target in TARGETS:
        names.add(_archive_name(identity, target))
        names.add(_fragment_name(identity, target))
    return names


def _discover_recursive(root: Path) -> dict[str, Path]:
    if root.is_symlink() or not root.is_dir():
        raise AssetError("asset input root must be a real directory")
    discovered: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise AssetError(f"asset input contains a symlink: {path.name}")
        if path.is_dir():
            continue
        _ = _require_regular(path, "asset input")
        if path.name in discovered:
            raise AssetError(f"duplicate asset input: {path.name}")
        discovered[path.name] = path
    return discovered


def _fragment_record(path: Path, identity: ReleaseIdentity, target: str) -> AssetRecord:
    fragment = _object(_load_json(path), "asset fragment")
    _exact_keys(
        fragment,
        {"fragment_schema_version", "plugin_version", "tag", "source_commit", "asset"},
        "asset fragment",
    )
    if fragment["fragment_schema_version"] != FRAGMENT_SCHEMA_VERSION:
        raise AssetError(f"fragment schema version mismatch: {path.name}")
    if fragment["plugin_version"] != identity.version or fragment["tag"] != identity.tag:
        raise AssetError(f"fragment release identity mismatch: {path.name}")
    if fragment["source_commit"] != identity.source_commit:
        raise AssetError(f"fragment source commit mismatch: {path.name}")
    record = _parse_record(fragment["asset"], f"asset fragment {path.name}")
    if record.target != target:
        raise AssetError(f"fragment target mismatch: {path.name}")
    if record.archive != _archive_name(identity, target):
        raise AssetError(f"fragment archive name mismatch: {path.name}")
    if record.minimum_os_or_libc != TARGET_CONTRACTS[target]:
        raise AssetError(f"fragment minimum platform mismatch: {path.name}")
    return record


def _verify_record_file(record: AssetRecord, path: Path, license_text: bytes) -> None:
    metadata = _require_regular(path, "archive")
    data = path.read_bytes()
    if metadata.st_size != record.byte_size:
        raise AssetError(f"archive size mismatch: {path.name}")
    if _sha256(data) != record.sha256:
        raise AssetError(f"archive digest mismatch: {path.name}")
    _validate_archive(path, license_text)


def _manifest(identity: ReleaseIdentity, records: list[AssetRecord]) -> dict[str, JsonValue]:
    return {
        "schema_version": SCHEMA_VERSION,
        "plugin_version": identity.version,
        "tag": identity.tag,
        "source_commit": identity.source_commit,
        "assets": [record.to_json() for record in records],
    }


def _checksum_text(identity: ReleaseIdentity, output_dir: Path) -> str:
    names = [_archive_name(identity, target) for target in TARGETS]
    names.append(_manifest_name(identity))
    return "".join(f"{_sha256((output_dir / name).read_bytes())}  {name}\n" for name in names)


def collect_assets(
    *,
    input_dir: Path,
    output_dir: Path,
    license_path: Path,
    identity: ReleaseIdentity,
) -> list[Path]:
    discovered = _discover_recursive(input_dir)
    expected = _expected_input_names(identity)
    actual = set(discovered)
    if actual != expected:
        raise AssetError(
            f"input asset set mismatch: missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )
    _ = _require_regular(license_path, "license")
    license_text = license_path.read_bytes()
    records: list[AssetRecord] = []
    output_names = {_archive_name(identity, target) for target in TARGETS}
    output_names.update({_manifest_name(identity), _checksums_name(identity)})
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise AssetError("asset output root must be a real directory")
        stale = {path.name for path in output_dir.iterdir()} - output_names
        if stale:
            raise AssetError(f"asset output contains unexpected entries: {sorted(stale)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        record = _fragment_record(discovered[_fragment_name(identity, target)], identity, target)
        archive_input = discovered[record.archive]
        _verify_record_file(record, archive_input, license_text)
        _atomic_write(output_dir / record.archive, archive_input.read_bytes())
        records.append(record)
    manifest_path = output_dir / _manifest_name(identity)
    manifest_data = (json.dumps(_manifest(identity, records), indent=2) + "\n").encode()
    _atomic_write(manifest_path, manifest_data)
    checksums_path = output_dir / _checksums_name(identity)
    _atomic_write(checksums_path, _checksum_text(identity, output_dir).encode())
    validate_assets(output_dir=output_dir, license_path=license_path, identity=identity)
    return [*(output_dir / _archive_name(identity, target) for target in TARGETS), manifest_path, checksums_path]


def _discover_output(root: Path, expected: set[str]) -> dict[str, Path]:
    if root.is_symlink() or not root.is_dir():
        raise AssetError("asset output root must be a real directory")
    paths = list(root.iterdir())
    if any(path.is_dir() for path in paths):
        raise AssetError("final asset set must not contain directories")
    discovered: dict[str, Path] = {}
    for path in paths:
        _ = _require_regular(path, "final asset")
        discovered[path.name] = path
    actual = set(discovered)
    if actual != expected:
        raise AssetError(
            f"final asset set mismatch: missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
        )
    return discovered


def _parse_manifest(path: Path, identity: ReleaseIdentity) -> list[AssetRecord]:
    manifest = _object(_load_json(path), "release manifest")
    _exact_keys(
        manifest,
        {"schema_version", "plugin_version", "tag", "source_commit", "assets"},
        "release manifest",
    )
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise AssetError("release manifest schema version mismatch")
    if manifest["plugin_version"] != identity.version or manifest["tag"] != identity.tag:
        raise AssetError("release manifest identity mismatch")
    if manifest["source_commit"] != identity.source_commit:
        raise AssetError("release manifest source commit mismatch")
    asset_values = manifest["assets"]
    if not isinstance(asset_values, list):
        raise AssetError("release manifest assets must be an array")
    records = [_parse_record(value, f"release manifest asset {index}") for index, value in enumerate(asset_values)]
    if [record.target for record in records] != list(TARGETS):
        raise AssetError("release manifest targets are missing, duplicated, unexpected, or out of order")
    return records


def validate_assets(*, output_dir: Path, license_path: Path, identity: ReleaseIdentity) -> None:
    expected = {_archive_name(identity, target) for target in TARGETS}
    expected.update({_manifest_name(identity), _checksums_name(identity)})
    discovered = _discover_output(output_dir, expected)
    _ = _require_regular(license_path, "license")
    license_text = license_path.read_bytes()
    records = _parse_manifest(discovered[_manifest_name(identity)], identity)
    for record in records:
        if record.archive != _archive_name(identity, record.target):
            raise AssetError(f"release manifest archive name mismatch: {record.target}")
        if record.minimum_os_or_libc != TARGET_CONTRACTS[record.target]:
            raise AssetError(f"release manifest minimum platform mismatch: {record.target}")
        _verify_record_file(record, discovered[record.archive], license_text)
    expected_checksums = _checksum_text(identity, output_dir)
    try:
        actual_checksums = discovered[_checksums_name(identity)].read_text(encoding="ascii")
    except (OSError, UnicodeError) as error:
        raise AssetError("checksum file must be readable ASCII") from error
    if actual_checksums != expected_checksums:
        raise AssetError("checksum file contents mismatch")


def _identity_arguments(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument("--version", required=True)
    _ = parser.add_argument("--tag", required=True)
    _ = parser.add_argument("--source-commit", required=True)


def _run_cli(function: object, args: argparse.Namespace) -> int:
    try:
        if function is package_asset:
            identity = _identity(args.version, args.tag, args.source_commit)
            _ = package_asset(
                binary=Path(args.binary),
                license_path=Path(args.license),
                output_dir=Path(args.output_dir),
                identity=identity,
                target=args.target,
            )
        elif function is collect_assets:
            identity = _identity(args.version, args.tag, args.source_commit)
            _ = collect_assets(
                input_dir=Path(args.input_dir),
                output_dir=Path(args.output_dir),
                license_path=Path(args.license),
                identity=identity,
            )
        elif function is validate_assets:
            identity = _identity(args.version, args.tag, args.source_commit)
            validate_assets(
                output_dir=Path(args.asset_dir),
                license_path=Path(args.license),
                identity=identity,
            )
        else:
            raise AssertionError("unknown release asset command")
    except (AssetError, OSError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    return 0


def candidate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release asset-candidate")
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--tag", required=True)
    _ = parser.add_argument("--source-commit", required=True)
    args = parser.parse_args(argv)
    try:
        identity = validate_candidate(Path(args.repo_root), args.tag, args.source_commit)
    except (AssetError, OSError) as error:
        print(f"ERROR={error}", file=sys.stderr)
        return 1
    print(f"VERSION={identity.version}")
    print(f"SOURCE_COMMIT={identity.source_commit}")
    return 0


def package_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release package-asset")
    _identity_arguments(parser)
    _ = parser.add_argument("--target", required=True, choices=TARGETS)
    _ = parser.add_argument("--binary", required=True)
    _ = parser.add_argument("--license", required=True)
    _ = parser.add_argument("--output-dir", required=True)
    return _run_cli(package_asset, parser.parse_args(argv))


def collect_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release collect-assets")
    _identity_arguments(parser)
    _ = parser.add_argument("--input-dir", required=True)
    _ = parser.add_argument("--output-dir", required=True)
    _ = parser.add_argument("--license", required=True)
    return _run_cli(collect_assets, parser.parse_args(argv))


def validate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release validate-assets")
    _identity_arguments(parser)
    _ = parser.add_argument("--asset-dir", required=True)
    _ = parser.add_argument("--license", required=True)
    return _run_cli(validate_assets, parser.parse_args(argv))
