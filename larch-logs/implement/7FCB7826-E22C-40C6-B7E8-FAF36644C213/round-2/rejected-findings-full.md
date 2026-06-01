### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicated rename parse/WARN block in phase drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` (lines 287–303) duplicates the tracking-issue-write rename parse/WARN logic already present in `design-init-runparams.sh`. Future changes to the rename stdout contract may be fixed in one driver and missed in the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared helper in `lib-phase-driver.sh` and use it from both drivers.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Verbatim `WARN=` replay from result env can steer orchestrator
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Step 5c replays parsed `WARN` bodies verbatim to top chat. Tampered `WARN=` lines in `.design-publish-result.env` could inject orchestrator-steering prose into the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Bound/sanitize WARN replay or allowlist known driver WARN templates only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Non-zero publish rc with `PUBLISH_OK=true` still allows rename
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If `design-log-publish.sh` returns non-zero but stdout still has `PUBLISH_OK=true`, rename may proceed and the tracking title becomes `[DESIGNED]` while log publish failed or is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Force `PUBLISH_OK=false` when `_publish_rc≠0` unless `rc=0`; add harness case.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Exit-code contract docs omit result-env failure on exit 1
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `design-publish.md` exit-code table does not document result-env write failure sharing exit `1` with plan-block-write failure, misleading operator/runbook expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align contract table with implementation or split exit codes.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Local `parse_kv_from_output` duplicates phase-driver KV pattern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-publish.sh` (lines 35–48) implements local `parse_kv_from_output` that mirrors an emerging phase-driver KV parsing pattern; a third driver may copy the same loop again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move parsing to `lib-phase-driver.sh` with allowlisted keys when a third caller appears.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Missing harness cases for marker-fail-continue and RENAMED= omit WARN
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Offline harness does not cover marker non-blocking failure, omitted `RENAMED=` warn paths, or exercise `RENAMED_OMIT_LINE` despite stub support. Regressions in append-tool-failure, `WARN=` for those branches, or rename helper contract dropping `RENAMED=` would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add marker-fail-continue and RENAMED-omit stub scenarios.
  - From cursor-specialist-testing-output.txt: Add case with `RENAMED_OMIT_LINE=true` asserting `WARN=` in `.design-publish-result.env`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Unexpected driver exit abort prose not structurally pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Driver exit codes outside `{0,1}` (`_publish_rc` not 0 or 1) and the fatal abort banner are not pinned in `SKILL.md` / structure tests. Orchestrator prose for fatal driver failures could regress while exit 2/1 pins still pass; operators might parse result env after a crash exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep for `design-publish.sh failed (exit ${_publish_rc}); aborting /design` mirroring design-route/init pins.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: PUBLISH_OK=false / unexpected-publish cases do not assert execution-issues.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness cases that skip rename on `PUBLISH_OK=false` or unexpected publish do not assert warnings land in `execution-issues.md`; `append-tool-failure` regressions could silence operator-visible publish failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `execution-issues.md` contains design Step 5c after those harness cases.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Unvalidated `FINAL_SUMMARY_PATH` read in Step 5c orchestrator block
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Parsed `FINAL_SUMMARY_PATH` from `.design-publish-result.env` is used for verbatim file read without tmpdir-prefix or symlink checks. A same-UID writer could point the result env at a sensitive readable file; the orchestrator would emit its contents to top chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Constrain reads to a non-symlink path under `$DESIGN_TMPDIR` or ignore parsed `FINAL_SUMMARY_PATH` for the emit step.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

