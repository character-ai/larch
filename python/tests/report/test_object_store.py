"""Shared object-store contract tests for S3, GCS, and R2."""
from __future__ import annotations
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast
import pytest
from larch.core import config, proc
from larch.report import object_store
from larch.report.object_store import ObjectStoreError, ObjectStoreErrorKind, object_store_for
from larch.report.storage_config import StorageBase, ToolRepositoryStorage
_ACCOUNT = "0123456789abcdef0123456789abcdef"
_ENDPOINT = f"https://{_ACCOUNT}.r2.cloudflarestorage.com"
_CONTRACT_PATH = Path(__file__).parents[3] / "tests/fixtures/run-log-object-store-contract-v1.json"


def _contract() -> dict[str, object]:
    return cast("dict[str, object]", json.loads(_CONTRACT_PATH.read_text(encoding="utf-8")))


def _result(code: int = 0, payload: object | None = None) -> proc.CommandResult:
    return proc.CommandResult((), code, "" if payload is None else json.dumps(payload), "", 0.0)
class FakeRunner:
    def __init__(self, *responses: proc.CommandResult, download: bool = False) -> None:
        self.responses = list(responses)
        self.download = download
        self.calls: list[tuple[str, ...]] = []
        self.call_kwargs: list[dict[str, object]] = []
    def run(self, argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        command = tuple(argv)
        self.calls.append(command)
        self.call_kwargs.append(_kwargs)
        if self.download:
            marker, offset = (("--destination", 1) if "--destination" in command else ("--key", 2))
            _ = Path(command[command.index(marker) + offset]).write_bytes(b"archive")
        return self.responses.pop(0)
def _store(scheme: str, runner: FakeRunner):
    environ = {config.ENV_LARCH_BINARY: "/fixture/larch", config.ENV_LARCH_R2_ACCOUNT_ID: _ACCOUNT, config.ENV_LARCH_R2_ENDPOINT: _ENDPOINT}
    storage = ToolRepositoryStorage(StorageBase(scheme, "bucket"), "larch")
    return object_store_for(storage, environ=environ, runner=cast("proc.Runner", runner))
@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_preflight_lists_only_the_tool_repository_prefix(scheme: str) -> None:
    runner = FakeRunner(_result(payload={"unexpected": "output"}))
    _store(scheme, runner).preflight_prefix()
    assert "larch/larch/" in runner.calls[0]
    assert "bucket" in " ".join(runner.calls[0])
    assert scheme == "gs" or runner.calls[0][runner.calls[0].index("--max-keys") + 1] == "1"
    with pytest.raises((ObjectStoreError, RuntimeError)):
        _store(scheme, FakeRunner(_result(1, {"objects": [{"key": "larch/larch/run"}]}))).preflight_prefix()


def test_gcs_preflight_builds_fresh_checkout_before_verified_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugin"
    (plugin_root / ".git").mkdir(parents=True)
    entrypoint = plugin_root / "scripts" / "larch.sh"
    monkeypatch.setattr(object_store, "larch_entrypoint", lambda: entrypoint)
    runner = FakeRunner(_result(), _result(payload={"unexpected": "output"}))
    storage = ToolRepositoryStorage(StorageBase("gs", "bucket"), "larch")

    object_store_for(storage, environ={}, runner=cast("proc.Runner", runner)).preflight_prefix()

    assert runner.calls == [
        (config.CARGO_CLI, "build", "--quiet", "--locked", "--release", "--package", "larch-cli", "--target-dir", str(plugin_root / "target")),
        (str(entrypoint), "object-store", "gcs", "--operation", "preflight", "--bucket", "bucket", "--prefix", "larch/larch/"),
    ]
    assert runner.call_kwargs[0]["cwd"] == str(plugin_root)
    runtime_environment = cast("dict[str, str]", runner.call_kwargs[1]["env"])
    assert runtime_environment[config.ENV_CLAUDE_PLUGIN_ROOT] == str(plugin_root)
    assert runtime_environment[config.ENV_LARCH_BINARY] == str(plugin_root / "target" / "release" / "larch")


def test_gcs_preflight_reports_fresh_checkout_build_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugin"
    (plugin_root / ".git").mkdir(parents=True)
    monkeypatch.setattr(object_store, "larch_entrypoint", lambda: plugin_root / "scripts" / "larch.sh")
    storage = ToolRepositoryStorage(StorageBase("gs", "bucket"), "larch")

    with pytest.raises(ObjectStoreError) as failure:
        object_store_for(storage, environ={}, runner=cast("proc.Runner", FakeRunner(_result(1)))).preflight_prefix()

    assert failure.value.kind is ObjectStoreErrorKind.CONFIGURATION
    assert failure.value.operation == "checkout-build"


def test_gcs_preflight_rejects_symlinked_checkout_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugin"
    (plugin_root / ".git").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (plugin_root / "target").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(object_store, "larch_entrypoint", lambda: plugin_root / "scripts" / "larch.sh")
    runner = FakeRunner()
    storage = ToolRepositoryStorage(StorageBase("gs", "bucket"), "larch")

    with pytest.raises(ObjectStoreError) as failure:
        object_store_for(storage, environ={}, runner=cast("proc.Runner", runner)).preflight_prefix()

    assert failure.value.operation == "checkout-build"
    assert runner.calls == []
@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_list_paginates_from_empty_prefix(scheme: str) -> None:
    if scheme == "gs":
        pages = ({"objects": [{"key": "larch/larch/a", "size": 1}], "next_page_token": "two"}, {"objects": [{"key": "larch/larch/b", "size": 2}]})
    else:
        pages = ({"Contents": [{"Key": "larch/larch/a", "Size": 1}], "NextContinuationToken": "two"}, {"Contents": [{"Key": "larch/larch/b", "Size": 2}]})
    runner = FakeRunner(*(_result(payload=page) for page in pages))
    objects = _store(scheme, runner).list_objects()
    assert [(item.key, item.size) for item in objects] == [("a", 1), ("b", 2)]
    assert "larch/larch/" in runner.calls[0]
    assert "two" in runner.calls[1]
    assert scheme == "gs" or "--no-paginate" in runner.calls[0]
    outside = {"objects": [{"key": "larch/larch/../outside", "size": 1}]} if scheme == "gs" else {"Contents": [{"Key": "larch/larch/../outside", "Size": 1}]}
    with pytest.raises(ObjectStoreError):
        _ = _store(scheme, FakeRunner(_result(payload=outside))).list_objects()


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_list_paginates_the_complete_run_log_prefix(scheme: str) -> None:
    if scheme == "gs":
        pages = (
            {"objects": [{"key": "larch/larch/run-logs/design/run-a.tar.gz", "size": 1}], "next_page_token": "two"},
            {"objects": [{"key": "larch/larch/run-logs/review/run-b.tar.gz", "size": 2}]},
        )
    else:
        pages = (
            {"Contents": [{"Key": "larch/larch/run-logs/design/run-a.tar.gz", "Size": 1}], "NextContinuationToken": "two"},
            {"Contents": [{"Key": "larch/larch/run-logs/review/run-b.tar.gz", "Size": 2}]},
        )
    runner = FakeRunner(*(_result(payload=page) for page in pages))

    objects = _store(scheme, runner).list_objects("run-logs/")

    assert [item.key for item in objects] == [
        "run-logs/design/run-a.tar.gz",
        "run-logs/review/run-b.tar.gz",
    ]
    assert "larch/larch/run-logs/" in runner.calls[0]
    assert "two" in runner.calls[1]
@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_upload_is_create_only(scheme: str, tmp_path: Path) -> None:
    source = tmp_path / "archive"
    _ = source.write_bytes(b"archive")
    payload = {"key": "larch/larch/run", "size": 7} if scheme == "gs" else {"ETag": "tag"}
    runner = FakeRunner(_result(payload=payload))
    assert _store(scheme, runner).upload_create("run", source).key == "run"
    command = runner.calls[0]
    assert ("upload-create" in command) if scheme == "gs" else (command[command.index("--if-none-match") + 1] == "*")
    assert scheme != "r2" or command[command.index("--endpoint-url") + 1] == _ENDPOINT
    if scheme == "r2":
        with pytest.raises(ObjectStoreError) as failure:
            _ = object_store_for(ToolRepositoryStorage(StorageBase("r2", "bucket"), "larch"), environ={}, runner=cast("proc.Runner", FakeRunner()))
        assert failure.value.kind is ObjectStoreErrorKind.CONFIGURATION
@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_metadata_and_download_normalize_providers(scheme: str, tmp_path: Path) -> None:
    payload = {"key": "larch/larch/run", "size": 7, "etag": "tag", "version": "2"} if scheme == "gs" else {"ContentLength": 7, "ETag": "tag", "VersionId": "2"}
    item = _store(scheme, FakeRunner(_result(payload=payload))).metadata("run")
    assert (item.key, item.size, item.etag, item.version) == ("run", 7, "tag", "2")
    destination = tmp_path / "archive"
    _ = destination.write_bytes(b"old")
    _store(scheme, FakeRunner(_result(), download=True)).download("run", destination)
    assert destination.read_bytes() == b"archive"
    assert not list(tmp_path.glob(".archive.*"))


def test_gcs_transport_matches_shared_machine_contract(tmp_path: Path) -> None:
    contract = _contract()
    assert contract["schema_version"] == 1
    remote = cast("dict[str, object]", contract["remote_object"])
    page = cast("dict[str, object]", contract["list_page"])
    key = str(remote["key"]).removeprefix("larch/larch/")

    listed = _store("gs", FakeRunner(_result(payload=page))).list_objects("run-logs/")
    assert listed[0]._asdict() == {
        "key": key,
        "size": remote["size"],
        "etag": remote["etag"],
        "version": remote["version"],
    }
    metadata = _store("gs", FakeRunner(_result(payload=remote))).metadata(key)
    assert metadata == listed[0]

    source = tmp_path / "archive"
    _ = source.write_bytes(b"archive")
    uploaded = _store("gs", FakeRunner(_result(payload=remote))).upload_create(key, source)
    assert uploaded == listed[0]

    errors = cast("list[dict[str, object]]", contract["transport_errors"])
    for fixture in errors:
        exit_code = cast("int", fixture["exit_code"])
        with pytest.raises(ObjectStoreError) as failure:
            _ = _store("gs", FakeRunner(_result(exit_code))).metadata(key)
        assert failure.value.kind.value == fixture["kind"]
