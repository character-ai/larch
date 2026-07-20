"""Workflow contract coverage for Rust-owned release asset commands."""

from __future__ import annotations

import re
from pathlib import Path

from larch.release import assets

REPO_ROOT = Path(__file__).parents[3]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rust-release-assets.yaml"


def test_release_workflow_uses_staged_rust_executable_for_asset_commands() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "python3 python/cli.py release" not in workflow
    assert "gh attestation verify" not in workflow
    assert "./target/release/larch release asset-candidate" in workflow
    assert '"./target/$TARGET/release/larch" release package-asset' in workflow
    assert "./target/release/larch release collect-assets" in workflow
    assert "./target/release/larch release validate-assets" in workflow
    assert "--verify-attestations" in workflow
    assert "LARCH_GH_TOKEN=" in workflow
    assert "actions/setup-python@" not in workflow


def test_release_workflow_prepares_platform_smoke_test_prerequisites() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    macos_step = workflow.split("- name: Build and smoke-test on macOS", maxsplit=1)[1]
    macos_step = macos_step.split("- name: Build and smoke-test at the GNU baseline", maxsplit=1)[0]
    linux_step = workflow.split("- name: Build and smoke-test at the GNU baseline", maxsplit=1)[1]
    linux_step = linux_step.split("- name: Package deterministic archive", maxsplit=1)[0]

    sign = 'codesign --force --sign - --timestamp=none "$binary"'
    verify = 'codesign --verify --verbose=2 "$binary"'
    cargo_test = (
        "cargo test --locked --package larch-test-support --package larch-adapters "
        '--package larch-cli --target "$TARGET"'
    )
    cli_only_test = 'cargo test --locked --package larch-cli --target "$TARGET"'
    cargo_build = 'cargo build --locked --release --package larch-cli --target "$TARGET"'
    linux_path = 'export PATH="/root/.cargo/bin:$PATH"'
    assert macos_step.index(sign) < macos_step.index(verify)
    assert linux_path in linux_step
    assert macos_step.index(cargo_test) < macos_step.index(cargo_build)
    assert linux_step.index(cargo_test) < linux_step.index(cargo_build)
    assert cli_only_test not in macos_step
    assert cli_only_test not in linux_step


def test_release_workflow_verifies_draft_assets_by_release_id() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    upload_step = workflow.split("- name: Upload the validated set to the draft Release", maxsplit=1)[1]
    upload_step = upload_step.split("- name: Upload validated release asset set", maxsplit=1)[0]

    assert "databaseId,isDraft,isImmutable,tagName" in upload_step
    assert 'release_id="$(jq -r \'.databaseId\' <<<"$release_state")"' in upload_step
    assert '[[ "$release_id" =~ ^[1-9][0-9]*$ ]]' in upload_step
    upload = 'gh release upload "$GITHUB_REF_NAME"'
    verify = 'gh api "repos/$GITHUB_REPOSITORY/releases/$release_id"'
    assert upload_step.index(upload) < upload_step.index(verify)
    assert "releases/tags/" not in upload_step


def test_expected_asset_names_are_stable() -> None:
    identity = assets.release_identity("1.2.3", "v1.2.3", "a" * 40)
    names = assets.expected_asset_names(identity)
    assert names == (
        "larch-v1.2.3-aarch64-apple-darwin.tar.gz",
        "larch-v1.2.3-x86_64-apple-darwin.tar.gz",
        "larch-v1.2.3-aarch64-unknown-linux-gnu.tar.gz",
        "larch-v1.2.3-x86_64-unknown-linux-gnu.tar.gz",
        "larch-v1.2.3-manifest.json",
        "larch-v1.2.3-SHA256SUMS",
    )
    assert set(assets.TARGETS) == {
        "aarch64-apple-darwin",
        "x86_64-apple-darwin",
        "aarch64-unknown-linux-gnu",
        "x86_64-unknown-linux-gnu",
    }
    _ = re.compile(r"larch-v")
