## Goal
Change health-check probe retry sleep default from 10s to 3s in check-reviewers.sh; confirm retries and mutex are already present

## Implementation Plan
## Findings from codebase research

`check-reviewers.sh` already has:
- Retry loop: `MAX_ATTEMPTS=3` (3 total attempts — matches the user's requirement)
- Mutex: `external_serial_lock_acquire` guards both `codex` and `cursor` probe spawns
- Gemini probe was removed in #1720; `session-setup.sh` hard-codes GEMINI_HEALTHY=false

Only actual delta: `SLEEP_BETWEEN` defaults to 10 s (`LARCH_TEST_PROBE_SLEEP_SECONDS:-10`); user wants 3 s.


### 1. Change default inter-retry sleep from 10 s → 3 s (`scripts/check-reviewers.sh`)

Edit line 269:
  `SLEEP_BETWEEN="${LARCH_TEST_PROBE_SLEEP_SECONDS:-10}"`
→ `SLEEP_BETWEEN="${LARCH_TEST_PROBE_SLEEP_SECONDS:-3}"`

### 2. Update prose in `scripts/check-reviewers.md`

- "with a 10-second sleep between attempts" → "with a 3-second sleep between attempts"
- Worst-case duration line: 2 × 10 s → 2 × 3 s, update to ≈ 366 s (~6m6s)

### 3. Update comment in `scripts/test-check-reviewers.sh`

Line 12: "a 10s sleep cycle. Production probes inherit the default 10s."
→ "a 3s sleep cycle. Production probes inherit the default 3s."


## Test plan

`make test-harnesses` (the harness overrides LARCH_TEST_PROBE_SLEEP_SECONDS=0 so tests pass at any default)
