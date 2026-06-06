### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/shared/scripts/oos-serialize.sh:31-62
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Security routing duplicated as inline Python instead of reusing lib-vote-tally.sh::is_security_block. Future security contract changes require editing lib-vote-tally, oos-serialize, python/oos.py, and awk in lockstep; harnesses test each copy independently so drift can ship silently. Source lib-vote-tally.sh in oos-serialize.sh and call is_security_block per block with explicit exit-2 handling; delete the inline Python heredoc.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:539-600
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Checkpoint harness lacks legacy FINDING header cases added for the gate primitive. Legacy-header blocks could behave differently in checkpoint wiring (tmpdir discovery, NDJSON paths) than in direct gate tests. Mirror #3550 legacy-header gate cases in the checkpoint section of test-oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1438-1457
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Skipped-OOS path calls is_security_block twice with nested if/else including unreachable sec_rc=0 branch. Harder to audit the 0=security / 1=normalize / 2=abort contract; future edits may reintroduce mis-routing. Single is_security_block call with case on exit code for security append, normalization, or abort.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: skills/review/scripts/tally-code-votes.sh:125-130
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS_WRITE_SEQ seeding uses non-security awk count that ignores bare legacy FINDING headers in accumulated-oos.md. Resuming a session with pre-#3550 accumulated content can reuse OOS_1 and produce duplicate or ambiguous blocks for filing parsers. Seed from normalized block count or normalize accumulated-oos.md before continuing the sequence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1438-1456
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate is_security_block invocation in the skipped-findings else branch with a dead sec_rc==0 path. No functional breakage today, but obscures the intended 0/1/2 branching and invites future mis-edits. Replace with one classifier call and explicit exit-code branching.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: architecture: scripts/lib-vote-tally.sh:36-75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Vote-tally security routing expanded beyond plan constraint and file list. Security-tagged OOS detected via focus-area: fields or [security] headings are routed differently than the plan’s unchanged-security-branch assumption. Amend plan for the broader contract or reduce changes to the minimum needed for #3550 header normalization.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/lib-vote-tally.sh:56-60
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan-scoped SIMPLE fix expanded into broad is_security_block contract changes across vote-tally, SECURITY.md, voting-protocol, oos-serialize, python/oos.py, and awk. Increases change surface and drift risk beyond the header-normalization / emit-tally bug; harder to reason about what #3550 alone required. Narrow to #3550-minimum security changes or extract one shared security-routing module consumed by all four surfaces.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: correctness: skills/review/scripts/tally-code-votes.sh:593-609
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT now excludes security-held accepted OOS. Downstream tooling that still treats OOS_ACCEPTED_COUNT as all accepted OOS may mis-handle security-only review rounds. Document the new meaning everywhere or split public vs security-held counters.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: correctness: skills/review/scripts/emit-tally.sh:161-167
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Preserve guard stricter than plan pseudocode (requires sink count match). Tally/env desync exits non-zero instead of blindly preserving per the plan’s if oos_accepted_count > 0 branch. Update plan to match implemented fail-closed/rebuild semantics or simplify to the planned guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: correctness: python/oos.py:32-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Python legacy-header regex broader than plan literal (.* vs \\s* before tag). Trailing [OUT_OF_SCOPE] headers count in Python/awk but not under the plan’s immediate-post-colon spec. Unify and document one header-tag placement rule across plan, awk, and Python.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/review/scripts/tally-code-votes.sh:122-123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NORMALIZE_OOS_HELPER uses SCRIPT_DIR-relative path while OOS_COUNT_HELPER uses PLUGIN_ROOT. Inconsistent helper resolution style in the same initialization block. Resolve both helpers from PLUGIN_ROOT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

