### OOS_1: Sibling harness doc still claims moved OOS/checkpoint and escalation-success prose live only in every-run parent references.
- **Description**: Sibling harness doc still claims moved OOS/checkpoint and escalation-success prose live only in every-run parent references.. Scenario: After the split, lines 17–18 will misdescribe where CI-fix, OOS-router, and Step 18a.5 filing prose live, causing future harness drift.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.md:17-18
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Sibling harness doc still claims OOS/checkpoint prose lives only in the every-run `ship-pr-exit-matrix.md` parent.
- **Description**: [OUT_OF_SCOPE] Sibling harness doc still claims OOS/checkpoint prose lives only in the every-run `ship-pr-exit-matrix.md` parent.. Scenario: After the OOS-router split, the contract note becomes false and can mislead future harness edits back toward duplicating router body in the matrix.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.md:17-18
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Step 18a.5 ownership forward still names only `step18-cleanup.md` as the full reporting owner after filing moves to `step18a5-filing.md`.
- **Description**: [OUT_OF_SCOPE] Step 18a.5 ownership forward still names only `step18-cleanup.md` as the full reporting owner after filing moves to `step18a5-filing.md`.. Scenario: Operators editing stall recovery may add filing steps to the wrong reference because the forward still implies cleanup owns the full escalation-success procedure.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/stall-recovery.md:53
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] `**Contract**` header still claims full escalation-success reporting ownership after only gate text remains inline.
- **Description**: [OUT_OF_SCOPE] `**Contract**` header still claims full escalation-success reporting ownership after only gate text remains inline.. Scenario: The header overstates every-run load semantics once filing moves to a conditional child reference, inviting prose drift back into cleanup.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/references/step18-cleanup.md:5
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: Step 18a.5 ownership forward still names only step18-cleanup.md after eligible filing moves to step18a5-filing.md
- **Description**: Step 18a.5 ownership forward still names only step18-cleanup.md after eligible filing moves to step18a5-filing.md. Scenario: stall-recovery.md and test-implement-structure.sh line 512 still require forwarding Step 18a.5 to step18-cleanup.md only. After the split, eligible filing authority lives in step18a5-filing.md; operators tracing escalation-success from stall recovery may load the gate file and miss the conditional filing reference.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/stall-recovery.md:51-53
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: Step 18a.5 ownership forward still names only step18-cleanup.md after eligible filing moves to step18a5-filing.md
- **Description**: Step 18a.5 ownership forward still names only step18-cleanup.md after eligible filing moves to step18a5-filing.md. Scenario: Operators on stall-recovery paths may load cleanup for filing steps that now live only in the child reference
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/references/stall-recovery.md:51-53
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_7: Sibling harness doc still claims OOS/checkpoint and escalation-success filing prose live only in every-run parent references
- **Description**: Sibling harness doc still claims OOS/checkpoint and escalation-success filing prose live only in every-run parent references. Scenario: Contributor docs contradict post-split lazy-load layout and can mislead harness edits
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.md:17-18
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_8: Contract header still claims full escalation-success reporting ownership after only gate text remains inline
- **Description**: Contract header still claims full escalation-success reporting ownership after only gate text remains inline. Scenario: Every-run readers infer filing authority still lives in cleanup though procedure moves to step18a5-filing.md
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/references/step18-cleanup.md:5
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

