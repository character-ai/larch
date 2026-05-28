## Decision 1: Approach to the test-fixture-leak issue

- **Question**: Should the two test harnesses be migrated to use `${TMPDIR}` fixtures (as the issue body proposes), or removed entirely?
- **Resolution**: Remove both test harnesses entirely and add no replacement tests. The user stated: "I don't want any tests for run_analysis. remove all tests for run_analysis and don't add new ones."
- **Source**: user

## Decision 2: Scope of removal

- **Question**: Are there other test files that exercise `skills/report-tokens/scripts/run-analysis.sh` that should also be removed?
- **Resolution**: Only the two files named in #3121 — `skills/report-tokens/scripts/test-report-tokens-recompute.sh` and `skills/report-tokens/scripts/test-rate-assertions.sh`. Repo-wide grep for `run-analysis.sh` shows these are the only consumers under `skills/report-tokens/scripts/`. The `.claude/skills/analyze-issues/scripts/run-analysis.sh` is a different script (separate skill).
- **Source**: codebase

## Decision 3: Orphan artifacts after deletion

- **Question**: What other artifacts become orphans once the two test files are deleted?
- **Resolution**: (a) `skills/report-tokens/scripts/test-rate-assertions.md` — sibling contract for the deleted harness; delete. (b) `skills/report-tokens/scripts/fixtures/recompute-run/` (containing `manifest.json` and `token-report.json`) — consumed only by the two deleted tests; delete. (c) The empty `skills/report-tokens/scripts/fixtures/` parent directory — delete. No other artifacts are orphaned.
- **Source**: codebase
