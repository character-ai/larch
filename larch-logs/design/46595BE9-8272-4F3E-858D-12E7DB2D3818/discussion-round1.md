## Decision 1: Title marker convention
- **Question**: Should the completion marker be [PLANNED] (brackets) or (PLANNED) (parentheses)?
- **Resolution**: [PLANNED] (brackets) — consistent with [IN PROGRESS], [DONE], [STALLED] convention in lib-title-markers.sh and tracking-issue-write.sh.
- **Source**: user

## Decision 2: Log artifact scope
- **Question**: All DESIGN_TMPDIR content or key artifacts only?
- **Resolution**: All DESIGN_TMPDIR content copied to larch-logs/design/<run-id>/.
- **Source**: user

## Decision 3: CI bypass mechanism
- **Question**: [skip ci] commit message, --admin merge, or both?
- **Resolution**: Both — [skip ci] in the log-flush commit message AND gh pr merge --squash --admin.
- **Source**: user

## Decision 4: Nested mode applicability
- **Question**: Should log flush + PR creation apply when /design is nested inside /implement?
- **Resolution**: /design will never again be invoked from inside /implement; no nested-mode guard needed.
- **Source**: user (with clarification: /design is now always standalone)

## Decision 5: Branch cleanup after merge
- **Question**: Delete design branch after PR merges?
- **Resolution**: Yes, delete after merge.
- **Source**: user

## Decision 6: Log flush infrastructure
- **Question**: Use larch-log.sh batches or a direct copy to larch-logs/design/<run-id>/?
- **Resolution**: Create scripts/flush-design-logs.sh — a dedicated script that copies all DESIGN_TMPDIR files (with redaction) to larch-logs/design/<run-id>/, creates manifest.json, and commits with [skip ci]. Does not require modifying larch-log-batches.sh.
- **Source**: codebase (larch-log.sh commit hardcodes the message without [skip ci]; adding all DESIGN_TMPDIR files as registered batches is impractical)

## Decision 7: Step ordering in Step 5
- **Question**: What order in Step 5? plan-write → rename → log flush → PR → merge → cleanup
- **Resolution**: plan-block-write.sh (5b) → tracking-issue-write.sh rename planned (5b-post) → flush-design-logs.sh (5c) → push branch → create-pr.sh → merge-pr.sh --admin → delete branch → cleanup-tmpdir.sh (5d)
- **Source**: codebase (Step 5c currently calls cleanup-tmpdir.sh last; log flush must precede it since DESIGN_TMPDIR is removed there)
