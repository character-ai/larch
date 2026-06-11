## Goal
Implement issue #4023: [IMPLEMENTING] [BUG] (URGENT) /design Step 3: remove --mode arg from orchestrator surface to prevent single-round regression\n\n## Symptoms.

## Implementation Plan
## Symptoms

During a SIMPLE-tier `/design 3988` run, the Step 3 review loop ran only 1 round instead of up to 5. After round 1 the main orchestrator received control with `LOOP_STATUS=complete`, manually applied 15 accepted findings directly to `plan.txt`, and proceeded to Gate B without any continuation check. Rounds 2–5 were never run.

## Context

SKILL.md Step 3 specifies the correct entry point as the `design-step3-review.sh` wrapper, which internally hardcodes `--mode loop`. That script-internal multi-round controller runs all review rounds, applies accepted findings via `revise-plan-with-waterfall.sh`, and only returns to the main agent for specific handoffs (`main-agent-vote-required`, `main-agent-apply-required`, etc.).

`--mode single` is labeled "legacy" in `run-step3-review.sh` line 5 and in SKILL.md: *"Legacy single-round LOOP_STATUS mapping for harnesses and manual `--mode single` calls"*. It runs exactly one round and exits — semantically incompatible with the up-to-5-round convergence requirement.

## Root Cause

1. The orchestrator attempted `run-step3-review.sh --mode launch --session-env-path ...` — an invented `--mode launch` value plus `--session-env-path`, which that script does not accept. The call failed with a usage error.

2. Instead of re-reading the SKILL.md fence verbatim, the orchestrator fell back to the usage line from the failed call: `[--preview-only | --no-preview | --mode single|loop]`. It picked `single`.

3. The correct wrapper `design-step3-review.sh` was never invoked.

The enabling condition is that `--mode` exists as a public argument on `run-step3-review.sh` with `single` as a valid value. When the orchestrator bypasses the wrapper and reaches the inner script, it has a recovery path to a valid-looking but semantically wrong invocation. The failure is silent: `--mode single` exits 0 with `LOOP_STATUS=complete` after one round, giving no indication that anything went wrong.

## Recommended Fix

Remove the `--mode` argument from the public surface entirely, so any bypass of `design-step3-review.sh` fails with a usage error rather than silently running one round.

1. **`run-step3-review.sh`**: remove `single` as a publicly accepted `--mode` value. If `single` must be retained for test harnesses, gate it behind a private flag (e.g. `--legacy-single-round` or an env var) so the usage line no longer shows it.

2. **`design-step3-review.sh`**: confirm it does not accept or expose a `--mode` flag; it should drive `--mode loop` internally without the caller being able to override it.

3. **SKILL.md Step 3 fence**: the fence already shows `design-step3-review.sh` with no `--mode` argument — no change needed. Audit any prose that mentions `--mode single` and remove or mark deprecated.

4. **Harness impact**: `test-run-step3-review.sh` tests that call `--mode single` directly should be updated to the new private flag name or refactored to call the internal round body function directly.

This ensures the orchestrator has one correct entry point with no mode choice to get wrong.


## Test plan
(no test plan section in plan-file)
