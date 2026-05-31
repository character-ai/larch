### FINDING_1: ISSUE_NUMBER / env refresh before init prelude
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Reordering Step 0b so feature-description is written before init, with env refresh only after rename inside `design-init-runparams.sh`, removes today’s 5.5-bis refresh that bound `ISSUE_NUMBER` before sub-step 6. On `ROUTE=proceed`, the init bash prelude still sources `source-env.sh` and runs the canonical pause-check using `$ISSUE_NUMBER`, but the last refresh may be Step 0a (no `--issue-number`). Until rename completes inside the driver, `source-env.sh` / the `current-design-env` symlink may lack `ISSUE_NUMBER`, widening the pause-save window documented at `skills/design/SKILL.md:282` and risking `set -u` failures, wrong issue binding, or incorrect pause-save behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In design-init-runparams.sh run the single write-design-current-env.sh call before tracking-issue-write.sh rename (still once per init), or add an orchestrator Bash refresh immediately after design-route.sh on ROUTE=proceed
  - From Cursor-Innovation: Keep the minimum pre-init refresh: either restore a proceed-path write-design-current-env.sh call in its own Bash fence before design-init-runparams.sh (same contract as today's 5.5-bis), or reorder design-init-runparams.sh to refresh env first and add an orchestrator fence line that exports ISSUE_NUMBER before the prelude when feature-description stays out-of-band


### FINDING_4: `ERROR` from pause-load dropped from `design-route` result contract
- **Reviewer(s)**: Codex-Edge, Cursor-dyn-phase-contract
- **Severity**: important
- **Concern**: `design-pause-load.sh` emits `LOAD_OK=false` with `ERROR=<token>` for expected restore failures, and Step 0b prose expects those `ERROR` lines to surface before fallthrough. The plan forwards `ERROR` in responsibilities but omits `ERROR` from the `design-route` result-env allowlist, so `phase_driver_read_result_env` drops `ERROR=` from `.design-route-result.env` and malformed pause markers or missing snapshots can degrade to a fresh run without surfacing the reason unless stdout is re-parsed ad hoc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add ERROR to the design-route result allowlist and require the orchestrator to re-emit ERROR lines as warnings on LOAD_OK=false fallthrough.
  - From Cursor-dyn-phase-contract: Add `ERROR` to the allowlist and `design-route.md`, and write it through `phase_driver_write_result_env` when surfacing pause-load failures


### FINDING_5: New driver scripts not pinned executable
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Proposed `SKILL.md` will invoke `design-route.sh` and `design-init-runparams.sh` by path. If they land with default non-executable mode, Step 0b fails with permission denied before routing or run-params setup. Adjacent driver coverage already pins scripts such as `run-step3-review.sh` as executable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Make both new .sh files executable and add test-design-structure.sh assertions that design-route.sh and design-init-runparams.sh are executable.


### FINDING_6: `BRAINSTORM_PREFIX` only applied on proceed route
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Proposed Step 0b route handling sends `already-planned` issues straight to the existing gate. A Brainstorm-prefixed issue that is already planned can miss `brainstorm_requested=true`, breaking the ad-hoc Q&A plus Step 1d.5 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Set brainstorm_requested=true and print the existing banner immediately after reading BRAINSTORM_PREFIX=true, before branching on ROUTE; then proceed/already-planned both see the same state


### FINDING_7: `LOAD_OK=false` forces `ROUTE=proceed` and skips clarify / already-planned gates
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Specifying `LOAD_OK=false` as `ROUTE=proceed` in edge cases means a failed pause load on an issue that also has `needs-design-clarification` or an existing `larch:plan` block can bypass clarify and already-planned gates and continue as a fresh replacement flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make LOAD_OK=false fall through to the normal title/reentry/final verdict logic instead of setting ROUTE=proceed early, and carry ERROR alongside WARN so the existing warning breadcrumb is preserved


### FINDING_8: Resume env refresh omits conditional `--manual-requested`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: On `resume@`, the plan moves env refresh to the orchestrator but does not carry the rule that today’s Step 0b applies on refresh when restored `run-params.json` has `manual_gate_b=true`. Restored run-params can set `manual_gate_b=true` while Gate B and `source-env` drop manual mode mid-resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After pause/resume, restored run-params.json can set manual_gate_b=true; today Step 0b adds --manual-requested true on refresh when required. The plan moves refresh to orchestrator on resume@ but does not carry that rule. Gate B and source-env can drop manual mode mid-resume. In the SKILL.md resume@ branch, keep the existing rule: after re-exporting pause KVs, refresh source-env with --manual-requested true when restored $DESIGN_TMPDIR/run-params.json has manual_gate_b=true (or equivalent), matching current sub-step 2.5-bis prose.

