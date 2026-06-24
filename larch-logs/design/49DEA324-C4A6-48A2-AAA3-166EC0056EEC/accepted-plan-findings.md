### FINDING_3: Default Codex role drops existing `--default-model` fallback contract
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan’s default-role resolution may bypass the existing `resolve_model_args("codex", default_model=...)` and `agent model-args --default-model` contract. Current code uses `default_model or "gpt-5.5"` when env and plugin options are unset. If the default role falls straight to `gpt-5.5` without honoring `default_model`, that CLI/Python surface breaks outside the cheap-role change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep the default-role ladder as `LARCH_CODEX_MODEL`, plugin option, then `default_model or gpt-5.5`; add a focused assertion for `agent model-args --tool codex --default-model custom`.


