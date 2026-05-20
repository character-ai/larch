## Goal
Include first 200 bytes of voter output in voter1-diag.txt when voter1_rc != 0

## Implementation Plan

### 1. scripts/dispatch-code-voters.sh
In the voter1 failure diagnostic block (lines ~320-335), inside the `{...}` subshell that writes voter1-diag.txt, add a new section after the `output_bytes` printf:

```bash
if [[ "$voter1_rc" -ne 0 && -s "$VOTER_1_PATH" ]]; then
    printf -- '--- first 200 bytes of voter output ---\n'
    head -c 200 "$VOTER_1_PATH"
    printf '\n'
fi
```

Guard: `voter1_rc -ne 0` (we are already inside the outer `voter1_rc != 0 || empty` block, but the new section is specifically for the non-zero-rc case) AND `-s "$VOTER_1_PATH"` (non-empty output).

### 2. scripts/test-dispatch-code-voters.sh
a. Add `fail_nonempty` case to the claude stub (writes content to stdout, exits 7).
b. In the `happy` section after the existing `CLAUDE_STUB_MODE=empty` test, add a test that uses `CLAUDE_STUB_MODE=fail_nonempty` and asserts the `--- first 200 bytes of voter output ---` section appears in the execution-issues Warning.

### 3. scripts/dispatch-code-voters.md
Update the sibling doc to reflect the new voter1-diag.txt field.


## Test plan
Run: scripts/test-dispatch-code-voters.sh --section happy
