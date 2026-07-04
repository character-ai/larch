### OOS_1: [OUT_OF_SCOPE] Readability-style content is not inlined for specialist renders
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Specialist render paths load pre-rendered reviewer bodies that rely on the readability-style directive, but they do not inline `readability-style.md`. As a result, Codex/Cursor read-only launches receive an instruction they cannot satisfy unless the render path supplies the style text or switches to a vendor-facing external-prompt token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: append inlined readability content in the specialist render path (or switch to the `external-prompt` `<READABILITY_STYLE>` form for vendor launches).
  - From cursor-specialist-edge-cases: Inline skills/shared/readability-style.md in _render_specialist_text (same pattern as render plan-review) or expand a render-time readability token; keep the agent directive for Claude subagents with Read.

### OOS_2: [OUT_OF_SCOPE] Empty agent-file walks can let readability lint pass
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_agent_files()` skips missing paths silently, so if all reviewer agent files are deleted the walk becomes empty and readability lint exits 0 instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: assert `agents/code-reviewer.md` exists or fail closed when the walk is empty.
