"""Regression tests for remaining release-adjacent Python helpers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

def test_release_skill_rebuilds_worktree_driver_across_version_change() -> None:
    skill = (ROOT / ".claude/skills/release/SKILL.md").read_text(encoding="utf-8")
    build = "cargo build --quiet --locked --release --package larch-cli"
    prepare = skill.index('"$PWD/scripts/larch.sh" release prepare')
    set_version = skill.index('"$PWD/scripts/larch.sh" release set-version')
    ensure_policy = skill.index('"$PWD/scripts/larch.sh" release ensure-policy')

    first_build = skill.index(build)
    candidate_build = skill.index(build, first_build + len(build))
    sync_complete = skill.index('sync_out="DRY_RUN_SYNC_SKIPPED=true"')
    checkout = skill.index('git checkout -b "release/v${NEW_VERSION}" "$RELEASE_SHA"')
    assert first_build < prepare < ensure_policy < checkout < set_version < candidate_build
    assert sync_complete < first_build

    recovery = skill.index("If Step 6 fails after Step 5 merged the release PR")
    recovery_build = skill.index(build, recovery)
    recovery_finish = skill.index('"$PWD/scripts/larch.sh" release finish', recovery)
    assert recovery < recovery_build < recovery_finish

    worktree_prefix = (
        'CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" '
        '"$PWD/scripts/larch.sh" release '
    )
    for verb in (
        "prepare",
        "set-version",
        "ensure-policy",
        "stage",
        "reconcile-notes",
        "asset-run",
        "validate-draft",
        "finish",
    ):
        assert f"{worktree_prefix}{verb}" in skill


def test_release_skill_step5_candidate_fence_has_timeout_override() -> None:
    skill = (ROOT / ".claude/skills/release/SKILL.md").read_text(encoding="utf-8")
    step = skill.index("## Step 5 — Merge the candidate, then validate its post-merge draft")
    timeout = skill.index(
        "Set Bash `timeout: 420000` (7 minutes) on this fence.", step
    )
    fence = skill.index("```bash", step)
    commit = skill.index('git commit -m "Release v${NEW_VERSION}"', fence)
    fence_end = skill.index("```", fence + len("```bash"))

    assert step < timeout < fence < commit < fence_end


def test_release_skill_stages_only_after_the_normal_queue_merge() -> None:
    skill = (ROOT / ".claude/skills/release/SKILL.md").read_text(encoding="utf-8")
    queue_submit = skill.index('"$PWD/scripts/larch.sh" merge pr')
    queue_wait = skill.index('"$PWD/scripts/larch.sh" merge wait')
    stage = skill.index('"$PWD/scripts/larch.sh" release stage')
    reconcile = skill.index('"$PWD/scripts/larch.sh" release reconcile-notes')
    validate = skill.index('"$PWD/scripts/larch.sh" release validate-draft')

    assert queue_submit < queue_wait < stage < reconcile < validate
    assert "--release-queue-bypass" not in skill
    queue_fence_end = skill.index(chr(96) * 3, queue_submit)
    queue_command = skill[queue_submit:queue_fence_end]
    assert "--no-admin-fallback" in queue_command
    assert "\n  --admin" not in queue_command
    assert 'SOURCE_COMMIT=$(git rev-parse "v${NEW_VERSION}^{commit}")' in skill
    assert 'git checkout -b "release/v${NEW_VERSION}" "$RELEASE_SHA"' in skill
    assert "RELEASE_SHA" in skill
    asset_start = skill.index("  --step release-assets")
    assert (
        skill.rfind('"$PWD/scripts/larch.sh" bgjob start', 0, asset_start)
        >= 0
    )
    asset_wait = skill.index("  --step release-assets", asset_start + 1)
    assert (
        skill.rfind('"$PWD/scripts/larch.sh" bgjob wait', 0, asset_wait)
        >= 0
    )


def test_release_skill_step7_upgrade_run_sets_the_driver_env_contract() -> None:
    skill = (ROOT / ".claude/skills/release/SKILL.md").read_text(encoding="utf-8")
    # The canonicalized parent is load-bearing: macOS TMPDIR lives under the
    # /var symlink and the /tmp fallback is itself a symlink, so an
    # uncanonicalized parent fails the larch.sh symlink-ancestor walk during
    # the release preflight (#7926). A relative, missing, or inaccessible
    # TMPDIR leaves the parent empty, and the fence reports it instead of
    # composing a misplaced staging path. test_rust_bootstrap.py runs the
    # real guard against these compositions.
    assert 'PLUGIN_DATA_PARENT=""' in skill
    assert (
        '/*) PLUGIN_DATA_PARENT="$(cd "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P)"'
        " || true ;;" in skill
    )
    assert 'if [ -n "$PLUGIN_DATA_PARENT" ]; then' in skill
    assert (
        'LARCH_EXPECTED_STABLE_VERSION="$NEW_VERSION" '
        'CLAUDE_PLUGIN_ROOT="$PWD" '
        'CLAUDE_PLUGIN_DATA="${PLUGIN_DATA_PARENT%/}/larch-plugin-data" '
        'LARCH_BINARY="$WORKTREE_LARCH" '
        '"$PWD/scripts/larch.sh" upgrade-larch run' in skill
    )


def test_release_skill_step8_uses_rust_local_cleanup() -> None:
    skill = (ROOT / ".claude/skills/release/SKILL.md").read_text(encoding="utf-8")
    step_start = skill.index("## Step 8 — Local cleanup (post-merge teardown)")
    step_end = skill.index("## Script index", step_start)
    step = skill[step_start:step_end]

    assert (
        'CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" '
        '"$PWD/scripts/larch.sh" session local-cleanup '
        '--branch "release/v${NEW_VERSION}"' in step
    )
    for key in ("CLEANUP_SUCCESS", "CURRENT_BRANCH", "BRANCH_DELETED"):
        assert f"--key {key} --match first" in step
    assert "python/cli.py session local-cleanup" not in skill
    assert "`scripts/larch.sh session local-cleanup`" in skill
