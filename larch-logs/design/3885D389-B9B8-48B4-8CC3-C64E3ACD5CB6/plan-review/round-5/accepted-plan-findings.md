### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1159-1174
- **Concern**: Proposed routing envelope omits REPO but Step 8+ still passes --repo "$REPO" from orchestrator shell state without a read-session-env-key rehydration in that block. Scenario: After the narrowed parse, $REPO is empty at first ship-pr.sh / gh-run-logs.sh invocation; cold init may fall back to resolve-repo.sh and diverge from bootstrap-resolved REPO (fork/upstream edge cases)
- **Proposed resolution**: Add REPO to the wrapper envelope + shared export list, or add an explicit REPO read from $IMPLEMENT_TMPDIR/session-env.sh in the Step 8+ Invoke block before --repo


