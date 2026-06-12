## Decision 1: Normalized token names for ci-wait.sh / ci_monitor.py
- **Question**: What token strings should replace the 5 prose BAIL_REASON values?
- **Resolution**: Use `poll-budget-exhausted`, `ci-wait-unexpected-exit`, `no-ci-checks-observed`, `ci-status-stale`, `ci-decide-error` (kebab-case, matching ci-decide.sh convention).
- **Source**: user

## Decision 2: ci_monitor.py in scope for Item 2
- **Question**: Should ci_monitor.py prose bail_reason values also be normalized?
- **Resolution**: Yes — fix both ci-wait.sh and ci_monitor.py in the same PR.
- **Source**: user

## Decision 3: KV encoding fix for multi-line values
- **Question**: How to handle embedded newlines in normalize-issue-env output?
- **Resolution**: Strip embedded newlines (collapse to spaces) before emitting KEY=value pairs.
- **Source**: user
