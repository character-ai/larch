### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:76-77 vs plan.txt:41-49
- **Concern**: Failure modes promise an adversarial ok-checks substring fixture but the test file update list omits it. Scenario: A mistuned `line_has_scoped_suppression_check` regex could treat `monitor_rc_init` inside the reason (or a suffix like `monitor_rc_initializer`) as a list token; the large-fence case would not catch that
- **Proposed resolution**: Add one harness case: anchor line `# lint-foreground-markers: ok-checks=monitor_rc_capture reason mentions monitor_rc_init` (or `monitor_rc_initializer`) and assert all three monitor_rc diagnostics still fire; document it in `scripts/test-lint-foreground-markers.md`

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:484-578
- **Concern**: Scoped ok-checks grep can match enum tokens in the reason text, not only in the comma list. Scenario: The planned pattern runs over the full suppression line, so e.g. `# lint-foreground-markers: ok-checks=monitor_rc_init note monitor_rc_capture` can satisfy `monitor_rc_capture` even though it is not listed, silencing that check while others still fire
- **Proposed resolution**: Parse only the list segment after `ok-checks=` up to the first whitespace (Bash 3.2 sed capture), then test each TOKEN against that substring with `,`/end boundaries; add a harness case with a second token only in the reason

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22
- **Concern**: The scoped-suppression regex only allows zero or one comma-delimited token before the requested token. Scenario: A documented valid list such as ok-checks=monitor_rc_init,monitor_rc_capture,monitor_rc_branch will not suppress monitor_rc_branch, because ([^[:space:]]*,)? can consume only one prior token
- **Proposed resolution**: Use a repeated token-prefix pattern such as ok-checks=([^[:space:],]+,)*TOKEN([,[:space:]]|$), and add the all-three-token case to the planned multi-token fixture

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:22-23
- **Concern**: Scoped-token grep is planned on the full suppression line. Scenario: Reason text after the list can contain another enum token as a word (e.g. ok-checks=monitor_rc_init … monitor_rc_capture) and satisfy ([,[:space:]]|$) for the wrong token, silencing checks that should still run
- **Proposed resolution**: Match tokens only inside the ok-checks value (sed/parameter expansion up to the first whitespace after =) or require the list to end at whitespace before reason; add a harness line whose reason mentions a different token and assert the other checks still fire

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lint-foreground-markers.sh:780-904
- **Concern**: Heredoc flags are planned inside per-anchor validation, not once per fence. Scenario: A large fence or shell file with many top-level Family B anchors rebuilds heredoc flags for each anchor, so the proposed fix remains O(k*n) and can still become O(n²) when anchors scale with lines
- **Proposed resolution**: Build FENCE_HEREDOC_FLAGS once after FG_FENCE_LINES is populated and once after shell-file lines are loaded, then let fence_has_family_b_pid_capture_and_wait only read the prepared flags

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:291-294
- **Concern**: Scoped suppression regex accepts no-reason comments. Scenario: The proposed boundary allows end-of-line after the token, so # lint-foreground-markers: ok-checks=monitor_rc_capture suppresses without the documented reason, unlike the existing bare ok form
- **Proposed resolution**: Require whitespace plus non-empty reason after the ok-checks list, for example match the list first and require [[:space:]]+[^[:space:]#] before returning true

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-foreground-markers.sh:1322-1695
- **Concern**: Plan states scoped token adjacency must not false-match and says an adversarial fixture enforces it, but the proposed test list only covers unknown tokens and does not cover valid-token substrings.. Scenario: A buggy regex could let ok-checks=monitor_rc_initializer or ok-checks=monitor_rc_init_test suppress monitor_rc_init, while the planned unknown-token fixture still passes because monitor_rc_unknown is not the risky prefix case.
- **Proposed resolution**: Add one scoped-suppression fixture in the monitor_rc fixture block using a valid-token substring such as ok-checks=monitor_rc_initializer and assert the relevant monitor_rc diagnostic still fires.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-regex-left-boundary, Codex-dyn-regex-left-boundary
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:45-49,76; scripts/test-lint-foreground-markers.sh:1008-1112
- **Concern**: The proposed ERE at plan line 22 does not match ok-checks=foomonitor_rc_init or ok-checks=monitor_rc_initializer under LC_ALL=C grep -Eq, so an extra (^|[, ]) left anchor is not needed; however the plan's adversarial fixture language only names a substring-not-token case and line 76's example monitor_rc_init_test exercises the right boundary, not the left boundary.. Scenario: An implementer could add only a monitor_rc_init_test-style fixture and miss a regression where ok-checks=foomonitor_rc_init incorrectly suppresses monitor_rc_init. The alternate regex shown at line 76 also differs from the ok-checks-anchored pattern and could invite a broader whole-line match.
- **Proposed resolution**: Keep the line 22 ok-checks-anchored pattern, do not add a separate leading anchor, and make the adversarial fixture explicit with ok-checks=foomonitor_rc_init <reason> for token monitor_rc_init while asserting all monitor_rc diagnostics still fire.
