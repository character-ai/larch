### OOS_1: [OUT_OF_SCOPE] Resolver tests need `LARCH_CLAUDE_SESSION_ID` precedence coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Resolver tests omit the `LARCH_CLAUDE_SESSION_ID` hit/miss/precedence cases, so override ordering is not pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add three focused _find_latest_claude_transcript tests for override hit, miss, and precedence.

### OOS_2: [OUT_OF_SCOPE] Design publish still needs stale-cache refetch regression coverage
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-transcript-capture
- **Severity**: nit
- **Concern**: Design publish still lacks a regression test for rejecting stale cached snapshots, so a dead `TRANSCRIPT_PATH` could stop being evicted without notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test seeding claude-source.env with a missing TRANSCRIPT_PATH and assert refetch plus successful capture.
  - From dyn-dyn-transcript-capture: Add a focused test that seeds a non-empty claude-source.env with a nonexistent TRANSCRIPT_PATH, asserts _materialize_claude_source_snapshot refetches, and confirms token claude-source is invoked.

### OOS_3: [OUT_OF_SCOPE] Run-log flush should validate transcript containment
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `capture_transcript_main` trusts snapshot `TRANSCRIPT_PATH` values that merely exist, so containment against arbitrary readable jsonl remains untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Apply the same containment rules as _validate_snapshot_replay before render/commit.

### OOS_4: [OUT_OF_SCOPE] Bootstrap stale snapshot reuse still lacks validation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_write_claude_source_snapshot` returns early on any existing `claude-source.env` without validating transcript freshness, so stale snapshots can survive long-lived tmpdirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Re-validate via token_claude_source replay or refresh when cached SESSION_UUID disagrees with ambient Claude session id.

### OOS_5: [OUT_OF_SCOPE] Invalid session IDs should fail closed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Invalid session IDs are still ignored in favor of newest-jsonl selection, which can choose the wrong transcript when the sid format is unexpected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fail closed when a sid env var is set but fails _SAFE_SESSION_RE, or log a warning before fallback.

### OOS_6: [OUT_OF_SCOPE] Update the transcript-session docs before operators misconfigure them
- **Reviewer(s)**: dyn-dyn-transcript-capture
- **Severity**: nit
- **Concern**: The `make test-token-claude-source` docs still omit `CLAUDE_CODE_SESSION_ID` and the retirement of `LARCH_TOKEN_SESSION_ID`, which can mislead operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-capture: Worth updating when tests/docs are next touched so operators do not misconfigure sessions.

### OOS_7: [OUT_OF_SCOPE] Add explicit `LARCH_CLAUDE_SESSION_ID` precedence testing
- **Reviewer(s)**: dyn-dyn-transcript-capture
- **Severity**: nit
- **Concern**: There is still no explicit test for `LARCH_CLAUDE_SESSION_ID` precedence when both override keys are set, so the plan contract remains only partially pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-transcript-capture: a one-line precedence test would fully pin the plan contract.

