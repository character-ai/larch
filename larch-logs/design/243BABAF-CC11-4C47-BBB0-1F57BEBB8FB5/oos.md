### OOS_1:
- **Description**: phase_plan_materialize and phase_coder_select stubs still overwrite IMPLEMENT_BAIL_REASON after phase_tracking when UP_TO_PHASE is plan coder or all. Scenario: Operators testing combined phases see not-yet-implemented-phase-3 tail unrelated to tracking work
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/implement-bootstrap.sh:286-294
- **Phase**: design


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2:
- **Description**: Top header says --sentinel emits ISSUE_NUMBER ADOPTED only. Scenario: Auditors or future docs may wrongly assume RUN_ID absent from stdout despite emit_kv RUN_ID and tests
- **Reviewer**: Cursor-dyn-sentinel-read-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/tracking-issue-read.sh:21-22 vs scripts/tracking-issue-read.sh:268-278
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_3:
- **Description**: Fork upstream get-issue-context failures currently abort Step 0; plan carve-out ignores failures (|| true). Scenario: Operators lose explicit fail-closed signal on upstream context fetch flakes; any secret-bearing stderr only lands in a log file
- **Reviewer**: Cursor-dyn-kv-emit-table-sync
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/implement/SKILL.md:646-658
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_4:
- **Description**: Top-of-file sentinel contract omits RUN_ID even though implementation emits it. Scenario: Implementers or reviewers mis-read the stdout key set versus scripts/tracking-issue-read.sh:276-278
- **Reviewer**: Cursor-dyn-stub-output-fidelity
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/tracking-issue-read.sh:21-23
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

