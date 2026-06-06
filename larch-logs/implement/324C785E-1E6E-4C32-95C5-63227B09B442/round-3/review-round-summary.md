# Review Round 3

- Mode: `diff`
- 13 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: collect-agent-results.sh codex-exec retry logic duplicated across paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-retry-contract-output.txt
- **Severity**: important
- **Concern**: The codex-exec outer-retry contract is implemented in parallel copies: `parse_retry_meta`, an inline empty-output meta parser, `launch_outer_retry_or_mark`, and the main retry loop. Empty-output retries duplicate launch logic instead of calling `launch_outer_retry_or_mark`, and inline parsing can drift from `parse_retry_meta`. Future `OUTER_LAUNCHER_*` keys or validation fixes applied in one path may not reach the others, causing silent retry misconfiguration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: After parse_retry_meta, call launch_outer_retry_or_mark and delete the inlined duplicate block.
  - From cursor-specialist-structure-output.txt: Replace inline meta parsing with parse_retry_meta "$META".
  - From dyn-retry-contract-output.txt: Have the empty-output loop call `parse_retry_meta "$META"` instead of inlining the parser, and extract a shared `build_codex_exec_outer_retry_args` helper used by both `launch_outer_retry_or_mark` and the main loop so validation and argv reconstruction cannot diverge again.


### FINDING_10: test-collect-agent-retry.sh lacks codex-exec fail-closed metadata cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Despite a new validation branch in `collect-agent-results.sh`, there are no codex-exec-specific fail-closed retry metadata cases. Invalid `OUTER_LAUNCHER_SANDBOX` or missing usage label could be accepted or mishandled without a targeted regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add case-r/s/u fixtures with OUTER_LAUNCHER_KIND=codex-exec and assert fail-closed before retry spawn.


### FINDING_11: Harness contract markdown not updated for new cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-collect-agent-results.md` and `test-run-negotiation-round.md` harness contracts were not updated for `C_T1_CODEX_EXEC` or expanded negotiation auth coverage. Future harness edits may drop codex-exec retry coverage without contract review catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update test-collect-agent-results.md and test-run-negotiation-round.md to pin the new cases.


### FINDING_14: jq-less collector retry loses multi add-dir grants
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On hosts without `jq`, codex-exec outer retry passes only `--add-dir workdir`. `lint-fix-loop` uses `run_dir` plus `REPO_ROOT`; empty-output retry can lose `run_dir` sandbox grant and fail silently or write outside intended dirs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add jq-less multi-add-dir harness or fail closed when full add-dir list cannot be reconstructed.


### FINDING_15: lib-external-launcher-common.md missing merged env-key coverage inventory
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance #9 requires identical merged env-key coverage inventory in four docs; `lib-external-launcher-common.md` only has a partial wired-call-site list and defers to `SECURITY.md`. Operators auditing coverage from that doc miss `/research`, voter/judge, and lint-fix surfaces that `SECURITY.md` lists, violating the plan's verbatim-inventory acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Embed the same merged inventory paragraph used in docs/external-reviewers.md:12 verbatim in lib-external-launcher-common.md.


