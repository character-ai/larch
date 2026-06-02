# scripts/ci-decide.sh — contract

`scripts/ci-decide.sh` is the pure decision-matrix helper invoked by `scripts/ci-wait.sh` to map current CI state and loop counters to the next action (`merge`, `already_merged`, `rebase`, `wait`, `bail`). No side effects: input via flags, output via `KEY=value` lines on stdout. Merge is always allowed when CI passes and the branch is up-to-date with main, regardless of safety limits; safety limits (`iteration >= 50`, `rebase_count >= 20`, `fix_attempts >= 10`) only block non-merge actions. Edits must keep the decision matrix in lockstep with the table in the script header and the `ci-wait.md` contract that consumes the action tokens.

## Terminal `BAIL_REASON` tokens

At the `fix_attempts >= 10` cap, `ci-decide.sh` emits `ACTION=bail` with **`BAIL_REASON=fix-attempts-exhausted`** (exact token, no prose). `ci-wait.sh` forwards that line verbatim on stdout. `scripts/ship-pr.sh` `needs_user_bail_reason` treats this token (and `design-flaw`, `escalate`, `all-vendors-failed`) as an operator-input bail, exiting **3** with `BAIL_NEEDS_USER_INPUT=true` — see `/implement` Step 16 in `skills/implement/SKILL.md`. This path is distinct from vendor-fix outer exhaustion (`run_evaluate_failure` → `exit_stall` with `STALL_STEP=10-max-retries` / exit **4** for `ci-initial`).
