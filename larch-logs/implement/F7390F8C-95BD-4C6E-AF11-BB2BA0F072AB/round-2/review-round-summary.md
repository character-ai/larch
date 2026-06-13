# Review Round 2

- Mode: `diff`
- 5 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Absorbed 1.r routing docs still branch on wrapper exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Procedural routing in `rebase-checkpoint-routing.md` and the Rebase Checkpoint Macro in `SKILL.md` still instruct branching on probe/wrapper process exit code for absorbed Step 1.r. Bootstrap invoke returns exit 0 while `REBASE_RC` holds the probe rc; on `ROUTE=conflict` (`REBASE_RC=1`, wrapper rc 0) the orchestrator can follow the exit-0 branch and proceed to Step 2 with unresolved conflicts, or double-run 1.r. For absorbed 1.r only, branch on envelope `REBASE_RC` and `ROUTE`; keep process-rc instructions for 4.r, 7.r, and 7a.r.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: For 1.r only branch on envelope REBASE_RC and ROUTE; keep process-rc instructions for 4.r 7.r 7a.r.
  - From cursor-specialist-correctness-output.txt: Add 1.r-specific macro text: use envelope REBASE_RC and ROUTE not step-0-bootstrap.sh exit code.
  - From cursor-specialist-edge-cases-output.txt: Add a Step 1.r-specific branch: use envelope ROUTE/REBASE_RC/REBASE_* only; never re-invoke the probe; treat REBASE_RC as probe rc.


### FINDING_10: Absorbed tail and routing table can emit `ROUTE=continue` despite Step 2 blockers
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `_continue_predicate` only checks bail, stall, readable `PLAN_FILE`, and non-empty `coder`; it does not mirror Step 2 blockers in `_phase_coder` (`REPO_UNAVAILABLE`, `feature-description.txt`) or the routing row at `skills/implement/SKILL.md:282`. On resume, `_preserve_resume_routing` can restore `coder` while those other guards still fail; the absorbed tail then runs the degraded gate and 1.r probe and can emit `ROUTE=continue` even though the run should not reach Step 2. The happy-path routing row now requires `ROUTE=continue` and is listed before the `REPO_UNAVAILABLE=true` row, so a first-match router can take the happy path and enter Step 2 instead of the cleanup row. This mis-route is easier now because `ROUTE=continue` is synthesized inside bootstrap rather than only after separate orchestrator gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Extend `_continue_predicate` (and tests) to require `REPO_UNAVAILABLE != "true"`, readable `$IMPLEMENT_TMPDIR/feature-description.txt`, and any other conditions the Step 0 routing table uses to block Step 2, so the absorbed tail matches the old prompt-side guards.
  - From dyn-architecture-output.txt: Move `REPO_UNAVAILABLE=true` (and missing `feature-description.txt`) above the `ROUTE=continue` row, and/or have bootstrap omit `ROUTE` when `REPO_UNAVAILABLE=true` or required plan artifacts are missing.


### FINDING_2: Resume absorbed continue tail skipped when `coder` cannot be restored
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-code-robustness-output.txt
- **Severity**: important
- **Concern**: Resume `--mode` does not emit `coder` on bootstrap stdout (`coder = ""` when `args.mode == "resume"`, and `up_to_phase="plan"` skips `_phase_coder`). The absorbed continue tail only runs when `_preserve_resume_routing` restores `coder` from a regular `bootstrap-routing.env`. Resume skips `_preserve_resume_routing` for symlinked routing files; if the file is missing (`_atomic_text` failure still returns exit 0), symlinked, or non-regular, `_continue_predicate` fails and internal 1.r is skipped. That breaks the post-`DEGRADED_PROMPT_REQUIRED` Continue path and can cause false missing-`ROUTE` stall or Step 2 without rebase vs prior standalone fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore coder from trusted source on resume or define explicit tail behavior when routing file is symlinked.
  - From dyn-code-robustness-output.txt: After `_preserve_resume_routing`, if resume mode still has no `coder`, read `coder` / `coder_fallback` from `$IMPLEMENT_TMPDIR/session-env.sh` or `run-flags.sh` (or persist them there on initial bootstrap). Alternatively, treat a readable `PLAN_FILE` plus restored presence keys as sufficient to run the absorbed tail on resume, since 1.r does not need `coder`. Add an integration test for resume after routing-file write refusal and after `DEGRADED_PROMPT_REQUIRED` Continue.


### FINDING_7: Non-TTY stdin misclassified as non-interactive
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Normal `/implement` Bash calls can be misclassified as non-interactive because the fallback treats non-TTY stdin as non-interactive. In Claude Code, Bash execution commonly has non-TTY stdin while the skill can still call `AskUserQuestion`, so both tools down will log and proceed instead of emitting `DEGRADED_PROMPT_REQUIRED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: remove the stdin TTY fallback from the canonical predicate, or make the wrapper default interactive unless an explicit non-interactive signal is present.


### FINDING_8: combine-issues audit-edge write command omits required CLI args
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The approved audit-edge write command in `.claude/skills/combine-issues/SKILL.md:329` omits the required `--client-issue` and `--blocker-issue` arguments. When an operator approves an audit edge, following this prompt runs an invalid `issue add-blocked-by --repo "$REPO"` command, so the dependency edge is never written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: document the full command shape: `python3 "$PWD/python/cli.py" issue add-blocked-by --client-issue <client> --blocker-issue <blocker> --repo "$REPO"`.


