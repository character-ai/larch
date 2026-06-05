## Proposed Design Outline

### Goals
- Give the shipped PR-metrics feature (`compute-pr-line-counts.sh` + `render-run-summary.sh` + `write-final-report.sh` integration) a vetted `larch:plan` with acceptance criteria on issue #3538.
- Close the one real test gap: `compose_self_fallback`'s `LINES_DATA_OK=true` branch is untested.

### Non-goals
- No timeout-hardening code (user decision: document the no-explicit-timeout posture only).
- No renderer-harness changes — `test-render-run-summary.sh` already covers both Lines-bullet shapes.
- No new pagination or security-validation code; both are shipped and test-pinned.

### Approach sketch
- The plan documents as-built architecture: KV contract (`LINES_STATUS=ok|skipped|unavailable`), non-fatal degradation to `N/A`, `gh api --paginate` usage, input validation.
- Acceptance criteria cover the four issue topics: integration, pagination edge cases (incl. the GitHub 3000-file API cap), timeout posture, REPO/PR_NUMBER validation.
- One code change: a new stage2-fallback test case in `skills/implement/scripts/test-write-final-report.sh` feeding a PR fixture + working gh shim with a failing renderer stub, asserting the formatted `Lines (PR diff)` bullet.
- Update the harness sibling `test-write-final-report.md` in the same PR (script-md-siblings rule).

### Surfaces in scope
- `skills/implement/scripts/test-write-final-report.sh` (new test case)
- `skills/implement/scripts/test-write-final-report.md` (sibling doc)
- Issue #3538 `larch:plan` block (plan + acceptance criteria)

### Open questions
- None.
