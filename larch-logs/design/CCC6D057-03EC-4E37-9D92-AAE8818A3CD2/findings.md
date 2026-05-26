### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Item C adds fallback_group only in dispatch-with-waterfall.sh; manifest rows are unchanged. Scenario: #2885 scenario (cursor slot pattern-miss Codex fallback while decomp-codex-* already OK) never triggers dedup; Item C ships dead for the 8-slot panel
- **Proposed resolution**: Add fallback_group per archetype to both jq manifest rows (e.g. decomp-${_a}) in the loop; document in decompose-panel.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:321-336
- **Concern**: Ledger/dedup scoped to Phase-2 Codex launch; phase1 OK on sibling codex slot not specified. Scenario: After phase1 collect, decomp-cursor-* can still launch redundant Codex in phase2 while decomp-codex-* already has OK + ## Recommendation
- **Proposed resolution**: Record ledger rows for every settled external OK (phase1/2) when fallback_group is set; before phase2 launch_slot for tool=codex, scan ledger for group OK codex

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:212-244
- **Concern**: is_anchor_for_basename matches basename inside quoted paths on assignment lines. Scenario: WATERFALL_SH=.../dispatch-with-waterfall.sh lines (e.g. decompose-panel-dispatch.sh:145) fire without unset in prior 5 lines; planned unset before "$WATERFALL_SH" at :153 does not satisfy look-back for :145
- **Proposed resolution**: Exclude simple VAR= assignments (no command substitution) from the new scan, or place unset immediately above each assignment alias line

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:212-244
- **Concern**: New rule only anchors literal dispatch-with-waterfall.sh basename. Scenario: Actual invocations use "$WATERFALL_SH" / "$DISPATCH_SH" / "$DISPATCH_WATERFALL" (decompose-panel-dispatch.sh:153, dispatch-panel.sh:404, aggregate-findings.sh:730) so unset is not lint-enforced on real exec lines
- **Proposed resolution**: Extend scan to treat exec of vars assigned from .../dispatch-with-waterfall.sh within N lines as anchors, or require literal path at call sites covered by the rule

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/dispatch-with-waterfall.sh:48-53
- **Concern**: Ledger path described via RESEARCH_/DESIGN_/REVIEW_TMPDIR env vars dispatcher does not read. Scenario: Wrong ledger directory or cross-run leakage if implementer exports ad hoc tmpdir vars
- **Proposed resolution**: Anchor ledger at dirname of resolved paths-file / slots-file under caller tmpdir (document in dispatch-with-waterfall.md)

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:145-171
- **Concern**: Plan claims two dispatch-with-waterfall callsites; script has one invocation. Scenario: Implementer may search for a nonexistent second callsite
- **Proposed resolution**: Edit plan to single callsite at lines 153-159 (WATERFALL_SH assignment at 145 is not a call)

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:48-53
- **Concern**: Edge case promises symmetric Cursor ledger tracking; body is Codex-only before phase2. Scenario: Cursor-primary slots in same group may still double Cursor fallbacks
- **Proposed resolution**: Add explicit phase2 dedup for whichever alt tool is launched, or narrow edge-case prose to Codex-only

### FINDING_8:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142, skills/design/scripts/dispatch-plan-review-panel.sh:84-120
- **Concern**: 1. Paired vendor manifests are not opted into fallback_group. Scenario: The dispatcher change is explicitly opt-in, and the plan says all existing manifests omit fallback_group, so the production cursor/codex pairs that motivated the PR still skip dedup and can launch duplicate Codex work
- **Proposed resolution**: Add fallback_group to both vendor rows for each paired archetype in decompose-panel-dispatch.sh and dispatch-plan-review-panel.sh, and update their harnesses to assert the group is present in generated NDJSON

### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:275-293, scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: 2. Dedup ledger only describes fallback successes, not successful primary peer results. Scenario: In a paired cursor/codex group, if the Codex primary slot succeeds in phase 1 and the Cursor primary slot fails, phase 2 will not find an OK Codex ledger row and will launch Codex again
- **Proposed resolution**: Record every grouped OK external result during collect_phase, including phase 1 primary successes, keyed by group and actual tool before building the phase 2 queue

### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-349, scripts/dispatch-with-waterfall.sh:388-414
- **Concern**: 3. Reused slots are not specified as settled in the existing output arrays. Scenario: A dedup-hit slot that is copied instead of launched can be absent from phase_outputs, then never gets final_outputs and final_tools set, producing blank ALL_OUTPUT_FILES entries or falling through to Claude
- **Proposed resolution**: Define a helper that copies the reused output, writes the sidecar and ledger row, sets final_outputs[idx] and final_tools[idx], and excludes that idx from later phase collection and phase 3 fallback

### FINDING_11:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:212-243, skills/review/scripts/dispatch-panel.sh:396-404, skills/design/scripts/decompose-panel-dispatch.sh:145-153
- **Concern**: 4. Planned linter rule does not cover variable-backed dispatcher invocations. Scenario: Most target callers invoke "$WATERFALL_SH" or "$DISPATCH_WATERFALL" rather than a literal dispatch-with-waterfall.sh command line, so a basename-only invocation scanner can miss the real call and fail to enforce the unset invariant
- **Proposed resolution**: Extend the scanner to track simple variable assignments whose value resolves to dispatch-with-waterfall.sh and then flag invocations of that variable, or change callers to invoke the literal path; add a regression fixture for this exact variable-backed shape

### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:82-124
- **Concern**: 5. fallback_group TSV field lacks line-oriented validation. Scenario: The proposed ledger writes group and slot values into TSV, but fallback_group is only described as a string; a tab or newline in a grouped manifest row can corrupt ledger parsing and reuse decisions
- **Proposed resolution**: Validate fallback_group as absent/null or a non-empty string without tab, LF, or CR before appending arrays; either also validate grouped slot names for TSV safety or write the ledger through a structured format instead of raw TSV

### FINDING_13:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: Plan assumes phase-2 launches are serialized; code fan-outs all phase-2 slots in one loop before collect_phase. Scenario: Concurrent phase-2 peers in the same fallback_group all launch before any ledger OK row exists; dedup never triggers and double Codex still runs
- **Proposed resolution**: Restructure phase-2 to per-slot launch (check ledger before launch_slot) or drain/wait group peers sequentially; document the invariant in dispatch-with-waterfall.md; add a harness case with two same-group slots queued together

### FINDING_14:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:84-120, skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Finding 1: The plan adds fallback_group support but does not update the real paired vendor manifests to set it. Scenario: Because absence of fallback_group preserves legacy behavior, the design plan-review and decomposition panels will still launch duplicate Codex work in production; only synthetic tests exercise dedup
- **Proposed resolution**: Add fallback_group to each cursor/codex pair in the paired panel manifests, including dynamic plan-review slots, and add caller-level tests asserting the generated NDJSON contains matching groups

### FINDING_15:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: Finding 2: The dedup design assumes phase-2 launches are serialized, but the current dispatcher launches all phase-2 fallbacks before collecting any result. Scenario: Two same-group slots that both need Codex fallback scan the ledger before either fallback has written an OK row, so both Codex processes launch despite the proposed ledger
- **Proposed resolution**: Revise phase 2 to process grouped fallbacks sequentially or elect one representative per fallback_group/tool, collect it, then copy its result to remaining eligible slots before launching more work

### FINDING_16:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:264-296, scripts/dispatch-with-waterfall.sh:326-332
- **Concern**: Finding 3: The plan only specifies writing a ledger row after fallback success, not after grouped primary success. Scenario: A paired Codex slot can succeed in phase 1 while its Cursor peer fails; without recording the phase-1 Codex OK result, the Cursor peer still launches Codex in phase 2
- **Proposed resolution**: Add ledger writes for every grouped OK result in collect_phase, including phase 1 primary successes, and add a regression where codex primary succeeds and cursor primary fails

### FINDING_17:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:85-107
- **Concern**: Finding 4: The new TSV ledger has no validation or encoding plan for fallback_group, slot, or output fields that contain tabs or newlines. Scenario: A malformed or future-generated fallback_group with a tab/newline can corrupt ledger columns, causing false dedup hits, missed dedup, or copied output attributed to the wrong slot
- **Proposed resolution**: Validate fallback_group and all TSV-written fields for no tab/CR/LF before accepting the manifest, or switch the ledger to JSONL so field boundaries cannot be silently corrupted

