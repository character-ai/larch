"""Shared object-store contract tests for S3, GCS, and R2."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from larch.core import config, proc
from larch.report.object_store import ObjectStoreError, ObjectStoreErrorKind, object_store_for
from larch.report.storage_config import StorageRoot

_ACCOUNT = "0123456789abcdef0123456789abcdef"
_ENDPOINT = f"https://{_ACCOUNT}.r2.cloudflarestorage.com"


def _result(code: int = 0, payload: object | None = None) -> proc.CommandResult:
    return proc.CommandResult((), code, "" if payload is None else json.dumps(payload), "", 0.0)


class FakeRunner:
    def __init__(self, *responses: proc.CommandResult, download: bool = False) -> None:
        self.responses = list(responses)
        self.download = download
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        command = tuple(argv)
        self.calls.append(command)
        if self.download:
            marker, offset = (("--destination", 1) if "--destination" in command else ("--key", 2))
            _ = Path(command[command.index(marker) + offset]).write_bytes(b"archive")
        return self.responses.pop(0)


def _store(scheme: str, runner: FakeRunner):
    environ = {config.ENV_LARCH_R2_ACCOUNT_ID: _ACCOUNT, config.ENV_LARCH_R2_ENDPOINT: _ENDPOINT}
    return object_store_for(StorageRoot(scheme, "bucket", "larch"), environ=environ, runner=cast("proc.Runner", runner))


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_preflight_uses_bucket_root_exit_status_only(scheme: str) -> None:
    runner = FakeRunner(_result(payload={"unexpected": "output"}))
    _store(scheme, runner).preflight_bucket()
    assert "larch" not in runner.calls[0]
    assert "bucket" in " ".join(runner.calls[0])


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_preflight_rejects_nonzero_even_with_object_output(scheme: str) -> None:
    with pytest.raises((ObjectStoreError, RuntimeError)):
        _store(scheme, FakeRunner(_result(1, {"objects": [{"key": "larch/run"}]}))).preflight_bucket()


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_list_paginates_from_empty_prefix(scheme: str) -> None:
    if scheme == "gs":
        pages = ({"objects": [{"key": "larch/a", "size": 1}], "next_page_token": "two"}, {"objects": [{"key": "larch/b", "size": 2}]})
    else:
        pages = ({"Contents": [{"Key": "larch/a", "Size": 1}], "NextContinuationToken": "two"}, {"Contents": [{"Key": "larch/b", "Size": 2}]})
    runner = FakeRunner(*(_result(payload=page) for page in pages))
    objects = _store(scheme, runner).list_objects()
    assert [(item.key, item.size) for item in objects] == [("a", 1), ("b", 2)]
    assert "larch/" in runner.calls[0]
    assert "two" in runner.calls[1]
    assert scheme == "gs" or "--no-paginate" in runner.calls[0]
    outside = {"objects": [{"key": "outside/a", "size": 1}]} if scheme == "gs" else {"Contents": [{"Key": "outside/a", "Size": 1}]}
    with pytest.raises(ObjectStoreError):
        _store(scheme, FakeRunner(_result(payload=outside))).list_objects()


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_upload_is_create_only(scheme: str, tmp_path: Path) -> None:
    source = tmp_path / "archive"
    _ = source.write_bytes(b"archive")
    payload = {"key": "larch/run", "size": 7} if scheme == "gs" else {"ETag": "tag"}
    runner = FakeRunner(_result(payload=payload))
    assert _store(scheme, runner).upload_create("run", source).key == "run"
    command = runner.calls[0]
    assert ("upload-create" in command) if scheme == "gs" else (command[command.index("--if-none-match") + 1] == "*")
    assert scheme != "r2" or command[command.index("--endpoint-url") + 1] == _ENDPOINT


def test_r2_requires_matching_explicit_account_endpoint() -> None:
    with pytest.raises(ObjectStoreError) as failure:
        _ = object_store_for(StorageRoot("r2", "bucket", "larch"), environ={}, runner=cast("proc.Runner", FakeRunner()))
    assert failure.value.kind is ObjectStoreErrorKind.CONFIGURATION


@pytest.mark.parametrize("scheme", ["s3", "gs", "r2"])
def test_metadata_and_download_normalize_providers(scheme: str, tmp_path: Path) -> None:
    payload = {"key": "larch/run", "size": 7, "etag": "tag", "version": "2"} if scheme == "gs" else {"ContentLength": 7, "ETag": "tag", "VersionId": "2"}
    item = _store(scheme, FakeRunner(_result(payload=payload))).metadata("run")
    assert (item.key, item.size, item.etag, item.version) == ("run", 7, "tag", "2")
    destination = tmp_path / "archive"
    _ = destination.write_bytes(b"old")
    _store(scheme, FakeRunner(_result(), download=True)).download("run", destination)
    assert destination.read_bytes() == b"archive"
    assert not list(tmp_path.glob(".archive.*"))
