### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Python ship-pr state remains raw while finalize state is quoted
- **Reviewer(s)**: dyn-python-shell-parity-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` still emits raw `KEY=value` lines, widening the contract split after finalize-state hardening. Special characters in fields like `PR_TITLE`, `PR_URL`, or `BRANCH_NAME` remain unsafe for checkpoint consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-shell-parity-output.txt: Reuse the same `_shell_single_quote` helper for `_write_ship_state` emission and add matching unquote support wherever `ship-pr-state.sh` values are parsed (at minimum `scripts/read-session-env-key.sh` or a shared normalizer), with parity tests mirroring `scripts/test-implement-finalize.sh` quoted-boolean coverage.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Finalize-state quoting helpers are duplicated across scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `restore-finalize-state.sh` duplicates unquote/truthy/quote logic from `implement-finalize.sh`, creating a risk that future quote escaping or boolean handling fixes land in only one path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Dynamic Codex allowlist assertions are duplicated across harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The same dynamic Codex allowlist expectations appear in both unit and write-round integration tests, so future sidecar additions require duplicate manual updates and one harness can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Retry-shaped dynamic Codex outputs are documented but not explicitly matched
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Docs mention retry dynamic Codex outputs, but matcher retention for retry-shaped artifacts depends on broad `*-output*` allows. Future deny changes could silently drop them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Missing negative fixture for phased dynamic vote-prompt basename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The write-round tests do not include `dyn-*-codex-output-phase*-vote-prompt.txt`, so a regression in phased dynamic vote-prompt exclusion could slip past that harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

