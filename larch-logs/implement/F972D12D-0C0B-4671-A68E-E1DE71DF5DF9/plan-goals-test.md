## Goal
Add CLAUDE_PLUGIN_ROOT rehydration to all SKILL.md Bash blocks and write-session-env.sh

## Implementation Plan

### Goal
Fix CLAUDE_PLUGIN_ROOT not being rehydrated in Bash blocks across skills/implement/SKILL.md,
causing exit 127 when CLAUDE_PLUGIN_ROOT is empty in a nested Bash subshell.

### Files to Modify

1. **scripts/write-session-env.sh**
   - Add `LARCH_CLAUDE_PLUGIN_ROOT=$CLAUDE_PLUGIN_ROOT` to the output when `CLAUDE_PLUGIN_ROOT` is set
   - Location: after the existing `PREV_IMPLEMENT_TMPDIR` line in the CONTENT assembly
   - New arg: `--claude-plugin-root <path>` (optional, like other optional fields)
   - Or simpler: read from env var directly (no new arg needed since write-session-env.sh
     is called from within the /implement skill where CLAUDE_PLUGIN_ROOT is set)
   - The simplest approach: unconditionally emit `LARCH_CLAUDE_PLUGIN_ROOT` if the env var
     is non-empty (no new arg needed)

2. **skills/implement/SKILL.md**
   - Mechanical sweep: for every ```bash block that contains `${CLAUDE_PLUGIN_ROOT}` but
     lacks the CLAUDE_PLUGIN_ROOT rehydration block, insert the rehydration.
   - The rehydration block to insert (after `export IMPLEMENT_TMPDIR` line):
     ```
     if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
       CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
     fi
     export CLAUDE_PLUGIN_ROOT
     ```
   - Strategy: Use a Python script (/tmp/fix-skill-md.py) to parse the fenced bash blocks,
     identify blocks needing the rehydration, and insert it at the right position.
   - Insertion rule:
     - If block has `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"` followed by `export IMPLEMENT_TMPDIR`:
       insert AFTER the `export IMPLEMENT_TMPDIR` line
     - If block starts with `${CLAUDE_PLUGIN_ROOT}/scripts/...` directly (e.g., Rebase Macro, Step 0 single-call blocks):
       insert BEFORE the first `${CLAUDE_PLUGIN_ROOT}` line
     - Step 0 carve-out: blocks containing `export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"`
       are exempt (CLAUDE_PLUGIN_ROOT guaranteed by Claude Code at session start)
   - Note: For Step 0 blocks like `create-branch.sh --check` and `session-setup.sh`,
     CLAUDE_PLUGIN_ROOT is guaranteed by Claude Code. We add the rehydration anyway since
     the guard `[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]` makes it a no-op when already set.
     But blocks before IMPLEMENT_TMPDIR is set (Session Step 0): add WITHOUT $IMPLEMENT_TMPDIR check.

3. **scripts/test-implement-timing-rehydration.sh**
   - Add Invariant C: every ```bash block (after Step 0) that uses `${CLAUDE_PLUGIN_ROOT}` 
     MUST contain the CLAUDE_PLUGIN_ROOT rehydration block
   - Step 0 carve-out: same as Invariant B (block with static LARCH_TIMING_LEDGER export)
   - Additional carve-out: Step 0 single-call blocks (create-branch.sh, session-entry-gate.sh,
     session-setup.sh) - these are before session-env.sh is written

### Approach for write-session-env.sh
The simplest approach that doesn't require a new CLI argument:
- In the CONTENT assembly, unconditionally add `LARCH_CLAUDE_PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT:-}`
  (empty value is fine - the rehydration block handles empty values gracefully)
- This means the key is always present in session-env.sh, making the awk lookup reliable

### Edge Cases
- Step 0 blocks: CLAUDE_PLUGIN_ROOT is guaranteed set; `if [ -z ... ]` guard is a no-op
- Resume case: IMPLEMENT_TMPDIR is set, session-env.sh exists, rehydration works
- Standalone invocations: CLAUDE_PLUGIN_ROOT is set by Claude Code at start

### Testing Strategy
- Extend test-implement-timing-rehydration.sh: add awk-based check that every ```bash block
  after Step 0 that uses ${CLAUDE_PLUGIN_ROOT} has the rehydration guard
- The carve-outs: same as Invariant B (Step 0 block with static LARCH_TIMING_LEDGER export)
- Run pre-commit and agent-lint after changes

### Diff Estimate: ~200+ lines (62 blocks × 4 lines each = ~248 lines added to SKILL.md + 2 lines in write-session-env.sh + ~30 lines in test file)

## Test plan
(no test plan section in plan-file)
