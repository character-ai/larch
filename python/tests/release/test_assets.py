"""Release asset packaging and fail-closed collector coverage."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import tarfile
from pathlib import Path
from typing import cast

import pytest

from larch.release import assets

VERSION = "1.2.3"
TAG = f"v{VERSION}"
SOURCE_COMMIT = "a" * 40
IDENTITY = assets.ReleaseIdentity(VERSION, TAG, SOURCE_COMMIT)
REPO_ROOT = Path(__file__).parents[3]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rust-release-assets.yaml"
SETUP_PYTHON = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6"


def _write_license(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    license_path = root / "LICENSE"
    _ = license_path.write_text("test license\n", encoding="utf-8")
    return license_path


def _write_binary(root: Path, version: str = VERSION) -> Path:
    binary = root / "larch"
    _ = binary.write_text(
        f"#!/bin/sh\n[ \"$1\" = --version ] || exit 2\nprintf 'larch {version}\\n'\n",
        encoding="utf-8",
    )
    binary.chmod(0o755)
    return binary


def _package_all(root: Path) -> tuple[Path, Path]:
    license_path = _write_license(root)
    binary = _write_binary(root)
    incoming = root / "incoming"
    for target in assets.TARGETS:
        output = incoming / f"build-{target}"
        _ = assets.package_asset(
            binary=binary,
            license_path=license_path,
            output_dir=output,
            identity=IDENTITY,
            target=target,
        )
    return incoming, license_path


def _collect(root: Path) -> tuple[Path, Path, Path]:
    incoming, license_path = _package_all(root)
    output = root / "release"
    _ = assets.collect_assets(
        input_dir=incoming,
        output_dir=output,
        license_path=license_path,
        identity=IDENTITY,
    )
    return incoming, output, license_path


def _json_object(path: Path) -> dict[str, object]:
    value = cast("object", json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(value, dict)
    return cast("dict[str, object]", value)


def _rewrite_json(path: Path, value: dict[str, object]) -> None:
    _ = path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def test_release_workflow_installs_supported_python_before_cli_in_every_job() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    jobs = workflow.split("\njobs:\n", maxsplit=1)[1]
    job_sections = re.split(r"(?m)^  (?=[a-z][a-z0-9_-]*:\n)", jobs)[1:]
    cli_jobs = [job for job in job_sections if "python3 python/cli.py" in job]

    assert len(cli_jobs) == 3
    assert workflow.count(SETUP_PYTHON) == len(cli_jobs)
    for job in cli_jobs:
        assert job.index(SETUP_PYTHON) < job.index("python3 python/cli.py")
        assert 'python-version: "3.11"' in job


def test_release_workflow_prepares_platform_smoke_test_prerequisites() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    macos_step = workflow.split("- name: Build and smoke-test on macOS", maxsplit=1)[1]
    macos_step = macos_step.split("- name: Build and smoke-test at the GNU baseline", maxsplit=1)[0]
    linux_step = workflow.split("- name: Build and smoke-test at the GNU baseline", maxsplit=1)[1]
    linux_step = linux_step.split("- name: Package deterministic archive", maxsplit=1)[0]

    sign = 'codesign --force --sign - --timestamp=none "$binary"'
    verify = 'codesign --verify --verbose=2 "$binary"'
    cargo_test = 'cargo test --locked --package larch-cli --target "$TARGET"'
    linux_path = 'export PATH="/opt/python/cp311-cp311/bin:/root/.cargo/bin:$PATH"'
    assert macos_step.index(sign) < macos_step.index(verify)
    assert linux_step.index(linux_path) < linux_step.index("python3 --version")
    assert linux_step.index("python3 --version") < linux_step.index(cargo_test)


def test_validate_candidate_requires_matching_plugin_and_workspace_versions(tmp_path: Path) -> None:
    (tmp_path / ".claude-plugin").mkdir()
    _ = (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        '{"version":"1.2.3"}\n', encoding="utf-8"
    )
    _ = (tmp_path / "Cargo.toml").write_text(
        '[workspace]\n[workspace.package]\nversion = "1.2.3"\n', encoding="utf-8"
    )

    assert assets.validate_candidate(tmp_path, TAG, SOURCE_COMMIT) == IDENTITY

    _ = (tmp_path / "Cargo.toml").write_text(
        '[workspace]\n[workspace.package]\nversion = "1.2.4"\n', encoding="utf-8"
    )
    with pytest.raises(assets.AssetError, match="does not match plugin version"):
        _ = assets.validate_candidate(tmp_path, TAG, SOURCE_COMMIT)


def test_package_is_deterministic_and_has_only_normalized_members(tmp_path: Path) -> None:
    license_path = _write_license(tmp_path)
    binary = _write_binary(tmp_path)
    first, _ = assets.package_asset(
        binary=binary,
        license_path=license_path,
        output_dir=tmp_path / "first",
        identity=IDENTITY,
        target=assets.TARGETS[0],
    )
    second, _ = assets.package_asset(
        binary=binary,
        license_path=license_path,
        output_dir=tmp_path / "second",
        identity=IDENTITY,
        target=assets.TARGETS[0],
    )

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        members = archive.getmembers()
    assert [member.name for member in members] == ["larch", "LICENSE"]
    assert [(member.mode, member.uid, member.gid, member.mtime) for member in members] == [
        (0o755, 0, 0, 0),
        (0o644, 0, 0, 0),
    ]


def test_package_rejects_wrong_staged_version(tmp_path: Path) -> None:
    with pytest.raises(assets.AssetError, match="requested version"):
        _ = assets.package_asset(
            binary=_write_binary(tmp_path, "9.9.9"),
            license_path=_write_license(tmp_path),
            output_dir=tmp_path / "output",
            identity=IDENTITY,
            target=assets.TARGETS[0],
        )


def test_collector_emits_exact_validated_asset_set(tmp_path: Path) -> None:
    _, output, license_path = _collect(tmp_path)
    expected = {
        *(f"larch-v{VERSION}-{target}.tar.gz" for target in assets.TARGETS),
        f"larch-v{VERSION}-manifest.json",
        f"larch-v{VERSION}-SHA256SUMS",
    }
    assert {path.name for path in output.iterdir()} == expected
    manifest = _json_object(output / f"larch-v{VERSION}-manifest.json")
    assert manifest["schema_version"] == 1
    assert manifest["plugin_version"] == VERSION
    assert manifest["tag"] == TAG
    assert manifest["source_commit"] == SOURCE_COMMIT
    manifest_assets = manifest["assets"]
    assert isinstance(manifest_assets, list)
    typed_assets = cast("list[dict[str, object]]", manifest_assets)
    assert [entry["target"] for entry in typed_assets] == list(assets.TARGETS)
    assets.validate_assets(output_dir=output, license_path=license_path, identity=IDENTITY)


def test_collector_rejects_missing_input(tmp_path: Path) -> None:
    incoming, license_path = _package_all(tmp_path)
    missing = incoming / f"build-{assets.TARGETS[0]}" / f"larch-v{VERSION}-{assets.TARGETS[0]}.asset.json"
    missing.unlink()

    with pytest.raises(assets.AssetError, match="input asset set mismatch"):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


def test_collector_rejects_duplicate_input(tmp_path: Path) -> None:
    incoming, license_path = _package_all(tmp_path)
    target = assets.TARGETS[0]
    fragment_name = f"larch-v{VERSION}-{target}.asset.json"
    duplicate_dir = incoming / "duplicate"
    duplicate_dir.mkdir()
    _ = shutil.copyfile(incoming / f"build-{target}" / fragment_name, duplicate_dir / fragment_name)

    with pytest.raises(assets.AssetError, match="duplicate asset input"):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


@pytest.mark.parametrize("content", [b"", b"unexpected"])
def test_collector_rejects_empty_or_unexpected_input(tmp_path: Path, content: bytes) -> None:
    incoming, license_path = _package_all(tmp_path)
    unexpected = incoming / "build-extra" / "unexpected.txt"
    unexpected.parent.mkdir()
    _ = unexpected.write_bytes(content)

    match = "must not be empty" if not content else "input asset set mismatch"
    with pytest.raises(assets.AssetError, match=match):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


def test_collector_rejects_fragment_identity_mismatch(tmp_path: Path) -> None:
    incoming, license_path = _package_all(tmp_path)
    target = assets.TARGETS[0]
    fragment = incoming / f"build-{target}" / f"larch-v{VERSION}-{target}.asset.json"
    value = _json_object(fragment)
    value["source_commit"] = "b" * 40
    _rewrite_json(fragment, value)

    with pytest.raises(assets.AssetError, match="source commit mismatch"):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


def test_collector_recomputes_archive_digest(tmp_path: Path) -> None:
    incoming, license_path = _package_all(tmp_path)
    target = assets.TARGETS[0]
    archive = incoming / f"build-{target}" / f"larch-v{VERSION}-{target}.tar.gz"
    _ = archive.write_bytes(archive.read_bytes() + b"tampered")

    with pytest.raises(assets.AssetError, match="size mismatch"):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


def test_collector_rejects_nondeterministic_gzip_metadata_after_digest_rewrite(tmp_path: Path) -> None:
    incoming, license_path = _package_all(tmp_path)
    target = assets.TARGETS[0]
    build_dir = incoming / f"build-{target}"
    archive = build_dir / f"larch-v{VERSION}-{target}.tar.gz"
    data = bytearray(archive.read_bytes())
    data[9] = 3
    _ = archive.write_bytes(data)
    fragment_path = build_dir / f"larch-v{VERSION}-{target}.asset.json"
    fragment = _json_object(fragment_path)
    record = fragment["asset"]
    assert isinstance(record, dict)
    typed_record = cast("dict[str, object]", record)
    typed_record["sha256"] = hashlib.sha256(data).hexdigest()
    _rewrite_json(fragment_path, fragment)

    with pytest.raises(assets.AssetError, match="gzip metadata is not deterministic"):
        _ = assets.collect_assets(
            input_dir=incoming,
            output_dir=tmp_path / "release",
            license_path=license_path,
            identity=IDENTITY,
        )


def test_final_validator_rejects_manifest_and_checksum_tampering(tmp_path: Path) -> None:
    _, output, license_path = _collect(tmp_path)
    manifest_path = output / f"larch-v{VERSION}-manifest.json"
    manifest = _json_object(manifest_path)
    manifest["tag"] = "v9.9.9"
    _rewrite_json(manifest_path, manifest)
    with pytest.raises(assets.AssetError, match="manifest identity mismatch"):
        assets.validate_assets(output_dir=output, license_path=license_path, identity=IDENTITY)

    _, clean_output, clean_license = _collect(tmp_path / "checksum-case")
    checksum_path = clean_output / f"larch-v{VERSION}-SHA256SUMS"
    _ = checksum_path.write_text("0" * 64 + "  wrong\n", encoding="ascii")
    with pytest.raises(assets.AssetError, match="checksum file contents mismatch"):
        assets.validate_assets(output_dir=clean_output, license_path=clean_license, identity=IDENTITY)


def test_final_validator_rejects_extra_assets(tmp_path: Path) -> None:
    _, output, license_path = _collect(tmp_path)
    _ = (output / "extra").write_text("not allowed\n", encoding="utf-8")

    with pytest.raises(assets.AssetError, match="final asset set mismatch"):
        assets.validate_assets(output_dir=output, license_path=license_path, identity=IDENTITY)
