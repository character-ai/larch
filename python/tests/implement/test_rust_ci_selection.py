"""Offline contract coverage for fail-closed Rust CI change selection."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from larch.core import redact
from larch.core.proc import CommandResult
from larch.implement import rust_ci_selection as selection


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40


def _result(argv: Sequence[str], *, stdout: str = "", returncode: int = 0) -> CommandResult:
    return CommandResult(
        argv=tuple(argv),
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration=0.0,
    )


def _empty_calls() -> list[tuple[str, ...]]:
    return []


@dataclass
class FakeRunner:
    responses: dict[tuple[str, ...], CommandResult]
    calls: list[tuple[str, ...]] = field(default_factory=_empty_calls)

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
    diff_argv = (
        "git",
        "diff",
        "--no-ext-diff",
        "--name-status",
        "-z",
        "--find-renames=50%",
        "--find-copies=50%",
        f"{base_sha}..{head_sha}",
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


def _assert_no_diff_or_metadata_calls(runner: FakeRunner) -> None:
    assert not any(call[:2] == ("git", "diff") for call in runner.calls)
    assert not any(call[:2] == ("cargo", "metadata") for call in runner.calls)


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
            name="workspace-cli",
            relative_root="crates/cli",
            dependencies=(("crates/adapters", "dev"),),
        ),
    ]
    return _metadata(root, packages)


def _required_consumer_workspace(root: Path) -> str:
    packages = [
        _package(root, identifier="core", name="larch-core", relative_root="crates/larch-core"),
        _package(root, identifier="lint", name="larch-lint", relative_root="crates/larch-lint"),
        _package(
            root,
            identifier="adapters",
            name="larch-adapters",
            relative_root="crates/larch-adapters",
            dependencies=(("crates/larch-core", None),),
        ),
        _package(
            root,
            identifier="cli",
            name="larch-cli",
            relative_root="crates/larch-cli",
            dependencies=(
                ("crates/larch-adapters", None),
                ("crates/larch-core", None),
                ("crates/larch-lint", "build"),
            ),
            has_library=False,
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


def test_checked_out_head_mismatch_selects_full_before_diff_or_metadata(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )
    checked_out_head_argv = ("git", "rev-parse", "--verify", "HEAD^{commit}")
    runner.responses[checked_out_head_argv] = _result(checked_out_head_argv, stdout=f"{BASE_SHA}\n")

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "checked-out-head-does-not-match-pr-head"
    _assert_no_diff_or_metadata_calls(runner)


def test_missing_checked_out_head_selects_full_before_diff_or_metadata(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )
    checked_out_head_argv = ("git", "rev-parse", "--verify", "HEAD^{commit}")
    runner.responses[checked_out_head_argv] = _result(checked_out_head_argv, returncode=1)

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "checked-out-head-failed"
    _assert_no_diff_or_metadata_calls(runner)


def test_unresolvable_checked_out_head_selects_full_before_diff_or_metadata(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )
    checked_out_head_argv = ("git", "rev-parse", "--verify", "HEAD^{commit}")
    runner.responses[checked_out_head_argv] = _result(checked_out_head_argv, stdout="not-a-commit\n")

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "invalid-checked-out-head-output"
    _assert_no_diff_or_metadata_calls(runner)


def test_unexpected_merge_base_error_selects_full_before_diff_or_metadata(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )
    merge_base_argv = ("git", "merge-base", "--is-ancestor", BASE_SHA, HEAD_SHA)
    runner.responses[merge_base_argv] = _result(merge_base_argv, returncode=2)

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "merge-base-ancestry-verification-failed"
    _assert_no_diff_or_metadata_calls(runner)


def test_advanced_base_with_a_dependent_absent_from_head_metadata_selects_full(tmp_path: Path) -> None:
    # A normal PR workflow would test a merge candidate that includes the base's
    # new dependent. Metadata from the checked-out head cannot prove that
    # dependent is in the selected closure, so no fallback diff may be partial.
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_metadata(
            tmp_path,
            [_package(tmp_path, identifier="core", name="core", relative_root="crates/core")],
        ),
        base_is_ancestor=False,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "pr-base-is-not-an-ancestor-of-pr-head"
    _assert_no_diff_or_metadata_calls(runner)


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


def test_overlapping_root_and_member_target_sources_select_full(tmp_path: Path) -> None:
    root_package = _package(tmp_path, identifier="root", name="root-package", relative_root="")
    root_package["targets"] = [
        {
            "kind": ["lib"],
            "src_path": str(tmp_path / "crates" / "foo" / "src" / "lib.rs"),
        }
    ]
    member_package = _package(
        tmp_path,
        identifier="foo",
        name="foo-package",
        relative_root="crates/foo",
    )
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/foo/src/lib.rs")),
        metadata=_metadata(tmp_path, [root_package, member_package]),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "ambiguous-workspace-package-ownership"


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


@pytest.mark.parametrize(
    "path",
    [
        "crates/larch-cli/src/main.rs",
        "crates/larch-core/src/lib.rs",
        "crates/larch-lint/src/lib.rs",
        "crates/larch-adapters/src/lib.rs",
    ],
)
def test_required_ci_consumer_or_normal_build_upstream_change_selects_full(tmp_path: Path, path: str) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", path)),
        metadata=_required_consumer_workspace(tmp_path),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "required-ci-consumer-closure"
    assert not result.partial_commands


def test_larch_test_support_dev_dependency_of_cli_selects_full(tmp_path: Path) -> None:
    metadata = _metadata(
        tmp_path,
        [
            _package(tmp_path, identifier="core", name="larch-core", relative_root="crates/larch-core"),
            _package(
                tmp_path,
                identifier="test-support",
                name="larch-test-support",
                relative_root="crates/larch-test-support",
                dependencies=(("crates/larch-core", None),),
            ),
            _package(
                tmp_path,
                identifier="cli",
                name="larch-cli",
                relative_root="crates/larch-cli",
                dependencies=(("crates/larch-test-support", "dev"),),
                has_library=False,
            ),
        ],
    )
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/larch-test-support/src/lib.rs")),
        metadata=metadata,
    )

    result = _select(tmp_path, runner)

    assert result.mode == "full"
    assert result.full_run_trigger == "required-ci-consumer-closure"
    assert not result.partial_commands


def test_reverse_dependency_closure_is_transitive_and_deterministic(tmp_path: Path) -> None:
    runner = _runner_for_pull_request(
        tmp_path,
        diff=_diff(("M", "crates/core/src/lib.rs")),
        metadata=_workspace(tmp_path),
    )

    result = _select(tmp_path, runner)

    assert result.mode == "partial"
    assert result.affected_packages == ("larch-adapters", "larch-core", "workspace-cli")
    assert result.reverse_dependents == ("larch-adapters", "workspace-cli")


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
    assert result.affected_packages == ("larch-adapters", "larch-core", "workspace-cli")
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
    secret = "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    secret_path = f"src/{secret}.rs"
    result = selection.Selection(
        mode="full",
        event_name="pull_request",
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        base_source="github-pr-base",
        changed_paths=(
            selection.ChangedPath(status="M", paths=("src/<untrusted>.rs",)),
            selection.ChangedPath(status="M", paths=(secret_path,)),
        ),
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
    assert secret not in summary
    assert secret_path not in summary
    assert "src/&lt;REDACTED-TOKEN&gt;.rs" in summary


def test_secret_shaped_selector_fields_are_redacted_from_artifact_and_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
    source_path = f"crates/secret/src/{secret}.rs"
    metadata = _metadata(
        tmp_path,
        [_package(tmp_path, identifier="secret", name=secret, relative_root="crates/secret")],
    )
    result = _select(
        tmp_path,
        _runner_for_pull_request(tmp_path, diff=_diff(("M", source_path)), metadata=metadata),
    )

    artifact = result.to_json()
    assert result.mode == "partial"
    assert secret not in artifact
    assert source_path not in artifact
    assert "<REDACTED-TOKEN>" in artifact
    assert json.loads(artifact)["changed_paths"]
    assert secret not in json.dumps(selection.ChangedPath(status="M", paths=(source_path,)).as_json())
    assert secret not in json.dumps(selection.CommandPlan(name=secret, argv=("cargo", secret)).as_json())

    result_file = tmp_path / "selector.json"
    _ = result_file.write_text(artifact, encoding="utf-8")
    assert selection.rust_select_summary_main(["--result-file", str(result_file)]) == 0

    summary = capsys.readouterr().out
    assert secret not in summary
    assert source_path not in summary
    assert "&lt;REDACTED-TOKEN&gt;" in summary


def test_public_redaction_failure_selects_static_full_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_redaction(_text: str) -> redact.ScrubLogSecretsResult:
        raise RuntimeError("redactor unavailable")

    monkeypatch.setattr(selection.redact, "scrub_log_secrets", fail_redaction)
    result = _select(
        tmp_path,
        _runner_for_pull_request(
            tmp_path,
            diff=_diff(("M", "crates/core/src/lib.rs")),
            metadata=_workspace(tmp_path),
        ),
    )

    assert result.mode == "full"
    assert result.full_run_trigger == "public-output-redaction-failed"
    assert not result.changed_paths
    assert "crates/core/src/lib.rs" not in result.to_json()
    assert "crates/core/src/lib.rs" not in selection.render_summary(result)


def test_invalid_summary_result_falls_back_to_a_full_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result_file = tmp_path / "invalid.json"
    _ = result_file.write_text("{}", encoding="utf-8")

    assert selection.rust_select_summary_main(["--result-file", str(result_file)]) == 0

    captured = capsys.readouterr()
    assert "Proposed mode: <code>full</code>" in captured.out
    assert "selector-result-unavailable-or-invalid" in captured.out
