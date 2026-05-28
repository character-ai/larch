### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:22,373-386
- **Concern**: plan checks revise exit code, but helper reports logical failures through REVISE_STATUS with exit 0. Scenario: All revise tiers can fail, plan.txt is restored, helper exits 0, and the loop treats the round as successfully auto-applied
- **Proposed resolution**: Parse REVISE_STATUS from stdout and require ok; treat failed-no-patch, failed-validation, and failed-apply as LOOP_STATUS=revision-failed

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/revise-plan-with-waterfall.md:11,34-39; scripts/design-log-publish.sh:363-374
- **Concern**: Revise artifact layout conflicts with the proposed publisher allowlist. Scenario: The helper writes plan-review/round-N/revise/*, while the plan says design-log-publish should disallow revise/ under plan-review; any auto-revise round will fail publish
- **Proposed resolution**: Choose one layout and update both sides: either move revise output to DESIGN_TMPDIR/revise/round-N or explicitly allow a constrained round-N/revise allowlist

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:368-377,501-509; skills/design/scripts/file-design-oos.sh:216-267
- **Concern**: Accepted OOS items from earlier internal rounds are overwritten. Scenario: The tally truncates oos-accepted-design.md every round, and file-design-oos only reads that final top-level file; round-1 accepted OOS can disappear after round 2
- **Proposed resolution**: Add an accumulated accepted-OOS artifact across internal rounds and make Step 5b read it, with stable IDs or round-qualified IDs

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/approval-gates.md:120-131; skills/design/scripts/revise-plan-with-waterfall.sh:250-256
- **Concern**: Moving auto-apply into the loop bypasses Gate B's shared post-apply pipeline. Scenario: The helper runs ACTION=EMIT_PLAN, but passive Gate B no longer runs duplicate sweep, full validator dispatch, or Step 2b.5 size/split gate after the final revised plan
- **Proposed resolution**: Factor the post-revision pipeline into a scriptable helper and call it after successful auto-revise, at least before Step 3b on the final loop result

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:24-58,699-705; skills/design/SKILL.md:987-994
- **Concern**: Single-pass compatibility contract is internally inconsistent. Scenario: The plan says omitted --round-cap preserves single-pass and LOOP_STATUS=complete, but the pseudocode still auto-applies and exits converged or cap-hit
- **Proposed resolution**: Track whether --round-cap was explicitly supplied; define legacy single-pass behavior separately, including whether revise runs and when complete is emitted

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: Makefile:4,63-102,427-461
- **Concern**: New integration harness is not listed as a Makefile update target. Scenario: The plan creates scripts/test-design-multi-round-integration.sh and says make lint runs it, but the file list omits Makefile changes needed for .PHONY, target, and shard wiring
- **Proposed resolution**: Add ### UPDATED: Makefile to the plan and specify the target plus test-harness shard wiring

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:348-386
- **Concern**: Plan treats revise failure as non-zero rc, but helper reports failed revisions via REVISE_STATUS while exiting 0. Scenario: A failed/no-patch waterfall is interpreted as success, PLAN_HASH_AFTER_REVISE stays equal, accepted findings are not applied, and the loop can converge or cap-hit with silently unapplied findings
- **Proposed resolution**: Parse revise stdout, require REVISE_STATUS=ok for success, branch revision-failed on any failed-* status, and add a regression where the helper exits 0 with REVISE_STATUS=failed-no-patch

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:104-108; scripts/design-log-publish.sh:352-367
- **Concern**: Plan disallows plan-review/round-N/revise while the revise helper writes there. Scenario: Any successful auto-apply creates plan-review/round-N/revise artifacts, then design-log-publish fail-closes on the unexpected nested path during final publish
- **Proposed resolution**: Either update revise-plan-with-waterfall.sh and its md/tests to write under DESIGN_TMPDIR/revise/round-N, or allow a constrained round-N/revise allowlist in design-log-publish and document it

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:368-377; skills/design/SKILL.md:1196-1223
- **Concern**: Accepted OOS artifacts are overwritten each internal round with no cross-round merge. Scenario: OOS accepted in round 1 disappears when round 2 rewrites oos-accepted-design.md, so Step 5b never files that accepted issue
- **Proposed resolution**: Define and test a cross-round OOS union artifact, dedupe OOS IDs across rounds, and make Step 5b consume the union after the loop

### FINDING_10:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/SKILL.md:917-993
- **Concern**: Proposed stale-round cleanup uses rm -rf through an unchecked plan-review path. Scenario: If DESIGN_TMPDIR/plan-review is a symlink or swapped path, rm -rf "$DESIGN_TMPDIR/plan-review/round-"* can delete round-* paths outside the session tree
- **Proposed resolution**: Before cleanup, reject symlink/non-directory plan-review paths, resolve the physical root, and delete only validated child directories under that root

### FINDING_11:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:82-96; skills/design/scripts/plan-review-loop.md:7-16
- **Concern**: Round summary schema omits fields Gate B is supposed to derive from it. Scenario: Passive-summary mode promises per-round LOOP_STATUS, but round-summary.env lacks LOOP_STATUS/REASON/REVISE_STATUS and may record pre-failure DEGRADED_PANEL values
- **Proposed resolution**: Add LOOP_STATUS, REASON, CONVERGENCE_STREAK, REVISE_STATUS, and revise tier/status fields to round-summary.env; write the final per-round state after revision outcome is known

### FINDING_12:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:24-58; skills/design/scripts/plan-review-loop.md:18-20
- **Concern**: Round-cap defaults and single-pass compatibility are internally inconsistent. Scenario: One part says --round-cap defaults to LARCH_DESIGN_ROUND_CAP, another says omitted --round-cap defaults to --round-num; existing callers may unexpectedly run multiple rounds or auto-revise when they expected a single complete pass
- **Proposed resolution**: Add an explicit ROUND_CAP_ARG_SEEN/single_pass_mode contract: omitted --round-cap ignores env and preserves old complete/no-auto-loop behavior, while SKILL.md passes explicit production caps

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:348-386; skills/design/scripts/plan-review-loop.sh:676-705
- **Concern**: Plan treats revise exit code as the only failure signal. Scenario: The revise helper reports logical total failure as REVISE_STATUS=failed-* with exit 0, so the loop can mark findings auto-applied and converge even though plan.txt was restored unchanged
- **Proposed resolution**: Parse revise stdout, require REVISE_STATUS=ok, and treat any failed-* status as LOOP_STATUS=revision-failed; update tests to stub rc=0 plus failed status

### FINDING_14:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:78-103; skills/design/references/approval-gates.md:180
- **Concern**: Manual Gate B contract is contradicted by unconditional inner-loop auto-apply. Scenario: Users who pass --manual still have accepted findings applied before Gate B, then see manual choices for changes already made
- **Proposed resolution**: Either disable inner-loop auto-apply when manual_gate_b=true, or explicitly make manual mode incompatible with multi-round auto-apply and change the prompt/contract

### FINDING_15:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:120-131
- **Concern**: Auto-applied revisions skip the existing post-apply pipeline. Scenario: The loop revises plan.txt, then passive Gate B can continue without duplicate sweep, plan validator, or Step 2b.5 size/decomposition checks that currently run after Gate B applies findings
- **Proposed resolution**: Run the shared post-apply pipeline once after the final successful auto-apply, or factor it into a script and invoke it from passive Gate B before Step 3b

### FINDING_16:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:104-108; scripts/design-log-publish.sh:362-374
- **Concern**: Revision forensics are written under a path the proposed publisher rejects. Scenario: revise-plan-with-waterfall.sh writes plan-review/round-N/revise/* today, while the plan says design-log-publish.sh will disallow revise/ under plan-review/round-N, so any successful auto-apply can make final log publishing fail closed
- **Proposed resolution**: Choose one contract: either allow a constrained round-N/revise allowlist in design-log-publish.sh, or change the revise helper output dir and add explicit publishing support for that subtree

### FINDING_17:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:337-377; skills/design/scripts/plan-review-loop.sh:676-705
- **Concern**: Per-round artifacts can reuse stale accepted findings after a tally error. Scenario: Early tally errors can happen before accepted-plan-findings.md is truncated, so round N can count and re-apply round N-1 findings instead of stopping cleanly
- **Proposed resolution**: Clear session-root review artifacts at the start of each round or use round-scoped files, and branch on TALLY_PLAN_REVIEW_STATUS=tally-error before accepted-count, convergence, or revise

### FINDING_18:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/test-plan-review-loop.sh:327-329; skills/design/scripts/plan-review-loop.sh:699-705
- **Concern**: Backward-compatible LOOP_STATUS=complete path conflicts with the proposed cap logic. Scenario: With --round-num K and no --round-cap, effective cap equals K, so a positive-finding single-pass run reaches the cap branch and emits cap-hit instead of current complete
- **Proposed resolution**: Track whether --round-cap was explicitly provided; in omitted-cap single-pass mode preserve LOOP_STATUS=complete and current artifact behavior

### FINDING_19:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:104-108 scripts/design-log-publish.sh:352-367
- **Concern**: Plan disallows plan-review/round-N/revise publishing, but the revise helper writes exactly that subtree. Scenario: Every successful auto-apply creates plan-review/round-N/revise/*, then design-log-publish.sh fails closed on nested unexpected files
- **Proposed resolution**: Update revise-plan-with-waterfall.sh and its md sibling to write forensics under DESIGN_TMPDIR/revise/round-N, or allow a constrained nested revise allowlist in design-log-publish.sh; make the plan choose one concrete contract

### FINDING_20:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:661-676 skills/design/scripts/tally-plan-review.sh:121-133
- **Concern**: Outer-loop pseudocode has no tally-error branch before accepted-count, revision, and convergence logic. Scenario: If tally fails before accepted-plan-findings.md is truncated, stale findings from a prior round can be revised again or counted as convergence/cap evidence
- **Proposed resolution**: After each round, branch on TALLY_PLAN_REVIEW_STATUS=tally-error before snapshot/revise/convergence; emit KVs that let SKILL.md roll back review-round-count.txt and do not consume stale accepted artifacts

### FINDING_21:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1037 skills/design/scripts/tally-plan-review.sh:103-105
- **Concern**: Main-agent vote rerun is left unchanged, so tally defaults findings-classification-out to round-1. Scenario: In internal round 2+, main-agent adjudication overwrites or misplaces the classification TSV and the round snapshot no longer matches the round that needed main-agent voting
- **Proposed resolution**: Update the main-agent-vote-required path to pass --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-$ROUNDS_COMPLETED/findings-classification.tsv" and define whether post-main-agent accepted findings are auto-applied or handled by Gate B

### FINDING_22:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.md:12-20 skills/design/scripts/plan-review-loop.sh:699-705
- **Concern**: The plan promises backward-compatible single-pass complete behavior, but the new pseudocode has no reachable complete path once auto-apply/cap/converged logic runs. Scenario: Existing callers/tests that omit --round-cap can see converged or cap-hit and plan revision side effects despite the documented compatibility contract
- **Proposed resolution**: Introduce an explicit legacy_single_pass mode when --round-cap is omitted, or remove the compatibility promise and update all tests/docs/callers to the new status and auto-apply semantics

### FINDING_23:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4-5
- **Concern**: The plan creates scripts/test-design-multi-round-integration.sh but does not list Makefile as an updated file. Scenario: New integration coverage is not run by make lint/test-harness shards, so the cross-script regression harness can silently rot
- **Proposed resolution**: Add Makefile to the plan with a phony test-design-multi-round-integration target and shard wiring; update docs/linting.md if target docs are expected

### FINDING_24:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:22 skills/design/scripts/plan-review-loop.sh:681-686
- **Concern**: Refactor plan does not reset the current global _dedup_failed per internal round. Scenario: A single dedup failure in round 1 can mark later clean rounds degraded, breaking convergence streaks and forcing unnecessary cap-hit runs
- **Proposed resolution**: Move _dedup_failed initialization inside _run_plan_review_round before dedup runs, and add a regression where only the first round dedup fails

### FINDING_25:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:381-386
- **Concern**: Plan checks revise_rc but the helper reports total revision failure through REVISE_STATUS while exiting 0. Scenario: All waterfall tiers fail, plan-review-loop treats revise_rc=0 as success, advances convergence or cap state, and Gate B passive summary can claim accepted findings were applied even though plan.txt was restored
- **Proposed resolution**: Parse REVISE_STATUS=ok from revise stdout or change revise-plan-with-waterfall.sh to exit nonzero on failed-*; add tests for failed-no-patch and failed-validation

### FINDING_26:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:104-108, scripts/design-log-publish.sh:362-367
- **Concern**: Revise forensics still live under plan-review/round-N/revise while the publish plan disallows nested plan-review paths. Scenario: A successful auto-apply round leaves revise/prompt.txt and output files under plan-review/round-N; design-log-publish.sh then fails closed on unexpected nested files
- **Proposed resolution**: Add UPDATED revise-plan-with-waterfall.sh to move revise forensics to DESIGN_TMPDIR/revise/round-N, or allow a constrained revise subdir in publisher; align snapshot and integration tests

### FINDING_27:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:120-131, skills/design/scripts/revise-plan-with-waterfall.sh:250-257
- **Concern**: Auto-apply inside the loop bypasses the existing post-apply validation and size-gate pipeline. Scenario: A revised plan can skip the duplicate sweep, full-review validator, and Step 2b.5 split threshold before Gate C, so an oversized or invalid final plan can be approved
- **Proposed resolution**: Add the shared post-apply pipeline after every successful loop revision or before passive Gate B continues; test validator and Step 2b.5 execution after loop auto-apply

### FINDING_28:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:368-377, skills/design/SKILL.md:1198-1203
- **Concern**: Multi-round tally overwrites root OOS and rejected artifacts each round. Scenario: An accepted OOS item from round 1 disappears if round 2 overwrites oos-accepted-design.md with no OOS items, so Step 5b never files it
- **Proposed resolution**: Maintain cumulative loop-level OOS and rejected artifacts or merge per-round snapshots into the root artifacts before Step 4 and Step 5b; add regression coverage

### FINDING_29:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1037, skills/design/scripts/plan-review-loop.sh:699-708
- **Concern**: main-agent-vote-required is left outside the auto-apply loop. Scenario: With zero external voters, the main-agent tally can accept findings, but the proposed loop halts before revision and does not define whether to resume rounds or route to manual Gate B
- **Proposed resolution**: After main-agent tally, either call the revise helper and resume/exit the loop by the same rules, or explicitly document and test a manual Gate B exception

### FINDING_30:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4, Makefile:26, Makefile:81-102
- **Concern**: New integration harness is required but Makefile is not in the change set. Scenario: make lint can miss test-design-multi-round-integration even though the plan makes it an acceptance check
- **Proposed resolution**: Add UPDATED: Makefile, wire test-design-multi-round-integration into a harness shard and .PHONY list, and update scripts/relevant-checks.sh if scoped checks must select it

### FINDING_31:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/plan-review-loop.sh:699-705, skills/design/scripts/plan-review-loop.md:12-20
- **Concern**: LOOP_STATUS=complete backward compatibility is underspecified. Scenario: The plan says complete remains and tests should keep a single-pass complete path, but the pseudocode exits as converged, cap-hit, revision-failed, panel-failed, or main-agent-vote-required
- **Proposed resolution**: Define the exact legacy-mode branch for omitted --round-cap, or remove complete from the contract and update all callers and tests

### FINDING_32:
- **Reviewer(s)**: Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:52-63; skills/design/scripts/revise-plan-with-waterfall.sh:348-386
- **Concern**: Revision failure is keyed to revise_rc, but the helper reports failed-no-patch, failed-validation, and failed-apply with exit 0. Scenario: A failed auto-apply round with ACCEPTED_COUNT <= threshold and IMPORTANT_ACCEPTED_COUNT == 0 falls through as a successful non-degraded round; convergence or cap-hit can fire instead of revision-failed
- **Proposed resolution**: Parse revise-plan-with-waterfall.sh stdout, branch on REVISE_STATUS != ok, and add a test where the helper exits 0 with REVISE_STATUS=failed-no-patch

### FINDING_33:
- **Reviewer(s)**: Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:57-63; <TMPDIR>/plan.txt:151-153
- **Concern**: round-summary.env is written before DEGRADED_PANEL is forced to 1 on revision-failed. Scenario: The emitted LOOP_STATUS can say revision-failed with DEGRADED_PANEL=1 while Gate B's per-round summary, read from round-summary.env, shows DEGRADED_PANEL=0
- **Proposed resolution**: Move DEGRADED_PANEL=1 before _write_round_summary on the revision-failed branch, then write the summary once after the final round status is known

### FINDING_34:
- **Reviewer(s)**: Cursor-dyn-loop-state-ordering, Codex-dyn-loop-state-ordering
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:40-50; skills/design/scripts/plan-review-loop.sh:243-249; skills/design/scripts/plan-review-loop.sh:303-324; skills/design/scripts/plan-review-loop.sh:518-522
- **Concern**: Zero-findings convergence is guarded only by readable panel paths, not by successful collection evidence. Scenario: If dispatch creates a readable paths file but collection returns no OK reviewer rows, findings.md is empty and the proposed outer loop can emit converged REASON=zero-findings instead of treating the round as broken or degraded
- **Proposed resolution**: Track COLLECT_OK_COUNT and COLLECT_FAILURE_COUNT in _run_plan_review_round; allow zero-findings convergence only when collector evidence proves reviewers actually completed, and add a broken-collector zero-findings regression test

### FINDING_35:
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:80-81,138-145; skills/design/SKILL.md:997-1005,1037-1049
- **Concern**: The plan emits and documents IMPORTANT_ACCEPTED_COUNT, CONVERGENCE_STREAK, and REASON, but the SKILL.md change only promises parsing them and only branches on LOOP_STATUS.. Scenario: The new scalar KVs become parse-only data; Gate B cannot distinguish REASON=zero-findings vs REASON=streak, cannot use IMPORTANT_ACCEPTED_COUNT to decide warning or passive-summary wording, and cannot validate CONVERGENCE_STREAK before treating convergence as settled.
- **Proposed resolution**: Add an explicit SKILL.md branch matrix for LOOP_STATUS plus REASON, IMPORTANT_ACCEPTED_COUNT, and CONVERGENCE_STREAK. Include the keys in the Bash case parser, initialize them, validate expected enum/range values, and define how each affects Gate B mode and warning text.

### FINDING_36:
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:138-145; skills/design/SKILL.md:969-1033
- **Concern**: The plan does not specify any durable handoff for the parsed KVs from the Step 3 Bash fence to later prompt-side branch prose.. Scenario: Current SKILL.md captures plan-review-loop.sh stdout into _plan_review_out, parses KVs into shell locals, and exits the fence without printing or persisting the normalized values. The prose that follows cannot reliably branch on converged, cap-hit, revision-failed, REASON, or CONVERGENCE_STREAK.
- **Proposed resolution**: Write a normalized env file such as $DESIGN_TMPDIR/.step3-plan-review-result.env and/or print the canonical parsed KVs after validation. Have later SKILL.md prose and Gate B read that durable result instead of relying on shell locals lost at fence exit.

### FINDING_37:
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:18,47-50,74-81,168-169; skills/design/scripts/plan-review-loop.sh:518-522,699-705
- **Concern**: The plan is internally inconsistent about preserving the old LOOP_STATUS=complete single-pass path.. Scenario: It says omitting --round-cap preserves single-pass behavior and says complete remains, but the pseudocode emits converged for zero findings and cap-hit when the one allowed round reaches the cap. Existing callers that key off complete would stop seeing it despite the backward-compat promise.
- **Proposed resolution**: Add an explicit single_pass_compat flag set when --round-cap is omitted. In that mode, keep the current complete emissions for normal and empty single-pass exits, and document exactly when complete can still appear in plan-review-loop.md and the tests.

### FINDING_38:
- **Reviewer(s)**: Cursor-dyn-kv-surface-sync, Codex-dyn-kv-surface-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:28,57-63,151
- **Concern**: The planned round-summary.env schema omits LOOP_STATUS, REASON, and CONVERGENCE_STREAK even though Gate B passive-summary mode is supposed to derive LOOP_STATUS from round-summary.env.. Scenario: Gate B cannot render the proposed per-round summary from round files, and revision-failed summaries can be stale because _write_round_summary runs before DEGRADED_PANEL is forced to 1 for revision-failed.
- **Proposed resolution**: Extend round-summary.env to include LOOP_STATUS, REASON, and CONVERGENCE_STREAK. Write the summary only after final status and degraded-panel mutations are complete, especially on revision-failed.

### FINDING_39:
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:22-25,113-129,202-203
- **Concern**: Two independent allowlist functions are planned without an ownership/update procedure. Scenario: The plan names the loop snapshot as source of truth, but implementers still have to edit round_artifact_included and design_round_artifact_included separately; a later artifact addition can update only one function and either fail publish or silently omit/publish the wrong files
- **Proposed resolution**: Make one shared allowlist helper or generated list used by both scripts; if duplication remains, document that additions/removals are owned by the plan-review-loop contract and require synchronized edits to both scripts, both sibling docs, and the drift test in the same change

### FINDING_40:
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22-25,117-129; skills/design/scripts/plan-review-loop.sh:632-640
- **Concern**: findings-classification.tsv is both listed as a loop snapshot artifact and described as a publish-only back-compat superset item. Scenario: The plan says publish is the same set plus findings-classification.tsv for back-compat, but the proposed loop include list already contains it and current tally writes it under plan-review/round-N; implementers can choose inconsistent behavior without tests revealing which contract is intended
- **Proposed resolution**: Choose and document one contract: either findings-classification.tsv remains a canonical loop-produced artifact, or it is legacy publish-only; update the loop allowlist, publish allowlist, docs, and golden fixtures to make that asymmetry explicit

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-allowlist-drift-contract, Codex-dyn-allowlist-drift-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:176-181,206-214; scripts/test-design-log-publish.sh:254-257,682-689
- **Concern**: The proposed integration test does not require an exact source-to-published plan-review file set. Scenario: A test that checks expected files exist, raw files are absent, and one unknown fixture fails can still miss drift: publish may stage an extra newly allowed file, or the loop may add an artifact that the publish fixture never includes
- **Proposed resolution**: Build the integration test from actual loop output, publish that same tmpdir, and compare sorted relative file lists exactly after documented legacy exceptions; also assert the unknown-file case leaves PUBLISH_OK=false and no staged plan-review artifact
