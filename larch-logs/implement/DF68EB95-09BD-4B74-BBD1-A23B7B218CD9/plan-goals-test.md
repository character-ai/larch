## Goal
Fix floor-prune in upgrade-larch.sh so keep-8 cap is the single retention policy

## Implementation Plan

Fix issue #2380: `/upgrade-larch` floor-prune defeats keep-8 cap, deletes cached plugin versions.

### Approach (Option A from issue)

Remove the "below-floor obsolete sweep" block entirely from `skills/upgrade-larch/scripts/upgrade-larch.sh`. The cap-prune (KEEP_LIMIT=8) already enforces the retention contract. The floor-prune is a hold-over that inadvertently overrides the cap.

### Files to modify

1. **`skills/upgrade-larch/scripts/upgrade-larch.sh`**
   - Remove helper functions: `release_train_of()`, `version_is_prune_protected()`, `version_lt()`
   - Remove `PREDECESSOR_STABLE=""` initialization
   - Remove the `sorted_stables` computation block and `PREDECESSOR_STABLE` derivation inside the `if GH_RELEASES_OUTPUT...` block
   - Remove the entire floor-prune block: lines from `# When the cache is already under the 8-version cap...` through the closing `done` of the `OBSOLETE_PRUNE_CANDIDATES` loop
   - Keep `version_gt()` (still used in the "newer than stable" loop)

2. **`skills/upgrade-larch/scripts/upgrade-larch.md`**
   - §8 Behavior: remove the "It also derives `PREDECESSOR_STABLE`..." sentence (same-release-train sweep sentence)
   - Remove the `## Limitations (Angle B)` section entirely

3. **`skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`**
   - `no-sessions-prunes-old`: change assertion — 29.1.19 stays (no pruning with 4 versions < cap 8)
   - `unparseable-session-prunes-normally`: same — 29.1.19 stays
   - `active-session-keeps-version`: re-seed with 9 starting versions (29.1.20-29.1.28), install 29.1.30, pin on 29.1.21; cap-prune removes 29.1.20, pin guards 29.1.21
   - `crlf-session-root-keeps-version`: re-seed similarly with 9 starting versions, CRLF pin on 29.1.21
   - `xdg-default-sessions-root-keeps-version`: change assertion — 29.1.19 stays
   - `tmp-fallback-sessions-root-keeps-version`: change assertion — 29.1.19 stays
   - Add new case `cap-prune-trims-to-eight`: seed 9 versions (29.1.21-29.1.29), install 29.1.30; cap-prune removes 2 oldest (29.1.21, 29.1.22), keeps 8

4. **`skills/upgrade-larch/scripts/test-upgrade-larch-prune.md`**
   - Sync covered cases list to reflect new cap-prune-only behavior
   - Remove floor-prune language, add new cap-prune case

5. **`SECURITY.md`**: No changes needed (no floor-specific language found)


## Test plan

Run `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh` and `skills/upgrade-larch/scripts/test-upgrade-larch.sh` after changes.
Run `make lint` and `/relevant-checks` on touched files.
