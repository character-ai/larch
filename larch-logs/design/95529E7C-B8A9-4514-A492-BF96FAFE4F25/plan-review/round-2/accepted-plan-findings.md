### FINDING_1: Publish-gate structural check ID mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan inconsistently identifies the new publish-gate structural check as `(25)` in Failure modes while Files/Testing reserve `(25)` for `design_reentry_marker_write` ordering and assign the publish-gate grep to `(27)`. This could lead implementers to modify the wrong assertion or omit the new gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Change plan.txt Failure modes line 113 to reference (27) consistently with lines 48 and 64; keep (25) reserved for design_reentry_marker_write ordering only
  - From Cursor-Edge: Correct plan.txt Failure modes line 113 to reference assertion (27) consistently with the Files section and scripts/test-design-structure.md note
  - From Cursor-Innovation: Align Failure modes mitigation text with `(27)` everywhere (match Files § test-design-structure and test-design-structure.md)


### FINDING_2: Pause-save publish path can trust PUBLISH_OK despite nonzero publish exit
- **Reviewer(s)**: Cursor-dyn-publish-state-machine
- **Severity**: important
- **Concern**: The plan omits parity for the pause publish path: `design-pause-save.sh` can still reach `PAUSE_OK=true` and write a resume marker when `design-log-publish.sh` exits nonzero but emits `PUBLISH_OK=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-publish-state-machine: Add a surgical pause-save bullet: any non-zero publish_rc forces publish-failed (before trusting PUBLISH_OK=true), mirroring the proposed design-publish.sh and Step 0b clarify rules; add a small test-design-pause-resume.sh or design-pause-save harness case if one exists


### FINDING_4: design-log-publish header contract not updated for malformed --repo
- **Reviewer(s)**: Codex-dyn-publish-state-machine
- **Severity**: latent
- **Concern**: The plan changes malformed `--repo` handling to exit 1 without a `PUBLISH_OK` envelope but leaves the script header contract saying pre-validation failures exit 0 for stdout parsing, creating contradictory guidance for direct callers and maintainers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-state-machine: Update the header comment alongside validate_repo to carve out malformed --repo as a structural argv failure: exit 1, no PUBLISH_OK success envelope, before gh/network work.

