### FINDING_1: `test-lint-fix-loop.sh` harness still pins removed Codex wiring
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The lint-fix-loop harness still requires removed `run_codex --stderr-sink` wiring and asserts stale `codex.events.jsonl` / `codex.wrapper.log` artifacts while implementation now routes through `launch-codex-exec.sh`. Codex cases stub `RUN_EXTERNAL_AGENT_SH` but `run_codex` calls `launch-codex-exec.sh`, so behavioral cases no longer control Codex argv/events. `make test-lint-fix-loop` fails immediately and plan-mandated `LAUNCHER_EXIT` / launcher-routing coverage is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Migrate harness to `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH` stub, `codex.log.*` artifacts, and `LAUNCHER_EXIT` parsing per plan.
  - From cursor-specialist-correctness-output.txt: Migrate harness to launch-codex-exec stub per plan; drop stderr-sink pin; assert new sidecars and `LAUNCHER_EXIT` parsing.
  - From cursor-specialist-testing-output.txt: Remove stale pin; migrate Codex cases to launch-codex-exec stub and new artifact paths.
  - From cursor-specialist-testing-output.txt: Stub `LINT_FIX_LOOP_LAUNCH_CODEX_EXEC_SH`; retarget to `codex.log.events.jsonl` and `codex.log.sidecar`.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-pinned fixtures to each harness and update sibling harness `.md` contracts.

### FINDING_2: Missing / stale collector outer-retry regression coverage for `launch-codex-exec`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Collector `launch-codex-exec` outer-retry behavior lacks adequate harness coverage. `test-collect-agent-retry.sh` case-s2 still expects a stale fail-closed string after collector message changes; there is no positive fixture asserting collector re-invokes `launch-codex-exec.sh` with preserved sandbox/add-dir metadata. `test-collect-agent-results.sh` also lacks the planned codex-exec outer-retry fixture, so metadata validation / `CMD_JSON` fallback regressions can reach `/research` collection paths undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add launch-codex-exec retry fixture; update expected error strings; assert launcher re-entry not raw codex exec.
  - From cursor-specialist-correctness-output.txt: Add fixture asserting collector re-invokes `launch-codex-exec.sh` with preserved sandbox/add-dir metadata.
  - From cursor-specialist-testing-output.txt: Update expected reason; add positive launch-codex-exec outer-retry fixture.
  - From cursor-specialist-testing-output.txt: Add happy-path and invalid-metadata fixtures to `test-collect-agent-retry.sh`.
  - From cursor-specialist-edge-cases-output.txt: Add planned codex-exec outer-retry harness fixture.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-pinned fixtures to each harness and update sibling harness `.md` contracts.

### FINDING_3: `test-run-negotiation-round.sh` missing plan-mandated auth/cleanup coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Negotiation Codex auth wiring (`OPENAI_API_KEY` modes, login/trust, temp `CODEX_HOME` cleanup, auth-prep exit 2) is not covered by the harness per plan acceptance criteria, so negotiation auth regressions can ship without automated detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add stub-based auth mode and cleanup assertions mirroring check-reviewers patterns.
  - From cursor-specialist-testing-output.txt: Extend stub logging and add env-key/login/auth-failure fixtures.
  - From cursor-specialist-plan-fidelity-output.txt: Add the plan-pinned fixtures to each harness and update sibling harness `.md` contracts.

### FINDING_4: `scripts/launch-codex-exec.md` contract is a stub vs implemented launcher
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The sibling contract documents almost none of the implemented launcher surface (flags, preflight bundle, inner sentinel, outer meta, harness pointer), so future auth/retry/collector contract changes lack an authoritative doc anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Expand `.md` to document flags, preflight bundle, inner sentinel, outer meta, and harness pointer.

### FINDING_5: `scripts/lint-fix-loop.md` `run_codex` section describes pre-refactor path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run_codex` contract prose still describes the old direct `codex exec` dispatch model and artifact names instead of `launch-codex-exec` routing and new sidecar names, misleading operators/debuggers during CI-fix failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rewrite `run_codex` section for launch-codex-exec routing and new sidecar names.
  - From cursor-specialist-plan-fidelity-output.txt: Author the four sibling `.md` files per plan specifications.

### FINDING_6: `scripts/run-negotiation-round.md` exit table omits Codex auth-setup failure on exit 2
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Exit-code documentation omits Codex auth-setup failure on exit 2, contradicting `skills/shared/external-reviewers.md` and implemented `run-negotiation-round.sh` behavior; wrappers may misclassify auth failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update exit table and add Codex auth contract subsection.
  - From cursor-specialist-edge-cases-output.txt: Update `run-negotiation-round.md` exit table to match implementation.
  - From cursor-specialist-plan-fidelity-output.txt: Author the four sibling `.md` files per plan specifications.