### FINDING_18:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Item C adds dispatcher dedup but no manifest producer sets fallback_group. Scenario: The worked example names decomp-cursor/decomp-codex pairs yet the plan never updates NDJSON builders; after merge dispatch-with-waterfall still runs legacy per-slot phase-2 for every row and #2898 cost/duplicate work remains
- **Proposed resolution**: Add fallback_group to each paired row in decompose-panel-dispatch.sh (and any other real fanout the issue targets); extend skills/design/scripts/test-decompose-panel-dispatch.sh to assert the field is emitted

### FINDING_19:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:84-120; skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: The plan adds opt-in fallback_group support but never updates the paired slot manifest producers to emit fallback_group. Scenario: The dispatcher change is inert for the paired Cursor/Codex slots that motivated the PR, so double Codex work still happens after this lands
- **Proposed resolution**: Add fallback_group to paired manifest rows, e.g. plan-${archetype}, dyn-plan-${slug}, and decomp-${archetype}; add caller-level assertions in the relevant tests

### FINDING_20:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: The dedup design assumes Phase 2 can observe an earlier group result before launching the next fallback, but current Phase 2 launches every fallback before collecting any result. Scenario: The proposed dedup-hit test cannot pass: two failed primaries in one group will both launch Codex because no OK ledger row exists until after all Phase 2 children have already started
- **Proposed resolution**: Change Phase 2 to be group-aware: launch at most one fallback per fallback_group, collect it, then copy/reuse for peers; or process grouped fallbacks sequentially while leaving ungrouped slots parallel

### FINDING_21:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:212-243; skills/design/scripts/dispatch-plan-review-panel.sh:138-140; skills/design/scripts/decompose-panel-dispatch.sh:145-153
- **Concern**: The proposed shell linter only matches basename-shaped invocation lines, but several real callers invoke dispatch-with-waterfall.sh through a variable. Scenario: The new invariant is not actually enforced on the callsites this plan edits, so future regressions can pass lint even without unset LARCH_PAIRED_PID_FILE
- **Proposed resolution**: Teach the scanner to resolve simple path variable assignments to dispatch-with-waterfall.sh and check the later variable command invocation, or require/directly lint an inline path invocation pattern after the unset

### FINDING_22:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Plan adds `fallback_group` parsing/dedup in `dispatch-with-waterfall.sh` but does not update manifest builders to emit the field on paired vendor slots (nor `dispatch-plan-review-panel.sh`). Scenario: Dedup stays dead code in the primary double-Codex paths this PR targets; only harness fixtures with synthetic manifests would exercise it
- **Proposed resolution**: Add `fallback_group` to jq manifest rows (e.g. `decomp-arch` for `decomp-cursor-*` + `decomp-codex-*` pairs) in decompose-panel-dispatch.sh and the static/dynamic rows in dispatch-plan-review-panel.sh; extend decompose-panel dispatch tests to assert the field is present

### FINDING_23:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:275-293, scripts/dispatch-with-waterfall.sh:321-332
- **Concern**: Plan does not ledger phase-1 OK grouped results before phase-2 decisions. Scenario: If the Codex sibling succeeds in phase 1 and the Cursor sibling fails, the Cursor slot still launches a Codex phase-2 fallback instead of reusing the existing Codex output
- **Proposed resolution**: Write ledger rows for every OK grouped result from each collected phase before building or launching the next phase

### FINDING_24:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: Phase-2 fallbacks are launched as a batch before any phase-2 result is collected. Scenario: Two same-group slots that both need Codex fallback will both launch Codex because the second launch cannot see the first fallback success yet
- **Proposed resolution**: Serialize grouped phase-2 fallback decisions per group/tool or collect and ledger each grouped fallback before launching the next peer

