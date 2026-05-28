## Decision 1: Test assertion target
- **Question**: Given SKILL.md Step 0b aborts (`exit 1`) on a `write-run-params.sh` non-zero exit *before* the router-flag recovery block runs, what should the new test case prove?
- **Resolution**: Prove the writer-failure abort short-circuits recovery — a failing writer must abort before `recovery_merge_if_needed` runs (recovery bypassed). Include a success-path positive control proving recovery DOES run after a successful write. No `/design` behavior change.
- **Source**: user

## Decision 2: Change scope
- **Question**: How wide should the change be?
- **Resolution**: Edit `scripts/test-step0b-router-flag-recovery.sh` and its sibling `scripts/test-step0b-router-flag-recovery.md` only. No SKILL.md behavior change; no new `scripts/test-design-structure.sh` pin.
- **Source**: user

## Decision 3: Is the recovery path reachable on a hard writer failure? (hard constraint)
- **Question**: Does SKILL.md Step 0b reach the router-flag recovery block after a `write-run-params.sh` non-zero exit?
- **Resolution**: No. SKILL.md Step 0b treats a writer non-zero exit as contract drift and aborts with `exit 1` before the recovery block. `scripts/test-design-structure.sh` also forbids any "run-params write failed; router-flag recovery" prose in SKILL.md. The new test must encode this boundary, not contradict it.
- **Source**: codebase
