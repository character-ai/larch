"""Mutable analysis-state path, recovery, and concurrency contracts."""

from __future__ import annotations
import concurrent.futures
import stat
from pathlib import Path
import pytest
from larch.report import analysis_state


def _path(tmp_path: Path) -> Path:
    repo = tmp_path / "literal repo"
    repo.mkdir(exist_ok=True)
    return analysis_state.state_path(
        repo_root=repo,
        state_home=tmp_path / "state",
        owner="validate-merged",
        name="state.json",
    )


def test_first_write_uses_private_repository_scoped_state(tmp_path: Path) -> None:
    path = _path(tmp_path)
    digest = analysis_state.write_bytes(
        path, b'{"schema_version":1}\n', expected_digest=analysis_state.MISSING_DIGEST
    )
    assert (
        path
        == tmp_path
        / "state/larch/analysis-state/literal repo/validate-merged/state.json"
    )
    assert analysis_state.read_snapshot(path).digest == digest
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_warm_read_imports_legacy_once(tmp_path: Path) -> None:
    path, legacy = _path(tmp_path), tmp_path / "legacy.json"
    _ = legacy.write_bytes(b"first\n")
    cold = analysis_state.import_legacy_file(path=path, legacy_path=legacy)
    _ = legacy.write_bytes(b"later\n")
    assert analysis_state.import_legacy_file(path=path, legacy_path=legacy) == cold
    assert path.read_bytes() == b"first\n"


def test_corrupt_non_regular_state_fails_closed(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.mkdir()
    with pytest.raises(analysis_state.AnalysisStateError, match="not a regular file"):
        _ = analysis_state.read_snapshot(path)


def test_concurrent_stale_writer_is_rejected(tmp_path: Path) -> None:
    path = _path(tmp_path)
    initial = analysis_state.write_bytes(
        path, b"initial\n", expected_digest=analysis_state.MISSING_DIGEST
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                analysis_state.write_bytes, path, value, expected_digest=initial
            )
            for value in (b"one\n", b"two\n")
        ]
    failures = sum(
        1
        for future in futures
        if isinstance(future.exception(), analysis_state.AnalysisStateConflict)
    )
    assert failures == 1
    assert path.read_bytes() in {b"one\n", b"two\n"}