### FINDING_7: `scripts/lib-external-launcher-common.md` stale helper inventory / missing Codex auth authority
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Helper inventory is stale; `external_launcher_append_codex_exec_outer_meta` and the canonical merged Codex auth inventory are undocumented. Acceptance criterion requiring identical inventory across docs fails; outer-meta and collector-retry contract for `launch-codex-exec.sh` lacks lib authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Refresh wired call sites and document codex-exec outer-meta helper and `mirror_quota` callers.
  - From cursor-specialist-plan-fidelity-output.txt: Update `lib-external-launcher-common.md` with verbatim inventory, outer-meta records, and collector replay semantics.
  - From cursor-specialist-plan-fidelity-output.txt: Author the four sibling `.md` files per plan specifications.

### FINDING_8: `scripts/collect-agent-results.md` missing codex-exec outer-retry contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Outer-retry docs cover only the `launch-review.sh` path. Maintainers may not know `OUTER_LAUNCHER_KIND=codex-exec` fields, replay semantics, or retry routing / `LAUNCHER_EXIT` grammar for the new branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document launch-codex-exec allowlist and required meta validation branch.
  - From cursor-specialist-plan-fidelity-output.txt: Author the four sibling `.md` files per plan specifications.

### FINDING_9: `scripts/test-launch-codex-exec.sh` implements only subset of plan harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: New launcher harness is much thinner than plan acceptance criteria: auth-prep failure, env-key/login modes, preflight bundles, inner.done promotion, outer meta, add-dir round-trip, retry sentinel, and temp `CODEX_HOME` leak cases are largely unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend harness with env-key/login, preflight bundle, retry sentinel, and leak cases.
  - From cursor-specialist-testing-output.txt: Expand harness to match `test-launch-codex-ci.sh` depth; document in `.md` sibling.
  - From cursor-specialist-plan-fidelity-output.txt: Expand harness and `test-launch-codex-exec.md` to the full case list in the plan testing strategy.

### FINDING_10: Unused `lib-codex-launcher-common.sh` import in `lint-fix-loop.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: After `run_codex` refactor, `lint-fix-loop.sh` still sources unused `lib-codex-launcher-common.sh`, obscuring actual launcher dependencies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused `lib-codex-launcher-common` source line.

### FINDING_11: `run_codex()` missing fail-closed `LAUNCHER_EXIT` fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_codex()` defaults missing `LAUNCHER_EXIT` to `launcher_rc` instead of fail-closed `1`. If a stub or broken launcher exits 0 without `LAUNCHER_EXIT`, lint-fix-loop treats Codex repair as success and may ship unfixed CI failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore `parsed_exit=1` fallback when `LAUNCHER_EXIT` is absent; add harness case for wrapper exit 0 without `LAUNCHER_EXIT`.
  - From cursor-specialist-edge-cases-output.txt: Default to failure when `LAUNCHER_EXIT` line is absent.

### FINDING_12: `launch-codex-exec.sh` silently writes empty `OUTER_LAUNCHER_ADD_DIRS_JSON` when `jq` absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-jq-retry-absent-output.txt
- **Severity**: important
- **Concern**: When `jq` is missing at metadata-write time, `_add_dirs_json` is forced to `[]` even though `ADD_DIRS` may contain multiple normalized paths (e.g. lint-fix `run_dir` + repo root). That lossy metadata is persisted as `OUTER_LAUNCHER_ADD_DIRS_JSON`, so retry cannot distinguish “no add-dirs” from “jq was absent when serializing,” and collector retry may drop extra grants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Persist add-dir list without jq or fail closed when jq is unavailable and add-dir count > 1.
  - From cursor-specialist-testing-output.txt: Add add-dir round-trip harness; non-jq JSON fallback.
  - From cursor-specialist-edge-cases-output.txt: Serialize add-dirs without jq or fail closed when jq missing and `ADD_DIRS>1`; test retry argv.
  - From dyn-jq-retry-absent-output.txt: Do not silently write `[]` when `jq` is absent and `ADD_DIRS` is non-empty; either fail closed before launch, or persist add-dirs without `jq` (e.g. newline sidecar / repeated `OUTER_LAUNCHER_ADD_DIR_N=` keys) so retry metadata is faithful.

