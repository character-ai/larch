### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:383-446
- **Concern**: Post-fence verbatim summary gate uses driver _route_rc=0 but cancel case bodies still exit 1 inside the same bash fence. Scenario: After thinning, render runs in design-route.sh and cancel branches collapse to exit 1 in the route fence; the Bash tool then reports failure even though the driver succeeded (_route_rc=0). Orchestrator may treat that as a hard stop and skip the planned post-fence read of final-summary.md (Step 5c item 3 pattern), so operators see only the driver reject banner and lose the structured summary block
- **Proposed resolution**: Spell out in SKILL.md Step 0b: driver _route_rc=0 plus ROUTE cancel-title-filter or cancel-reentry-guard requires the post-fence verbatim emit even when the route fence bash exits 1; post-fence abort terminates /design after the emit, not before it

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:383-456
- **Concern**: Proposed cancel routes both exit inside the Bash fence and rely on post-fence prose to emit final-summary.md. Scenario: The title-filter or reentry route can render final-summary.md in the driver, print the reject banner, then the Bash fence exits 1 before the orchestrator-side verbatim summary handler reliably runs
- **Proposed resolution**: Choose one terminal owner: for orchestrator-side summary emission, remove the cancel-title-filter and cancel-reentry-guard exit 1 from the fence and add the explicit post-fence cancellation handler before sub-step 3; that handler reads final-summary.md and then stops

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-126
- **Concern**: Plan expands the router-flag recovery harness to assert design-route fence shape and moved banners. Scenario: This couples unrelated route rendering behavior to a jq/run-params recovery test, increasing maintenance cost beyond the SIMPLE minimum-change lane
- **Proposed resolution**: Keep design-route thinned-fence and banner ownership pins in scripts/test-design-structure.sh; do not add new route fixtures to test-step0b-router-flag-recovery.sh unless an existing design-route invocation there must be updated with --session-id

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:337-344,70-70
- **Concern**: Post-fence cancel summary gate uses `_route_rc=0` while cancel `case` branches `exit 1`. Scenario: Thinned fence ends with `exit 1` on cancel routes; `_route_rc` is a bash-fence variable lost after the tool returns, and exit 1 is easy to treat as `design-route.sh failed` at lines 341-343 — operator may never get the verbatim `final-summary.md` emit the driver wrote
- **Proposed resolution**: Post-fence prose: gate on `ROUTE` read from `$DESIGN_TMPDIR/.design-route-result.env` (or stdout KVs) after a successful `design-route.sh` capture, explicitly not on overall fence exit 0; add one line that cancel-branch `exit 1` is expected and must still run the Step 5c item 3 verbatim emit before abort

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:236-245
- **Concern**: Finding 1: proposed resume env refresh moves write-design-current-env.sh under the quiet route driver without preserving child stderr. Scenario: When a paused run has a bad SESSION_ID, repo, output path, or symlink failure, write-design-current-env.sh larch_err diagnostics inherit the driver quiet log fds and are not visible to the operator; current inline Step 0b shows them
- **Proposed resolution**: Use the same quiet-aware stderr bridge planned for render-final-summary.sh around the resume write-design-current-env.sh call, or capture child stderr and replay it via larch_err before the generic resume failure banner

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:260-267,298-304
- **Concern**: Finding 2: proposed cancel branches render and upsert the final summary before proving the route result-env contract can be written. Scenario: If .design-route-result.env is a symlink or otherwise refused, the driver can still write final-summary.md and upsert the GitHub summary comment, then exit 1 before the caller has a valid ROUTE; that turns a contract failure into external side effects
- **Proposed resolution**: Before any cancel render, write or preflight .design-route-result.env with the same symlink refusal contract; simplest is to split route result-env write from stdout emit so result-env refusal happens before render-final-summary.sh runs

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:324-456
- **Concern**: Post-fence cancel summary gate keys off `_route_rc=0` and shell `ROUTE` after the route bash fence closes. Scenario: `_route_rc` and `ROUTE` are bound only inside the bash fence; cancel branches `exit 1` there so the fence can end non-zero and those bindings do not survive. Post-fence prose may never run, or anti-halt may advance to sub-step 3 with a cancel `ROUTE` still on disk
- **Proposed resolution**: Key off `.design-route-result.env` (`ROUTE=cancel-title-filter|cancel-reentry-guard`) plus `[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]`; state the emit is mandatory even when the fence exited 1; then abort before sub-step 3

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:383-421
- **Concern**: Proposed cancel path keeps in-fence `exit 1` and adds post-fence verbatim summary emit. Scenario: Duplicates abort paths and fights Step 5c item 3 (driver writes file; orchestrator emits after handoff while bash may already have exited 1). Extra orchestration surface for minimum-change goal
- **Proposed resolution**: Drop `exit 1` from collapsed cancel `case` bodies; let the fence finish after driver `exit 0`, run post-fence verbatim emit + abort only outside the fence (matches Final summary block / Step 5c item 3 split)

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:172-198,263-303
- **Concern**: Plan moves cancel summary render and GitHub upsert before the route result-env contract is known to be writable. Scenario: If .design-route-result.env is a symlink or the result-env write is refused, the proposed driver can still render/upsert a cancellation summary, then exit 1; current behavior aborts before those side effects and the orchestrator will not do the verbatim summary handoff
- **Proposed resolution**: For cancel routes, write/validate the result env before render-final-summary.sh side effects, then render and emit KVs; or split emit_route_result into build/write/emit helpers so result-env refusal aborts before any summary render or GitHub upsert

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:383-402,69-70
- **Concern**: Cancel routes use in-fence exit 1 while verbatim summary emit is post-fence orchestrator prose. Scenario: Plan puts cancel-title-filter/cancel-reentry-guard case bodies at exit 1 inside the bash fence but Step 5c item 3-style summary emit after the fence closes; bash exit 1 aborts the fence before that prose runs, and render stdout is redirected so the operator may see only the driver reject banner with no final-summary.md body in chat
- **Proposed resolution**: Match Step 5c: make cancel case bodies no-op inside bash (keep _route_valid), close the fence with exit 0, run post-fence verbatim emit when ROUTE is cancel-* and final-summary.md is non-empty, then orchestrator-abort before sub-step 3; do not exit 1 inside bash for those routes

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:30-33; skills/design/scripts/render-final-summary.sh:58-59
- **Concern**: Plan contradicts its empty SESSION_ID_ARG edge case. Scenario: The plan requires validate_plain_scalar for required --session-id, which rejects empty values, but also says empty SESSION_ID_ARG should fall back to RUN_ID=unknown. An empty session id on a title-filter or reentry cancel would exit 2 before render, so no final-summary.md or summary upsert occurs.
- **Proposed resolution**: Track --session-id flag presence separately and allow an empty value while still rejecting newline/CR, or remove the empty-session fallback edge and document the intentional exit-2 behavior.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-stream-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:35-40; skills/design/scripts/design-route.sh:172-181
- **Concern**: Plan tells design-route.sh to export SESSION_ID="$SESSION_ID_ARG" before cancel renders even though emit_route_result reads the shared SESSION_ID variable. Scenario: Bash export assignment clobbers module SESSION_ID; a cancel-title-filter or cancel-reentry-guard path can emit SESSION_ID from the cancel render identity or overwrite a pause-loaded SESSION_ID after pause-load fallthrough, violating the SESSION_ID_ARG vs pause-loaded SESSION_ID split
- **Proposed resolution**: Use a command-scoped environment for render-final-summary.sh such as DESIGN_TMPDIR="$DESIGN_TMPDIR" ISSUE_NUMBER="$ISSUE" SESSION_ID="$SESSION_ID_ARG" render-final-summary.sh ... so the module SESSION_ID remains pause-load-only before emit_route_result

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1287-1290
- **Concern**: Check 20 lifecycle/archival reject pins lack named removal and replacement literals. Scenario: Plan says move reject literals to `$DESIGN_ROUTE_SH` but never lists the two current `$SKILL_MD` substrings (`issue title starts with managed lifecycle marker`, `issue title matches archival report-prefix`) or the exact new `grep -Fq` lines on `$DESIGN_ROUTE_SH`. Lines 1287-1290 would keep failing after banners leave `SKILL.md`.
- **Proposed resolution**: In `### UPDATED: scripts/test-design-structure.sh`, spell out delete 1287-1290 and add matching `grep -Fq` pins on `$DESIGN_ROUTE_SH` for those exact literals (or `larch_err`/`larch_errf` equivalents).

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1494-1498
- **Concern**: Check 26 re-entry banner pins lack explicit driver anchors. Scenario: Plan relocates the session-cache banner to `$DESIGN_ROUTE_SH` with `$CLAUDE_PID`, but harness text only says “marker-path wording.” It does not require removing the two `$SKILL_MD` greps at 1494-1498 or pin the new driver literal (today `ppid=${PPID}` becomes argv `$CLAUDE_PID`).
- **Proposed resolution**: Document delete 1494-1498 and add `$DESIGN_ROUTE_SH` pins for the full spurious re-entry string plus `delete ${DESIGN_REENTRY_MARKER_PATH} to override.` using the post-move `$CLAUDE_PID` form.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:73-81
- **Concern**: Post-fence `[ -s "${FINAL_SUMMARY_PATH:-…}"]` gate has no concrete harness add line. Scenario: Step 0b prose and the step0b_block bullet name the gate, but unlike contract-drift (359-361) the Files section never gives an implementable assertion such as `printf '%s\n' "$step0b_block" | grep -Fq '[ -s "${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}" ]'`. Prose-only coverage risks the new Step 0b cancel handoff shipping without a structure-test pin.
- **Proposed resolution**: Add an explicit `test-design-structure.sh` line (with line anchor) grep-ing that exact gate inside `$step0b_block` post-fence prose.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-pin-migration
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:80-81
- **Concern**: `2>&4` quiet redirect pin allows comment-only anchor. Scenario: “`2>&4` (or quiet-aware redirect comment anchor)” permits a comment stub without the `LARCH_QUIET_PID`/`2>&4` redirect from `scripts/render-run-summary.sh:12-17`, weakening FINDING_4 stderr contract enforcement.
- **Proposed resolution**: Pin the conditional redirect literally (`[ "${LARCH_QUIET_PID:-}" = "$$" ]` and `2>&4`) in `$DESIGN_ROUTE_SH`; drop the comment-only alternative.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:75, scripts/test-design-structure.sh:1092-1095
- **Concern**: FINDING_20_ENV_REFRESH_BANNER is cited only as env-refresh-failed text, not the exact literal being moved from SKILL.md to the driver.. Scenario: The harness update can silently pin a weaker or different string in design-init-runparams.sh while the current SKILL.md literal at skills/design/SKILL.md:519-521 is removed.
- **Proposed resolution**: Revise the harness bullet to name the exact literal `write-design-current-env.sh failed during Step 0b env refresh` and its replacement target `$DESIGN_INIT_SH`; keep only the generic init failure prose in `$SKILL_MD`.

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:76-80, scripts/test-design-structure.sh:1165-1173,1278-1290,1494-1498
- **Concern**: Several relocated pin bullets use vague anchors instead of exact replacement literals: `rc capture`, lifecycle/archival reject literals, reentry guard literals, `export ISSUE_NUMBER="$ISSUE"` or equivalent, and `2>&4` or quiet-aware redirect comment anchor.. Scenario: An implementer could satisfy the plan with comments, renamed prose, or partial assertions, dropping the exact SKILL.md literals currently pinned by the structure test.
- **Proposed resolution**: Replace vague phrases with exact grep anchors in `$DESIGN_ROUTE_SH`, including `_wdce_resume_rc=$?`, `issue title starts with managed lifecycle marker`, `issue title matches archival report-prefix`, `**⚠ /design: refusing spurious re-entry — guard=session-cache`, `delete ${DESIGN_REENTRY_MARKER_PATH} to override.`, `export ISSUE_NUMBER="$ISSUE"`, and executable `2>&4` redirect coverage.

### OOS_1:
- **Description**: Testing section claims `--session-id` and thinned-fence assertions in router-flag recovery harness. Scenario: File only exercises `design-init-runparams.sh` (no `design-route.sh` invocation); plan work there is misleading churn
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-259
- **Phase**: design

### OOS_2:
- **Description**: Plan adds design-route.sh --session-id fixtures and thinned-fence assertions to the router-flag jq-merge recovery harness. Scenario: The file only exercises design-init-runparams.sh today; mixing route-driver/thin-fence coverage here expands scope beyond #3420 minimum change while test-design-structure.sh already carries the planned pin updates
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-step0b-router-flag-recovery.sh:1-258
- **Phase**: design