### FINDING_25:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:190-222, skills/review/scripts/dispatch-panel.sh:25, skills/review/scripts/dispatch-panel.sh:404
- **Concern**: The proposed linter rule cannot see variable-mediated dispatch-with-waterfall invocations. Scenario: Real callers resolve dispatch-with-waterfall.sh into variables and later invoke "$DISPATCH_WATERFALL" or "$DISPATCH_SH", so basename-only anchor scanning will miss the actual callsites
- **Proposed resolution**: Track variable assignments to the child path and treat later variable command invocations as checked callsites, or require direct calls and update callers

### FINDING_26:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:79-108
- **Concern**: New TSV ledger fields lack validation or escaping. Scenario: A fallback_group, slot name, or output path containing tabs or newlines can corrupt waterfall-group-results.tsv and produce incorrect reuse decisions
- **Proposed resolution**: Reject tab CR LF in fallback_group and ledgered identifiers/paths, or use JSONL for the ledger instead of raw TSV

### FINDING_27:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Plan adds fallback_group dedup to dispatch-with-waterfall.sh but never wires fallback_group into the 8-slot decompose manifest. Scenario: Primary goal "prevent double Codex work" on paired decomp-cursor-* / decomp-codex-* slots never activates; all manifests omit the field so dispatcher stays on legacy per-slot path
- **Proposed resolution**: Add fallback_group to each jq manifest row (e.g. fallback_group:"decomp-${_a}" shared by the cursor/codex pair per archetype); update skills/design/scripts/test-decompose-panel-dispatch.sh to assert the field is present

### FINDING_28:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: FINDING_1 Plan assumes Phase-2 fallbacks are serialized, but current code launches every Phase-2 process before collection. Scenario: The proposed dedup hit cannot occur for two failed same-group slots because both Codex fallbacks are started before the first one can write an OK ledger row; the planned exactly-one-Codex-launch test will fail unless the dispatcher architecture changes
- **Proposed resolution**: Revise the plan to process grouped Phase-2 fallback candidates in a sequence that collects and records each group result before launching the next same-group fallback, or otherwise explicitly serialize per fallback_group while preserving unrelated parallelism

### FINDING_29:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:84-120; skills/design/scripts/decompose-panel-dispatch.sh:128-142
- **Concern**: FINDING_2 Plan adds an opt-in fallback_group field but does not add it to the production paired vendor manifests. Scenario: The dispatcher will support dedup, but all real paired cursor/codex slots still omit fallback_group, so the feature remains inactive and double Codex work is not prevented in the intended plan-review/decomposition paths
- **Proposed resolution**: Add fallback_group to the paired static and dynamic plan-review rows and the paired decomposition rows, with tests that inspect those manifests for matching group IDs per archetype

### FINDING_30:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:309-337
- **Concern**: FINDING_3 Dedup plan records fallback successes but is silent on recording Phase-1 grouped successes. Scenario: In the normal dual-vendor case, a codex-primary peer can already have an OK Phase-1 result when the cursor-primary peer needs Codex fallback; without recording Phase-1 OK results in the ledger, the cursor slot launches a second Codex process
- **Proposed resolution**: Add a plan step to ledger all OK grouped results from every phase before later fallback decisions, and add a regression where codex-primary succeeds, cursor-primary fails, and the cursor slot reuses the codex-primary output

### FINDING_31:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:209-243; skills/review/scripts/dispatch-panel.sh:396-404
- **Concern**: FINDING_4 The planned linter rule only matches literal basename invocation lines, but several callers invoke dispatch-with-waterfall through variables. Scenario: Lines like waterfall_output=$("$DISPATCH_WATERFALL" ...) do not contain dispatch-with-waterfall.sh, while plain variable assignments are not actual child invocations; the linter can miss missing unset regressions in the scripts the plan is trying to protect
- **Proposed resolution**: Revise the linter plan to either resolve constant wrapper variables to later variable invocations or require and test a literal path/call-site pattern that the scanner can actually recognize

