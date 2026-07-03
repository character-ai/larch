### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh:activation_is_live
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback re-arms leaked stale hook registrations when another skill creates a fresh sentinel. Scenario: Plan keeps tokenless invocation activating on any fresh sentinel. A harness-leaked registration still calls deny-edit-write.sh without a token (pre-upgrade wiring). /bug Step 2 then writes bug-$PPID; the leaked tokenless hook treats that as live and denies non-/tmp Write/Edit/NotebookEdit again — matching the reported /design Gate B failure after an intervening /bug run even though /research never executed. Token scoping on new frontmatter does not apply to the stale registration.
- **Proposed resolution**: Drop tokenless any-sentinel fallback: when $1 is empty, activation_is_live returns false (fail-open). Both consumers already pass research|bug via frontmatter; structural pins enforce that. Add a harness case: tokenless hook + fresh bug-* sentinel + repo-path stdin must allow (empty stdout).



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/research/SKILL.md:96-102
- **Concern**: Filing-findings abort paths omit activation-sentinel cleanup. Scenario: ## Filing findings as issues aborts on VERIFIED=false (and item 5 on ISSUES_FAILED>=1) without session cleanup-tmpdir or activation-sentinel removal. Those paths can run mid-run after Step 0 creates the sentinel. A leaked hook then stays armed until TTL (about 360 minutes), blocking unrelated skills. Plan only names research-phase.md cleanup-tmpdir branches and Step 4.
- **Proposed resolution**: Add activation-sentinel removal (and prefer cleanup-tmpdir when appropriate) to the Filing findings VERIFIED=false and ISSUES_FAILED>=1 abort prose; pin in scripts/test-research-structure.sh alongside the research-phase abort pins.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh
- **Concern**: [SCOPE-REDUCTION] Tokenless hook invocation activates on any fresh sentinel, not only the consumer token. Scenario: The plan keeps a tokenless fallback that treats any fresh file under deny-edit-write-active as live. A stale leaked registration wired as bare deny-edit-write.sh (no argv) is exactly the reported failure mode: /bug Step 2 writes bug-$PPID, the leaked hook sees a fresh sentinel, and unrelated /design Write/Edit calls keep denying until TTL even though /research never ran. Token scoping in new frontmatter does not help sessions still carrying old tokenless registrations.
- **Proposed resolution**: Remove the tokenless branch: when $1 is empty, treat activation as inactive (exit 0 allow) instead of matching any sentinel. Keep token-scoped checks only for explicit research and bug argv.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/deny-edit-write.sh:approach
- **Concern**: Shared user-level activation directory couples unrelated Claude sessions. Scenario: Activation sentinels live under ${XDG_CACHE_HOME:-${HOME:-}/.cache}/larch/deny-edit-write-active with no session identity (#5684 forbids hook-side PID correlation). A /research run in session B can leave a fresh research-* file that arms a leaked research-token hook still registered in session A, blocking session A /design writes even though session A never invoked /research. This is a new cross-session coupling the always-deny leaked hook did not have.
- **Proposed resolution**: Document as an explicit residual risk in SECURITY.md and deny-edit-write.md, or narrow the directory (for example only sentinels under the active session tmpdir tree) if a hook-readable session anchor exists without PPID matching.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/research/SKILL.md:96-102
- **Concern**: `/research` `Filing findings as issues` abort paths omit activation-sentinel cleanup from the structural pin contract. Scenario: The plan requires sentinel removal on every post-creation abort and pins `research-phase.md` cleanup-tmpdir aborts in `scripts/test-research-structure.sh`, but the inline `Filing findings as issues` aborts at VERIFIED=false (lines 96-99) and ISSUES_FAILED>=1 (line 102) have no matching prose or harness pins. An implementer can pass structure tests yet leave a fresh `research-*` sentinel after those aborts; a leaked hook then keeps denying unrelated skills for up to the 360-minute TTL
- **Proposed resolution**: Add explicit sentinel-removal steps to both filing abort branches in `skills/research/SKILL.md`, and extend `scripts/test-research-structure.sh` / `.md` with pins mirroring the bug Step 6 failure sentinel-removal checks ## 1. risk-integration — `skills/research/SKILL.md:96-102` **Concern:** The plan pins sentinel removal for `research-phase.md` cleanup-tmpdir aborts but not for the `Filing findings as issues` abort paths that can run after the activation sentinel exists. **Scenario:** `/issue` verification fails (`VERIFIED=false`) or batch filing reports `ISSUES_FAILED>=1`. Research stops without Step 4 cleanup. A fresh `research-*` sentinel remains. A leaked hook stays active until TTL expiry and can block `/design` or other skills, matching the original bug class. **Suggested revision:** Add explicit `rm` of the `research-$PPID` activation sentinel to both filing abort branches, and add matching structural pins in `scripts/test-research-structure.sh` so the harness fails if those paths are missed.



### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17,41-43,61-64,179
- **Concern**: [SCOPE-REDUCTION] Prior accepted FINDING_5 fix is incomplete because the tokenless fallback keeps an any-fresh-sentinel activation path. Scenario: The plan says a tokenless hook activates on any fresh sentinel. A leaked stale hook registered without the new research argument, or a future frontmatter regression, can be re-armed by a bug-* sentinel and deny unrelated Edit/Write calls, recreating the cross-skill leak this fix is meant to remove
- **Proposed resolution**: Remove tokenless fallback. Require a recognized token for activation, and treat missing or unknown tokens as inactive fail-open. Update tests and docs to drop tokenless activation.



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh
- **Concern**: Tokenless hook invocations activate on any fresh consumer sentinel, not only the matching skill token. Scenario: The reproduction sequence ran `/bug` before `/design` writes failed. A leaked `/research` PreToolUse registration that still calls `deny-edit-write.sh` without a token argument will run the new gate in tokenless mode; when `/bug` creates a fresh `bug-*` activation sentinel, that leaked hook becomes live and can deny unrelated skills until TTL expiry, partially recreating the reported cross-skill leak
- **Proposed resolution**: Make tokenless invocation fail-open (treat as inactive) instead of matching any fresh sentinel; rely on frontmatter token args plus structural pins for correct wiring, accepting that mis-wired consumers without a token stay unguarded



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-18,42,63,179
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback keeps the cross-skill re-arm path that the token gate is meant to remove. Scenario: A leaked or stale no-arg /research hook can see a fresh bug-* sentinel, activate via any-fresh-sentinel matching, and deny unrelated /design writes until cleanup or TTL
- **Proposed resolution**: Make missing or empty token fail open instead of scanning all sentinels; update the tests and docs to remove the tokenless any-sentinel fallback and rely on structural pins to catch missing token wiring



