### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: finalize-state writes are repeated across bail paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Repeated `write_finalize_state` blocks in `ship.py` make it easy to miss fields like `STALL_STEP` on one branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Availability probes ignore RunContext session fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `codex_present`/`cursor_present` are re-probed from env instead of loaded session context, so resume routing can diverge from Step 0 availability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: CI wiring for merge-parity harness is unclear
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan mentioned CI wiring for merge parity, but the diff appears to rely on Makefile/shard changes without clear `ci.yaml` traceability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: JSON stdout redaction is incomplete
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: stdout JSON redaction skips `pr_url` and only partially handles free-text fields, allowing tokenized/internal URLs or sensitive strings to reach orchestrator output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: 8-pre-ship probe text is bash-only
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The 8-pre-ship SKILL probe still assumes bash state-file prerequisites, which can confuse or misroute Python-path operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: run_ship is a monolithic orchestrator
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/ship.py::run_ship` contains a large nested orchestration flow with repeated state writes, making phase changes and tests brittle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: Python CI-fix log refresh still depends on ship-pr-state.sh
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: important
- **Concern**: Autonomous CI-fix steps read `FAILED_RUN_ID`/`REPO` and refresh logs through `ship-pr-state.sh`, which is absent on the Python path, so post-fix log batches can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: RunContext has duplicate fields for the same concepts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `RunContext` duplicates branch/issue/fork fields with inconsistent fallbacks, so partial updates can make call sites diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_44

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_44: Post-merge sentinel writer allows newline injection
- **Reviewer(s)**: dyn-teardown-state-output.txt
- **Severity**: latent
- **Concern**: `run_postmerge_phase` writes `MERGE_RESULT={ctx.merge_result}` without newline/carriage-return validation, unlike finalize-state serialization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

