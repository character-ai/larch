### [Plan Review] FINDING_2

### FINDING_2: Structure-test harness still pins removed Step 0b SKILL.md anchors
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still pins Step 0b `write-run-params` / jq merge prose in `SKILL.md` after extraction. The plan may re-point FINDING_13/#3008/refusal greps but not Check 21 (#2930) anchors at lines 602–612 that require `--manual-gate-b` and the canonical jq filter in `$SKILL_MD`. After Step 0b inline bash removal, `make lint` structure tests can fail despite green driver logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend scripts/test-design-structure.sh updates to re-point lines 602-612 (and any related 617-621 greps) at design-init-runparams.sh, or keep one SKILL.md forwarder fence that satisfies the pins


### [Plan Review] FINDING_3

### FINDING_3: `already-planned` route uses weak plan-marker detection
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The proposed `already-planned` verdict only checks that the issue body contains a `larch:plan` block. `plan-block-read.sh` treats partial or duplicate markers as malformed, not present; a naive start-marker grep can mis-route or diverge from `/implement` Preflight semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin detection in design-route.md to the plan-block-read.sh MARK_START/MARK_END count rules on --issue-body-file (present only when exactly one well-formed pair)


