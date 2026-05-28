## Proposed Design Outline

### Goals
- Emit a `larch_err` warning when the cap-trim loop terminates with `${#SANITIZED_VERSIONS[@]} > 8` (Part A from #2993).
- Remove the dead `list_cached_versions()` function from `upgrade-larch.sh` (revised Part B from #2992).
- Preserve existing prune-path behavior: mtime ordering, pinned-aware skip, per-failure warnings, idempotent-already-stable exit.

### Non-goals
- Touching `sort_versions()`, `version_gt()`, or `collect_active_session_versions()` — `sort_versions()` is still live via those two callers (lines 50, 194).
- Changing the cap value (8), the ordering strategy (mtime), or any pinning logic.
- Adding new harness scenarios beyond what is needed to cover the warning path.

### Approach sketch
- Inside the existing `if [ "$VERSION_COUNT" -gt "$KEEP_LIMIT" ]` branch in `skills/upgrade-larch/scripts/upgrade-larch.sh`, after the `while` loop, add a post-loop guard that re-checks `${#SANITIZED_VERSIONS[@]} > KEEP_LIMIT` and emits a single `larch_err` line naming the remaining count and noting pinned entries.
- Delete `list_cached_versions()` (lines 102-113 plus surrounding blank-line hygiene). Keep `sort_versions()` and all other helpers untouched.
- Extend `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh` with one scenario where every cached version is pinned, asserting the new warning appears in stderr.

### Surfaces in scope
- `skills/upgrade-larch/scripts/upgrade-larch.sh`
- `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`

### Open questions
- None.
