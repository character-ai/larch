"""Offline contract coverage for fail-closed Rust CI change selection."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.implement import rust_ci_selection as selection


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
MERGE_BASE_SHA = "c" * 40


def _result(argv: Sequence[str], *, stdout: str = "", returncode: int = 0) -> CommandResult:
    return CommandResult(
        argv=tuple(argv),
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration=0.0,
    )


@dataclass
class FakeRunner:
    responses: dict[tuple[str, ...], CommandResult]
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
        key = tuple(argv)
        self.calls.append(key)
        return self.responses.get(key, _result(key, returncode=1))


def _diff(*records: tuple[str, ...]) -> str:
    values: list[str] = []
    for record in records:
        values.extend(record)
    return "\0".join(values) + "\0"


def _package(
    root: Path,
    *,
    identifier: str,
    name: str,
    relative_root: str,
    dependencies: tuple[tuple[str, str | None], ...] = (),
    has_library: bool = True,
) -> dict[str, object]:
    package_root = root / relative_root
    targets: list[dict[str, object]] = [
        {
            "kind": ["lib"] if has_library else ["bin"],
            "src_path": str(package_root / "src" / "lib.rs"),
        }
    ]
    return {
        "dependencies": [
            {"kind": kind, "path": str(root / dependency_root)}
            for dependency_root, kind in dependencies
        ],
        "id": identifier,
        "manifest_path": str(package_root / "Cargo.toml"),
        "name": name,
        "targets": targets,
    }


def _metadata(root: Path, packages: list[dict[str, object]], members: list[str] | None = None) -> str:
    return json.dumps(
        {
            "packages": packages,
            "workspace_members": members or [str(package["id"]) for package in packages],
            "workspace_root": str(root),
        }
    )


def _runner_for_pull_request(
    _root: Path,
    *,
    diff: str,
    metadata: str = "{}",
    base_sha: str = BASE_SHA,
    head_sha: str = HEAD_SHA,
    base_is_ancestor: bool = True,
    merge_base: str = MERGE_BASE_SHA,
    missing_base: bool = False,
) -> FakeRunner:
    responses: dict[tuple[str, ...], CommandResult] = {
        ("git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"): _result(
            ("git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"),
            stdout=f"{base_sha}\n",
            returncode=1 if missing_base else 0,
        ),
        ("git", "rev-parse", "--verify", f"{head_sha}^{{commit}}"): _result(
            ("git", "rev-parse", "--verify", f"{head_sha}^{{commit}}"), stdout=f"{head_sha}\n"
        ),
        ("git", "rev-parse", "--verify", "HEAD^{commit}"): _result(
            ("git", "rev-parse", "--verify", "HEAD^{commit}"), stdout=f"{head_sha}\n"
        ),
        ("git", "merge-base", "--is-ancestor", base_sha, head_sha): _result(
            ("git", "merge-base", "--is-ancestor", base_sha, head_sha),
            returncode=0 if base_is_ancestor else 1,
        ),
    }
    comparison_base = base_sha if base_is_ancestor else merge_base
    if not base_is_ancestor:
        responses[("git", "merge-base", base_sha, head_sha)] = _result(
            ("git", "merge-base", base_sha, head_sha), stdout=f"{merge_base}\n"
        )
        responses[("git", "merge-base", "--is-ancestor", merge_base, base_sha)] = _result(
            ("git", "merge-base", "--is-ancestor", merge_base, base_sha)
        )
        responses[("git", "merge-base", "--is-ancestor", merge_base, head_sha)] = _result(
            ("git", "merge-base", "--is-ancestor", merge_base, head_sha)
        )
    diff_argv = (
        "git",
        "diff",
        "--no-ext-diff",
        "--name-status",
        "-z",
        "--find-renames=50%",
        "--find-copies=50%",
        f"{comparison_base}..{head_sha}",
    )
    responses[diff_argv] = _result(diff_argv, stdout=diff)
    metadata_argv = ("cargo", "metadata", "--no-deps", "--format-version", "1", "--locked", "--offline")
    responses[metadata_argv] = _result(metadata_argv, stdout=metadata)
    return FakeRunner(responses=responses)


def _select(root: Path, runner: FakeRunner, *, event_name: str = "pull_request") -> selection.Selection:
    return selection.select(
        event_name=event_name,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        repo_root=root,
        runner=runner,
    )


def _workspace(root: Path) -> str:
    packages = [
        _package(root, identifier="core", name="larch-core", relative_root="crates/core"),
        _package(
            root,
            identifier="adapters",
            name="larch-adapters",
            relative_root="crates/adapters",
            dependencies=(("crates/core", None),),
        ),
        _package(
            root,
            identifier="cli",
            name="larch-cli",
            relative_root="crates/cli",
            dependencies=(("crates/adapters", "dev"),),
        ),
    ]
    return _metadata(root, packages)


@pytest.mark.parametrize("event_name", ["push", "workflow_dispatch", "schedule", "merge_group", "other"])
def test_non_pull_request_events_always_select_full(tmp_path: Path, event_name: str) -> None:
    result = _select(tmp_path, FakeRunner({}), event_name=event_name)

    assert result.mode == "full"
    assert result.full_run_trigger == f"non-pull-request-event:{event_name}"
    assert not result.partial_commands


def test_missing_base_or_head_sha_selects_full_without_running_tools(tmp_path: Path) -> None:
    runner = FakeRunner({})
    result = selection.select(
        event_name="pull_request",
        base_sha="",
        head_sha=HEAD_SHA,
        repo_root=tmp_path,
        runner=runner,
    )

    assert result.mode == "full"
    assert result.full_run_trigger == "missing-or-invalid-pr-base-sha"
    assert not runner.calls


def test_non_string_event_or_sha_inputs_select_full_without_running_tools(tmp_path: Path) -> None:
    invalid_event = selection.select(
        event_name=object(),
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        repo_root=tmp_path,
        runner=FakeRunner({}),
    )
    runner = FakeRunner({})
    invalid_base = selection.select(
        event_name="pull_request",
        base_sha=object(),
        head_sha=HEAD_SHA,
        repo_root=tmp_path,
        runner=runner,
    )

    assert invalid_event.mode == "full"
    assert invalid_event.full_run_trigger == "non-pull-request-event:unrecognized"
    assert invalid_base.mode == "full"
    assert invalid_base.full_run_trigger == "missing-or-invalid-pr-base-sha"
    assert not runner.calls


def test_missing_or_shallow_base_commit_selects_full(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
        missing_base=True,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "base-commit-failed"
    assert not any(call[0] == "cargo" for call in runner.calls)


def test_verified_merge_base_is_used_when_pr_base_is_not_an_ancestor(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
        base_is_ancestor=False,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.base_sha == MERGE_BASE_SHA
    assert result.base_source == "verified-merge-base"


@pytest.mark.parametrize(
    ("path", "trigger"),
    [
        ("Cargo.lock", "global-input:cargo-lock"),
        ("Cargo.toml", "global-input:cargo-manifest"),
        ("crates/core/Cargo.toml", "global-input:cargo-manifest"),
        ("rust-toolchain.toml", "global-input:rust-toolchain"),
        (".cargo/config.toml", "global-input:cargo-configuration"),
        ("crates/core/build.rs", "global-input:build-script"),
        (".github/workflows/ci.yaml", "global-input:rust-ci-workflow"),
        ("Makefile", "global-input:rust-makefile"),
        ("deny.toml", "global-input:dependency-policy"),
        ("python/larch/implement/rust_ci_selection.py", "global-input:rust-selector"),
        ("nextest.toml", "global-input:test-profile"),
    ],
)
def test_global_inputs_select_full_and_preserve_changed_path(
    tmp_path: Path,
    path: str,
    trigger: str,
) -> None:
    runner = _runner_for_pull_request(tmp_path, diff=_diff(("M", path)))

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == trigger
    assert result.changed_paths == (selection.ChangedPath(status="M", paths=(path,)),)
    assert not any(call[0] == "cargo" for call in runner.calls)


def test_root_package_rust_source_can_select_partial(tmp_path: Path) -> None:
    metadata = _metadata(
        tmp_path,
        [_package(tmp_path, identifier="root", name="root-package", relative_root="")],
    )
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "src/lib.rs")),
        metadata=metadata,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.affected_packages == ("root-package",)


def test_rust_path_outside_a_metadata_target_source_selects_full(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/scripts/utility.rs")),
        metadata=_workspace(tmp_path),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "rust-path-not-owned-by-workspace-target"


def test_missing_cargo_target_source_path_selects_full(tmp_path: Path) -> None:
    metadata = json.loads(_workspace(tmp_path))
    del metadata["packages"][0]["targets"][0]["src_path"]
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=json.dumps(metadata),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "cargo-metadata-invalid-target-source"


def test_reverse_dependency_closure_is_transitive_and_deterministic(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.affected_packages == ("larch-adapters", "larch-cli", "larch-core")
    assert result.reverse_dependents == ("larch-adapters", "larch-cli")


def test_build_and_dev_edges_are_included_in_reverse_dependency_closure(tmp_path: Path) -> None:
    metadata = _metadata(
        tmp_path,
        [
            _package(tmp_path, identifier="base", name="base", relative_root="crates/base"),
            _package(
                tmp_path,
                identifier="build-consumer",
                name="build-consumer",
                relative_root="crates/build-consumer",
                dependencies=(("crates/base", "build"),),
            ),
            _package(
                tmp_path,
                identifier="dev-consumer",
                name="dev-consumer",
                relative_root="crates/dev-consumer",
                dependencies=(("crates/build-consumer", "dev"),),
            ),
        ],
    )
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/base/src/lib.rs")),
        metadata=metadata,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.affected_packages == ("base", "build-consumer", "dev-consumer")
    assert result.reverse_dependents == ("build-consumer", "dev-consumer")


@pytest.mark.parametrize(
    "record",
    [
        ("D", "crates/core/src/removed.rs"),
        ("R100", "crates/core/src/old.rs", "crates/core/src/new.rs"),
        ("A", "crates/core/src/added.rs"),
    ],
)
def test_additions_deletions_and_renames_are_classified(tmp_path: Path, record: tuple[str, ...]) -> None:
    runner = _runner_for_pull_request(tmp_path, diff=_diff(record), metadata=_workspace(tmp_path))

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.affected_packages == ("larch-adapters", "larch-cli", "larch-core")
    assert result.changed_paths[0].status == record[0]


def test_new_crate_or_workspace_membership_change_is_full(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(tmp_path, diff=_diff(("A", "crates/new/Cargo.toml")))

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "global-input:cargo-manifest"


def test_mixed_supplementary_and_rust_changes_select_full_without_skip(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "README.md"), ("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "unknown-path-has-no-named-validation-owner"
    assert result.skip_proof is None


@pytest.mark.parametrize(
    ("diff", "trigger"),
    [
        ("", "empty-or-malformed-diff"),
        (_diff(("T", "crates/core/src/lib.rs")), "unsupported-diff-status"),
        (_diff(("M", "outside/package.rs")), "rust-path-not-owned-by-workspace-package"),
    ],
)
def test_ambiguous_or_unknown_diff_inputs_select_full(tmp_path: Path, diff: str, trigger: str) -> None:
    runner = _runner_for_pull_request(tmp_path, diff=diff, metadata=_workspace(tmp_path))

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == trigger


def test_malformed_cargo_metadata_selects_full(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata="not-json",
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "cargo-metadata-invalid-json"


def test_partial_commands_are_locked_all_feature_and_coverage_free(tmp_path: Path) -> None:
    metadata = _metadata(
        tmp_path,
        [
            _package(tmp_path, identifier="library", name="library", relative_root="crates/library"),
            _package(tmp_path, identifier="binary", name="binary", relative_root="crates/binary", has_library=False),
        ],
    )
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/library/src/lib.rs"), ("M", "crates/binary/src/main.rs")),
        metadata=metadata,
    )

    result = _select(tmp_path, runner)
    commands = {command.name: command.argv for command in result.partial_commands}

    assert result.mode == "partial"
    assert commands["format"] == ("cargo", "fmt", "--all", "--check")
    assert commands["clippy"] == (
        "cargo",
        "clippy",
        "--package",
        "binary",
        "--package",
        "library",
        "--all-targets",
        "--all-features",
        "--locked",
        "--",
        "-D",
        "warnings",
    )
    assert commands["test"] == (
        "cargo",
        "test",
        "--package",
        "binary",
        "--package",
        "library",
        "--all-targets",
        "--all-features",
        "--locked",
    )
    assert commands["doctests"] == (
        "cargo",
        "test",
        "--doc",
        "--package",
        "library",
        "--all-features",
        "--locked",
    )
    assert "coverage" not in " ".join(" ".join(command.argv) for command in result.partial_commands)
    assert result.dependency_policy_required is False


def test_output_order_is_deterministic_across_diff_and_metadata_order(tmp_path: Path) -> None:
    packages = [
        _package(tmp_path, identifier="core", name="core", relative_root="crates/core"),
        _package(
            tmp_path,
            identifier="consumer",
            name="consumer",
            relative_root="crates/consumer",
            dependencies=(("crates/core", None),),
        ),
    ]
    first = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/consumer/src/lib.rs"), ("M", "crates/core/src/lib.rs")),
        metadata=_metadata(tmp_path, packages),
    )
    second = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs"), ("M", "crates/consumer/src/lib.rs")),
        metadata=_metadata(tmp_path, list(reversed(packages)), members=["consumer", "core"]),
    )

    first_result = _select(tmp_path, first)
    second_result = _select(tmp_path, second)

    assert first_result.to_json() == second_result.to_json()


def test_summary_escapes_untrusted_paths_and_declares_observation_only() -> None:
    result = selection.Selection(
        mode="full",
        event_name="pull_request",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        base_source="github-pr-base",
        changed_paths=(selection.ChangedPath(status="M", paths=("src/<untrusted>.rs",)),),
        affected_packages=(),
        reverse_dependents=(),
        full_run_trigger="unknown-path-has-no-named-validation-owner",
        skip_proof=None,
        partial_commands=(),
        dependency_policy_required=True,
        dependency_policy_reason="full-mode-requires-the-existing-rust-deny-lane",
        format_required=True,
    )

    summary = selection.render_summary(result)

    assert "Full Rust CI remains required during the observation window." in summary
    assert "src/&lt;untrusted&gt;.rs" in summary
    assert "src/<untrusted>.rs" not in summary


def test_invalid_summary_result_falls_back_to_a_full_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result_file = tmp_path / "invalid.json"
    result_file.write_text("{}", encoding="utf-8")

    assert selection.rust_select_summary_main(["--result-file", str(result_file)]) == 0

    captured = capsys.readouterr()
    assert "Proposed mode: <code>full</code>" in captured.out
    assert "selector-result-unavailable-or-invalid" in captured.out
