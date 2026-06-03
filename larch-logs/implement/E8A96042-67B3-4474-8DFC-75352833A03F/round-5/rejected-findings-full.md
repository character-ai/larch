### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `mv` failure on `bootstrap-routing.env` aborts wrapper under `set -e`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/implement-bootstrap-invoke.sh` (~201–205), if bootstrap succeeds but `mv` to a read-only `bootstrap-routing.env` fails, `set -e` aborts the wrapper before emitting the stdout envelope. Orchestrator sees non-zero rc and no routing keys despite valid bootstrap stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On mv failure emit stdout envelope and warn (mirror symlink path) or exit 2 with operator message


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Plan file inventory omits `parse-bootstrap-routing-envelope` artifacts
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Implementation plan called for inline parse in SKILL.md; delivery uses `scripts/parse-bootstrap-routing-envelope.sh` (and contract sibling) not listed in the plan “Files to modify/create” inventory. Follow-ups scoped only to the plan list can miss parse contract and `--preserve-coder` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add parse-bootstrap-routing-envelope.{sh,md} to the plan file list and to implement-bootstrap.md edit-in-sync.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Mixed `_ib_*` vs `_inv_*` names in bootstrap invoke wrapper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: New `scripts/implement-bootstrap-invoke.sh` wrapper (lines 42–68) uses `_ib_*` internal names while SKILL and parse helpers use `_inv_*`, adding trace friction in Step 0.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Routing key allowlist duplicated in multiple places
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Canonical routing key list is duplicated (e.g. `scripts/test-implement-structure.sh` around line 555 and invoke/parse literals). Harness `expected_routing_keys` can drift even when invoke and parse still match.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Overly broad `grep '*)'` pin in structure harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh` (lines 588–589) pins default exit-2 handling with `grep '*)'`, which can false-positive on unrelated `case` arms containing the same token.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Default `*)` exit-2 handler not exercised in invoke harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-bootstrap-invoke.sh` pins structural requirements for the wrapper default handler (e.g. ~335–343) but has no case with an unknown `STEP_FAILED`. Operator-message regressions on the generic exit-2 branch may not fail CI (related to structure harness gap at FINDING_4).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add run_exit2_case with unknown STUB_STEP_FAILED and assert bootstrap failed at step= on stderr
  - From cursor-specialist-plan-fidelity-output.txt: Add one exit-2 test with an unlisted STEP_FAILED and assert stderr message plus empty stdout.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Redaction failure operator strings untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/test-implement-bootstrap-invoke.sh` (~345–371) tests `copy-plan` / `gh-issue-view` redaction success but not `redact-secrets.sh` failure fallbacks; stderr operator text for redaction failure is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub redact-secrets.sh to fail and assert stderr redaction failed operator text without leaking raw secrets


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Success path without `IMPLEMENT_TMPDIR` in bootstrap stdout untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap-invoke.sh` (~423–427) exits 1 when bootstrap omits `IMPLEMENT_TMPDIR`, but the invoke harness has no regression stub for that success shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub success output without IMPLEMENT_TMPDIR line and assert exit 1


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

