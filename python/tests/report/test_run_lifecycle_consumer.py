# pyright: reportPrivateUsage=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Tests for the thin Python consumer of Rust lifecycle commands."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from larch.report import run_lifecycle


@pytest.mark.rust_integration
def test_consumer_reaches_rust_through_its_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = os.environ.get("LARCH_TEST_RUST_BINARY", "")
    if not binary:
        pytest.skip("CI Rust test binary is unavailable")
    expected_sha256 = os.environ.get("LARCH_TEST_RUST_BINARY_SHA256", "")
    assert expected_sha256, "integration job must provide the verified Rust binary checksum"
    rust_ci_mode = os.environ.get("RUST_CI_MODE", "")
    assert rust_ci_mode in {"full", "partial", "skip"}, (
        "integration job must provide a valid Rust CI mode"
    )
    binary_path = Path(binary)
    assert binary_path.is_file()
    assert os.access(binary_path, os.X_OK)
    assert hashlib.sha256(binary_path.read_bytes()).hexdigest() == expected_sha256

    repo = tmp_path / "client"
    repo.mkdir()
    profile_directory = tmp_path / "runner-temp"
    profile_directory.mkdir()
    monkeypatch.setenv(
        "LLVM_PROFILE_FILE", str(profile_directory / "larch-python-%p.profraw")
    )
    _ = subprocess.run(
        ["git", "init", "--quiet", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    _ = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "remote",
            "add",
            "origin",
            "https://github.com/example/client.git",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # Deliberately omit LLVM_PROFILE_FILE: the lifecycle bootstrap must retain
    # the ambient redirect. Full and skip use a coverage-built executable and
    # prove the redirect by writing a profile; partial is not instrumented.
    environment = {
        "HOME": str(tmp_path / "home"),
        "LARCH_BINARY": str(binary_path),
        "PATH": os.environ["PATH"],
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }

    started = run_lifecycle.start_run(
        repo_root=repo,
        skill="review",
        run_id="python-consumer",
        environ=environment,
    )
    assert started.storage_resolution.mode == "disabled"
    assert started.context_file.is_file()

    terminal = run_lifecycle.finish_run(
        repo_root=repo,
        skill="review",
        run_id="python-consumer",
        outcome="success",
        environ=environment,
    )
    assert terminal.outcome == "success"
    assert terminal.publication is None
    assert terminal.storage_mode == "disabled"
    if rust_ci_mode != "partial":
        assert list(profile_directory.glob("larch-python-*.profraw"))
    assert not list(repo.rglob("default_*.profraw"))


def test_consumer_uses_its_own_bootstrap_when_ambient_root_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []

    def fake_run(
        command: Sequence[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        observed.extend(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/tmp/other-plugin")
    monkeypatch.setattr(run_lifecycle.subprocess, "run", fake_run)

    _ = run_lifecycle._invoke(["run-log", "lifecycle-start"])

    plugin_root = Path(run_lifecycle.__file__).resolve().parents[3]
    assert observed[0] == str(plugin_root / "scripts" / "larch.sh")


def test_explicit_bootstrap_environment_preserves_coverage_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_profile = "/runner-temp/larch-python-%p.profraw"
    observed_environment: dict[str, str] = {}

    def fake_run(
        command: Sequence[str],
        *,
        capture_output: bool,
        check: bool,
        env: Mapping[str, str],
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, check, text)
        observed_environment.update(env)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("LLVM_PROFILE_FILE", expected_profile)
    monkeypatch.setattr(run_lifecycle.subprocess, "run", fake_run)

    _ = run_lifecycle._invoke(
        ["run-log", "lifecycle-start"], environ={"PATH": "/usr/bin"}
    )

    assert observed_environment["LLVM_PROFILE_FILE"] == expected_profile


def test_start_consumer_parses_rust_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = tmp_path / "context.json"
    _ = context.write_text(
        json.dumps(
            {
                "local_namespace_id": "local-id",
                "schema_version": 3,
            }
        ),
        encoding="utf-8",
    )
    stdout = "\n".join(
        (
            "RUN_ID=run-1",
            "SKILL=review",
            f"LOG_ROOT={tmp_path / 'logs'}",
            f"RUN_DIR={tmp_path / 'logs/review/run-1'}",
            f"CONTEXT_FILE={context}",
            "RUN_LOG_STORAGE=disabled",
            "RUN_LOG_STORAGE_REASON=config-file-missing",
            "CLIENT_REPO=client",
            "LIFECYCLE_STARTED=true",
        )
    )
    monkeypatch.setattr(
        run_lifecycle,
        "_invoke",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout, ""),
    )

    started = run_lifecycle.start_run(
        repo_root=tmp_path,
        skill="review",
        run_id="run-1",
    )

    assert started.run_id == "run-1"
    assert started.context_file == context
    assert started.storage_resolution.mode == "disabled"


def test_terminal_consumer_parses_published_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stdout = "\n".join(
        (
            "RUN_ID=run-1",
            "SKILL=review",
            "OUTCOME=success",
            "RUN_LOG_STORAGE=enabled",
            "RUN_LOG_STORAGE_REASON=repository-config",
            "REMOTE_KEY=run-logs/review/run-1.tar.gz",
            "ARCHIVE_SHA256=" + "a" * 64,
            f"CACHE_DIR={tmp_path / 'cache'}",
            "SECRET_SCRUB_VIOLATIONS=2",
            "RUN_LOG_PUBLICATION=published",
            "LIFECYCLE_FLUSHED=true",
            "LIFECYCLE_TERMINALIZED=true",
        )
    )
    monkeypatch.setattr(
        run_lifecycle,
        "_invoke",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout, ""),
    )

    terminal = run_lifecycle.finish_run(
        repo_root=tmp_path,
        skill="review",
        run_id="run-1",
        outcome="success",
    )

    assert terminal.publication is not None
    assert terminal.publication.remote_key == "run-logs/review/run-1.tar.gz"
    assert terminal.secret_scrub_violations == 2
