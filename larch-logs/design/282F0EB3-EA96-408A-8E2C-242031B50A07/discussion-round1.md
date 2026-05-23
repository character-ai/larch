## Decision 1: /implement admission when title lacks [DESIGNED]
- **Question**: When /implement starts and the issue title does NOT begin with [DESIGNED], what should happen?
- **Resolution**: Hard-fail (reject the run). Forked-mode and resume paths may still skip the check consistent with current admission-skip carve-outs.
- **Source**: user

## Decision 2: Scope of literal-string rewrites in historical artifacts
- **Question**: Should literal [IN PROGRESS] / [PLANNED] strings be rewritten in committed historical artifacts (CHANGELOG.md and larch-logs/**)?
- **Resolution**: Leave historical artifacts unchanged. Only update active runtime surface (skills/, scripts/, agents/, .claude/, SECURITY.md, AGENTS.md, tests).
- **Source**: user

## Decision 3: Disposition of [STALLED] prefix
- **Question**: Should [STALLED] be renamed as part of this overhaul?
- **Resolution**: Keep [STALLED] unchanged. The issue does not mention it, and its semantics (recoverable failure path) are unaffected by the design/implement naming overhaul.
- **Source**: codebase (not raised in issue body)

⏩ 1d: discussion r1 — 3 scope decisions resolved (2 from user, 1 from codebase); no further scope branches require discussion
