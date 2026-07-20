"""Tests for the deterministic run-log archive format."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path
from typing import cast

import pytest

from larch.report import run_log_archive


def _write_tree(root: Path) -> None:
    nested = root / "nested" / "caf\u00e9"
    nested.mkdir(parents=True)
    _ = (root / "empty.txt").write_bytes(b"")
    executable = root / "run.sh"
    _ = executable.write_text("#!/bin/sh\necho archive\n", encoding="utf-8")
    executable.chmod(0o700)
    _ = (nested / "large.bin").write_bytes((b"archive-data-" * 300_000) + b"end")
    (root / "empty-dir").mkdir()


def _manifest_from_archive(path: Path) -> dict[str, object]:
    with tarfile.open(path, mode="r:gz") as archive:
        manifest = archive.extractfile(run_log_archive.ARCHIVE_MANIFEST_NAME)
        assert manifest is not None
        decoded: object = json.loads(manifest.read().decode("utf-8"))
        assert isinstance(decoded, dict)
        return cast("dict[str, object]", decoded)


def test_create_run_archive_is_byte_deterministic_and_preserves_source(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_tree(staging)
    before = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}

    first = run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=tmp_path / "first",
        skill="implement",
        run_id="run-archive-1",
    )
    os.utime(staging / "nested" / "caf\u00e9" / "large.bin", (1_700_000_000, 1_700_000_000))
    (staging / "empty.txt").chmod(0o600)
    second = run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=tmp_path / "second",
        skill="implement",
        run_id="run-archive-1",
    )

    assert first.archive_path.name == "run-archive-1.tar.gz"
    assert first.archive_path.read_bytes() == second.archive_path.read_bytes()
    assert first.archive_sha256 == hashlib.sha256(first.archive_path.read_bytes()).hexdigest()
    assert {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()} == before

    manifest = _manifest_from_archive(first.archive_path)
    assert manifest["archive_format"] == run_log_archive.ARCHIVE_FORMAT
    assert manifest["schema_version"] == 1
    members_value: object = manifest["members"]
    assert isinstance(members_value, list)
    members: list[object] = cast("list[object]", members_value)
    records: list[dict[str, object]] = [cast("dict[str, object]", member) for member in members if isinstance(member, dict)]
    assert len(records) == len(members)
    large = next(record for record in records if record["path"] == "nested/caf\u00e9/large.bin")
    assert large["size"] == (staging / "nested" / "caf\u00e9" / "large.bin").stat().st_size
    assert large["sha256"] == hashlib.sha256((staging / "nested" / "caf\u00e9" / "large.bin").read_bytes()).hexdigest()


def test_archive_members_use_normalized_metadata_and_include_empty_directories(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_tree(staging)

    result = run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=tmp_path / "archives",
        skill="design",
        run_id="run-archive-2",
    )

    with tarfile.open(result.archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        assert names == sorted(names)
        assert run_log_archive.ARCHIVE_MANIFEST_NAME in names
        assert "empty-dir" in names
        executable = archive.getmember("run.sh")
        assert executable.mode == 0o755
        for member in members:
            assert member.mtime == 0
            assert member.uid == 0
            assert member.gid == 0
            assert member.uname == ""
            assert member.gname == ""


def test_archive_rejects_symlink_and_output_inside_staging(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "regular.txt").write_text("safe", encoding="utf-8")
    (staging / "link.txt").symlink_to("regular.txt")

    with pytest.raises(OSError, match="unsupported archive member type"):
        _ = run_log_archive.create_run_archive(
            staging_root=staging,
            output_dir=tmp_path / "archives",
            skill="review",
            run_id="run-archive-3",
        )

    (staging / "link.txt").unlink()
    with pytest.raises(ValueError, match="must not be inside the staging tree"):
        _ = run_log_archive.create_run_archive(
            staging_root=staging,
            output_dir=staging / "archives",
            skill="review",
            run_id="run-archive-3",
        )
    assert not (staging / "archives").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes are unavailable on this platform")
def test_archive_rejects_named_pipe(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    os.mkfifo(staging / "events.pipe")

    with pytest.raises(OSError, match="unsupported archive member type"):
        _ = run_log_archive.create_run_archive(
            staging_root=staging,
            output_dir=tmp_path / "archives",
            skill="review",
            run_id="run-archive-pipe",
        )


def test_archive_rejects_unicode_normalization_collision(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "caf\u00e9.txt").write_text("nfc", encoding="utf-8")
    _ = (staging / "cafe\u0301.txt").write_text("nfd", encoding="utf-8")
    if len(list(staging.iterdir())) != 2:
        pytest.skip("filesystem normalizes Unicode filenames")

    with pytest.raises(ValueError, match="Unicode normalization"):
        _ = run_log_archive.create_run_archive(
            staging_root=staging,
            output_dir=tmp_path / "archives",
            skill="review",
            run_id="run-archive-4",
        )


def test_archive_main_emits_archive_and_manifest_digests(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "result.txt").write_text("completed", encoding="utf-8")

    rc = run_log_archive.main(
        [
            "--staging-root",
            str(staging),
            "--output-dir",
            str(tmp_path / "archives"),
            "--skill",
            "implement",
            "--run-id",
            "run-archive-5",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0
    assert f"ARCHIVE_PATH={tmp_path / 'archives' / 'run-archive-5.tar.gz'}\n" in output
    assert "ARCHIVE_SHA256=" in output
    assert "MANIFEST_SHA256=" in output
    assert "MEMBER_COUNT=1\n" in output