### FINDING_13: Collector codex-exec retry mishandles missing `jq` or lossy `[]` add-dir metadata
- **Reviewer(s)**: dyn-jq-retry-absent-output.txt
- **Severity**: important
- **Concern**: On empty-output retry, the `launch-codex-exec.sh` path validates `META_OUTER_LAUNCHER_ADD_DIRS_JSON` with `jq`. If `jq` is absent at retry time, validation fails and `mark_retry_metadata_invalid` drops the retry entirely. When `jq` is present and metadata is `[]` from write-time fallback, validation passes but no `--add-dir` flags are forwarded beyond workdir, dropping extra grants such as lint-fix `run_dir` outside repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-jq-retry-absent-output.txt: Treat a missing/unparseable `jq` the same as an empty array for codex-exec retries (skip add-dir reconstruction and still launch the outer launcher so its workdir default applies), and/or reject launch at write time when add-dir metadata cannot be serialized; when metadata is `[]` but `WORKDIR` is known, explicitly pass `--add-dir "$META_OUTER_LAUNCHER_WORKDIR"` before launch so behavior matches the documented default even without relying on launcher internals.

### FINDING_14: `lint-fix-loop.sh` passes large prompt via `--prompt` instead of `--prompt-file`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_codex` passes `--prompt` with full `prompt_body` despite `prompt.md` on disk. Large CI logs (~60KB+) can exceed `ARG_MAX` and abort Codex dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use `--prompt-file "$run_dir/prompt.md"` instead of `--prompt "$prompt_body"`.

### FINDING_15: `lint-codex-exec-auth.sh` shell scanner bypassed by backslash continuation
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: Shell scanner matches `codex[[:space:]]+exec` only within a single physical line, so `codex \` / `exec …` continuations bypass the guard while remaining idiomatic in allowlisted launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: Teach both scanners to join continuation lines before matching (track a trailing `\`, concatenate the next line), or reject any line ending in `codex[[:space:]]*\\` and any continuation line starting with `exec`. Add a harness fixture with a two-line `codex \` / `exec` dispatch in `scripts/test-lint-codex-exec-auth.sh`.

### FINDING_16: `lint-codex-exec-auth.sh` env-prefix strip false-negative for `B=codex exec`
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: Leading-env strip treats `B=codex` as a complete assignment, reducing `B=codex exec …` to `exec --full-auto …` and missing `codex exec` detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: Only strip env prefixes when the value cannot be the command name `codex` (e.g. require `=` value not equal to `codex`, or strip only known launcher prefixes like `CODEX_HOME=`), or run the `codex exec` match on the original line as well as the stripped line. Pin `B=codex exec` (and `A=1 B=codex exec`) as failing fixtures in `scripts/test-lint-codex-exec-auth.sh`.

### FINDING_17: `lint-codex-exec-auth.sh` markdown fence scanner bypassed by continuation lines
- **Reviewer(s)**: dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: Markdown fence scanner has the same per-line `codex[[:space:]]+exec` limitation, so two-line `codex \` / `exec` fences in `skills/**/*.md` are invisible to the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-bypass-output.txt: Apply the same continuation-aware pre-pass in `scan_markdown_file` and add a markdown-fence bypass fixture to the harness (the plan and `docs/linting.md:508` claim a markdown-fence failure case, but `scripts/test-lint-codex-exec-auth.sh` has none).

### FINDING_18: `test-lint-codex-exec-auth.sh` harness far narrower than plan contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-linter-bypass-output.txt
- **Severity**: important
- **Concern**: Linter harness omits plan-specified fixtures: markdown fences, env-assignment skip shapes, helper-plus-raw-exec, continuation bypasses, `CODEX_HOME=… codex exec` outside allowlist, and documented negative cases. Bypass regressions can land without CI signal despite linter being the mechanical enforcement layer for #3475.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add TMPROOT fixtures per plan case; expand `.md` contract.
  - From cursor-specialist-plan-fidelity-output.txt: Add missing fixtures per `scripts/test-lint-codex-exec-auth.md` plan contract.
  - From dyn-linter-bypass-output.txt: Extend `scripts/test-lint-codex-exec-auth.sh` with explicit failing fixtures for each bypass shape and passing fixtures for the documented negative cases; update `scripts/test-lint-codex-exec-auth.md` to list them.

### FINDING_19: `launch-codex-exec.sh` lacks `--add-dir` path validation / containment checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--add-dir` paths are passed to `codex exec` without directory validation or containment checks unlike `launch-review.sh` hardening. A buggy or malicious caller passing `--add-dir /tmp` or `$HOME/.ssh` in full-auto mode can grant Codex write access outside the intended workspace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Mirror launch-review.sh add-dir validation: reject `..`, require canonical existing directories, and optionally require paths under `--workdir` or session root.

