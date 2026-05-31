## Decision 1: Fix scope — test + documentation, no behavior change
- **Question**: Gap 1's bounded nested-scan already exists and is tested; how should this OOS fix be scoped?
- **Resolution**: Minimal fix. (a) Add the gap-2 find-failure test to `test-cleanup.sh`; (b) correct the stale `cleanup.md` so it describes the real `maxdepth 5` nested-activity scan, the find-failure fail-safe, and the depth-bound tradeoff; (c) add a short clarifying comment in `cleanup.sh` near `should_remove_by_age`. No change to `cleanup.sh` runtime behavior. Do NOT make the depth bound configurable or alter the depth.
- **Source**: user

## Decision 2: Proceed with the design, then close via /implement
- **Question**: "Close the issue" — close without code, or do the minimal fix first?
- **Resolution**: Do the minimal fix first; write the `larch:plan` to issue #3229; closure happens through the normal `/implement` → merge flow.
- **Source**: user

## Decision 3: Hard constraints (codebase-derived)
- **Question**: What must not break?
- **Resolution**: `cleanup.sh` runtime behavior is unchanged (comment-only edit). The new find-stub test MUST target only the `should_remove_by_age` nested scan (key on the `-maxdepth 5` / `-quit` signature) and delegate every other `find` invocation to the real binary, so cache enumeration, `/tmp` passes, and symlink reaping still work. All existing `test-cleanup.sh` cases must continue to pass. Bash 3.2 compatibility is preserved. Keep edit-in-sync siblings (`test-cleanup.md`) consistent.
- **Source**: codebase
