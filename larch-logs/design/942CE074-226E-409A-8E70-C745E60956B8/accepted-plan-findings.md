### FINDING_1: Manual probe orders bare value flag incorrectly
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Manual probe expects a bare `--partition-requested` before `--output` to report “requires a value,” but the proposed parser still treats `--output` as the flag value. The probe would fail through an unknown/enum-style parse path rather than the stated stderr substring, because only a last-position bare flag maps to an empty value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update the manual probe to put --output before the bare boolean flag, matching the planned tests and minimum-change parity with --manual-gate-b; only expand parser scope if flag-looking tokens must be treated as missing values


### FINDING_2: Caller audit missing for flag missing-value contract change
- **Reviewer(s)**: Cursor-dyn-call-sites, Codex-dyn-call-sites
- **Severity**: important
- **Concern**: Plan does not include the required caller audit for the rc/message contract change on `--partition-requested` and `--brainstorm-requested` missing or empty values. Active call sites include the runtime SKILL invocation, write-run-params harness, Step 0b recovery harness, flag-signature fixture, and structure grep, but the plan only updates the writer, one harness, and docs. Reviewers cannot verify whether any caller or test relied on the previous Bash nounset `rc=1` behavior or stderr text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-call-sites, Codex-dyn-call-sites: Add a short caller-audit bullet to the plan listing each existing write-run-params.sh invocation and stating the observed contract: SKILL.md treats any nonzero as drift and does not inspect rc/text; test-step0b-router-flag-recovery.sh uses only valid values; test-lint-skill-md-flag-signature.sh and test-design-structure.sh only inspect prompt text/signature; test-write-run-params.sh will own the new rc=2/message assertions.

