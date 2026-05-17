## Goal
Add stable-release resolution, idempotency, pre-release verification, and version pruning to upgrade-larch.sh

## Implementation Plan
Fix upgrade-larch.sh: stable release resolution, idempotency, pre-release verification, and version pruning


### Objective
Modify `skills/upgrade-larch/scripts/upgrade-larch.sh` so that:
1. It resolves the latest stable (non-pre-release) release via GitHub API before upgrading.
2. It skips the upgrade if the installed version already matches the latest stable (idempotency).
3. It verifies the post-install version matches the expected stable release and warns if a pre-release was installed instead.
4. It prunes old installed versions after a successful upgrade, keeping only the latest and its immediate predecessor.

Update `skills/upgrade-larch/scripts/upgrade-larch.md` to reflect the new behavior (edit-in-sync rule).
Update `docs/installation-and-setup.md` Upgrade section to mention idempotency behavior.

### Files to modify
- `skills/upgrade-larch/scripts/upgrade-larch.sh` (primary)
- `skills/upgrade-larch/scripts/upgrade-larch.md` (sibling contract doc)
- `docs/installation-and-setup.md` (upgrade section)

### Implementation details

**upgrade-larch.sh changes:**

1. Derive `LARCH_CACHE_DIR="$(dirname "$PLUGIN_ROOT")"` and `INSTALLED_VERSION="$(basename "$PLUGIN_ROOT")"`.

2. Resolve latest stable release (before any mutation):
   ```bash
   LATEST_STABLE=""
   if command -v gh >/dev/null 2>&1; then
       LATEST_STABLE=$(gh api repos/character-ai/larch/releases \
         --jq '[.[] | select(.prerelease == false and .draft == false)] | first | .tag_name' \
         2>/dev/null | sed 's/^v//') || true
   fi
   ```

3. Idempotency guard:
   ```bash
   if [ -n "$LATEST_STABLE" ] && [ "$INSTALLED_VERSION" = "$LATEST_STABLE" ]; then
       emit_breadcrumb "Already at latest stable larch release (${INSTALLED_VERSION}). No upgrade needed."
       exit 0
   fi
   ```

4. Keep existing uninstall → remove-marketplace → re-add → install block (unchanged).

5. Post-install pre-release verification:
   - Check if `$LARCH_CACHE_DIR/$LATEST_STABLE` directory exists.
   - If missing, find the actually-installed version using `ls -d "$LARCH_CACHE_DIR"/[0-9]*/ | sort -V | tail -1`.
   - Warn via `larch_err` if the installed version doesn't match expected stable.

6. Prune old versions (keep newest 2):
   ```bash
   VERSION_COUNT=$(ls -d "$LARCH_CACHE_DIR"/[0-9]*/ 2>/dev/null | sort -V | wc -l | tr -d ' ')
   KEEP=2
   if [ "$VERSION_COUNT" -gt "$KEEP" ]; then
       PRUNE_COUNT=$((VERSION_COUNT - KEEP))
       ls -d "$LARCH_CACHE_DIR"/[0-9]*/ 2>/dev/null | sort -V | head -n "$PRUNE_COUNT" | while IFS= read -r dir; do
           emit_breadcrumb "  Removing old version: $(basename "$dir")"
           rm -rf "$dir"
       done
   fi
   ```
   Note: `sort -V` is GNU coreutils; on macOS it's in `coreutils` via Homebrew. The `ls | sort -V` pattern is already used in existing larch scripts.

### Edge cases
- `gh` not available: LATEST_STABLE="" → idempotency check and pre-release verification are skipped; pruning still runs.
- Only 1-2 versions installed: pruning is a no-op (nothing pruned).
- Dev checkout where PLUGIN_ROOT is the repo itself: `ls -d "$LARCH_CACHE_DIR"/[0-9]*/` finds no version dirs → VERSION_COUNT=0 → pruning is a no-op.

### Testing / verification
- Run `/relevant-checks` (pre-commit + agent-lint) after changes.
- Verify script syntax: `bash -n skills/upgrade-larch/scripts/upgrade-larch.sh`.
- Check markdown lint for docs changes.

### Estimated diff size
~35-45 LOC (upgrade-larch.sh) + ~20 LOC (upgrade-larch.md) + ~5 LOC (install docs) ≈ 60-70 LOC total.

## Test plan
(no test plan section in plan-file)
