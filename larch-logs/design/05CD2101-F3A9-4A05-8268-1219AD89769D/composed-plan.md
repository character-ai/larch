## Plan

### Files to modify

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.sh`

Two surgical edits.

1. **Cap-overflow warning (Part A from #2993).** After the `while [ "$VERSION_COUNT" -gt "$KEEP_LIMIT" ]` loop closes (around line 388), but still inside the outer `if [ "$VERSION_COUNT" -gt "$KEEP_LIMIT" ]` block, add a post-loop guard:

   ```bash
   if [ "${#SANITIZED_VERSIONS[@]}" -gt "$KEEP_LIMIT" ]; then
       larch_err "Warning: cache cap (${KEEP_LIMIT}) exceeded — ${#SANITIZED_VERSIONS[@]} versions remain; pinned entries or prune failures blocked full trim."
   fi
   ```

   The warning text names **both** causes (pinned entries and `rm -rf` failures) because the loop can exit with `${#SANITIZED_VERSIONS[@]} > KEEP_LIMIT` from either path: every remaining version pinned by `LATEST_STABLE` or `ACTIVE_SESSION_VERSIONS`, or every removable candidate already in `PRUNE_FAILED_VERSIONS`. The `else` branch ("No old versions to prune.") at the bottom of the same `if`/`else` is unaffected.

2. **Remove dead `list_cached_versions()` (revised Part B from #2992).** Delete the function definition at lines 102-113 plus the blank line that separates it from `stat_mtime()` below. Keep `sort_versions()` intact — it has two live callers outside the dead function: `version_gt()` (line 50, called from the prune-newer-than-stable branch at line 324) and `collect_active_session_versions()` (line 194, called from line 308 in the prune-path active-session-pin scan).

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.md`

Update the prune-step description so it mentions the new post-loop cache-cap warning: when the trim loop exits with retained set still above `KEEP_LIMIT`, the script logs a stderr warning naming the remaining count and identifying pinned entries or prune failures as the cause. Keep the rest of the prune contract text unchanged. Also drop any incidental reference to `list_cached_versions()` if one appears (none was found in the current sibling doc, so this is defensive only).

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`

Add one scenario: every cached version is pinned (each appears in either `LATEST_STABLE` or `ACTIVE_SESSION_VERSIONS`) and cache size > 8. Reuse existing fixture helpers (`make_plugin_root`, `write_stub_claude`, the active-session env-file pattern). Assert two things on the captured run output:

- The new `larch_err` line is present with the expected count and pinning prose (use `assert_contains` with a stable substring such as `"cache cap (8) exceeded"`).
- The cache directory still contains all pre-run version directories (no eviction occurred).

### Approach

- The Part A fix is a single 3-line `if` block. Reuse `larch_err` to match existing warning style (`warn_prune_failure`, `warn_preserved_active_version_once`).
- Place the new guard inside the outer `if [ "$VERSION_COUNT" -gt "$KEEP_LIMIT" ]` so caches that started at or below the cap never produce a spurious warning.
- Use `${#SANITIZED_VERSIONS[@]}` in the new check to match the acceptance text verbatim. `VERSION_COUNT` mirrors the same value throughout the loop.
- Warning text covers both causes (pinned entries and `rm -rf` failures) with one static message — no conditional branching on `PRUNE_FAILED_VERSIONS` emptiness. Simpler than a per-cause split and still accurate.
- The Part B scope correction (operator-confirmed in Step 1c) is the minimum-change reading: drop only the genuinely dead helper. `sort_versions()` removal would break `version_gt()` and `collect_active_session_versions()` and is explicitly out of scope.
- Sibling-doc update for `upgrade-larch.md` is required by `.claude/rules/script-md-siblings.md`: behavior changes to a `scripts/*.sh` file ship with the matching `.md` update in the same commit.

### Edge cases

- **Cache started at or below cap.** Outer `if` is false; new warning never runs.
- **Loop drains cleanly.** Final `${#SANITIZED_VERSIONS[@]}` is `KEEP_LIMIT`; warning suppressed.
- **All entries pinned.** Loop exits with `REMOVED_VERSION=false`, count unchanged; warning fires once.
- **All removable candidates fail `rm -rf`.** Per-failure `warn_prune_failure` calls already log each failure; the new warning also fires because `${#SANITIZED_VERSIONS[@]}` is still > cap. The unified warning text covers this case — no double-counting because the new line is one summary, not per-version.
- **Mixed pinning plus `rm -rf` failures.** Same as above; one summary warning plus the existing per-failure warnings.
- **`KEEP_LIMIT` changes in future.** Message uses `${KEEP_LIMIT}` so any cap change propagates to the warning text automatically.

### Testing strategy

- Extend `test-upgrade-larch-prune.sh` with the all-pinned scenario described above (one new test function or appended block, plus a single dispatch call from the test runner).
- `make test-upgrade-larch-prune` and `make test-upgrade-larch` to confirm existing coverage still passes after deleting `list_cached_versions()`.
- `bash -n skills/upgrade-larch/scripts/upgrade-larch.sh` for parse hygiene.
- `bash scripts/relevant-checks.sh` (or `make lint`) before commit; this also exercises the script-md-siblings linter so the `upgrade-larch.md` update is verified in CI.

## Acceptance

- When the cap-trim loop exits with `${#SANITIZED_VERSIONS[@]} > 8`, `upgrade-larch.sh` emits a stderr warning via `larch_err` naming the remaining count and identifying pinned entries or prune failures as the cause (item A from #2993; the original wording "pinned entries blocked full trim" was widened during plan review to cover both causes).
- `list_cached_versions()` is removed from `skills/upgrade-larch/scripts/upgrade-larch.sh` (revised item B from #2992). `sort_versions()` is retained because `version_gt()` (line 50) and `collect_active_session_versions()` (line 194) still call it; removing `sort_versions()` would break the live prune path.
- The existing prune behavior (mtime-ordered, pinned-aware, per-failure warnings) is otherwise unchanged.
- `skills/upgrade-larch/scripts/upgrade-larch.md` is updated so its prune-step description mentions the new post-loop cache-cap warning (sibling-doc invariant from `.claude/rules/script-md-siblings.md`).
- A new scenario in `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh` exercises the all-pinned cap-overflow path and asserts the warning appears in stderr with no evictions occurring.

diff_lines: 65