### FINDING_20: Collector outer-retry replays `OUTER_LAUNCHER_ADD_DIRS_JSON` without per-path safety checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Outer-retry for `launch-codex-exec` replays `OUTER_LAUNCHER_ADD_DIRS_JSON` without per-path safety checks. Same-UID tampering with a session `.meta` sidecar could inject arbitrary add-dir paths on empty-output retry, widening Codex write grants in full-auto lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate each jq-decoded add-dir with `validate_meta_scalar_path`, reject `..`, require existing directories, and bind to `META_OUTER_LAUNCHER_WORKDIR` before retry launch.

### FINDING_21: `launch-codex-exec.sh` pre-auth failures may exit without collector preflight bundle
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-auth failures (prompt sidecar write, `mktemp`) exit under `set -e` without collector bundle. Background research/voter lanes may hang `wait-for-reviewers` or leave inconsistent sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Route early failures through `write_preflight_bundle`.

### FINDING_22: Research lanes use `--prompt` not `--prompt-file` for large prompts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Research lanes use `--prompt` not `--prompt-file` for large lane prompts. Long `RESEARCH_QUESTION` can exceed argv limits and fail lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write per-lane prompt file and use `--prompt-file`.

### FINDING_23: `scripts/test-launch-codex-exec.md` contract stub offers no regression pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness contract stub enumerates no cases or exit codes, so future harness deletion/shrinkage is not caught by doc-sync unlike peer harness `.md` files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Enumerate cases and exit codes like peer harness `.md` files.

### FINDING_24: Stale comment in `validation-phase.md` references old temp-file pattern
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Stale comment references temp-file agent-model-args pattern after Codex fence moved to `launch-codex-exec.sh`. Orchestrators following the comment may reintroduce raw `codex exec` wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Replace comment to state `launch-codex-exec.sh` owns model-args and auth.

### FINDING_25: `dialectic-protocol.md` timing prose stale after judge fence uses launcher
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Timing note still claims Codex judge emits no timing rows after judge fence uses `launch-codex-exec.sh`. Operators may believe judge timing is still unmeasured when codex-exec rows are now recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update timing prose or pass an explicit codex-judge timing-task-kind if intended.

### FINDING_26: `scripts/lib-timing-kinds.md` not updated for changed runtime surfaces
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan-mandated sibling contract `lib-timing-kinds.md` was not updated alongside changed runtime surfaces for retry routing and launcher timing semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Author the four sibling `.md` files per plan specifications.

### FINDING_27: [OUT_OF_SCOPE] `scripts/run-external-agent.sh` remains generic codex dispatcher without shared auth
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-linter-bypass-output.txt
- **Severity**: latent
- **Concern**: Generic external-agent wrapper still dispatches raw `codex exec` without env-key auth wiring; auth remains caller responsibility and is outside this PR’s six swept surfaces. Future callers bypassing launchers miss `OPENAI_API_KEY` preference unless caught by linter patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Follow-up sweep if centralizing auth at wrapper is desired.
  - From cursor-specialist-correctness-output.txt: Follow-up sweep per OOS issue #3475.
  - From cursor-specialist-testing-output.txt: Follow-up sweep per OOS; out of this PR scope.
  - From cursor-specialist-security-output.txt: No change required unless consolidating all codex dispatch through one launcher (explicitly out of scope).
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep per original OOS issue.
  - From dyn-linter-bypass-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Auth setup duplicated across launch-codex-exec, launch-codex-ci, run-negotiation-round
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Auth setup is intentionally duplicated per plan across multiple launchers, increasing long-term parity maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider shared prepare-codex-home helper in a future refactor.

### FINDING_29: [OUT_OF_SCOPE] Negotiation auth harness gap noted as follow-up
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Negotiation auth wiring lacks planned env-key/login/cleanup harness coverage as an explicit out-of-scope follow-up distinct from in-scope plan acceptance on the same harness file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add planned auth-mode and temp `CODEX_HOME` cleanup assertions.

### FINDING_30: [OUT_OF_SCOPE] No structural pin for launch-codex-exec fences in research references
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No research-specific structural pin for `launch-codex-exec` fences; fence could regress to raw `codex exec` without research-specific harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rely on lint-codex-exec-auth or add research-structure pin.

### FINDING_31: [OUT_OF_SCOPE] `collect-agent-results.md` omits new `jq` dependency for codex-exec outer retry
- **Reviewer(s)**: dyn-jq-retry-absent-output.txt
- **Severity**: latent
- **Concern**: Contract still says outer-launcher branch “does not deserialize `CMD_JSON`” and implies `jq` is only needed on inner `CMD_JSON` path, but `OUTER_LAUNCHER_KIND=codex-exec` now hard-depends on `jq` for `OUTER_LAUNCHER_ADD_DIRS_JSON`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-jq-retry-absent-output.txt: Address the concern above.
