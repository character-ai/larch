### FINDING_1: monitor_rc conditional scan rejects canonical two-branch waits
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-regex-vs-evidence, Codex-dyn-regex-vs-evidence
- **Severity**: important
- **Concern**: The planned check for conditional branching on `monitor_rc` scans only after the matched `wait`, but the canonical Family B pattern branches on `monitor_rc` before the line-initial waits inside the `then`/`else` branches. This would falsely reject documented and live canonical fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Scan monitor_idx+1 through end-of-fence (heredoc-aware) for if|elif|case referencing monitor_rc before the first post-monitor wait, or accept the opening if line when wait lines are nested inside it
  - From Codex-Arch: Search for a monitor_rc conditional in the post-monitor region before or enclosing the matching wait, and keep fixture updates in the canonical multi-line shape where wait remains detectable
  - From Cursor-Edge, Codex-Edge: Search for the monitor_rc conditional between monitor_idx + 1 and the matching wait line, or otherwise detect a conditional that encloses the matching wait; keep fixtures using standalone wait lines that extract_wait_ident already recognizes
  - From Codex-Innovation: Change check (3) to detect an if/case on monitor_rc after the monitor and before or enclosing the matched wait line, and keep wait on its own line in fixtures so the existing wait identifier check still applies.
  - From Cursor-Pragmatic, Codex-Pragmatic: Keep the minimum-change contract by leaving wait on its own line in fixtures and changing check 3 to scan the post-monitor region up to and including the matched wait line for an if/case/elif conditional referencing monitor_rc; do not require a conditional to start after wait_idx unless extract_wait_ident is also intentionally broadened.
  - From Cursor-Requirements: Align check (3) with issue wording (conditional later in same fence): scan from monitor logical-end through end-of-fence for if/elif/case/while/until referencing bareword monitor_rc; do not require the branch to appear after wait
  - From Codex-Requirements: Search for the monitor_rc conditional after the monitor logical end and before or around the matching wait, not only from wait_idx + 1
  - From Cursor-dyn-regex-vs-evidence, Codex-dyn-regex-vs-evidence: Start the branch scan at monitor_idx+1, not wait_idx+1, and accept a conditional referencing monitor_rc before or around the matched wait; keep the check token-based to preserve SIMPLE scope

### FINDING_2: inline if-then-wait fixtures bypass wait detection
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The proposed one-line fixture shape puts `wait` after `then` on the same line, but `extract_wait_ident` only detects lines whose first command is `wait`. Those fixtures would report a missing wait before exercising the new `monitor_rc` checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Search for the monitor_rc conditional between monitor_idx + 1 and the matching wait line, or otherwise detect a conditional that encloses the matching wait; keep fixtures using standalone wait lines that extract_wait_ident already recognizes
  - From Codex-Innovation: Change check (3) to detect an if/case on monitor_rc after the monitor and before or enclosing the matched wait line, and keep wait on its own line in fixtures so the existing wait identifier check still applies.
  - From Cursor-Pragmatic, Codex-Pragmatic: Keep the minimum-change contract by leaving wait on its own line in fixtures and changing check 3 to scan the post-monitor region up to and including the matched wait line for an if/case/elif conditional referencing monitor_rc; do not require a conditional to start after wait_idx unless extract_wait_ident is also intentionally broadened.
  - From Cursor-Requirements: Use multiline canonical shape (monitor_rc=0, monitor || monitor_rc=$?, if on monitor_rc, then line-initial wait in each branch) matching case 45 and BASH_AUTHORING.md §4

### FINDING_3: existing shell-file fixture case 46 is omitted from the update sweep
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-fixture-enumeration, Codex-dyn-fixture-enumeration
- **Severity**: important
- **Concern**: The test update plan focuses on Markdown fence anchors, but existing shell-file clean fixture case 46 also exercises Family B wait detection with `ship-pr.sh`, `breadcrumb-monitor.sh`, and bare `wait`. Once shell-file scanning inherits the new checks, that fixture will fail unless it is updated too.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In §“UPDATED: scripts/test-lint-foreground-markers.sh” step 1, broaden the checklist to every `assert_case_clean` that exercises `fence_has_family_b_pid_capture_and_wait` (Markdown fences and shell files), and explicitly list case 46; keep the failure-mode-2 grep checklist keyed on top-level writer basenames, not `collect-agent-results.sh` alone
  - From Cursor-dyn-fixture-enumeration, Codex-dyn-fixture-enumeration: Update the existing case 46 shell-file fixture to the canonical monitor_rc two-branch shape, or make the planned shell-file positive fixture replace this case rather than only adding a new one

### FINDING_4: heredoc false-positive coverage is missing for monitor_rc initialization
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan requires the backward initialization walk to reuse heredoc skipping, but the required tests do not include a fixture where `monitor_rc=0` appears only inside a heredoc above the monitor. Without that coverage, asymmetric heredoc handling could ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one negative fixture (called out under Failure modes) with `monitor_rc=0` only in a heredoc body above `breadcrumb-monitor.sh` and assert check (1) still reports `missing monitor_rc= initialization` (and that checks 2–3 do not false-pass)
