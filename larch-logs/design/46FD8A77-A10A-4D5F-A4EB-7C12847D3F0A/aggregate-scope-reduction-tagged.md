### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh:activation_is_live
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback re-arms leaked stale hook registrations when another skill creates a fresh sentinel. Scenario: Plan keeps tokenless invocation activating on any fresh sentinel. A harness-leaked registration still calls deny-edit-write.sh without a token (pre-upgrade wiring). /bug Step 2 then writes bug-$PPID; the leaked tokenless hook treats that as live and denies non-/tmp Write/Edit/NotebookEdit again — matching the reported /design Gate B failure after an intervening /bug run even though /research never executed. Token scoping on new frontmatter does not apply to the stale registration.
- **Proposed resolution**: Drop tokenless any-sentinel fallback: when $1 is empty, activation_is_live returns false (fail-open). Both consumers already pass research|bug via frontmatter; structural pins enforce that. Add a harness case: tokenless hook + fresh bug-* sentinel + repo-path stdin must allow (empty stdout).

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh
- **Concern**: [SCOPE-REDUCTION] Tokenless hook invocation activates on any fresh sentinel, not only the consumer token. Scenario: The plan keeps a tokenless fallback that treats any fresh file under deny-edit-write-active as live. A stale leaked registration wired as bare deny-edit-write.sh (no argv) is exactly the reported failure mode: /bug Step 2 writes bug-$PPID, the leaked hook sees a fresh sentinel, and unrelated /design Write/Edit calls keep denying until TTL even though /research never ran. Token scoping in new frontmatter does not help sessions still carrying old tokenless registrations.
- **Proposed resolution**: Remove the tokenless branch: when $1 is empty, treat activation as inactive (exit 0 allow) instead of matching any sentinel. Keep token-scoped checks only for explicit research and bug argv.

### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17,41-43,61-64,179
- **Concern**: [SCOPE-REDUCTION] Prior accepted FINDING_5 fix is incomplete because the tokenless fallback keeps an any-fresh-sentinel activation path. Scenario: The plan says a tokenless hook activates on any fresh sentinel. A leaked stale hook registered without the new research argument, or a future frontmatter regression, can be re-armed by a bug-* sentinel and deny unrelated Edit/Write calls, recreating the cross-skill leak this fix is meant to remove
- **Proposed resolution**: Remove tokenless fallback. Require a recognized token for activation, and treat missing or unknown tokens as inactive fail-open. Update tests and docs to drop tokenless activation.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-18,42,63,179
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback keeps the cross-skill re-arm path that the token gate is meant to remove. Scenario: A leaked or stale no-arg /research hook can see a fresh bug-* sentinel, activate via any-fresh-sentinel matching, and deny unrelated /design writes until cleanup or TTL
- **Proposed resolution**: Make missing or empty token fail open instead of scanning all sentinels; update the tests and docs to remove the tokenless any-sentinel fallback and rely on structural pins to catch missing token wiring
