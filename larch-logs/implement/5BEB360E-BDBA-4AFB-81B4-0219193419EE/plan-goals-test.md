## Goal
Move timing-ledger marks into factored scripts and fix post-design boundary precondition gaps

## Implementation Plan

Fix post-#1891 wiring regression: four independent precondition/side-effect gaps where factored scripts fail when invoked without prose-side setup.

### A — Timing/token-ledger marks (Steps 4, 7, 7a)

Files: `skills/implement/scripts/commit-implementation.sh`, `commit-review-fixes.sh`, `generate-code-flow-diagram.sh`, `skills/implement/SKILL.md`

Add `token-ledger.sh mark "Step N — ..."` and `timing-ledger.sh mark "Step N — ..."` calls to the top of each script's main body (after arg parsing, before the primary action). Remove the now-redundant marks from SKILL.md prose blocks (lines 1286-1289, 1492-1495, 1534-1537).

Pattern (each script already has PLUGIN_ROOT; marks inherit LARCH_TIMING_LEDGER + LARCH_TOKEN_SESSION_ID from caller environment):
```bash
"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step N — ..." || true
"$PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step N — ..." || true
```

### B — feature-description.txt path

Files: `skills/design/scripts/write-design-manifest.sh`

After copying plan/tally/etc to STAGE_DIR, also copy feature-description.txt to IMPLEMENT_TMPDIR (outside the staging pattern since it is not a manifest artifact):
```bash
if [[ -f "$DESIGN_TMPDIR/feature-description.txt" ]]; then
    cp "$DESIGN_TMPDIR/feature-description.txt" "$IMPLEMENT_TMPDIR/feature-description.txt"
fi
```
Place after the final `mv` of manifest artifacts (before `emit_kv MANIFEST_WRITTEN`). No sibling-path security check needed since the destination is $IMPLEMENT_TMPDIR, not design-export.

### C — PLAN_FILE/FEATURE_FILE in session-env

Files: `skills/implement/scripts/post-design-boundary.sh`

After READER_OUT is captured and validated (before the hook-mode branch), extract PLAN_FILE from READER_OUT and atomically write PLAN_FILE + FEATURE_FILE keys to SESSION_ENV_PATH:
```bash
_PLAN_FILE=$(printf '%s\n' "$READER_OUT" | awk -F= '/^PLAN_FILE=/{print substr($0, index($0,"=")+1); exit}')
if [[ -n "$_PLAN_FILE" && -n "$SESSION_ENV_PATH" && -f "$SESSION_ENV_PATH" ]]; then
    _FEATURE_FILE="$IMPLEMENT_TMPDIR/feature-description.txt"
    _TMP=$(mktemp "${SESSION_ENV_PATH}.tmp.XXXXXX")
    { grep -v '^PLAN_FILE=' "$SESSION_ENV_PATH" | grep -v '^FEATURE_FILE='; \
      printf 'PLAN_FILE=%s\n' "$_PLAN_FILE"; \
      printf 'FEATURE_FILE=%s\n' "$_FEATURE_FILE"; } > "$_TMP" \
    && mv "$_TMP" "$SESSION_ENV_PATH" || rm -f "$_TMP"
fi
```
This runs for both hook-mode and non-hook-mode since both need the keys written.

### D — parent-issue.md write in post-tracking-issue.sh

Files: `skills/implement/scripts/post-tracking-issue.sh`, `skills/implement/SKILL.md`

Add `--issue-number <N>` and `--adopted <true|false>` parameters to `post-tracking-issue.sh`.
- When `--issue-number` is provided, use it directly for ISSUE_NUMBER (skip reading from parent-issue.md)
- After successful metadata post, write `parent-issue.md` with ISSUE_NUMBER, RUN_ID, ADOPTED
- When `--issue-number` is NOT provided, read from existing parent-issue.md (Branch 1 resume)

Update SKILL.md:
- Branch 2 call: `post-tracking-issue.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --issue-number "$ISSUE_ARG" --adopted true`
- Remove the separate "Then write $IMPLEMENT_TMPDIR/parent-issue.md:" prose block after Branch 2
- Branch 3 call: add `--issue-number "$RECOVERED_N" --adopted true`
- Remove the separate Branch 3 sentinel write prose
- Branch 4 call: add `--issue-number "$ISSUE_NUMBER" --adopted false`
- Remove Branch 4 Step 6 "Write the sentinel LAST" block
- Update Load-Bearing Invariant #4 to note sentinel is written by post-tracking-issue.sh

### E — Structural test guard

Files: `scripts/test-implement-structure.sh`

Add 3 assertions (after existing ones): each factored script must contain its timing-ledger mark:
```bash
grep -qF 'timing-ledger.sh" mark "Step 4 — commit implementation"' \
  "$REPO_ROOT/skills/implement/scripts/commit-implementation.sh" \
  || fail "commit-implementation.sh must contain Step 4 timing-ledger mark"
# ... similar for commit-review-fixes.sh (Step 7) and generate-code-flow-diagram.sh (Step 7a)
```

### Files touched
- A: `skills/implement/scripts/commit-implementation.sh`, `commit-review-fixes.sh`, `generate-code-flow-diagram.sh`, `skills/implement/SKILL.md`
- B: `skills/design/scripts/write-design-manifest.sh`
- C: `skills/implement/scripts/post-design-boundary.sh`
- D: `skills/implement/scripts/post-tracking-issue.sh`, `skills/implement/SKILL.md`
- E: `scripts/test-implement-structure.sh`
- Sibling .md files for each modified script


## Test plan
- `make lint` (runs test-implement-structure.sh, pre-commit)
- Run `test-post-tracking-issue.sh` and `test-post-design-boundary.sh` manually
