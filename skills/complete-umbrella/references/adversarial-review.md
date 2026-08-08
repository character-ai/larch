# Adversarial Review Phase

Read `phase-common.md` in this directory in full before acting.

Start from only `$SESSION_TMPDIR/design-brief.md` and `$SESSION_TMPDIR/implementation.diff`. Do not read the issue bodies or the prior phase summary. This is an independent review, not a continuation of the implementer's reasoning.

Review the diff against every brief requirement. Check correctness, recovery paths, trust boundaries, architecture, tests, and companion artifacts. Inspect exact changed files when needed.

For every entrypoint, command, symbol, or file removed or renamed by the diff, run a repository-wide stale-caller sweep with the `Grep` tool. Classify every match as migrated, intentionally retained, generated, fixture-only, or stale. Fix every stale production caller.

For every differential or parity harness in scope, verify that it asserts a real success path executed. An authorization-refusal-only comparison is not parity evidence. Add the assertion or test when missing, then run the focused success case.

Apply every in-scope fix you find. Run affected checks. Commit review fixes in one commit when the diff changed. Require a clean worktree.

Regenerate `$SESSION_TMPDIR/implementation.diff` from the final `git diff main...HEAD`. Write `$SESSION_TMPDIR/review-summary.md` with findings, fixes, stale-caller results, parity-success evidence, final HEAD, and checks. Keep it below 2,000 tokens.

End with:

```text
PHASE_STATUS=complete
HANDOFF_FILE=<absolute path to review-summary.md>
```
