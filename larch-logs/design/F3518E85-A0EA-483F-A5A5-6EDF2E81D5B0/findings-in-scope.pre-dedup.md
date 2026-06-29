### FINDING_1:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:83-119
- **Concern**: Plan omits the middle always-loaded prose sections.. Scenario: The rewrite can leave the uncompressed Progress Reporting, Extracted Script Registry, Bash block prelude, and Verbosity Control blocks intact, so the PR only partially delivers the requested whole-file compression.
- **Proposed resolution**: Add those sections to the prose-compression pass and shorten them in place while preserving their anchors, tokens, and exact required strings.



### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-Implement Contract Guardian Phase2
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:238-247,537-543,566-573,647-663
- **Concern**: Plan "Preserve exactly" and "Target areas" do not explicitly freeze the launcher-adjacent anchor prose that sits outside Bash fences.. Scenario: scripts/test-implement-structure.sh:265-272 requires the nearby "Foreground required", "Immediate-background required", timeout, "<task-notification>", and "Continue after child returns." sentinels around Step 0, Step 5, Step 6, and Step 8. If prose compression trims or moves them, the unchanged harness fails and the orchestration loses the foreground/background gating the contract depends on.
- **Proposed resolution**: Add an explicit preserve list for these non-fence anchors, or state that all wrapper-adjacent wait and gating lines are byte-stable unless the harness is being updated too.



