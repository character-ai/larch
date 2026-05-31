## Decision 1: Root cause and fix layer
- **Question**: Is the undocumented exit 2 caused by a missing exit-code translation in `run_evaluate_failure` (the issue's stated premise), or by a `set -e` state leak?
- **Resolution**: `set -e` state leak. `ship-pr.sh` runs `set +e` by design (line 4-7, "Intentionally no set -e"). `run_pr_prep_phase` and its OOS-gate helper unconditionally re-enable `set -e` at lines 1052 / 1557 / 1567 after their `set +e` blocks, instead of the save/restore idiom at line 139-147. The leaked errexit reaches the CI-fix phases, where `_run_per_job_command_capture` (line 2265) runs the local harness with a set-e-fragile `cmd > log 2>&1; rc=$?` capture; a failing harness aborts the whole script with the raw harness code (2) before `_RCC_CMD_RC=$?` runs. Fix: make the three leak sites save/restore errexit AND make the harness rc-capture sites defensively `-e`-safe (defense-in-depth).
- **Source**: codebase + user

## Decision 2: Routing scope for confirmed failures
- **Question**: After the crash is fixed, should confirmed local failures be re-routed to the autonomous main-agent CI-fix path (`BAIL_REASON=first-fixer-non-health`, exit 3 autonomous) as the issue suggests?
- **Resolution**: No. Keep the existing documented exits (`ci-local-unfixable` exit 3 user-input path; `…-max-retries` stall exit 4). Re-routing confirmed failures to the autonomous main-agent path is a separate behavioral change and is out of scope for this fix.
- **Source**: user

## Decision 3: Hard constraints and non-goals
- **Question**: What must be preserved, and what is explicitly out of scope?
- **Resolution**: Preserve the documented "no `set -e`" invariant. Preserve existing rc-capture semantics — the hardened capture sites must still record the command's real exit code. Maintain Bash 3.2 portability (no Bash 4+ constructs). Do NOT change `run_evaluate_failure` exit-code routing. Do NOT touch the `review-and-fix.sh` `classifier-failed` bug from the reproduction context (separate incident detail, out of scope). The fix is confined to the errexit-toggle sites and the CI-fix harness/helper rc-capture sites in `ship-pr.sh`.
- **Source**: codebase + user
