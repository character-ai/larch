---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Legacy check-mode failure semantics are not fully pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan does not explicitly wire legacy syntax-error and stale-baseline behavior through the engine. Engine defaults can produce a syntax finding with exit 1 and warning-only stale handling, whereas legacy check mode requires exit 2 for both cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In thin main(), call run_rule with strict_stale=not bool(parsed.write) on check runs, matching the markdown port. Add a RULE contract assertion or CLI test that stale rows exit 2 while write mode stays non-strict.
  - From Cursor-Pragmatic: Pin `RULE.syntax_policy="raise"`, `allow_inline_suppression=False`, and `occurrence_baseline=True`; in `main()`, pass `strict_stale=not bool(parsed.write)` to `run_rule`, matching `lint_markdown_heading_fence_state.py`.


### [Plan Review] FINDING_4

### FINDING_4: Tracked symlink exclusion is incompatible with current engine discovery
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: A tracked in-scope symlink may be rejected by engine discovery before a rule-level path filter can exclude it, changing the legacy linter’s behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a safe rule-specific discovery mechanism that skips these legacy-excluded symlinks before engine filesystem validation, and cover a tracked in-scope symlink in the port tests.


---LARCH-REJECTED-END---
