### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_consecutive_bash.py:82-87
- **Concern**: Suppression pairing semantics are unspecified. Scenario: A valid `# lint-consecutive-bash: ok <reason>` on only one fence of an adjacent pair may still be reported if the implementer requires both fences to carry a pragma; triple-chain gaps (A–B–C) may need duplicate suppressions on B
- **Proposed resolution**: State explicitly that one valid suppression on either fence suppresses that adjacent pair, and a suppression on the middle fence of a short-gap chain suppresses both pairs it participates in

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9-12
- **Concern**: The planned scan scope omits `skills/shared/*.md`, which is an orchestrator-facing shared skill prompt surface. The existing bare-grep lint treats shared Markdown as orchestrator-facing, and shared files such as `skills/shared/external-reviewers.md:18-58` contain Bash tool-call fences used by multiple skills.. Scenario: A consecutive Bash pair added to a shared prompt fragment would pass `make lint` and the pre-commit hook, so the new lint would not fully enforce the requested no-consecutive-prompt-side-Bash rule across orchestrator-facing skill Markdown.
- **Proposed resolution**: Add `skills/shared/*.md` to the scoped patterns, git and non-git enumeration, pre-commit `files:` filter, docs, and first-run remediation/test coverage.