### FINDING_32:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:91-118
- **Concern**: FINDING_5 New fallback_group TSV data lacks a validation plan. Scenario: The ledger format is group<TAB>slot_name<TAB>tool<TAB>output_path<TAB>status, but fallback_group and slot names can currently be arbitrary strings; tabs or newlines can corrupt rows and cause wrong dedup matches or misleading sidecars
- **Proposed resolution**: Add manifest validation for fallback_group and any ledger-written fields, rejecting tab, CR, and LF at minimum, and add malformed fallback_group regression tests

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-caller-site-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:153-159
- **Concern**: Plan claims two synchronous dispatch-with-waterfall callsites (around 145 and 171); repo has one invocation at 153-159 via "$WATERFALL_SH". Scenario: Implementer may add a second unset near the failure-log block (171) or treat 171 as a call; 171 is --tool "dispatch-with-waterfall.sh" on append-execution-issue.sh, not an exec
- **Proposed resolution**: Revise plan to one callsite at 153-159; place unset LARCH_PAIRED_PID_FILE within 5 lines immediately before line 153 (e.g. after set +e at 152)

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-caller-site-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:212-243; skills/design/scripts/dispatch-plan-review-panel.sh:138-140; skills/design/scripts/decompose-panel-dispatch.sh:145-153; skills/design/scripts/decompose-aggregator.sh:113-116; skills/review/scripts/aggregate-findings.sh:631,730; skills/review/scripts/dispatch-panel.sh:25,404
- **Concern**: Proposed linter rule is literal-basename based, but the planned target callers invoke dispatch-with-waterfall.sh through variables. Scenario: CI can pass without enforcing the new parent-unset invariant on the very callers the sweep targets, because the actual command lines are "$DISPATCH_WATERFALL_SH", "$WATERFALL_SH", "$DISPATCH_SH", and "$DISPATCH_WATERFALL"; the basename appears only in assignments or the diagnostic --tool string at decompose-panel-dispatch.sh:171
- **Proposed resolution**: Extend the scanner to resolve simple variable assignments to dispatch-with-waterfall.sh and enforce unset before the variable invocation, or rewrite the callers to invoke the literal path directly after unset; add regression fixtures for variable-mediated calls and for excluding the --tool "dispatch-with-waterfall.sh" non-invocation

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-caller-site-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:145-153,168-174; skills/review/scripts/aggregate-findings.sh:631,729-737; skills/review/scripts/dispatch-panel.sh:25,396-404
- **Concern**: The plan's callsite line guidance misidentifies variable definitions and a diagnostic string as invocation sites. Scenario: Following the stated lines can place unset outside the five-line look-back or at a non-invocation: decompose-panel-dispatch.sh:145 is eight lines before the actual call at 153 and line 171 is only an append-execution-issue --tool argument; aggregate-findings.sh:631 is nearly 100 lines before the actual call at 730; dispatch-panel.sh:25 is a variable definition while the actual call is at 404
- **Proposed resolution**: Revise the sweep to target actual invocation adjacency: dispatch-plan-review-panel.sh before 140, decompose-panel-dispatch.sh before 153 only, decompose-aggregator.sh before 116, aggregate-findings.sh immediately before 730 inside the loop, and dispatch-panel.sh immediately before 404; explicitly state that decompose-panel-dispatch.sh:171 is excluded both from the sweep and the linter rule

### FINDING_36:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:324-337
- **Concern**: Plan claims phase-2 launches are serialized within one dispatcher call; implementation backgrounds every phase-2 slot then waits once in collect_phase. Scenario: Peer slots in the same fallback_group can both pass the empty ledger and launch duplicate Codex before any row is written; write+rename after success does not serialize concurrent launch_slot calls
- **Proposed resolution**: Revise dispatch-with-waterfall.sh phase-2 loop to process fallback_group members sequentially (launch/wait/ledger per group) or add a pre-launch group lock; remove or correct the serialized phase-2 invariant in dispatch-with-waterfall.md and plan edge cases

### FINDING_37:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:227-303
- **Concern**: Proposed dedup only consults/writes the ledger around phase-2 Codex fallback; no step records phase-1 OK rows for grouped slots. Scenario: Motivating #2898 case: decomp-codex-* settles phase-1 Codex OK while decomp-cursor-* fails --require-result-pattern and needs phase-2 Codex; ledger empty so redundant Codex still runs
- **Proposed resolution**: After each collect_phase (at least phase-1), append ledger rows for slots with fallback_group when STATUS is OK/cap_hit (tool + resolved output path); dedup scan must match group+tool across phases not only phase-2 launches

