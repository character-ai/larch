# lib-changelog.sh

Shared CHANGELOG helpers sourced by `scripts/commit-changelog.sh`, `scripts/implement-finalize.sh`, and `scripts/ship-pr.sh`. The file has no shebang and must be sourced.

## API

- `changelog_first_version_heading [path=CHANGELOG.md]` — print the first `## [X.Y.Z]` version (skipping `## [Unreleased]`); empty when absent.
- `changelog_duplicate_version_heading_count VERSION [path=CHANGELOG.md]` — count of `## [VERSION] -` headings (the `## [VERSION] - YYYY-MM-DD` prefix grammar).
- `changelog_extract_version_body VERSION DEST [path=CHANGELOG.md]` — extract the body lines under `## [VERSION] - YYYY-MM-DD` (heading excluded) to `DEST`, stripping leading/trailing blank lines. Returns 0 with `DEST` populated when a non-empty body exists, 1 otherwise (and removes `DEST`). Used by `ship-pr.sh ship_pr_stage_rebump_bullets` to preserve bullets before `drop-changelog-commit.sh` strips the companion changelog commit (issue #2952 Bug A).
- `write_changelog_entry VERSION CATEGORIES_FILE OUTPUT [REPLACES_VERSION=""]` — insert a new `## [VERSION] - today` section with body read from `CATEGORIES_FILE` (`### Category` headers + `- bullet` lines), writing the result to `OUTPUT`. With `REPLACES_VERSION` set and different from `VERSION`, the existing `## [REPLACES_VERSION]` section is replaced wholesale. Returns 0 on success, 3 when no anchor was found, 4 when the target heading already exists multiple times. Originally lived in `implement-finalize.sh`; hoisted so `ship-pr.sh` can reconstruct an entry after the rebase+rebump path drops the companion changelog commit.

## Sentinel

`LARCH_LIB_CHANGELOG_LOADED=1` is set after definition. Callers may probe it for fail-closed loading guards.

## Edit-in-sync

When editing `scripts/lib-changelog.sh`:
- Update this file for API additions/changes.
- Update `scripts/commit-changelog.sh` if `changelog_first_version_heading` / `changelog_duplicate_version_heading_count` contract changes (commit-changelog.sh is the primary owner).
- Update `scripts/implement-finalize.sh` Step 8a and `scripts/ship-pr.sh ship_pr_commit_changelog_after_rebump` for any `write_changelog_entry` signature or return-code change.
- Update `scripts/test-drop-changelog-commit.sh` smoke for `changelog_extract_version_body` contract changes.
