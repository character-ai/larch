### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:567-580
- **Concern**: Plan harness update omits HARD round-1 case D2C that still asserts assess skipped. Scenario: Round-1 firing applies to both tiers; D2C will fail after assess-plan-round change while plan only mentions SIMPLE assertion rewrites
- **Proposed resolution**: Rewrite D2C (and handoff cases D1B/D1C) to expect round-1 assess dispatch with plan.txt-original anchor; drop ASSESSOR_STATUS=skipped expectations

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-postplan-emit.sh:259-302
- **Concern**: Plan only flips D2e skipped-not-hard; removing WORKFLOW_PATH orphans classification WARN harness cases. Scenario: D2d_warn D2d_invalid_warn and D2d_silent_nonzero assert read-design-classification WARNs that design-postplan-emit will no longer emit; make lint fails despite plan claiming harness green
- **Proposed resolution**: Explicitly drop or relocate those WARN assertions when deleting WORKFLOW_PATH resolution; keep tier-agnostic snapshot taken/preserved coverage only

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1227,1688
- **Concern**: SKILL.md HARD-only prose cleanup list is incomplete. Scenario: Gate B handoff (1227) and helper catalog (1688) still say HARD-only after Step 3.6 opens on SIMPLE; orchestrator prose contradicts driver behavior
- **Proposed resolution**: Add both lines to the SKILL.md update step alongside the three mentions already listed

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:84,167
- **Concern**: approval-gates tier prose beyond the two HARD-only links is not in plan. Scenario: Zero-findings path still says Step 3.6 runs on HARD runs only (84); Gate C re-run still says cursor advances on HARD runs only (167) after run-step3-review opens cursor on SIMPLE
- **Proposed resolution**: Same edit pass: remove HARD-only link text and replace on HARD runs qualifiers with both-tier wording

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1915
- **Concern**: Structure harness still pins the SIMPLE Step 3.6 skip breadcrumb even though the plan removes the SKILL.md tier skip. Scenario: Following the plan deletes `design_classification=${_design_classification}; skipped` from SKILL.md, then `scripts/test-design-structure.sh` and `make lint` fail on the stale `contains` assertion
- **Proposed resolution**: Update or remove this structure assertion in the same change; prefer pinning the qualified `design-plan-quality-assessor.sh` invocation/no tier-skip shape instead of the retired skip breadcrumb

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-assess-plan-round.sh:309-382
- **Concern**: Round-1 firing omits rewrite of existing two-entry HARD integration block. Scenario: The plan adds new round-1 cases but leaves the two-entry test expecting Entry 1 ASSESSOR_STATUS=skipped and a round-2-only mock; after assess-plan-round fires on ROUND_NUM=1 that block fails and the mock paths miss round-1 dispatch
- **Proposed resolution**: Explicitly rewrite the two-entry integration: Entry 1 must expect assessor dispatch (not skipped), point the mock at round-1 output paths, and keep Entry 2 round-2 behavior; or delete/replace the block if covered elsewhere

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:567-580
- **Concern**: HARD round-1 harness #4c still expects assessor skip after global round-1 firing. Scenario: Plan only lists SIMPLE driver-harness updates; #4c asserts ASSESSOR_STATUS/VERDICT=skipped after write-after on HARD ROUND_NUM=1, which contradicts the ROUND_NUM<2 removal shared by both tiers
- **Proposed resolution**: make lint fails on test-design-plan-quality-assessor.sh Rewrite #4c to expect round-1 assessor dispatch (or TIE/not-worse with round-1 stubs), mirroring the new round-1 contract; do not leave HARD-only skip assertions

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-run-step3-review.sh:581-614
- **Concern**: Plan cites mirroring an existing HARD round-cursor advance success assertion in test-run-step3-review.sh. Scenario: The harness only pins HARD write-cursor failure (D10); there is no HARD success advance assertion to mirror, so the proposed SIMPLE coverage may be underspecified or placed in the wrong harness
- **Proposed resolution**: Add a new explicit SIMPLE (and optionally HARD) success case asserting cursor advance when plan-after-round-N exists, or reference test-assess-plan-round.sh advance_step3_cursor / run-step3-review launcher integration instead of a nonexistent mirror target

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-design-structure.sh:1915
- **Concern**: The plan removes the Step 3.6 SIMPLE skip breadcrumb from SKILL.md but does not update the structure pin that still requires `design_classification=${_design_classification}; skipped`.. Scenario: `make lint`/`scripts/test-design-structure.sh` will fail after the proposed SKILL.md tier wrapper deletion even if the runtime behavior is correct.
- **Proposed resolution**: Update or remove this structure assertion with the other Step 3.6 pin changes so it matches the new both-tier assessor path.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-pause-load.sh:287-288
- **Concern**: Pause resume STEP=3b→3.6 upgrade remains HARD-only after assessor opens on SIMPLE. Scenario: Legacy SIMPLE pause markers with STEP=3b and step-3.5 complete but no step-3.6 resume at Step 3b and permanently skip the new assessor lane (HARD already has harness coverage at test-design-pause-resume.sh:921-932)
- **Proposed resolution**: Drop the HARD classification guard (or extend to SIMPLE) in design-pause-load.sh; add a SIMPLE legacy STEP=3b case to test-design-pause-resume.sh and list both files in the plan

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:135
- **Concern**: Plan opens Step 3.6 assessor to SIMPLE but omits SECURITY.md trust-boundary update. Scenario: After the PR, SECURITY.md still says the assessor lane is HARD-only, so operators auditing external Codex/Cursor delegation and untrusted assessor output may wrongly believe SIMPLE runs skip this boundary
- **Proposed resolution**: Add SECURITY.md to the plan and change the HARD-only wording to tier-agnostic Step 3.6/both tiers while preserving the existing controls; no new mechanism needed

### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1915
- **Concern**: Step 3.6 cheap-skip structure pin not in plan update list. Scenario: Removing the SKILL.md `if [ "$_design_classification" != HARD ]` skip leaves the pin `design_classification=${_design_classification}; skipped` unsatisfied and `scripts/test-design-structure.sh` fails during `make lint`
- **Proposed resolution**: Add removing or replacing the line-1915 pin to the `test-design-structure.sh` section (alongside the existing HARD-only comment pins)

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:197-217
- **Concern**: `apply_step3_6_handoff` mirrors the tier skip the plan deletes. Scenario: Plan updates driver/harness cases but not the orchestrator mirror; cases 3/3b/3c and other handoff paths keep expecting SIMPLE skip breadcrumbs and no assess invocation
- **Proposed resolution**: Update `apply_step3_6_handoff` in the same change as SKILL.md Step 3.6; rewrite SIMPLE handoff cases and case 4c (HARD round-1 assess was skipped, now must run after `ROUND_NUM < 2` removal)

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-postplan-emit.sh:236-302
- **Concern**: Classification-coupled postplan emit tests not fully enumerated. Scenario: Deleting `WORKFLOW_PATH` resolution drops `read-design-classification` WARN paths; cases 2c/2d/D2d_warn/D2d_invalid_warn/D2d_silent_nonzero still assert classification-driven snapshot/WARN behavior and will fail
- **Proposed resolution**: List each classification fixture to delete or rewrite when snapshot becomes tier-agnostic (not only D2e `skipped-not-hard`)

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:125-179
- **Concern**: `on HARD runs` Step 3.6 forward links omitted from plan file list. Scenario: After SIMPLE runs Step 3.6, prose still says assessor fires only on HARD in zero-findings / all-rejected paths
- **Proposed resolution**: Add `skills/design/references/plan-review.md` (and approval-gates.md line-84/167 tier-only cursor prose) to doc updates or accept deliberate doc drift

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1911-1916
- **Concern**: Step 3.6 structure test still pins the cheap SIMPLE skip breadcrumb that the plan removes. Scenario: An implementation that follows the plan and removes the SKILL.md tier wrapper will fail make lint because test-design-structure.sh still requires design_classification=${_design_classification}; skipped
- **Proposed resolution**: Update this structure pin in the plan to remove or replace the cheap-skip breadcrumb assertion with a tier-agnostic Step 3.6 driver invocation assertion

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:567-580
- **Concern**: Plan omits rewriting case 4c which still asserts round-1 assess is skipped on HARD. Scenario: Relaxing ROUND_NUM<2 in assess-plan-round.sh makes case 4c fail under make lint while the plan only lists SIMPLE harness updates and tier-skip rewrites in test-assess-plan-round.sh
- **Proposed resolution**: Rewrite case 4c (and note it in the Testing strategy) so round 1 expects assess dispatch anchored to plan.txt-original with ASSESSOR_STATUS=ok or degraded-default-open—not skipped—and optionally add a round-1 WORSE-majority rc=10 path tier-agnostic with the existing trailer assertions

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/assess-plan-round.sh:21-28,127
- **Concern**: [SCOPE-REDUCTION] Plan deletes the existing --design-classification helper option instead of preserving it as a compatibility no-op. Scenario: Any direct or downstream caller that still passes the documented option will start failing with unknown option, and the extra caller/docs/test churn is not required to run the SIMPLE assessor
- **Proposed resolution**: Keep --design-classification HARD|SIMPLE accepted and validated but ignored; remove only the tier skip and stop relying on the value for behavior

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-orphan-var-cleanup
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:197-217
- **Concern**: apply_step3_6_handoff still mirrors removed SKILL.md SIMPLE tier skip. Scenario: After SKILL.md drops the Step 3.6 classification gate, handoff cases 3b/3c (and parity checks vs production) keep expecting a SIMPLE skip breadcrumb and never invoke the driver assessor path
- **Proposed resolution**: make apply_step3_6_handoff call design-plan-quality-assessor.sh unconditionally (matching the de-indented SKILL.md fence) and rewrite handoff SIMPLE cases to expect banner plus assessor lane output

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-orphan-var-cleanup
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1911-1916
- **Concern**: The plan updates the four Step 3.6 HARD-only pins but misses the structure-test pin that still requires the removed SIMPLE skip breadcrumb. Scenario: After `skills/design/SKILL.md` drops the Step 3.6 tier wrapper, `bash scripts/test-design-structure.sh` and `make lint` still fail because the test requires `design_classification=${_design_classification}; skipped`
- **Proposed resolution**: Update the plan's `scripts/test-design-structure.sh` step to remove or replace this breadcrumb assertion with a both-tier assessor invocation assertion

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-round1-prompt-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/scripts/render-assessor-prompt.sh:49-63
- **Concern**: Plan re-anchors the comparison sentence but never describes or guards the round-1 degenerate prompt where `plan_prev` and `plan_original` are the same path so Original and Previous sections duplicate. Scenario: Assessor models may treat identical Original/Previous blocks as “no inter-round change” and return TIE even when Current regressed vs the pre-review anchor
- **Proposed resolution**: Add one explicit round-1 sentence when `PLAN_PREV` resolves to the same path as `PLAN_ORIGINAL` (or pass `--round-num 1`) stating verdict is Current vs Original only and Previous duplicates the anchor; spell out the exact replacement instruction text in the plan

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-round1-prompt-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/scripts/render-assessor-prompt.sh:47-63; skills/shared/scripts/test-render-assessor-prompt.sh:18-31
- **Concern**: Prompt plan omits the round-1 identical-original-and-previous shape. Scenario: Plan lines 29 and 31-32 make round 1 pass plan_prev == plan_original while still rendering both Original plan and Previous round plan sections; without an explicit note, assessor models can treat the duplicate Previous round section as a normal multi-round baseline and under-detect current-vs-original regression, weakening the round-1 WORSE gate the issue requires
- **Proposed resolution**: Add a minimal conditional note in render-assessor-prompt.sh when original and previous inputs are the same path/content, stating that round 1 has no prior-round plan and the Previous section intentionally repeats the original anchor; add test-render-assessor-prompt.sh coverage for that identical-input prompt shape alongside the original-anchor assertion

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-harness-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1915
- **Concern**: Plan omits removal of the `design_classification cheap-skip breadcrumb` structure pin while SKILL.md Step 3.6 drops the tier skip. Scenario: `make lint` / `test-design-structure.sh` fails after the fence removes `design_classification=${_design_classification}; skipped`
- **Proposed resolution**: Delete or replace the pin at line 1915 in the same change as the Step 3.6 fence rewrite; update the four thin-fence self-test excerpts at lines 580-631 if they still embed the tier gate

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:135
- **Concern**: The plan does not update SECURITY.md even though the assessor trust boundary changes from HARD-only to SIMPLE+HARD.. Scenario: After implementation, the security policy still says the untrusted assessor lane is HARD-only, so consumers and reviewers can incorrectly believe SIMPLE runs do not dispatch the assessor panel.
- **Proposed resolution**: Add a SECURITY.md update that removes HARD-only wording and states the same bounded-output and trailer-only controls now apply on SIMPLE and HARD.

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:1903-1917
- **Concern**: The plan's structure-test update misses the obsolete cheap-skip breadcrumb pin for Step 3.6.. Scenario: If SKILL.md removes the SIMPLE tier wrapper as planned, make lint can fail on the stale design_classification skipped assertion; if the assertion is preserved, it pressures the implementation to keep old skip behavior.
- **Proposed resolution**: Delete or replace the cheap-skip breadcrumb assertion with a pin for unconditional design-plan-quality-assessor.sh invocation and retained rc/trailer handling.

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-plan-quality-assessor.sh:197-217,567-580
- **Concern**: The plan updates SIMPLE driver assertions but does not target the local handoff shim or the round-1 skipped fixture that still encode old behavior.. Scenario: The harness can still pass while simulating prompt-side SIMPLE skip, and it can keep asserting round 1 skipped through a stub even though round 1 must now fire against plan.txt-original.
- **Proposed resolution**: Update apply_step3_6_handoff to invoke the driver for SIMPLE, and change or remove the round-1 skipped fixture so it expects assessor invocation/result rather than skipped.

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:84,167
- **Concern**: The plan only names two HARD-only forward-link edits and misses nearby Gate C guidance that says the assessor/cursor behavior is HARD-only.. Scenario: Post-change docs can still tell operators that normal Step 3.6 sequence or round-cursor advancement applies only on HARD runs, contradicting the tier-agnostic code path.
- **Proposed resolution**: Update the surrounding approval-gates prose to say Step 3.6 and round-cursor advancement apply on both SIMPLE and HARD settled review paths.

### OOS_1:
- **Description**: plan-review.md still gates Step 3.6 to HARD runs. Scenario: Zero-findings and all-rejected paths document assessor only on HARD; SIMPLE operators reading plan-review get wrong sequencing
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:125,179
- **Phase**: design

### OOS_2:
- **Description**: SECURITY.md still labels assessor lane HARD-only. Scenario: Policy doc understates SIMPLE assessor exposure after this change; trust-boundary prose still applies but tier label is stale
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:135
- **Phase**: design

### OOS_3:
- **Description**: Snapshot failure message still says HARD assessor flow. Scenario: Operator-facing error text stays tier-wrong after SIMPLE snapshots are enabled
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/design-postplan-emit.sh:261
- **Phase**: design
