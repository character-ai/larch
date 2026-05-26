# test-drop-changelog-commit.sh

Stub for the offline regression harness covering `scripts/drop-changelog-commit.sh`.

See `scripts/drop-changelog-commit.md` for the contract.

The harness builds isolated temp repos, exercises the happy/walk-back/guard paths, verifies walk-back integrity (commits above the dropped one survive), and includes a smoke test for `changelog_extract_version_body` in `scripts/lib-changelog.sh` (which `scripts/ship-pr.sh` calls from `ship_pr_stage_rebump_bullets`). Wired into `make test-harnesses` via the `test-drop-changelog-commit` target.
