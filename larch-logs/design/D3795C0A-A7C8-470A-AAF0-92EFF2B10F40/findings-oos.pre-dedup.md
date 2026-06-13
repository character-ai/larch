### OOS_1:
- **Description**: `normalize_scout_manifest()` proposal redirects Python stderr to `/dev/null`. Scenario: CLI failures or `UsageError` text are discarded; operators only see static-only fallback (`SCOUT_STATUS=parse-failed`) with no WARN lines from `filter-manifest`. Behavior matches today’s silent jq failure path, not a new regression from Item 6.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/review/scripts/dispatch-panel.sh:190-201
- **Phase**: design

