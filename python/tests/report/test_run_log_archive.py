"""Tests for the deterministic run-log archive format."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from pathlib import Path
from typing import cast

import pytest

from larch.report import run_log_archive


FixtureMember = tuple[str, str, bytes, bytes]


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


def _fixture_manifest_bytes(
    members: list[tuple[str, str, bytes]],
    *,
    skill: str = "implement",
    run_id: str = "run-materialize",
    digest_override: dict[str, str] | None = None,
) -> bytes:
    overrides: dict[str, str] = {} if digest_override is None else digest_override
    records: list[dict[str, object]] = []
    for name, kind, content in members:
        records.append(
            {
                "kind": kind,
                "path": name,
                "sha256": overrides.get(name, hashlib.sha256(content).hexdigest()) if kind == "file" else None,
                "size": len(content) if kind == "file" else 0,
            }
        )
    payload: dict[str, object] = {
        "archive_format": run_log_archive.ARCHIVE_FORMAT,
        "member_count": len(records),
        "members": records,
        "run_id": run_id,
        "schema_version": run_log_archive.ARCHIVE_SCHEMA_VERSION,
        "skill": skill,
    }
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _write_fixture_archive(
    path: Path,
    *,
    manifest_members: list[tuple[str, str, bytes]],
    archive_members: list[FixtureMember] | None = None,
    digest_override: dict[str, str] | None = None,
) -> None:
    manifest_bytes: bytes = _fixture_manifest_bytes(manifest_members, digest_override=digest_override)
    default_members: list[FixtureMember] = [
        (name, kind, content, tarfile.DIRTYPE if kind == "directory" else tarfile.REGTYPE)
        for name, kind, content in manifest_members
    ]
    selected_members: list[FixtureMember] = default_members if archive_members is None else archive_members
    all_members: list[FixtureMember] = [
        *selected_members,
        (run_log_archive.ARCHIVE_MANIFEST_NAME, "file", manifest_bytes, tarfile.REGTYPE),
    ]
    with tarfile.open(path, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        for name, kind, content, member_type in sorted(all_members, key=lambda item: item[0]):
            info = tarfile.TarInfo(name)
            info.type = member_type
            info.mode = 0o755 if kind == "directory" else 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            if member_type == tarfile.SYMTYPE:
                info.linkname = "target"
                info.size = 0
                archive.addfile(info)
            elif kind == "directory":
                info.size = 0
                archive.addfile(info)
            else:
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))


def _create_materialization_fixture(staging: Path, tmp_path: Path) -> run_log_archive.RunArchiveResult:
    return run_log_archive.create_run_archive(
        staging_root=staging,
        output_dir=tmp_path / "archives",
        skill="implement",
        run_id="run-materialize",
    )


def _materialize(
    archive_path: Path,
    run_dir: Path,
    *,
    limits: run_log_archive.ArchiveExtractionLimits | None = None,
) -> run_log_archive.RunArchiveMaterializationResult:
    return run_log_archive.materialize_run_archive(
        archive_path=archive_path,
        run_dir=run_dir,
        expected_skill="implement",
        expected_run_id="run-materialize",
        limits=limits,
    )


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


def test_materialize_run_archive_reproduces_and_verifies_tree(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_tree(staging)
    expected: dict[Path, bytes] = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"

    result = _materialize(created.archive_path, run_dir)

    actual: dict[Path, bytes] = {path.relative_to(run_dir): path.read_bytes() for path in run_dir.rglob("*") if path.is_file() and path.name != run_log_archive.ARCHIVE_MANIFEST_NAME}
    assert actual == expected
    assert result.member_count == created.member_count
    assert run_log_archive.verify_materialized_run_directory(run_dir=run_dir, expected_skill="implement", expected_run_id="run-materialize") == result
    assert not list(run_dir.parent.glob(".run-materialize.materialize-*"))


def test_promote_staging_run_directory_copies_without_extracting_archive(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_tree(staging)
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"

    result = run_log_archive.promote_staging_run_directory(
        staging_root=staging,
        run_dir=run_dir,
        expected_skill="implement",
        expected_run_id="run-materialize",
        expected_manifest_sha256=created.manifest_sha256,
    )

    assert result.run_dir == run_dir
    assert result.manifest_sha256 == created.manifest_sha256
    assert run_log_archive.verify_materialized_run_directory(
        run_dir=run_dir,
        expected_skill="implement",
        expected_run_id="run-materialize",
    ) == result
    assert not list(run_dir.parent.glob(".run-materialize.promote-*"))


def test_promote_staging_run_directory_rejects_staging_drift(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _write_tree(staging)
    created = _create_materialization_fixture(staging, tmp_path)
    _ = (staging / "new.txt").write_text("late mutation", encoding="utf-8")
    run_dir = tmp_path / "cache" / "run-materialize"

    with pytest.raises(ValueError, match="no longer matches"):
        _ = run_log_archive.promote_staging_run_directory(
            staging_root=staging,
            run_dir=run_dir,
            expected_skill="implement",
            expected_run_id="run-materialize",
            expected_manifest_sha256=created.manifest_sha256,
        )

    assert not run_dir.exists()


@pytest.mark.parametrize("unsafe_name", ["/absolute.txt", "../escape.txt", "nested/../../escape.txt", "a\\b"])
def test_materialize_rejects_escaping_or_ambiguous_paths(tmp_path: Path, unsafe_name: str) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    _write_fixture_archive(
        archive_path,
        manifest_members=[],
        archive_members=[(unsafe_name, "file", b"escape", tarfile.REGTYPE)],
    )
    run_dir = tmp_path / "cache" / "run-materialize"

    with pytest.raises(ValueError, match="archive member path"):
        _ = _materialize(archive_path, run_dir)

    assert not run_dir.exists()
    assert not (tmp_path / "escape.txt").exists()


@pytest.mark.parametrize("member_type", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE])
def test_materialize_rejects_links_devices_and_special_files(tmp_path: Path, member_type: bytes) -> None:
    archive_path = tmp_path / "special.tar.gz"
    _write_fixture_archive(
        archive_path,
        manifest_members=[],
        archive_members=[("special", "file", b"", member_type)],
    )
    run_dir = tmp_path / "cache" / "run-materialize"

    with pytest.raises(ValueError, match="unsupported archive member type"):
        _ = _materialize(archive_path, run_dir)

    assert not run_dir.exists()


def test_materialize_rejects_duplicate_members_and_path_collisions(tmp_path: Path) -> None:
    duplicate_archive = tmp_path / "duplicate.tar.gz"
    _write_fixture_archive(
        duplicate_archive,
        manifest_members=[("same.txt", "file", b"one")],
        archive_members=[
            ("same.txt", "file", b"one", tarfile.REGTYPE),
            ("same.txt", "file", b"one", tarfile.REGTYPE),
        ],
    )
    run_dir = tmp_path / "cache" / "run-materialize"
    with pytest.raises(ValueError, match="ambiguous archive member path"):
        _ = _materialize(duplicate_archive, run_dir)

    collision_archive = tmp_path / "collision.tar.gz"
    _write_fixture_archive(
        collision_archive,
        manifest_members=[
            ("parent", "file", b"file"),
            ("parent/child", "file", b"child"),
        ],
    )
    with pytest.raises(ValueError, match="path collision"):
        _ = _materialize(collision_archive, run_dir)
    assert not run_dir.exists()


def test_materialize_rejects_incomplete_manifest_and_digest_mismatch(tmp_path: Path) -> None:
    incomplete_archive = tmp_path / "incomplete.tar.gz"
    _write_fixture_archive(
        incomplete_archive,
        manifest_members=[],
        archive_members=[("extra.txt", "file", b"extra", tarfile.REGTYPE)],
    )
    run_dir = tmp_path / "cache" / "run-materialize"
    with pytest.raises(ValueError, match="do not match archive manifest"):
        _ = _materialize(incomplete_archive, run_dir)

    digest_archive = tmp_path / "digest.tar.gz"
    _write_fixture_archive(
        digest_archive,
        manifest_members=[("result.txt", "file", b"expected")],
        digest_override={"result.txt": "0" * 64},
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        _ = _materialize(digest_archive, run_dir)
    assert not run_dir.exists()
    assert not list(run_dir.parent.glob(".run-materialize.materialize-*"))


def test_materialize_rejects_corrupt_and_truncated_archive_without_partial_run(tmp_path: Path) -> None:
    archive_path = tmp_path / "truncated.tar.gz"
    _write_fixture_archive(
        archive_path,
        manifest_members=[("large.txt", "file", b"content" * 100_000)],
    )
    _ = archive_path.write_bytes(archive_path.read_bytes()[: len(archive_path.read_bytes()) // 2])
    run_dir = tmp_path / "cache" / "run-materialize"

    with pytest.raises((OSError, tarfile.TarError, ValueError, EOFError)):
        _ = _materialize(archive_path, run_dir)

    assert not run_dir.exists()
    assert not list(run_dir.parent.glob(".run-materialize.materialize-*"))


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        (run_log_archive.ArchiveExtractionLimits(max_members=1), "member-count"),
        (run_log_archive.ArchiveExtractionLimits(max_member_bytes=16), "individual size"),
        (run_log_archive.ArchiveExtractionLimits(max_expanded_bytes=32), "expanded-size"),
        (run_log_archive.ArchiveExtractionLimits(max_compression_ratio=2), "compression-ratio"),
        (run_log_archive.ArchiveExtractionLimits(max_members=True), "positive integers"),
    ],
)
def test_materialize_enforces_all_expansion_limits(
    tmp_path: Path,
    limits: run_log_archive.ArchiveExtractionLimits,
    message: str,
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "repeated.txt").write_bytes(b"x" * 1_000_000)
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"

    with pytest.raises(ValueError, match=message):
        _ = _materialize(created.archive_path, run_dir, limits=limits)

    assert not run_dir.exists()


def test_materialize_never_merges_into_existing_destination(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "new.txt").write_text("new", encoding="utf-8")
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(FileExistsError, match="refusing to merge"):
        _ = _materialize(created.archive_path, run_dir)

    assert (run_dir / "old.txt").read_text(encoding="utf-8") == "old"
    assert not (run_dir / "new.txt").exists()


def test_materialized_directory_verification_detects_tampering(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "result.txt").write_text("trusted", encoding="utf-8")
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"
    _ = _materialize(created.archive_path, run_dir)
    _ = (run_dir / "result.txt").write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match archive manifest"):
        _ = run_log_archive.verify_materialized_run_directory(
            run_dir=run_dir,
            expected_skill="implement",
            expected_run_id="run-materialize",
        )


def test_materialize_main_emits_verified_run_envelope(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    _ = (staging / "result.txt").write_text("completed", encoding="utf-8")
    created = _create_materialization_fixture(staging, tmp_path)
    run_dir = tmp_path / "cache" / "run-materialize"

    rc = run_log_archive.materialize_main([
        "--archive-path", str(created.archive_path), "--run-dir", str(run_dir),
        "--skill", "implement", "--run-id", "run-materialize",
    ])

    output = capsys.readouterr().out
    assert rc == 0
    assert f"RUN_DIR={run_dir}\n" in output
    assert "MANIFEST_SHA256=" in output
    assert "MEMBER_COUNT=1\n" in output
    assert "EXPANDED_SIZE=" in output
