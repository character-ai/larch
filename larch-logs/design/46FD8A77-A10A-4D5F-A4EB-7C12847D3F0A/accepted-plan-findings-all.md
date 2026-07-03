### FINDING_1: Step 3 bug abort can leave the activation sentinel behind
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Hook Scope Security
- **Severity**: important
- **Concern**: `/bug` can hit a security abort in Step 3 after Step 2 has already created the activation sentinel, but the abort path only removes `$BUG_TMPDIR`. If the hook registration leaks, that leftover sentinel can keep the deny gate live until TTL expiry and block unrelated skills.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Prefer minimum change: create the bug activation sentinel at Step 4 immediately before the first Write, not in Step 2. If Step 2 creation stays, add explicit sentinel removal to the Step 3 security-abort branch and pin it in scripts/test-bug-structure.sh.`
  - From Cursor-Innovation: `Add sentinel removal to the Step 3 security-abort path alongside \`$BUG_TMPDIR\` removal, mirroring the Step 5 contract.`
  - From Cursor-Pragmatic: `Add Step 3 security abort to skills/bug/SKILL.md and scripts/test-bug-structure.sh: remove the activation sentinel when removing $BUG_TMPDIR, same as the planned Step 5 security path`
  - From Cursor-Requirements: `Mirror Step 5: on Step 3 security abort, remove the activation sentinel before or with $BUG_TMPDIR removal. Pin the prose in scripts/test-bug-structure.sh.`
  - From Cursor-dyn-Hook Scope Security: `Add sentinel removal to the Step 3 security-abort branch in skills/bug/SKILL.md and pin it in scripts/test-bug-structure.sh`


### FINDING_2: Research sentinel is written before degraded-tools gating finishes
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-Hook Scope Security
- **Severity**: important
- **Concern**: The `/research` activation sentinel is created right after `RESEARCH_TMPDIR` is bound, before the degraded-tools gate fully resolves. That means Step 0 Abort or a failed gate can leave a fresh marker with no cleanup path, so a leaked hook can keep denying later skills until TTL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Create the research activation sentinel only after Step 0a fully succeeds, including degraded-tools Continue (or non-interactive pass), immediately before the first Write/Edit/NotebookEdit need. Pin that ordering in scripts/test-research-structure.sh.`
  - From Cursor-Innovation: `Defer sentinel creation until after the degraded-tools gate resolves (Continue or already-prompted one-down), or explicitly remove the sentinel on every Step 0 abort path that can run after it is written.`
  - From Cursor-Pragmatic: `Create the activation sentinel only after degraded-tools gate returns ok/continue, or document and implement sentinel removal on Abort before exit in skills/research/SKILL.md and scripts/test-research-structure.sh`
  - From Codex-Requirements: `Add skills/research/references/research-phase.md to the plan and remove the activation sentinel before each cleanup/exit branch, or route those branches through the same sentinel-aware cleanup helper; pin this controlled-abort cleanup in the research structure test.`
  - From Cursor-dyn-Hook Scope Security: `Add ### UPDATED: skills/research/references/research-phase.md: remove the activation sentinel in every cleanup-tmpdir abort branch (lines 67, 93, 99), mirroring Step 4 cleanup`


### FINDING_3: PPID-based activation is brittle across harness and production parents
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Hook Scope Security
- **Severity**: important
- **Concern**: The activation check is coupled to a parent PID that may differ between direct-child harness invocations and production PreToolUse hook lifecycles. That can make activation flaky in tests or silently fail open/closed in live runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Document in scripts/deny-edit-write.md that activation keys off the hook process $PPID. In the harness helper, create fresh sentinels keyed to the invoking shell PID ($$) when the hook is spawned as a direct child, and isolate XDG_CACHE_HOME as already planned.`
  - From Cursor-Pragmatic: `Treat liveness as any fresh sentinel in the activation directory (mtime within TTL), matching hook-bg-poll-guard marker liveness rather than hook $PPID equality; keep skill prefix in filenames for debugging only and add a harness case that creates the sentinel from a wrapper subprocess whose $PPID differs from the hook parent`
  - From Cursor-dyn-Hook Scope Security: `Add one harness case that creates the sentinel from a parent subshell and invokes the hook from a sibling child sharing that parent (or document and test the exact PID convention); abort setup if sentinel write succeeds but a probe hook call sees inactive`


### FINDING_4: Unset HOME can break the planned cache-root expansion
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed activation cache root can trip `set -u` when both `XDG_CACHE_HOME` and `HOME` are unset. In stripped environments, the hook can abort before it emits either the inactive allow or active deny decision, which regresses the always-exit-0 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: `Require a nounset-safe cache root, for example \`${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}\`, or make unresolved cache state return inactive without expanding an unset \`HOME\`.`


