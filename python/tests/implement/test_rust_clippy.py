"""Hermetic tests for changed-path Cargo Clippy selection."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core import config
from larch.core.proc import CommandResult
from larch.implement import rust_clippy


def _empty_calls() -> list[tuple[tuple[str, ...], Mapping[str, str] | None]]:
    return []


def _metadata(*, repo: Path) -> str:
    root = str(repo)
    package_id = "path+file:///repo/crates/demo#demo"
    targets = [
        {"name": "demo", "kind": ["lib"], "src_path": f"{root}/crates/demo/src/lib.rs"},
        {"name": "daemon", "kind": ["bin"], "src_path": f"{root}/crates/demo/src/bin/daemon.rs"},
        {"name": "api", "kind": ["test"], "src_path": f"{root}/crates/demo/tests/api.rs"},
        {"name": "alpha", "kind": ["test"], "src_path": f"{root}/crates/demo/tests/alpha.rs"},
        {"name": "zeta", "kind": ["test"], "src_path": f"{root}/crates/demo/tests/zeta.rs"},
        {"name": "sample", "kind": ["example"], "src_path": f"{root}/crates/demo/examples/sample.rs"},
        {"name": "speed", "kind": ["bench"], "src_path": f"{root}/crates/demo/benches/speed.rs"},
        {"name": "worker", "kind": ["bin"], "src_path": f"{root}/crates/demo/src/bin/worker/main.rs"},
        {"name": "build-script-build", "kind": ["custom-build"], "src_path": f"{root}/crates/demo/build.rs"},
    ]
    other_id = "path+file:///repo/crates/other#other"
    return json.dumps(
        {
            "workspace_members": [package_id, other_id],
            "packages": [
                {
                    "id": package_id,
                    "name": "demo",
                    "manifest_path": f"{root}/crates/demo/Cargo.toml",
                    "targets": targets,
                },
                {
                    "id": other_id,
                    "name": "other",
                    "manifest_path": f"{root}/crates/other/Cargo.toml",
                    "targets": [
                        {"name": "other", "kind": ["lib"], "src_path": f"{root}/crates/other/src/lib.rs"},
                    ],
                },
            ],
        }
    )


def _plan(tmp_path: Path, paths: Sequence[str]) -> rust_clippy.RustClippyPlan:
    repo = tmp_path / "repo"
    repo.mkdir()
    return rust_clippy.build_rust_clippy_plan(
        metadata_text=_metadata(repo=repo),
        repo_root=repo,
        changed_paths=paths,
    )


def test_production_source_selects_its_package_default_targets(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["crates/demo/src/worker.rs"])

    assert plan.commands() == (
        (config.CARGO_CLI, "clippy", "--locked", "--package", "demo", "--", "-D", "warnings"),
    )
    assert plan.selected_targets() == ("demo:default-production",)


def test_crate_manifest_selects_its_package_default_targets(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["crates/demo/Cargo.toml"])

    assert plan.commands() == (
        (config.CARGO_CLI, "clippy", "--locked", "--package", "demo", "--", "-D", "warnings"),
    )


@pytest.mark.parametrize(
    ("path", "flag", "name"),
    [
        ("crates/demo/tests/api.rs", "--test", "api"),
        ("crates/demo/examples/sample.rs", "--example", "sample"),
        ("crates/demo/benches/speed.rs", "--bench", "speed"),
        ("crates/demo/src/bin/daemon.rs", "--bin", "daemon"),
        ("crates/demo/src/bin/worker/helpers.rs", "--bin", "worker"),
    ],
)
def test_explicit_targets_select_only_the_changed_target(
    tmp_path: Path,
    path: str,
    flag: str,
    name: str,
) -> None:
    plan = _plan(tmp_path, [path])

    assert plan.commands() == (
        (config.CARGO_CLI, "clippy", "--locked", "--package", "demo", flag, name, "--", "-D", "warnings"),
    )


def test_multiple_changed_targets_coalesce_deterministically(tmp_path: Path) -> None:
    plan = _plan(
        tmp_path,
        ["crates/demo/tests/zeta.rs", "crates/demo/tests/alpha.rs", "crates/demo/tests/zeta.rs"],
    )

    assert plan.commands() == (
        (
            config.CARGO_CLI,
            "clippy",
            "--locked",
            "--package",
            "demo",
            "--test",
            "alpha",
            "--test",
            "zeta",
            "--",
            "-D",
            "warnings",
        ),
    )


def test_multiple_packages_are_ordered_deterministically(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["crates/other/src/lib.rs", "crates/demo/src/worker.rs"])

    assert plan.commands() == (
        (config.CARGO_CLI, "clippy", "--locked", "--package", "demo", "--", "-D", "warnings"),
        (config.CARGO_CLI, "clippy", "--locked", "--package", "other", "--", "-D", "warnings"),
    )

def test_default_production_and_integration_target_coalesce_once(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["crates/demo/src/worker.rs", "crates/demo/tests/api.rs"])

    assert plan.commands() == (
        (
            config.CARGO_CLI,
            "clippy",
            "--locked",
            "--package",
            "demo",
            "--lib",
            "--bin",
            "daemon",
            "--bin",
            "worker",
            "--test",
            "api",
            "--",
            "-D",
            "warnings",
        ),
    )


@pytest.mark.parametrize(
    "path",
    ["Cargo.toml", "Cargo.lock", "rust-toolchain.toml", ".cargo/config.toml"],
)
def test_workspace_inputs_select_one_default_feature_workspace_command(tmp_path: Path, path: str) -> None:
    plan = _plan(tmp_path, [path])

    assert plan.workspace is True
    assert plan.commands() == (
        (config.CARGO_CLI, "clippy", "--locked", "--workspace", "--", "-D", "warnings"),
    )


def test_shared_integration_test_module_selects_each_affected_target(tmp_path: Path) -> None:
    plan = _plan(tmp_path, ["crates/demo/tests/support/helpers.rs"])

    assert plan.commands() == (
        (
            config.CARGO_CLI,
            "clippy",
            "--locked",
            "--package",
            "demo",
            "--test",
            "alpha",
            "--test",
            "api",
            "--test",
            "zeta",
            "--",
            "-D",
            "warnings",
        ),
    )


def test_unmappable_rust_path_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(rust_clippy.RustClippyError, match="unmappable Rust path"):
        _ = _plan(tmp_path, ["crates/demo/generated/support.rs"])


@dataclass
class RecordingRunner:
    metadata: str
    calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = field(default_factory=_empty_calls)

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
    ) -> CommandResult:
        _ = timeout, cwd, check, stdout, stderr
        command = tuple(argv)
        self.calls.append((command, env))
        if command[:2] == (config.CARGO_CLI, "metadata"):
            return CommandResult(argv=command, returncode=0, stdout=self.metadata, stderr="", duration=0.0)
        return CommandResult(argv=command, returncode=0, stdout="", stderr="", duration=0.0)


def test_runner_uses_one_bounded_configuration_and_emits_proof(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runner = RecordingRunner(metadata=_metadata(repo=repo))

    rc = rust_clippy.run_changed_rust_clippy(
        runner,
        repo_root=repo,
        changed_paths=["crates/demo/src/worker.rs"],
        env={
            config.ENV_CARGO_INCREMENTAL: "1",
            config.ENV_CARGO_PROFILE_DEV_DEBUG: "2",
            config.ENV_CARGO_PROFILE_TEST_DEBUG: "2",
        },
    )

    assert rc == 0
    assert len(runner.calls) == 2
    metadata_command, metadata_env = runner.calls[0]
    clippy_command, clippy_env = runner.calls[1]
    assert metadata_command == (config.CARGO_CLI, "metadata", "--locked", "--format-version", "1", "--no-deps")
    assert clippy_command == (
        config.CARGO_CLI,
        "clippy",
        "--locked",
        "--package",
        "demo",
        "--",
        "-D",
        "warnings",
    )
    for child_env in (metadata_env, clippy_env):
        assert child_env is not None
        assert child_env[config.ENV_CARGO_INCREMENTAL] == "0"
        assert child_env[config.ENV_CARGO_PROFILE_DEV_DEBUG] == "0"
        assert child_env[config.ENV_CARGO_PROFILE_TEST_DEBUG] == "0"
    assert "--all-targets" not in clippy_command
    assert "--all-features" not in clippy_command
    assert "--release" not in clippy_command
    output = capsys.readouterr().out
    assert "RUST_CLIPPY_SELECTED_PACKAGES=demo" in output
    assert "RUST_CLIPPY_HOOK_RAN=true" in output


def test_changed_from_git_mode_uses_the_shared_change_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    captured: dict[str, object] = {}

    def fake_resolve_repo_root(*, runner: object, raw: str) -> Path:
        _ = runner, raw
        return repo

    def fake_changed_paths(*, runner: object, cwd: str) -> tuple[str, ...]:
        _ = runner
        assert cwd == str(repo)
        return ("crates/demo/src/lib.rs", "python/ignored.py")

    def fake_run(
        runner: object,
        *,
        repo_root: Path,
        changed_paths: Sequence[str],
        env: Mapping[str, str] | None = None,
    ) -> int:
        _ = runner, env
        captured["repo_root"] = repo_root
        captured["changed_paths"] = tuple(changed_paths)
        return 0

    monkeypatch.setattr(rust_clippy, "_resolve_repo_root", fake_resolve_repo_root)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(rust_clippy, "changed_paths_from_git", fake_changed_paths)
    monkeypatch.setattr(rust_clippy, "run_changed_rust_clippy", fake_run)

    assert rust_clippy.rust_clippy_main(["--repo-root", str(repo), "--changed-from-git"]) == 0
    assert captured == {
        "repo_root": repo,
        "changed_paths": ("crates/demo/src/lib.rs",),
    }
