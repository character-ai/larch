## Goal
Retroactively migrate larch run-log meta (token reports and all anchor sections) from GitHub issue comments into larch-logs/implement/ directories for 29 issues whose PRs predated the larch-logs commit infrastructure.

## Implementation Plan

1. Write Python migration script that:
   - For Group A (26 old-format issues): fetches anchor comments, extracts sections, creates issue-NNNN/ directories
   - For Group B (3 new-format issues): fetches larch:token-report comments, creates UUID-named directories
2. Run the script to generate all larch-logs/implement/ directories
3. Add .markdownlintignore excluding larch-logs/ from markdownlint
4. Exclude larch-logs/ from lint-mermaid-fences.sh --changed-only via case filter
5. Document exclusions in docs/linting.md

## Test plan
- Run /relevant-checks — pre-commit + agent-lint must pass
- Verify each expected directory exists with manifest.json
- Verify lint-mermaid-fences.sh correctly excludes larch-logs/ paths
