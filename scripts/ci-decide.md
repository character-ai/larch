# scripts/ci-decide.sh — contract

`scripts/ci-decide.sh` is the pure decision-matrix helper invoked by `scripts/ci-wait.sh` to map current CI state and loop counters to the next action (`merge`, `already_merged`, `rebase`, `wait`, `bail`). No side effects: input via flags, output via `KEY=value` lines on stdout. Merge is always allowed when CI passes and the branch is up-to-date **or** conflict-free while behind (`--conflicted false`), regardless of safety limits; safety limits (`iteration >= 50`, `rebase_count >= 20`, `fix_attempts >= 10`) only block non-merge actions. When CI passes, the branch is behind, and `--conflicted true`, the action is `rebase`. Edits must keep the decision matrix in lockstep with the table in the script header and the `ci-wait.md` contract that consumes the action tokens.

## Inputs

| Flag | Meaning |
|------|---------|
| `--status` | `pass`, `fail`, `pending`, or `merged` from `ci-status.sh` |
| `--behind` | Non-negative commit count behind base from `ci-status.sh` |
| `--conflicted` | `true`/`false` — derived from `mergeStateStatus` in `ci-status.sh` (`DIRTY`/`UNKNOWN`/empty → `true`; default `false` when omitted) |
| `--iteration` | Outer poll-loop iteration (caller re-invocations after rebase/fix) |
| `--rebase-count` | Rebases performed so far |
| `--fix-attempts` | CI fix attempts so far |

## Terminal `BAIL_REASON` tokens

At the `fix_attempts >= 10` cap, `ci-decide.sh` emits `ACTION=bail` with **`BAIL_REASON=fix-attempts-exhausted`** (exact token, no prose). `ci-wait.sh` forwards that line verbatim on stdout. `scripts/ship-pr.sh` `needs_user_bail_reason` treats this token (and `design-flaw`, `escalate`, `all-vendors-failed`) as an operator-input bail, exiting **3** with `BAIL_NEEDS_USER_INPUT=true` — see `/implement` Step 16 in `skills/implement/SKILL.md`. This path is distinct from vendor-fix outer exhaustion (`run_evaluate_failure` → `exit_stall` with `STALL_STEP=10-max-retries` / exit **4** for `ci-initial`).
