## Decision 1: Metric format
- **Question**: For each bucket (code vs larch logs), what number format should the /implement final report show?
- **Resolution**: Added/deleted split, e.g. `code +X/−Y, larch logs +A/−B`.
- **Source**: user

## Decision 2: Code-vs-larch-logs split boundary
- **Question**: How should the script split "code" from "larch logs"?
- **Resolution**: Purely by the `larch-logs/` path prefix. Every other changed path (docs, tests, config, scripts) counts as code.
- **Source**: user

## Decision 3: Diff source
- **Question**: Where should the script get the PR diff numbers from?
- **Resolution**: GitHub PR files API (`gh api repos/<repo>/pulls/<N>/files`, additions/deletions per file). Reflects the merged PR, stays correct after `--merge` deletes the local branch. Show N/A when no PR exists or the repo/API is unavailable.
- **Source**: user

## Constraint: scope is /implement only
- **Question**: Does the design final report also need line counts?
- **Resolution**: No. `render-run-summary.sh` is shared, but `/design` runs write plans to issues and create no code PR, so the new bullet is gated to `--skill implement` only (same pattern as the existing `if [ "$SKILL" != design ]` PR/Code-review guards).
- **Source**: codebase

## Constraint: computation lives in a script
- **Question**: Where do the line-count computations run?
- **Resolution**: In a shell script (git/gh + arithmetic), never in SKILL.md orchestrator prose. Per the issue body.
- **Source**: user
