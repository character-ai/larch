### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Codex argv forwarding tests are weaker outside negotiation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The lint-fix and review-and-fix harnesses do not log and assert forwarded `--json`, `--output-last-message`, and `--` argv the way the negotiation test does, so dropped production flags could slip through if stubs only enforce flags internally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Empty or unparsable Codex events skip token-ledger row
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-external-launcher-common.sh` skips token-ledger recording when `events.jsonl` is empty or unparsable, even on failed Codex runs. Operators may mistake a missing `codex_*` ledger row for missing telemetry rather than an early crash or parse failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_18: Pre-run cleanup omits legacy Codex log files
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh` and `skills/review-and-fix/scripts/review-and-fix.sh` do not remove legacy `codex.log` / `coder-codex.log` files before dispatch, so repeated runs could briefly expose stale final-message output from `--output-last-message`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Triplicated Codex JSONL telemetry dispatch logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/lint-fix-loop.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`, and `scripts/run-negotiation-round.sh` duplicate the Codex JSONL telemetry dispatch block, so future argv, cleanup, or exit-code changes can drift across sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated flag validation in get-issue-state
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` duplicates `--issue` and `--repo` value guard logic with inconsistent `emit_kv` formatting, creating drift risk for future error-envelope changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: round_artifact_included test probes function body indirectly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-larch-log.sh` uses `awk` plus `eval` against a function body to test `round_artifact_included`, which can silently break if the implementation is refactored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Redundant serial lock assignment in review-and-fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` assigns `_SERIAL_LOCK=""` redundantly before acquiring the Codex lock, adding minor noise to the dispatch flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

