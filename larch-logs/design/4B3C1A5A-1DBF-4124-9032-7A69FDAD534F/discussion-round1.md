## Decision 1: Hard-cutover rule applies to all callers
- **Question**: Are callers in non-dev-only scripts (`status.sh`, `refresh-execution-issues.sh`, `implement-finalize.sh`) in scope for cutover in this issue?
- **Resolution**: Yes — the migration playbook hard-cutover rule requires ALL consumers to be updated in the same commit. This includes `skills/status/scripts/status.sh`, `skills/implement/scripts/refresh-execution-issues.sh`, `scripts/implement-finalize.sh`, and all test stubs that create stub `.sh` files.
- **Source**: codebase (migration playbook + issue DoD)

## Decision 2: No test harnesses for combine-issues or analyze-issues
- **Question**: Do `fetch-combinable-issues.sh`/`apply-combination.sh` and `fetch-issues.sh`/`run-analysis.sh` require pytest harnesses?
- **Resolution**: `test-analyze.sh` already exists and must be updated/replaced. `combine-issues` has no dedicated harness — representative pytest coverage follows the standard recipe. `test-audit-runs.sh` and `test-release-prepare.sh` port to pytest with representative behavioral coverage (as confirmed in Step 1c).
- **Source**: codebase + user confirmation

## Decision 3: classify-bump.md stays as authoritative classification doc
- **Question**: Is `classify-bump.md` being deleted or retained?
- **Resolution**: Retained — the issue explicitly states "release classification rules remain authoritative in .claude/skills/release/scripts/classify-bump.md". Only the `.sh` script is deleted; the `.md` doc survives.
- **Source**: issue body

## Decision 4: analyze.py and render-chart.py move to python/
- **Question**: Are the existing `.claude/skills/analyze-issues/scripts/analyze.py` and `render-chart.py` moved to `python/`?
- **Resolution**: Yes — move both to `python/`, register CLI verbs in `cli.py`, and update the test harness. As confirmed in Step 1c.
- **Source**: user confirmation (Step 1c)
