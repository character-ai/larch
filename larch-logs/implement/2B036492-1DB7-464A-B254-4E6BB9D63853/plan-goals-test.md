## Goal
Detect and warn on OOS-bundled files before dispatcher commits

## Implementation Plan

### Goal
Detect and warn when an external implementer writes files to the working tree that are not declared in its manifest (OOS-bundled files), making contamination visible before the `git add -A && git commit` in `step2-implement.sh`.

### Files to modify
- `skills/implement/scripts/step2-implement.sh` — add OOS-bundle detection between Step 7a and Step 7b
- `skills/implement/scripts/test-step2-dispatch.sh` — add regression test (Test 18) for OOS detection
- `agents/codex-implementer.md` — add NEVER #8: do not modify files outside plan scope
- `agents/cursor-implementer.md` — parity: add NEVER #7: do not modify files outside plan scope

### Step 1 — OOS detection in `step2-implement.sh`

Insert after the `paths_invalid == "true"` bail block (Step 7a, ~line 650) and before the
`# 7b: dispatcher commits` comment block, still inside the `if [[ "$STATUS" == "complete" ]]; then`
guard. The check:

1. Enumerate working-tree changes via `git -C "$REPO_ROOT" status --porcelain`. Extract filenames
   (last field of each line).
2. Enumerate manifest-declared files: `jq -r '[.files_touched[].path, .tests_added_or_modified[]] | .[]'`
   from `$MANIFEST_RAW_PATH`.
3. Compute OOS = (working-tree files) ∖ (manifest-declared files) using sorted `comm -23`.
4. If OOS non-empty, call `append-execution-issue.sh --log "$TMPDIR_ARG/execution-issues.md"
   --category Warnings --entry "..."` listing the count and first 5 OOS paths.

Guard with `[[ -x "$APPEND_TOOL" && -d "$TMPDIR_ARG" ]]`; wrap the entire block in `|| true`
so a failure doesn't crash the dispatcher. Warn but don't bail — the existing revert mechanism
remains the safety net.

### Step 2 — Regression test in `test-step2-dispatch.sh`

Add Test 18 before the summary block. Pattern: scratch git repo (like Test 16), stub Codex that
writes a manifest declaring one file, plus an extra OOS file written to the working tree by hand
(simulating what Codex did). Run the dispatcher; check that `execution-issues.md` in the tmpdir
contains the OOS warning.

### Step 3 — `agents/codex-implementer.md` NEVER list

After NEVER #7, add NEVER #8:
```
8. **NEVER modify files outside the plan's stated scope.** If you notice an issue in an
   out-of-plan file, record it in `oos_observations[]` instead of editing it. The dispatcher
   detects undeclared working-tree changes and logs a Warning; the reviewer pipeline is the
   backstop. Editing unrelated files contaminates the PR diff and makes OOS contamination
   harder to review.
```

### Step 4 — `agents/cursor-implementer.md` parity

After NEVER #6, add NEVER #7 with identical text (same rule as Codex).

### Edge cases
- Empty manifest `files_touched`: all working-tree changes appear as OOS — correct.
- Working tree clean (no changes): `git status --porcelain` returns empty; check is a no-op.
- Renamed files (`R  old -> new`): `awk '{print $NF}'` picks up `new` (the created path); fine.
- `append-execution-issue.sh` absent or non-executable: guarded; check silently skips.
- `TMPDIR_ARG` not a directory (degenerate dispatcher invocation): guarded with `[[ -d "$TMPDIR_ARG" ]]`.

### Testing strategy
- `/relevant-checks` (pre-commit + agent-lint) after each file edit.
- Test 18 in `test-step2-dispatch.sh`: verify the Warning appears in `execution-issues.md` when
  OOS files are present.

## Test plan
(no test plan section in plan-file)
