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
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" release asset-candidate' in workflow
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" release package-asset' in workflow
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" release collect-assets' in workflow
    assert '"$GITHUB_WORKSPACE/scripts/larch.sh" release validate-assets' in workflow
    assert "LARCH_BINARY=" in workflow
    assert "--verify-checkout" in workflow
    assert "git rev-parse" not in workflow
    assert "--verify-attestations" in workflow
    assert "gh auth login --hostname github.com --with-token" in workflow
    assert "unset GH_TOKEN GITHUB_TOKEN" in workflow
    assert "LARCH_GH_TOKEN=" not in workflow
    assert "actions/setup-python@" not in workflow


def test_release_workflow_prepares_platform_smoke_test_prerequisites() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    macos_step = workflow.split("- name: Build and smoke-test on macOS", maxsplit=1)[1]
    macos_step = macos_step.split("- name: Package deterministic archive", maxsplit=1)[0]

    sign = 'codesign --force --sign - --timestamp=none "$binary"'
    verify = 'codesign --verify --verbose=2 "$binary"'
    cargo_test = (
        "cargo test --locked --package larch-test-support --package larch-adapters "
        '--package larch-cli --target "$TARGET"'
    )
    cli_only_test = 'cargo test --locked --package larch-cli --target "$TARGET"'
    cargo_build = 'cargo build --locked --release --package larch-cli --target "$TARGET"'
    assert macos_step.index(sign) < macos_step.index(verify)
    assert macos_step.index(cargo_test) < macos_step.index(cargo_build)
    assert cli_only_test not in macos_step
    # Apple Silicon is the only release target; no Linux container step remains.
    assert "Build and smoke-test at the GNU baseline" not in workflow
    assert "manylinux" not in workflow


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
        "larch-v1.2.3-manifest.json",
        "larch-v1.2.3-SHA256SUMS",
    )
    assert set(assets.TARGETS) == {"aarch64-apple-darwin"}
    _ = re.compile(r"larch-v")