### FINDING_5: Any fresh sentinel for the current PPID can re-arm a leaked hook across skills
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: The planned `activation_is_live()` behavior treats any fresh per-PPID sentinel as active across both `/research` and `/bug`. That means `/bug` Step 2 can recreate activity for a leaked `/research` hook and reproduce the cross-skill deny even when `/research` never ran in the visible session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: `Pass a skill token from each SKILL.md hook command (for example deny-edit-write.sh research vs deny-edit-write.sh bug). Have activation_is_live check only that token sentinel for $PPID. Add harness cases: research sentinel does not activate bug-only checks and vice versa; neither activates a hook invoked with the other skill token.`


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh:36-67
- **Concern**: [SCOPE-REDUCTION] PPID-suffixed sentinel lookup repeats the #5684 production failure mode. Scenario: `hook-bg-poll-guard.md` and `hook-no-progress-guard.md` document that PreToolUse hook `$PPID` does not reliably match orchestrator Bash `$PPID`; `scripts/test-deny-edit-write.sh` invokes the hook as a direct child so sentinel PID and hook `$PPID` always match in CI but may diverge in Claude Code. If lookup fails, activation stays false, the gate fail-opens, and `/research` loses mechanical `/tmp`-only enforcement while still passing tests.
- **Proposed resolution**: Have `activation_is_live()` treat any fresh file under the activation directory (mtime within TTL) as live, without PPID correlation; skills may still embed `$PPID` in filenames for debugging only. Add a production-divergence harness case modeled on `scripts/test-hook-bg-poll-guard.sh` T14 that creates a sentinel under a foreign PID and asserts active deny still works.


### FINDING_1: Missing sentinel cleanup in filing-abort paths
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The `/research` "Filing findings as issues" abort branches can fire after the activation sentinel exists but before cleanup runs, leaving a stale hook armed until TTL and blocking unrelated skills.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add activation-sentinel removal (and prefer cleanup-tmpdir when appropriate) to the Filing findings VERIFIED=false and ISSUES_FAILED>=1 abort prose; pin in scripts/test-research-structure.sh alongside the research-phase abort pins.
  - From Cursor-Pragmatic: Add explicit sentinel-removal steps to both filing abort branches in `skills/research/SKILL.md`, and extend `scripts/test-research-structure.sh` / `.md` with pins mirroring the bug Step 6 failure sentinel-removal checks


### FINDING_3: Tokenless hook invocation matches any fresh sentinel
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Tokenless `deny-edit-write.sh` invocations can activate on any fresh consumer sentinel, so a leaked registration can start denying unrelated skills.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Make tokenless invocation fail-open (treat as inactive) instead of matching any fresh sentinel; rely on frontmatter token args plus structural pins for correct wiring, accepting that mis-wired consumers without a token stay unguarded


### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/deny-edit-write.sh:activation_is_live
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback re-arms leaked stale hook registrations when another skill creates a fresh sentinel. Scenario: Plan keeps tokenless invocation activating on any fresh sentinel. A harness-leaked registration still calls deny-edit-write.sh without a token (pre-upgrade wiring). /bug Step 2 then writes bug-$PPID; the leaked tokenless hook treats that as live and denies non-/tmp Write/Edit/NotebookEdit again — matching the reported /design Gate B failure after an intervening /bug run even though /research never executed. Token scoping on new frontmatter does not apply to the stale registration.
- **Proposed resolution**: Drop tokenless any-sentinel fallback: when $1 is empty, activation_is_live returns false (fail-open). Both consumers already pass research|bug via frontmatter; structural pins enforce that. Add a harness case: tokenless hook + fresh bug-* sentinel + repo-path stdin must allow (empty stdout).


### FINDING_5:
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


### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-18,42,63,179
- **Concern**: [SCOPE-REDUCTION] Tokenless fallback keeps the cross-skill re-arm path that the token gate is meant to remove. Scenario: A leaked or stale no-arg /research hook can see a fresh bug-* sentinel, activate via any-fresh-sentinel matching, and deny unrelated /design writes until cleanup or TTL
- **Proposed resolution**: Make missing or empty token fail open instead of scanning all sentinels; update the tests and docs to remove the tokenless any-sentinel fallback and rely on structural pins to catch missing token wiring


