### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:17,84,100,159,169; skills/design/scripts/run-step3-review.sh:167; scripts/test-design-structure.sh:371-379,1568
- **Concern**: The plan retargets SKILL.md Step 3b routing but leaves adjacent normative Gate B/C and cap-routing text/tests pinned to direct Step 3b → Step 4/Gate C routing without the new completion boundary.. Scenario: Cap-reached, zero-findings, passive-summary, or bypass paths can follow the stale reference/breadcrumb and enter Step 4 after the Step 4 standalone FINALIZE item is removed; the updated SKILL wording also conflicts with exact test needles that still require the old route.
- **Proposed resolution**: Include these route strings and their test pins in the same minimum-change retarget: say "run the Step 3b completion boundary, then Step 4/Gate C" everywhere, or keep Step 4 FINALIZE until all normative routes are boundary-aware.

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:654-658
- **Concern**: Proposed Step 2a fence names read-design-classification.sh without the plugin-root path. Scenario: A literal unqualified call will usually be command-not-found, hit the HARD fallback, and SIMPLE runs will not write the folded sentinels
- **Proposed resolution**: Use "${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" in the Step 2a entry fence and pin that qualified path in the new structure assertion

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:38-39
- **Concern**: Planned Step 3b routing guard uses substring `continue to Step 4` without excluding Step 4b. Scenario: After SKILL.md edits, line 1369 (`IMMEDIATELY continue to Step 4b`) still matches the guard and fails CI even when Step 3b exit prose is correctly retargeted
- **Proposed resolution**: Pin the guard to Step 3b-only lines (slice already used elsewhere) and match `continue to Step 4` with a word boundary or explicit `(4[^b]|4$)` exclusion so Step 4→4b continuation is not flagged

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:167; skills/design/references/approval-gates.md:17,84,100,159,169; scripts/test-design-structure.sh:371-379,1568
- **Concern**: Plan moves FINALIZE to the Step 3b completion boundary but misses runtime/normative Step 3b-to-Step 4 routing surfaces outside SKILL.md.. Scenario: Cap-reached or Gate-B-settled paths can still emit/load instructions to continue from Step 3b straight to Step 4 after Step 4 item 1 is removed, so FINALIZE can be skipped.
- **Proposed resolution**: Update those surfaces to say run the Step 3b completion boundary before Step 4, and adjust the pinned test needles/add a run-step3-review.sh routing assertion.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-bypass-path-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1059
- **Concern**: Plan item 3 lists Step 3b exit retargets (~1303, 1334, 1336, 1338, 1340, 1168) but omits the review-round cap entry-guard sentence that says to jump to Step 3b/4/4b. Scenario: Cap-reached orchestration can still treat Step 4 as the next hop without running the Step 3b completion boundary (FINALIZE); proposed harness guard Step 3b.*Step 4 will not match the Step 3b/4 shorthand
- **Proposed resolution**: Add skills/design/SKILL.md:1059 to the retarget list (require Step 3b completion boundary before Step 4) and extend scripts/test-design-structure.sh routing guards to fail Step 3b/4 or Step 3b/4/4b unless the same line names the completion boundary

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-bypass-path-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:344
- **Concern**: Existing assertion pins the old cap-reached wording "jump to Step 3b/4/4b" while the plan retargets that SKILL.md route through the Step 3b completion boundary.. Scenario: Implementing the required SKILL.md retarget at skills/design/SKILL.md:1059 either fails test-design-structure.sh or tempts keeping direct-routing prose to satisfy the stale pin.
- **Proposed resolution**: Update this exact assertion to the new boundary-qualified cap wording or replace it with the planned line-scoped Gate-B-bypass routing guard.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-harness-regression-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (proposed harness § lines 41-42) vs plan failure mode 6 (plan.txt:96-97)
- **Concern**: FM6 mitigation requires nonzero exit on both Step 3b boundary and Step 4 compatibility branches, but proposed harness pins only the Step 3b completion fence. Scenario: Step 4 entry guard can regress to warning-only (today skills/design/SKILL.md:1364) while CI still passes; old paused sessions resume into Step 4 reads without FINALIZE
- **Proposed resolution**: Add a Step 4 entry-fence-scoped pin mirroring the Step 3b check: the compatibility guard must contain a non-zero exit on FINALIZE failure (e.g. exit "$_finalize_rc"), not merely a repair warning

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-harness-regression-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:38-40; scripts/test-design-structure.sh:371-379; skills/design/references/approval-gates.md:17,84,100,159,169
- **Concern**: Routing harness is too narrow and omits mandatory approval-gates route prose. Scenario: The planned guard catches `continue to Step 4` and the SKILL Step 3 slice, but a direct route phrased as `proceed to Step 4`, `auto-continue ... Step 4`, or existing approval-gates `Step 3b → Step 4` prose can bypass the Step 3b completion boundary without failing the updated structure test
- **Proposed resolution**: Use one line-scoped scanner for SKILL Step 3b, SKILL Step 3/Gate-B-bypass, and approval-gates route prose; match continue/proceed/auto-continue/route/jump/enter/go plus Step 4 and Step 3b arrow/comma forms, and require the same line to mention the Step 3b completion boundary. Update the existing approval-gates positive pins to the boundary-qualified wording.
