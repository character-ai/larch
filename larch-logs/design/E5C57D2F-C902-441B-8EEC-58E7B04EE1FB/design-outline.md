## Proposed Design Outline

### Goals
- Stop `ship-pr.sh` from crashing with undocumented exit 2 when a local CI harness confirms a failure.
- Restore the documented "no `set -e`" invariant by fixing the errexit leak in `run_pr_prep_phase`.
- Harden the CI-fix harness rc-capture so a future errexit leak cannot crash a harness run.

### Non-goals
- No re-routing of confirmed failures to the autonomous main-agent path (`first-fixer-non-health`) — separate follow-up.
- No change to `run_evaluate_failure` exit-code routing or the documented exit table.
- No fix to the `review-and-fix.sh` `classifier-failed` bug from the reproduction context.

### Approach sketch
- Replace the unconditional `set -e` at lines 1052/1557/1567 with the save/restore idiom already at line 139-147 (snapshot `$-`, restore only if errexit was on).
- Make `_run_per_job_command_capture` capture the harness rc without aborting under errexit (e.g. `cmd … || _RCC_CMD_RC=$?`).
- Audit peer `cmd; rc=$?` capture sites in the CI-fix path and harden the harness-running ones.
- Add regression coverage that a failing local harness no longer propagates a raw exit code.

### Surfaces in scope
- `scripts/ship-pr.sh` — errexit toggle sites + harness rc-capture.
- `scripts/test-ship-pr.sh` — regression test.
- `scripts/ship-pr.md` — sibling contract note (only if behavior wording needs it).

### Open questions
- None.
