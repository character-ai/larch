### FINDING_1: Scoped ok-checks can match reason text
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The scoped suppression check can search the full suppression line instead of only the comma-delimited `ok-checks=` value, allowing enum tokens mentioned later in the reason text to suppress checks that were not actually listed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one harness case: anchor line `# lint-foreground-markers: ok-checks=monitor_rc_capture reason mentions monitor_rc_init` (or `monitor_rc_initializer`) and assert all three monitor_rc diagnostics still fire; document it in `scripts/test-lint-foreground-markers.md`
  - From Cursor-Edge: Parse only the list segment after `ok-checks=` up to the first whitespace (Bash 3.2 sed capture), then test each TOKEN against that substring with `,`/end boundaries; add a harness case with a second token only in the reason
  - From Cursor-Innovation: Match tokens only inside the ok-checks value (sed/parameter expansion up to the first whitespace after =) or require the list to end at whitespace before reason; add a harness line whose reason mentions a different token and assert the other checks still fire

### FINDING_2: Multi-token scoped suppression misses later tokens
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The scoped-suppression regex only allows zero or one comma-delimited token before the requested token, so valid lists with two or more prior entries can fail to suppress later listed checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Use a repeated token-prefix pattern such as ok-checks=([^[:space:],]+,)*TOKEN([,[:space:]]|$), and add the all-three-token case to the planned multi-token fixture

### FINDING_3: Heredoc flags remain recomputed per anchor
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Heredoc flags are planned inside per-anchor validation instead of once per fence or shell file, so large inputs with many Family B anchors can still degrade toward quadratic work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Build FENCE_HEREDOC_FLAGS once after FG_FENCE_LINES is populated and once after shell-file lines are loaded, then let fence_has_family_b_pid_capture_and_wait only read the prepared flags

### FINDING_4: Scoped suppression accepts missing reasons
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: The scoped suppression regex can accept an `ok-checks=` comment that ends immediately after the token, allowing suppression without the documented non-empty reason required by the existing bare ok form.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Require whitespace plus non-empty reason after the ok-checks list, for example match the list first and require [[:space:]]+[^[:space:]#] before returning true

### FINDING_5: Token-boundary adversarial fixtures are incomplete
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Cursor-dyn-regex-left-boundary, Codex-dyn-regex-left-boundary
- **Severity**: important
- **Concern**: The planned scoped-suppression tests do not fully cover valid-token substring boundary failures, including right-boundary cases like suffixes and left-boundary cases like prefixed tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add one scoped-suppression fixture in the monitor_rc fixture block using a valid-token substring such as ok-checks=monitor_rc_initializer and assert the relevant monitor_rc diagnostic still fires.
  - From Codex-Requirements: Add one scoped-suppression fixture in the monitor_rc fixture block using a valid-token substring such as ok-checks=monitor_rc_initializer and assert the relevant monitor_rc diagnostic still fires.
  - From Cursor-dyn-regex-left-boundary: Keep the line 22 ok-checks-anchored pattern, do not add a separate leading anchor, and make the adversarial fixture explicit with ok-checks=foomonitor_rc_init <reason> for token monitor_rc_init while asserting all monitor_rc diagnostics still fire.
  - From Codex-dyn-regex-left-boundary: Keep the line 22 ok-checks-anchored pattern, do not add a separate leading anchor, and make the adversarial fixture explicit with ok-checks=foomonitor_rc_init <reason> for token monitor_rc_init while asserting all monitor_rc diagnostics still fire.