### FINDING_38:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-panel-dispatch.sh:131-142
- **Concern**: Item C adds fallback_group to the manifest schema but Files to modify does not update the decompose panel jq rows that emit the 16 vendor slots. Scenario: Dedup stays opt-out for every production caller; double Codex on narration-only fallback in decompose panel remains after the PR
- **Proposed resolution**: Add --arg fallback_group "decomp-${_a}" (or the documented name) to both jq -nc manifest builders in decompose-panel-dispatch.sh; extend test-decompose-panel-dispatch.sh to assert the field is present

### FINDING_39:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:212-244
- **Concern**: New parent-unset rule matches only lines containing the literal basename dispatch-with-waterfall.sh. Scenario: Most callers invoke via "$WATERFALL_SH" / "$DISPATCH_WATERFALL_SH" / "$DISPATCH_SH" / "$DISPATCH_WATERFALL" (e.g. skills/design/scripts/decompose-panel-dispatch.sh:153, skills/review/scripts/dispatch-panel.sh:404); unset may be added but CI will not enforce it
- **Proposed resolution**: Extend scan_shell_file_for_unset_before_nested_child to treat a line as an anchor when it invokes a variable assigned from *dispatch-with-waterfall.sh on an earlier line, or require literal script paths at call sites; add fixtures for variable-mediated invocations

### FINDING_40:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-dispatch-with-waterfall.sh
- **Concern**: Planned dedup tests describe two slots both failing primary then sharing one Codex fallback; they omit the accepted OOS scenario (peer phase-1 Codex OK + cursor slot phase-2 Codex). Scenario: Regression can pass while production decompose still double-bills Codex on the real failure mode
- **Proposed resolution**: Add a case: slot A (codex primary) phase-1 OK with ## Recommendation, slot B (cursor primary) phase-1 pattern-miss, same fallback_group; assert zero extra Codex invocations and DEDUPE_REUSED_FROM pointing at A

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/dispatch-with-waterfall.sh:77-124
- **Concern**: Plan mentions a session mapping file but not parallel per-slot fallback_group storage alongside slot_names[]. Scenario: Implementers may omit group lookup by slot index and break dedup at launch time
- **Proposed resolution**: Add slot_fallback_groups+=() during manifest parse (jq -r '.fallback_group // empty'); skip ledger logic when empty

### FINDING_42:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:17
- **Concern**: States decompose-panel-dispatch.sh has two dispatch-with-waterfall callsites; repo has one synchronous capture at line 153. Scenario: Misleading implementer scope (unnecessary second unset hunt)
- **Proposed resolution**: Correct the plan to a single callsite; keep decompose-aggregator.sh as a separate one-slot caller (no fallback_group unless later needed)

### FINDING_43:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:49-50
- **Concern**: Ledger status value OK,reused embeds a comma inside the status column. Scenario: Naive TSV parsers or grep for status=OK may miss reused rows or split fields wrong
- **Proposed resolution**: Use a single-token status (reused) plus optional source_slot column, or document strict five-field tab parsing only

### FINDING_44:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/dispatch-with-waterfall.sh:84-95
- **Concern**: Optional fallback_group has no jq type guard when present. Scenario: Non-string fallback_group could corrupt ledger keys or scans
- **Proposed resolution**: Add jq elif for has("fallback_group") requiring a non-empty string, mirroring agent/prompt_file checks

### FINDING_45:
- **Reviewer(s)**: Codex-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:187-225,324-337
- **Concern**: Plan relies on serialized phase-2 fallback launches, but current phase 2 launches every queued alternate-external slot in background before any collection or ledger write can occur. Scenario: Two slots in the same fallback_group can both scan an empty ledger and launch Codex concurrently; mktemp+mv makes each write atomic but does not prevent the duplicate-launch race
- **Proposed resolution**: Revise the plan to make grouped phase-2 dispatch sequential per fallback_group, or add an atomic in-flight reservation/lock and peer wait/read path before launch; keep ungrouped slots on the existing parallel path if desired

