Normalized aggregator output from the supplied reviewer findings:

### FINDING_1: collect-agent-results.sh codex-exec retry logic duplicated across paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-retry-contract-output.txt
- **Severity**: important
- **Concern**: The codex-exec outer-retry contract is implemented in parallel copies: `parse_retry_meta`, an inline empty-output meta parser, `launch_outer_retry_or_mark`, and the main retry loop. Empty-output retries duplicate launch logic instead of calling `launch_outer_retry_or_mark`, and inline parsing can drift from `parse_retry_meta`. Future `OUTER_LAUNCHER_*` keys or validation fixes applied in one path may not reach the others, causing silent retry misconfiguration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: After parse_retry_meta, call launch_outer_retry_or_mark and delete the inlined duplicate block.
  - From cursor-specialist-structure-output.txt: Replace inline meta parsing with parse_retry_meta "$META".
  - From dyn-retry-contract-output.txt: Have the empty-output loop call `parse_retry_meta "$META"` instead of inlining the parser, and extract a shared `build_codex_exec_outer_retry_args` helper used by both `launch_outer_retry_or_mark` and the main loop so validation and argv reconstruction cannot diverge again.

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

### FINDING_4: voting-protocol.md direct-fence vs dispatch-script routing undocumented
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The generic Codex voter fence implies `dispatch-plan-voters` mirrors it, but plan voters use `launch-review.sh`. Direct copies of the fence can diverge from automated `/design` and `/review` voter dispatch, which still use `launch-review` auth/retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split documentation: direct fence vs dispatch-script routing.

### FINDING_5: research lanes pass huge prompts via --prompt argv
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Research lanes pass large `RESEARCH_PROMPT_*` strings via `--prompt` argv instead of `--prompt-file`. Very large prompts can fail at shell/Codex argv limits while validation and negotiation paths succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use --prompt-file for lane prompts like the validation lane does.

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

### FINDING_12: Collector retry replays add-dir paths without path safety validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Codex-exec outer retry replays add-dir paths from `OUTER_LAUNCHER_ADD_DIRS_JSON` with only array-type validation. Same-UID tampering can append a malicious line to a session `.meta` file; on empty-output retry Codex full-auto may receive extra `--add-dir` grants outside the intended workspace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each JSON add-dir element (reject .. and symlinks, canonicalize paths, optionally constrain under OUTER_LAUNCHER_WORKDIR) before appending to _codex_exec_retry_args.

### FINDING_13: launch-codex-exec.sh passes --add-dir without canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--add-dir` values are passed through to `codex exec` without symlink or `..` canonicalization checks present in `launch-review.sh`. An orchestrator-supplied symlinked add-dir could expand Codex full-auto write access beyond the intended directory on research/lint-fix/voter lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Apply launch-review-style _codex_canonical_existing_dir validation to every --add-dir before dispatch.

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

### FINDING_16: run-negotiation-round.sh lacks auth-retry loop
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The negotiation Codex path has no auth-retry loop unlike `launch-codex-exec.sh`. Transient `OPENAI_API_KEY`/auth startup failures fail negotiation immediately without the retries other swept paths get.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document intentional asymmetry or add shared auth-retry wrapper.

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

### OOS_1: [OUT_OF_SCOPE] run-negotiation-round.sh inline Codex auth duplicates shared launcher patterns
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inline Codex auth duplicates shared launcher patterns. Plan-intentional; future auth contract changes need manual sync in negotiation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared ephemeral-home/auth helper in a follow-up.

### OOS_2: [OUT_OF_SCOPE] run-external-agent.sh and unwired codex exec paths remain outside sweep
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-auth-sweep-output.txt, dyn-retry-contract-output.txt
- **Severity**: nit
- **Concern**: Generic wrapper and other unwired `codex exec` paths outside this PR scope still bypass or partially bypass shared auth; follow-up sweep still needed per #3475 OOS. `/research` lanes are largely addressed via `launch-codex-exec.sh` wrapping `run-external-agent.sh`; negotiation remains a deliberate inline site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Wire remaining call sites per #3475 OOS.
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep only if centralizing all exec inside one launcher is desired.
  - From dyn-retry-contract-output.txt: This PR does not claim to fix that path.

### OOS_3: [OUT_OF_SCOPE] launch-codex-exec.sh vs launch-codex-ci.sh auth/retry consolidation deferred
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Heavy overlap with `launch-codex-ci.sh` auth/retry stack. Plan excluded consolidating existing launchers onto `launch-codex-exec.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Defer consolidation to a later refactor PR.

### OOS_4: [OUT_OF_SCOPE] lint-codex-exec-auth.sh scanner scope excludes hooks/agents/docs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Linter scope excludes `hooks/`, `agents/`, and docs/ markdown fences. A future unwired `codex exec` added outside scanned paths would bypass `make lint` until manually discovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend scanner scope or document the explicit allowlist of directories that must remain clean by convention.

### OOS_5: [OUT_OF_SCOPE] lint-fix-loop.sh launcher env override lacks path guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH` env override has no canonical launcher-path guard. Same-UID env injection during `/implement` CI-fix could redirect Codex dispatch to an arbitrary executable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Resolve and verify the launcher path against $SCRIPT_DIR/launch-codex-exec.sh (realpath + basename check), or ignore the override outside test harnesses.

### OOS_6: [OUT_OF_SCOPE] research SKILL.md still describes raw codex exec launches
- **Reviewer(s)**: dyn-auth-sweep-output.txt, dyn-linter-coverage-output.txt
- **Severity**: nit
- **Concern**: `skills/research/SKILL.md:53` still describes `/research` Codex lanes as direct `codex exec --full-auto -C "$PWD"` launches while references route through `launch-codex-exec.sh`. Skill entrypoint prose can mislead readers about env-key auth coverage; markdown scanner ignores non-fence prose.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] run-negotiation-round.sh serial-lock failure branch effectively dead
- **Reviewer(s)**: dyn-auth-sweep-output.txt
- **Severity**: nit
- **Concern**: `run-negotiation-round.sh` treats serial-lock acquisition failure as exit 2 with cleanup, but `external_serial_lock_acquire` fail-opens with `return 0` after exhausting tries. That branch is effectively dead on Darwin today and predates this PR.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] jq-less multi-add-dir retry limitation documented but unresolved
- **Reviewer(s)**: dyn-retry-contract-output.txt
- **Severity**: latent
- **Concern**: When `jq` is absent at collector retry time, both launch sites fall back to a single `--add-dir "$META_OUTER_LAUNCHER_WORKDIR"`, even if `.meta` records multiple grants. Multi-dir callers can still lose sandbox grants on retry in jq-less environments.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] dispatch voter scripts use launch-review.sh not launch-codex-exec.sh
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `dispatch-plan-voters.sh` / `dispatch-code-voters.sh` still use `launch-review.sh` not `launch-codex-exec.sh`. Auth already covered; only `voting-protocol` prose needed updating unless consolidating launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track as follow-up doc alignment or migrate dispatch path in a separate change.
  - From cursor-specialist-edge-cases-output.txt: No functional change required unless consolidating launchers.

---

**Merge summary**: 42 raw inputs → 18 in-scope findings + 9 OOS blocks. Subsumed without separate output: FINDING_42 (verified-OK attestation, not an actionable defect). FINDING_17/28 doc/runtime voter mismatch folded into FINDING_3. FINDING_37 folded into OOS_8 (same jq-less limitation, explicitly OOS-tagged in source). FINDING_35 informational note folded into OOS_2.
