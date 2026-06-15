### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/configuration-and-permissions.md:210 / SECURITY.md:170
- **Concern**: Acceptance stale-default greps omit obsolete Codex-availability routing phrases. Scenario: Implementer updates model default bullets and grep passes for claude-fable-5 / prefer codex / defaults to Codex, but intro sentences still claim Claude is only used when Codex is unavailable or that Codex is the default when present; operators misconfigure LARCH_DESIGN_DRAFTER / LARCH_DESIGN_PLAN_MODEL
- **Proposed resolution**: Add when Codex is unavailable, default when Codex is available, and Codex is unavailable and the drafter to the in-scope stale grep list and acceptance criteria; require zero matches in updated drafter-doc surfaces

