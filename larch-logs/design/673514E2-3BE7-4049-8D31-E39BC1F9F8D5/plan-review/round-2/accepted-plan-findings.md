### FINDING_1: Route-driver render environment can lose session/issue identity
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-dyn-harness-retargeting
- **Severity**: important
- **Concern**: The proposed route-driver flow does not fully preserve and export the identity values that `render-final-summary.sh` depends on. The orchestrator may omit `--session-id`, the driver may clobber `SESSION_ID` after parsing, and `ISSUE_NUMBER` may never be exported from `--issue`, causing cancel summaries/upserts to use unknown or incomplete run/issue metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use a separate SESSION_ID_ARG for fresh-run rendering, or move/remove the SESSION_ID reset so argv is not clobbered; keep pause-loaded SESSION_ID for resume paths
  - From Cursor-Innovation: Add export ISSUE_NUMBER="$ISSUE" (and export SESSION_ID from --session-id) immediately before each render-final-summary.sh call; extend test-design-structure.sh pins mirroring (15b) for design-route.sh
  - From Cursor-dyn-harness-retargeting: Add a step0b_block (or invocation-line) grep pin that SKILL.md passes --session-id "$SESSION_ID" to design-route.sh alongside existing ${REPO:+--repo} threading pins


### FINDING_2: Resume env refresh may drop manual Gate B state
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Moving resume env refresh into `design-route.sh` does not specify how `manual_gate_b` is sourced after thinning removes the existing `jq` read from `run-params.json`, so resume paths may call `write-design-current-env.sh` without the correct `--manual-requested` flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In design-route.sh resume branch, mirror today's jq guard on $DESIGN_TMPDIR/run-params.json before write-design-current-env.sh; add a structure pin on $DESIGN_ROUTE_SH for manual_gate_b / --manual-requested


### FINDING_3: Cancel-output ownership and ordering are underspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-driver-contracts, Cursor-dyn-operator-channels
- **Severity**: important
- **Concern**: The plan inconsistently describes whether cancel banners, summary emission, and related abort messaging live in `design-route.sh` or the orchestrator. This can lead to missing structured summaries, duplicated output, or reordered operator-visible messages when driver stdout is redirected and stderr banners are emitted before the orchestrator reads `final-summary.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update the sub-step 2.5 prose to state cancel reject banners and resume env refresh live in design-route.sh; orchestrator only emits final-summary.md verbatim (when non-empty), cancel-pause-load abort, and AskUserQuestion gates
  - From Cursor-dyn-driver-contracts: In `skills/design/SKILL.md` Step 0b, keep cancel `case` bodies to `exit 1` only; add explicit orchestrator prose immediately after the route-driver bash fence (same contract as line 569 / Step 5c item 3): when `_route_rc=0` and `ROUTE` is `cancel-title-filter` or `cancel-reentry-guard`, Read `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` and emit the full body verbatim before aborting
  - From Cursor-dyn-operator-channels: Keep stdout-redirected render in the driver, but leave lifecycle/archival/reentry reject text in the orchestrator `case` after the `[ -s …/final-summary.md ]` verbatim emit (today’s order). If driver-owned `larch_err` is mandatory, document the reorder explicitly in the plan and acceptance checks.


### FINDING_4: Quieted driver can hide renderer stderr
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: Redirecting only `render-final-summary.sh` stdout is insufficient if `design-route.sh` has already redirected stderr to its quiet log; renderer diagnostics may not remain caller-visible despite the stated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: When invoking render-final-summary.sh from design-route.sh, preserve stdout redirection but route child stderr to the driver’s original stderr under quiet mode, e.g. use 2>&4 when LARCH_QUIET_PID matches $$, or explicitly revise the plan to stop claiming live renderer stderr.


### FINDING_5: design-route exit-code docs omit resume env-refresh failure
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The updated `design-route.md` exit-code table does not document the new resume env-refresh failure path, where the driver exits 1 before emitting a resume route, making the contract inconsistent with the planned behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend ### UPDATED design-route.md: add exit 1 row for write-design-current-env.sh failure before ROUTE emit; distinguish from cancel routes (exit 0 + ROUTE=cancel-*)

