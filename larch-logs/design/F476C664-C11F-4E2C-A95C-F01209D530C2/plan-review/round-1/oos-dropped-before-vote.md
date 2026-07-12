### OOS_4: Cross-language tagging omits `.claude/skills` and `.claude/agents` consumers
- **Description**: Cross-language tagging omits `.claude/skills` and `.claude/agents` consumers. Scenario: Feature examples center on `scripts/` and `skills/`, but dev-only consumers under `.claude/` would be listed without the `cross-language` tag, weakening scanability of the bundle section
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/issue/analyze_bugs.py:716-778
- **Phase**: design

