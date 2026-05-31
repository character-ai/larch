## Proposed Design Outline

### Goals
- Close OOS #3229 by adding the missing regression coverage for the `cleanup.sh` find-failure fail-safe (gap 2).
- Correct the stale `cleanup.md` so it accurately documents the current `maxdepth 5` nested-activity retention, the find-failure fail-safe, and the depth-bound tradeoff (gap 1's "document the tradeoff" half).

### Non-goals
- No change to `cleanup.sh` runtime behavior — the nested scan already exists; this is a comment-only edit there.
- Do not make the depth bound configurable or change the `maxdepth 5` value.
- No changes to retention semantics, the `/tmp` pattern list, or symlink reaping.

### Approach sketch
- Add a `find`-failure regression case to `test-cleanup.sh` reusing the existing `PATH_PREFIX` stub-injection pattern; the stub fails only on the `should_remove_by_age` nested scan (keyed on the `-maxdepth 5` / `-quit` signature) and delegates every other `find` call to the real binary.
- Assert the fail-safe contract: warning emitted, stale dir retained, `CACHE_REMOVED=0`, exit 0.
- Add a short clarifying comment in `cleanup.sh` near `should_remove_by_age` (depth bound + skip-on-scan-failure rationale).
- Fix the inaccurate retention/enumeration bullets in `cleanup.md`; keep `test-cleanup.md` edit-in-sync (note the new case).

### Surfaces in scope
- `skills/cleanup/scripts/test-cleanup.sh` (new find-failure test case)
- `skills/cleanup/scripts/cleanup.sh` (comment only)
- `skills/cleanup/scripts/cleanup.md` (doc correction)
- `skills/cleanup/scripts/test-cleanup.md` (edit-in-sync note)

### Open questions
- None.
