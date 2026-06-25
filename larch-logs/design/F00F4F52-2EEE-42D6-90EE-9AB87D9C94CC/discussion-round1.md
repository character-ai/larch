## Decision 1: Reviewer role for the generic slot
- **Question**: Use new agent file, existing agents/code-reviewer.md, or free-form prompt?
- **Resolution**: Reuse `agents/code-reviewer.md` for both /design and /implement.
- **Source**: user

## Decision 2: Model for the generic slot
- **Question**: Use gpt-5.5 (CODEX_DEFAULT_MODEL) or keep gpt-5.4-mini (review model)?
- **Resolution**: Use gpt-5.5 via CODEX_DEFAULT_MODEL, overridable through existing LARCH_CODEX_MODEL env var. Per-slot model_role="default" in the manifest row; the waterfall falls back to global model_role when slot model_role is empty.
- **Source**: user

## Decision 3: Round gating for /implement
- **Question**: "Rounds 1 and 2" means which rounds for /implement?
- **Resolution**: Same round-num concept as /design: review dispatch-panel --round-num 1 and 2.
- **Source**: user

## Decision 4: Slot naming convention
- **Question**: What output filename for the generic slot?
- **Resolution**: /design uses "codex-plan-generic-output.txt" (already expected by test_design_log_publish_flow). /implement uses "codex-generalist-output.txt" (already expected by review_tally, audit_runs, progress_report).
- **Source**: codebase
