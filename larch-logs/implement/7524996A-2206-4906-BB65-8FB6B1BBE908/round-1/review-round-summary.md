# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Codex implement rater still ignores difficulty tier
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-model-routing
- **Severity**: minor
- **Concern**: `python/larch/implement/dispatch_step2.py` still resolves the Codex rater model as the default tier instead of the active difficulty tier, so TRIVIAL launches are recorded under the wrong model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY[st.difficulty] when resolving Codex rater-model
  - From dyn-dyn-model-routing: When `st.tool_tag == "codex"` and `st.difficulty` is set, resolve the rater model with the same precedence as `launch-codex-implement` (`LARCH_CODEX_MODEL` / plugin override, then `CODEX_IMPLEMENT_MODEL_BY_DIFFICULTY[tier]`, then `CODEX_DEFAULT_MODEL`), and add a test that TRIVIAL records `gpt-5.6-terra`.


### FINDING_7: CI launcher still defaults resolve-conflict to the wrong Claude model
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The shared CI launcher still applies the CI-recovery default to `resolve-conflict`, so rebase conflicts can launch the wrong Claude model unless the role is handled explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Make the Claude CI default role-sensitive, or pass `--model config.CLAUDE_CI_FIX_MODEL` for `resolve-conflict` while keeping `CLAUDE_CI_RECOVERY_MODEL` for `role=fix`.
  - From codex-specialist-edge-cases: Branch on args.role so only CI fix uses the new recovery models; keep resolve-conflict on Opus, Codex default role, and normal Cursor default.


### FINDING_8: Codex usage recording drops the resolved model
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Codex usage recording drops the resolved launch model on the Step 2 and CI sidecar paths, so token buckets can attribute Terra and other routed launches to the default model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Extract the selected `-m` value from `model_args` and pass it to `_record_usage_from_events` or `_record_usage_from_events_and_emit_token` for Step 2 and CI Codex launches.
  - From codex-specialist-edge-cases: Pass and record the resolved `-m` value in CI and implement Codex usage paths, including token sidecars and direct record-vendor calls.


### FINDING_10: CI launcher tests still assert the old recovery-model behavior
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing, cursor-specialist-plan-fidelity-forced
- **Severity**: major
- **Concern**: The CI and launcher tests still expect the old `CLAUDE_CI_FIX_MODEL`/Opus behavior, so they will fail until the recovery path is separated from lint-fix coverage and the new token-record normalization is asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Update assertion and add CLAUDE_CI_RECOVERY_MODEL check
  - From cursor-specialist-testing: Split CI recovery vs lint-fix launcher model tests
  - From codex-specialist-testing: Update the expected model to CLAUDE_CI_RECOVERY_MODEL and keep one assertion for the normalized token-record value.
  - From cursor-specialist-plan-fidelity-forced: Assert order codex,cursor,claude and CLAUDE_CI_RECOVERY_MODEL while keeping lint-fix Opus checks.
  - From cursor-specialist-plan-fidelity-forced: Update CI recovery test for Sonnet [1m]; keep separate lint-fix Opus test.


