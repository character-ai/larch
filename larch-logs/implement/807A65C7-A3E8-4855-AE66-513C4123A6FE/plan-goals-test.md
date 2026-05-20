## Goal
Add transient API error documentation to dispatch-code-voters.md Behavior section

## Implementation Plan

**Goal**: Add one paragraph to the end of the `## Behavior` section in `scripts/dispatch-code-voters.md` documenting the `voter1_rc=1` + non-empty `output_bytes` + empty launcher-stderr pattern as an accepted transient API-level error.

**File**: `scripts/dispatch-code-voters.md`

**Location**: After line 30 (the `DISPATCH_OK` sentence that ends the Behavior section), before the `## Output` heading at line 32.

**Content to add**:

```
A `voter1_rc=1` exit with non-zero `output_bytes` and empty launcher-stderr indicates the claude CLI received an API-level error response (rate limit, server overload, or transient auth failure) rather than a wrapper validation failure; the CLI exits 1 with JSON error body on stdout while the `launch-claude-review.sh` shell wrapper passes all its own checks and emits nothing to stderr. This shape is distinct from `voter1_rc=2`, which indicates a wrapper validation failure caught inside `launch-claude-review.sh` before the CLI return. When only Voter 1 is affected, the 2-judge fallback (Voters 2 and 3) is the accepted recovery; no manual intervention is required. See #2433 for the investigation that identified and characterized this pattern.
```

**Verification**: `make lint` (pre-commit on the modified file) should pass.

## Test plan
(no test plan section in plan-file)
