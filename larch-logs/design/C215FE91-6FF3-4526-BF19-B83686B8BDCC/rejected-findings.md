### [Plan Review] FINDING_1

### FINDING_1: Scoped ok-checks can match reason text
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The scoped suppression check can search the full suppression line instead of only the comma-delimited `ok-checks=` value, allowing enum tokens mentioned later in the reason text to suppress checks that were not actually listed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one harness case: anchor line `# lint-foreground-markers: ok-checks=monitor_rc_capture reason mentions monitor_rc_init` (or `monitor_rc_initializer`) and assert all three monitor_rc diagnostics still fire; document it in `scripts/test-lint-foreground-markers.md`
  - From Cursor-Edge: Parse only the list segment after `ok-checks=` up to the first whitespace (Bash 3.2 sed capture), then test each TOKEN against that substring with `,`/end boundaries; add a harness case with a second token only in the reason
  - From Cursor-Innovation: Match tokens only inside the ok-checks value (sed/parameter expansion up to the first whitespace after =) or require the list to end at whitespace before reason; add a harness line whose reason mentions a different token and assert the other checks still fire


### [Plan Review] FINDING_2

### FINDING_2: Multi-token scoped suppression misses later tokens
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The scoped-suppression regex only allows zero or one comma-delimited token before the requested token, so valid lists with two or more prior entries can fail to suppress later listed checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use a repeated token-prefix pattern such as ok-checks=([^[:space:],]+,)*TOKEN([,[:space:]]|$), and add the all-three-token case to the planned multi-token fixture