### FINDING_46:
- **Reviewer(s)**: Codex-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:84-97,109-120; skills/design/scripts/decompose-panel-dispatch.sh:127-143
- **Concern**: Plan adds dispatcher support for optional fallback_group but does not update the paired vendor manifest writers that would opt production slots into dedup. Scenario: Tests with hand-authored fallback_group rows can pass while the actual plan-review and decomposition panels still emit cursor/codex pairs with no fallback_group, so double Codex work remains possible
- **Proposed resolution**: Add fallback_group to the jq-rendered NDJSON rows for intended paired slots, such as plan-${_archetype}, plan-dyn-${_slug}, and decomp-${_a}; add caller tests that assert paired cursor/codex rows share the same group

### FINDING_47:
- **Reviewer(s)**: Codex-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:82-123,388-396
- **Concern**: The proposed raw TSV ledger lacks a validation or escaping rule for fallback_group, slot_name, and output_path fields. Scenario: Current parsing accepts arbitrary non-empty slot strings and output paths with tabs; a tab or newline in a grouped field can shift TSV columns or create synthetic rows, causing missed or wrong dedup reuse
- **Proposed resolution**: Specify and implement Bash-3.2-compatible validation for grouped ledger fields: reject tab, LF, and CR in fallback_group and slot_name, and reject tab in grouped output paths or switch the ledger to JSONL parsed with jq/read loops

### FINDING_48:
- **Reviewer(s)**: Cursor-dyn-prose-fence-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:90-91,scripts/lint-foreground-markers.sh:198-206,408-412,483-491
- **Concern**: Failure modes claim fence_stale_foreground_markers will catch reintroduction of the contradictory post-fence line; it only flags OLD foreground banner/comment tokens inside the fence body or the pre-fence window, not post-fence prose. Scenario: Re-adding `Do NOT set run_in_background: true` immediately after a background+monitor fence (as at skills/research/references/research-phase.md:215 and validation-phase.md:209 today) would pass make lint-foreground-markers because scan_markdown_file stops analyzing at fence close and never inspects following lines for that phrase
- **Proposed resolution**: Revise Failure modes #3 to state the gap explicitly; extend lint (post-fence contradiction scan when fence has run_in_background: true plus breadcrumb-monitor.sh) or add test-lint-foreground-markers fixtures copying research-phase.md/validation-phase.md post-fence patterns

### FINDING_49:
- **Reviewer(s)**: Codex-dyn-prose-fence-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:198-206; scripts/lint-foreground-markers.sh:408-412; skills/research/references/research-phase.md:215; skills/research/references/validation-phase.md:209
- **Concern**: The plan relies on existing stale-marker detection for the exact contradictory post-fence prose, but the linter only checks OLD_BANNER/OLD_COMMENT inside the fence body or the pre-fence window. The current contradictory sentence is after the fenced background+monitor block and is the bare prose "Do NOT set run_in_background: true", so the existing stale-marker rule does not cover the specific pattern Item A removes.. Scenario: A future edit could reintroduce the same post-fence "Do NOT set run_in_background: true" sentence after a correct background+monitor collector fence in research-phase.md or validation-phase.md, and make lint-foreground-markers would not catch it.
- **Proposed resolution**: Revise the plan to extend scripts/lint-foreground-markers.sh and scripts/test-lint-foreground-markers.sh with a targeted post-fence stale-prose check for background+monitor Family B fences, or replace the plan's reliance on lint with an explicit regression test that fails when research-phase.md or validation-phase.md contain that contradictory post-fence sentence.

### OOS_1:
- **Description**: 10+12 slot plan-review manifest has same dual-vendor waterfall shape but no fallback_group wiring. Scenario: Duplicate Codex work on large plan-review panels after decompose-only wiring
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:1-200
- **Phase**: design

### OOS_2:
- **Description**: No harness update to assert single Codex launch with fallback_group. Scenario: Regression slips for #2885 panel path
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-decompose-panel-dispatch.sh:1-999
- **Phase**: design

### OOS_3:
- **Description**: §4 parent-unset list still names only dispatch-plan-voters.sh; plan adds more parents via linter but not the canonical prose list. Scenario: Drift between docs and enforced callers
- **Reviewer**: Cursor-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: architecture
- **Location**: BASH_AUTHORING.md:73
- **Phase**: design
