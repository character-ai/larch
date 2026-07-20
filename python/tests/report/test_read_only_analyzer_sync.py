"""Parity coverage for standalone read-only analyzers using the synced cache."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("name", "relpath"),
    [
        ("fixture_voter_calibration", "skills/voter-calibration/scripts/voter-calibration.py"),
        ("fixture_fluff_analysis", "skills/fluff-analysis/scripts/fluff-analysis.py"),
    ],
)
def test_default_synced_corpus_matches_explicit_fixture(
    name: str,
    relpath: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path(__file__).resolve().parents[3]
    module = _load_module(name, repository / relpath)
    log_root = tmp_path / "larch-logs"
    for skill in ("design", "implement", "review"):
        (log_root / skill).mkdir(parents=True)
    sync_calls = 0

    def _sync(*, repo_root: Path) -> Path:
        nonlocal sync_calls
        assert repo_root == tmp_path
        sync_calls += 1
        return log_root

    monkeypatch.setattr(module.repo_roots, "consumer_repo_root", lambda: tmp_path)
    monkeypatch.setattr(module.run_log_corpus, "synchronized_repository_log_root", _sync)

    assert module.main(["--log-root", str(log_root)]) == 0
    explicit = capsys.readouterr()
    assert module.main([]) == 0
    synchronized = capsys.readouterr()

    assert synchronized.out == explicit.out
    assert synchronized.err == explicit.err
    assert sync_calls == 1
