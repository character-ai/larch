### FINDING_1: Review Step 0 binds the wrong session key for `claude-source`
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Standalone review Step 0 can skip or misbind the source snapshot because it uses `SESSION_ID` instead of the session key `token claude-source` expects, and it does not enforce `SESSION_UUID` matching before writing `claude-source.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `design_publish._fetch_claude_source_snapshot`: gate on non-empty `LARCH_TOKEN_SESSION_ID`, export it for `token claude-source`, require `SESSION_UUID` to match, write `$REVIEW_TMPDIR/claude-source.env` from stdout, set `LARCH_CLAUDE_SOURCE_FILE` to that path.
  - From Codex-Pragmatic: Run token claude-source with LARCH_TOKEN_SESSION_ID="$SESSION_ID" and bind LARCH_CLAUDE_SOURCE_FILE only when SESSION_UUID matches SESSION_ID. Leave it empty and skip capture on mismatch.
  - From Cursor-Requirements: Drop the `SESSION_ID` binding. When `LARCH_CLAUDE_SOURCE_FILE` is empty, call `token claude-source` with `LARCH_TOKEN_SESSION_ID` from caller-env or host env when set; otherwise rely on the helper latest-mtime fallback. Write `$REVIEW_TMPDIR/claude-source.env` only when stdout contains `TRANSCRIPT_PATH`, matching `design_publish._materialize_claude_source_snapshot`


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/SKILL.md:75-106; python/larch/review/review_tally.py:1259-1273
- **Concern**: [SCOPE-REDUCTION] Do not add session-transcript to the generic review log-phase path. Scenario: The planned nested guard wraps direct capture and commit only. The existing RUN_ID log-phase block also runs for nested /review inside /implement, so adding session-transcript there can bypass the guard and write or attempt a raw review transcript under the parent run.
- **Proposed resolution**: Drop session-transcript from review log-phase allowlist, tests, and batch list. Rely only on the guarded standalone run-log capture-transcript call plus guarded commit.


