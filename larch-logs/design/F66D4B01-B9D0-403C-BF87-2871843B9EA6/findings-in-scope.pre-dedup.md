### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/sessionstart-health.sh:26-28;scripts/deny-edit-write.sh:41-59;skills/implement/scripts/hook-stop-fail-close.sh:11-84
- **Concern**: Per-hook inline FD-3 contract is fully specified only for deny-edit-write.sh. Scenario: SessionStart uses conditional larch_quiet_init when dirname/mkdir exist so emit() goes to FD 3 under quiet redirect but to stdout in stripped-PATH harness runs; Stop hook always quiet-inits then emit() block JSON; deleting lib-quiet without equivalent per-hook routing breaks SessionStart advisories and/or test-sessionstart-health stdout cases and Stop block output
- **Proposed resolution**: Extend the blocking hook FD-3 section to cover sessionstart-health.sh (conditional redirect plus stdout fallback when init skipped) and skills/implement/scripts/hook-stop-fail-close.sh (inline exec 3>&1 plus hook_emit for block JSON); keep make test-sessionstart-health and hooks.json Stop behavior in Testing strategy



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:24-29
- **Concern**: Terminal-lib cut list names only hooks/pre-commit/sleep-seconds but live orchestration shells still source lib-quiet/lib-phantom-probe/lib-execution-issues. Scenario: At E3 time skills/implement/scripts/step-2-post-dispatch.sh skills/implement/scripts/flush-execution-issues.sh skills/implement/scripts/generate-code-flow-diagram.sh skills/design/scripts/design-step3-review.sh and others still source terminal libs; hook-only refactors then lib deletion break /implement Step 2 and related paths
- **Proposed resolution**: Extend preflight/testing with an explicit enumerated runtime source scan (or add firm ### UPDATED entries for every remaining non-residual .sh) and treat any hit as block-E3 until cut; do not delete terminal libs on hook-only work



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/scripts/hook-stop-fail-close.sh:80-84
- **Concern**: FD-3 hook contract emission unspecified when lib-quiet is removed. Scenario: Plan only mandates inline `exec 3>&1` + `hook_emit()` for `deny-edit-write.sh`, but `hook-stop-fail-close.sh` calls `emit()` for Stop-hook `decision:block` JSON after `larch_quiet_init`. Removing `lib-quiet.sh` without an equivalent leaves `emit` undefined or writes block JSON to the quiet log instead of the hook contract stream, breaking post-/review halt protection
- **Proposed resolution**: Extend the `hook-stop-fail-close.sh` ### UPDATED section with the same minimal per-hook FD-3 inline contract as `deny-edit-write.sh` (one-time stdout dup to FD 3, local `hook_emit`, route every `emit` call through it); document in SECURITY.md alongside deny-edit-write



### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:99-114
- **Concern**: lint-awk target set conflicts with preserved .awk coverage. Scenario: The plan narrows lint-awk-multibyte-regex discovery to residual Bash manifest paths, but the manifest only lists .sh and .inc.bash while the test plan says to preserve standalone .awk coverage. Implemented literally, standalone .awk files stop being scanned or the preserved harness fails.
- **Proposed resolution**: Revise the linter plan to scan residual manifest .sh/.inc.bash plus existing tracked .awk targets, or explicitly delete/retire all standalone .awk files and update the test/doc contract accordingly.



