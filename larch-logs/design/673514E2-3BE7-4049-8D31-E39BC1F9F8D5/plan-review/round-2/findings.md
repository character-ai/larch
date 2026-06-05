### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:67-166
- **Concern**: Plan adds required --session-id but does not account for the existing SESSION_ID result-variable reset after argv parsing. Scenario: Fresh cancel-title-filter or cancel-reentry-guard can validate --session-id, then clear it before render-final-summary.sh runs, producing RUN_ID=unknown and unstable summary upsert markers
- **Proposed resolution**: Use a separate SESSION_ID_ARG for fresh-run rendering, or move/remove the SESSION_ID reset so argv is not clobbered; keep pause-loaded SESSION_ID for resume paths

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:237-244
- **Concern**: Resume wdce move omits how manual_gate_b is resolved. Scenario: Thinning SKILL.md removes the jq '.manual_gate_b // false' read on run-params.json (skills/design/SKILL.md:424-426) but the plan only says pass --manual-requested when manual_gate_b=true without naming the source; driver may omit the flag or read argv/session env and resume with wrong MANUAL_REQUESTED for Gate B
- **Proposed resolution**: In design-route.sh resume branch, mirror today's jq guard on $DESIGN_TMPDIR/run-params.json before write-design-current-env.sh; add a structure pin on $DESIGN_ROUTE_SH for manual_gate_b / --manual-requested

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:34-35
- **Concern**: render-final-summary.sh requires ISSUE_NUMBER in the environment; the driver only binds --issue as ISSUE and the plan does not require export ISSUE_NUMBER="$ISSUE" (design-publish.sh:156-157 and test-design-structure.sh:1425-1426 already pin the publish path). Scenario: Cancel summaries and GitHub upsert can lose issue number/URL even when routing succeeded; harness has no design-route equivalent of the publish export pin
- **Proposed resolution**: Add export ISSUE_NUMBER="$ISSUE" (and export SESSION_ID from --session-id) immediately before each render-final-summary.sh call; extend test-design-structure.sh pins mirroring (15b) for design-route.sh

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:322
- **Concern**: Step 2.5 intro still says cancel banners stay in the orchestrator; the plan moves title-filter/reentry banners and resume env refresh into design-route.sh (pause-load banner excepted). Scenario: Inline orchestration may keep printf banners in SKILL.md despite the driver move, recreating duplicate/misordered operator output
- **Proposed resolution**: Update the sub-step 2.5 prose to state cancel reject banners and resume env refresh live in design-route.sh; orchestrator only emits final-summary.md verbatim (when non-empty), cancel-pause-load abort, and AskUserQuestion gates

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:7-9; scripts/lib-quiet.sh:58-67; skills/design/scripts/render-final-summary.sh:538-541
- **Concern**: Redirecting only render-final-summary stdout does not keep its stderr live inside the quieted route driver. Scenario: Under normal quiet mode, design-route.sh has already redirected FD2 to its quiet log. A nested render-final-summary.sh then inherits that quiet-log stderr, so render diagnostics are not caller-visible despite the plan’s “leave stderr live” contract.
- **Proposed resolution**: When invoking render-final-summary.sh from design-route.sh, preserve stdout redirection but route child stderr to the driver’s original stderr under quiet mode, e.g. use 2>&4 when LARCH_QUIET_PID matches $$, or explicitly revise the plan to stop claiming live renderer stderr.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.md:40-46
- **Concern**: Exit-code table not slated for resume env-refresh failure. Scenario: Plan adds driver exit 1 before ROUTE=resume@* emit and SKILL _route_rc abort, but design-route.md still documents exit 0 for all routing verdicts and exit 1 only for result-env write refusal; resume failure is neither
- **Proposed resolution**: Extend ### UPDATED design-route.md: add exit 1 row for write-design-current-env.sh failure before ROUTE emit; distinguish from cancel routes (exit 0 + ROUTE=cancel-*)

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-driver-contracts
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:383-421 (proposed Step 0b route `case` collapse)
- **Concern**: Thinned cancel branches gate on `[ -s …/final-summary.md ]` but do not spell out the post–route-bash orchestrator verbatim emit that replaces today's inline `render-final-summary.sh` stdout. Scenario: After the driver redirects render stdout to `/dev/null`, a route fence that only `exit 1`s (or `cat`s inside the bash fence) leaves no structured summary in chat even when `final-summary.md` was written
- **Proposed resolution**: In `skills/design/SKILL.md` Step 0b, keep cancel `case` bodies to `exit 1` only; add explicit orchestrator prose immediately after the route-driver bash fence (same contract as line 569 / Step 5c item 3): when `_route_rc=0` and `ROUTE` is `cancel-title-filter` or `cancel-reentry-guard`, Read `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` and emit the full body verbatim before aborting

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-harness-retargeting
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:327-334
- **Concern**: Harness retarget list pins DESIGN_ROUTE_SH accepting --session-id but not SKILL.md passing --session-id on the design-route.sh invocation. Scenario: Orchestrator call can omit the new required flag while structure tests still pass; cancel-route render-final-summary.sh gets empty SESSION_ID and wrong RUN_ID in summaries
- **Proposed resolution**: Add a step0b_block (or invocation-line) grep pin that SKILL.md passes --session-id "$SESSION_ID" to design-route.sh alongside existing ${REPO:+--repo} threading pins

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-operator-channels
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:387-421
- **Concern**: skills/design/scripts/design-route.sh (proposed cancel paths). Scenario: Cancel routes move `render-final-summary.sh` and `larch_err` reject banners into `design-route.sh` inside `_route_out=$(…)`, while the thinned orchestrator `case` only cats `final-summary.md` afterward. During command substitution the operator sees the reject banner before the structured summary; today the inline fence prints the summary to stdout first, then the reject line to stderr. That inverts visible ordering despite the plan’s “behavior preserved” claim.
- **Proposed resolution**: Keep stdout-redirected render in the driver, but leave lifecycle/archival/reentry reject text in the orchestrator `case` after the `[ -s …/final-summary.md ]` verbatim emit (today’s order). If driver-owned `larch_err` is mandatory, document the reorder explicitly in the plan and acceptance checks.