### FINDING_17: lint-codex-exec-auth.sh pragma suppresses anywhere on line
- **Reviewer(s)**: dyn-linter-coverage-output.txt
- **Severity**: important
- **Concern**: The pragma guard uses `/#[[:space:]]*lint-codex-exec-auth:[[:space:]]*ok/` anywhere on the line, so a quoted or earlier substring can suppress a later real dispatch on the same line. A single embedded pragma token can hide an unwired `codex exec` on the same physical line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-coverage-output.txt: Tighten suppression to trailing-comment pragmas only (e.g. require `/[[:space:]]#[[:space:]]*lint-codex-exec-auth:[[:space:]]*ok/` at end-of-line, mirroring `lint-bare-grep-probe.sh`'s `ok([[:space:]]|$)` discipline), and add harness fixtures proving string-embedded pragma tokens do **not** suppress while negotiation-style trailing pragmas (`scripts/run-negotiation-round.sh:115`) still do.


### FINDING_18: test-lint-codex-exec-auth.sh missing multi-env-prefix and long-line fixtures
- **Reviewer(s)**: dyn-linter-coverage-output.txt
- **Severity**: important
- **Concern**: The harness covers single-prefix env lines and a simple trailing pragma, but not the multi-assignment prefix shape (`CODEX_HOME=x OTHER=y codex exec`) or a negotiation-length line with env prefix plus trailing pragma. A regression in the env-prefix strip regex or pragma handling on long dispatched lines would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-coverage-output.txt: Add fixtures for `CODEX_HOME=x OTHER=y codex exec …` (expect fail) and a `run-negotiation-round.sh`-shaped line with `CODEX_HOME="$codex_home" codex exec … # lint-codex-exec-auth: ok …` (expect pass).


### FINDING_2: launch-codex-exec.md contract vs add-dir serialization implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-sweep-output.txt
- **Severity**: important
- **Concern**: `scripts/launch-codex-exec.md` promises preflight failure when `--add-dir` metadata cannot be serialized safely, but `launch-codex-exec.sh` logs a warning and records workdir-only `OUTER_LAUNCHER_ADD_DIRS_JSON`. First launch may grant multiple `--add-dir` paths while retry metadata records only workdir; `collect-agent-results` replay can under-grant on empty-output retry, narrowing the Codex sandbox or changing behavior vs the initial launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align implementation and contract (fail-closed preflight or documented degradation + harness).
  - From cursor-specialist-edge-cases-output.txt: Restore fail-closed preflight behavior or update the contract and add a harness for unserializable add-dir paths.
  - From dyn-auth-sweep-output.txt: Update `scripts/launch-codex-exec.md` to match the implemented degradation (warn + workdir-only fallback), and add a harness case that asserts the degraded metadata shape rather than a preflight bundle.


### FINDING_3: voting-protocol.md launcher prose mismatches runtime dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/shared/voting-protocol.md` names `launch-codex-exec.sh` and `run-external-agent.sh` for Codex voter paths, but `dispatch-code-voters.sh` and `dispatch-plan-voters.sh` route through `launch-review.sh` via waterfall. Operators, doc-driven harnesses, and future edits may target the wrong launcher and outer-retry metadata contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Fix prose to launch-review.sh/waterfall or migrate dispatch-with-waterfall Codex slots.
  - From cursor-specialist-edge-cases-output.txt: Align prose with dispatch-code-voters.sh actual launch-review.sh path.
  - From cursor-specialist-edge-cases-output.txt: Update plan-review composition text to launch-review.sh.


### FINDING_6: test-launch-codex-exec.sh missing auth-prep, login-fallback, and related coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-auth-sweep-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires auth-prep failure handling, login-fallback when `OPENAI_API_KEY` is unset/empty, sandbox mapping, and auth-retry cases, but `test-launch-codex-exec.sh` largely pins env-key mode and only model-args failure. Auth-prep, login-fallback, or auth-retry regressions in `launch-codex-exec.sh` can merge while `make test-launch-codex-exec` stays green; `OPENAI_API_KEY` preference may silently break on `/research`, voter, and judge lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add harness fixtures for auth-prep failure bundle login-mode symlink behavior and auth-retry inner-done promotion per plan.
  - From cursor-specialist-testing-output.txt: Port auth-prep, login-mode, sandbox, and LARCH_EXTERNAL_AUTH_RETRIES fixtures from test-launch-codex-ci.sh / test-launch-review.sh; assert full preflight bundle on auth and model-args failures.
  - From dyn-auth-sweep-output.txt: Add stubbed `external_prepare_codex_auth` failure fixtures for both scripts: assert `launch-codex-exec.sh` writes `.diag`/`.meta`/`.done`, emits non-zero `LAUNCHER_EXIT`, and exits 0; assert `run-negotiation-round.sh` exits 2, emits `RESPONSE_FILE=`, and removes the temp `CODEX_HOME`.
  - From dyn-auth-sweep-output.txt: Add login-mode fixtures with a fake `~/.codex/auth.json`, unset `OPENAI_API_KEY`, and assert argv omits env-key provider overrides while the stub observes a temp `CODEX_HOME` without persisting credential-bearing config after cleanup.


### FINDING_7: test-run-negotiation-round.sh missing auth-prep, login-mode, and config tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-auth-sweep-output.txt
- **Severity**: important
- **Concern**: The negotiation harness lacks login-mode, config-stripping, and auth-prep-failure tests required by the plan. Negotiation can regress to wrong auth mode, leak temp `CODEX_HOME` on auth setup failure, or miss login-mode argv expectations without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add login-fallback, config-copy/stripping, and auth-prep→exit-2 fixtures mirroring check-reviewers / launch-review patterns.
  - From dyn-auth-sweep-output.txt: Add stubbed `external_prepare_codex_auth` failure fixtures for both scripts: assert `launch-codex-exec.sh` writes `.diag`/`.meta`/`.done`, emits non-zero `LAUNCHER_EXIT`, and exits 0; assert `run-negotiation-round.sh` exits 2, emits `RESPONSE_FILE=`, and removes the temp `CODEX_HOME`.
  - From dyn-auth-sweep-output.txt: Add login-mode fixtures with a fake `~/.codex/auth.json`, unset `OPENAI_API_KEY`, and assert argv omits env-key provider overrides while the stub observes a temp `CODEX_HOME` without persisting credential-bearing config after cleanup.


### FINDING_8: test-collect-agent-results.sh C_T1_CODEX_EXEC lacks metadata passthrough assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `C_T1_CODEX_EXEC` only checks `CMD_JSON` non-replay, not metadata passthrough required by plan acceptance. Collector retry could drop `--sandbox`, `--usage-label`, `--timing-task-kind`, or `--add-dir` when re-entering `launch-codex-exec.sh` and still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert stub argv contains replayed sandbox, usage label, timing kind, and add-dir; add fail-closed codex-exec cases to test-collect-agent-retry.sh.


### FINDING_9: No structural pin for launch-codex-exec fences in research/voter/judge references
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-research-structure.sh` has no structural pin for `${CLAUDE_PLUGIN_ROOT:?}/scripts/launch-codex-exec.sh` fences in swept research/voter/judge references. Markdown fences could revert to bare `scripts/launch-codex-exec.sh` or raw `codex exec` in consumer repos without failing structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep pins for ${CLAUDE_PLUGIN_ROOT:?}/scripts/launch-codex-exec.sh and expected output stems in test-research-structure.sh or a sibling harness.


