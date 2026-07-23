"""Tests for repository storage-root configuration and S3 preflight."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from larch.core import config, proc
from larch.report import storage_config


def _write_config(repo_root: Path, uri: str) -> None:
    _ = (repo_root / "config.toml").write_text(f'[logs]\nuri = "{uri}"\n', encoding="utf-8")


def _result(*, returncode: int, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(
        argv=(), returncode=returncode, stdout=stdout, stderr=stderr, duration=0.0
    )


class FakeRunner:
    """Capture the preflight command without invoking the AWS CLI."""

    def __init__(self, result: proc.CommandResult) -> None:
        self.result = result
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> proc.CommandResult:
        _ = timeout, cwd, env, check, stdout, stderr
        self.calls.append(tuple(argv))
        return self.result


def test_load_storage_root_derives_run_logs_uri(tmp_path: Path) -> None:
    _write_config(tmp_path, "s3://zhupanov/larch")

    storage_root = storage_config.load_storage_root(repo_root=tmp_path, environ={})

    assert storage_root.uri == "s3://zhupanov/larch"
    assert storage_root.run_logs_uri == "s3://zhupanov/larch/run-logs/"


def test_environment_storage_uri_overrides_repository_config(tmp_path: Path) -> None:
    _write_config(tmp_path, "s3://file-root/larch")

    storage_root = storage_config.load_storage_root(
        repo_root=tmp_path,
        environ={config.ENV_LARCH_LOGS_URI: "s3://environment-root/override"},
    )

    assert storage_root.uri == "s3://environment-root/override"


def test_load_storage_root_does_not_use_former_larch_directory(tmp_path: Path) -> None:
    legacy_directory = tmp_path / ".larch"
    legacy_directory.mkdir()
    _ = (legacy_directory / "config.toml").write_text(
        '[logs]\nuri = "s3://legacy-root/larch"\n', encoding="utf-8"
    )

    with pytest.raises(storage_config.StorageConfigurationError, match=r"config\.toml"):
        _ = storage_config.load_storage_root(repo_root=tmp_path, environ={})


def test_load_legacy_migration_descriptor_is_repository_scoped(tmp_path: Path) -> None:
    _ = (tmp_path / "config.toml").write_text("""[logs]
uri = "s3://zhupanov/larch"

[logs.legacy_migration]
schema = "larch-run-log-migration-inventory-v1"
source_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
storage_root = "s3://zhupanov/larch"
inventory_key = "migration/inventory.json"
inventory_sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
""", encoding="utf-8")

    descriptor = storage_config.load_legacy_migration_descriptor(
        repo_root=tmp_path, storage_root=storage_config.StorageRoot("s3", "zhupanov", "larch"),
    )

    assert descriptor is not None
    assert descriptor.inventory_key == "migration/inventory.json"
    assert descriptor.inventory_sha256 == "b" * 64


def test_load_legacy_migration_descriptor_rejects_other_storage_root(tmp_path: Path) -> None:
    _ = (tmp_path / "config.toml").write_text("""[logs]
uri = "s3://zhupanov/larch"

[logs.legacy_migration]
schema = "larch-run-log-migration-inventory-v1"
source_commit = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
storage_root = "s3://zhupanov/larch"
inventory_key = "migration/inventory.json"
inventory_sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
""", encoding="utf-8")

    with pytest.raises(storage_config.StorageConfigurationError, match="active storage root"):
        _ = storage_config.load_legacy_migration_descriptor(
            repo_root=tmp_path, storage_root=storage_config.StorageRoot("s3", "other", "larch"),
        )


def test_discover_storage_root_uses_the_git_toplevel(tmp_path: Path) -> None:
    _write_config(tmp_path, "s3://zhupanov/larch")

    def fake_consumer_repo_root(start: Path | None = None) -> Path:
        assert start == tmp_path / "nested"
        return tmp_path

    storage_root = storage_config.discover_storage_root(
        start=tmp_path / "nested",
        environ={},
        root_resolver=fake_consumer_repo_root,
    )

    assert storage_root.uri == "s3://zhupanov/larch"


def test_missing_storage_config_has_setup_guidance(tmp_path: Path) -> None:
    with pytest.raises(storage_config.StorageConfigurationError, match="LARCH_LOGS_URI"):
        _ = storage_config.load_storage_root(repo_root=tmp_path, environ={})


@pytest.mark.parametrize(
    ("uri", "message"),
    [
        ("s3://bucket", "non-empty storage-root prefix"),
        ("https://bucket/prefix", "must use one of"),
        ("s3://key:secret@bucket/prefix", "must not contain credentials"),
        ("s3://bucket:not-a-port/prefix", "valid bucket name without a port"),
        ("s3://bucket/a/../prefix", "must not contain empty, '.' or '..' segments"),
    ],
)
def test_storage_uri_rejects_unsafe_or_incomplete_shapes(uri: str, message: str) -> None:
    with pytest.raises(storage_config.StorageConfigurationError, match=message):
        _ = storage_config._parse_storage_uri(uri)  # pyright: ignore[reportPrivateUsage] - direct URI boundary coverage


def test_s3_preflight_uses_bucket_root_exit_status_only() -> None:
    runner = FakeRunner(_result(returncode=0, stdout="larch/\n"))
    storage_root = storage_config.StorageRoot(scheme="s3", bucket="zhupanov", prefix="larch")

    storage_config.preflight_s3_bucket(storage_root=storage_root, runner=runner)

    assert runner.calls == [(config.AWS_CLI, "s3", "ls", "s3://zhupanov")]


def test_s3_preflight_does_not_accept_output_when_listing_fails() -> None:
    runner = FakeRunner(_result(returncode=1, stdout="larch/\n", stderr="access denied"))
    storage_root = storage_config.StorageRoot(scheme="s3", bucket="zhupanov", prefix="larch")

    with pytest.raises(storage_config.StoragePreflightError, match="exit 1") as exc_info:
        storage_config.preflight_s3_bucket(storage_root=storage_root, runner=runner)

    assert "larch/" not in str(exc_info.value)
    assert runner.calls == [(config.AWS_CLI, "s3", "ls", "s3://zhupanov")]


def test_s3_preflight_reports_missing_aws_cli() -> None:
    runner = FakeRunner(_result(returncode=config.AWS_CLI_NOT_FOUND_EXIT_CODE))
    storage_root = storage_config.StorageRoot(scheme="s3", bucket="zhupanov", prefix="larch")

    with pytest.raises(storage_config.StoragePreflightError, match="AWS CLI is required"):
        storage_config.preflight_s3_bucket(storage_root=storage_root, runner=runner)
