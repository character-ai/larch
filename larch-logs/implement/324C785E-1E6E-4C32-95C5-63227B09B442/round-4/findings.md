### FINDING_1: Duplicate `json_array_from_args` risks retry metadata drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `json_array_from_args` is duplicated in `scripts/launch-codex-exec.sh` and `scripts/collect-agent-results.sh` for add-dir JSON serialization. A one-sided escaping change can desynchronize retry metadata deserialization and cause `collect-agent-results.sh` to fail closed on empty-output retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move json_array_from_args into lib-external-launcher-common.sh and source it from both scripts

### FINDING_2: Codex judge docs still point at unwired `run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Judge-launch documentation is inconsistent after the Codex judge migration to `launch-codex-exec.sh` with shared auth. `skills/design/references/dialectic-execution.md` (line 177) still instructs `run-external-agent.sh --tool codex`, and `skills/shared/dialectic-protocol.md` (line 142) still lists Codex judges via `run-external-agent.sh`. An orchestrator following either surface can launch Codex judges without `external_prepare_codex_auth`, so `OPENAI_API_KEY` preference does not apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace the bullet with the launch-codex-exec.sh fence from dialectic-protocol.md or remove it and defer solely to the protocol Launching Judges section; add a structural test pin.
  - From cursor-specialist-correctness-output.txt: Update slot 2 to reference launch-codex-exec.sh consistently with the fence and docs inventory.

### FINDING_3: Research telemetry prose still names old Codex launcher
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/research/references/research-phase.md` (line 210) still attributes external Codex lanes to `run-external-agent.sh` directly. This does not change runtime but misleads operators/docs readers about the new launcher surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reword to launch-codex-exec.sh.

### FINDING_4: Multi `--add-dir` metadata loss narrows Codex sandbox on empty-output retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When jq is missing or add-dir JSON serialization fails, `scripts/launch-codex-exec.sh` degrades multi `--add-dir` metadata to workdir-only while the live launch still uses all `ADD_DIR_ARGS`. A later empty-output retry replays only workdir, narrowing Codex sandbox access relative to the first attempt. This can break lint-fix and similar flows that depend on `run_dir` write grants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed when multi add-dir metadata cannot be recorded faithfully, or persist exact add-dir argv for retry.
  - From cursor-specialist-edge-cases-output.txt: Fail closed when multi add-dir cannot be serialized, or persist lossless add-dir sidecar for replay.

### FINDING_5: Lint-fix Codex spend no longer reaches `LARCH_TOKEN_LEDGER`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After launcher routing, Codex lint-fix in `scripts/lint-fix-loop.sh` no longer feeds `LARCH_TOKEN_LEDGER`. Usage is written only to `$run_dir/codex.log.token-record`, so final token reports omit `codex_lint_fix` spend that previously reached the ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: After successful run_codex, call append-token-record.sh on codex.log.token-record (or restore ledger write); re-add LARCH_TOKEN_LEDGER assertion in test-lint-fix-loop case0a.

### FINDING_6: `test-launch-codex-exec.sh` missing plan-required auth-retry and sandbox coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The launcher harness lacks plan-required cases for auth-retry behavior, sandbox argv mapping, and inner `.done` promotion timing. Regressions in `LARCH_EXTERNAL_AUTH_RETRIES` handling, `--sandbox` mapping, or premature `.inner.done` promotion could ship undetected; only happy-path promotion is currently asserted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stub-driven auth-retry fixture (mirror test-launch-review.sh) and read-only vs full-auto argv assertions.
  - From cursor-specialist-plan-fidelity-output.txt: Add a stub codex that fails auth on attempt 1 and succeeds on attempt 2; assert .inner.done is not promoted until after the loop completes.

### FINDING_7: `test-run-negotiation-round.sh` missing config copy and credential-stripping assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required assertions for temp `config.toml` copy and credential stripping are absent. Negotiation could regress to launching with unstripped `api_key` lines in temp `CODEX_HOME` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Log and assert temp config.toml contents in env-key and login modes like test-launch-review.sh.

### FINDING_8: `test-lint-fix-loop.sh` missing add-dir and usage-label routing assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required assertions for `--add-dir "$run_dir"` routing and `codex_lint_fix` usage labeling are not implemented. `run_codex` could drop add-dir paths or mislabel usage while the harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Make stub log argv; assert both add-dir paths and codex_lint_fix usage label on invocation.

### FINDING_9: Research structural pin covers only one Codex lane stem
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-research-structure.sh` pins only the arch lane output stem. Three other research lanes could remain on unwired Codex exec while check 10 still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert all four codex-research-*-output.txt stems in research-phase.md fences.

### FINDING_10: `test-launch-codex-exec.md` misstates auth-prep exit contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness contract misstates `LAUNCHER_EXIT` on auth-prep failure. Operators following the `.md` expect `LAUNCHER_EXIT=2`, but implementation emits `AUTH_PREP_RC` (often 1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document LAUNCHER_EXIT mirrors auth-prep exit code; align test description with implementation.

### FINDING_11: `lint-codex-exec-auth.sh` markdown fence scanner breaks on nested fences
- **Reviewer(s)**: dyn-linter-fidelity-output.txt
- **Severity**: important
- **Concern**: The markdown scanner at `scripts/lint-codex-exec-auth.sh:205-212` uses a single `in_fence` flag with no nesting depth. Any line inside an open `bash`/`sh`/`shell` fence that matches a bare closing fence clears `in_fence`, even when that close belongs to nested markdown/heredoc content still inside the outer fence. Later `codex exec` lines in the same outer block are then skipped, so unwired dispatch in skill/reference fences can slip through undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-fidelity-output.txt: Track fence depth (increment on open, decrement on bare close) or only treat a closing fence as valid when depth returns to zero; add a harness fixture with a bash fence containing an inner ` ``` ` example and a trailing raw `codex exec`.

### FINDING_12: `lint-codex-exec-auth.sh` basename-only allowlist is too broad
- **Reviewer(s)**: dyn-linter-fidelity-output.txt
- **Severity**: important
- **Concern**: Allowlisting is basename-only (`basename "$rel"`) before the per-line scan. Under the in-scope glob `skills/*/scripts/*.sh`, any file named `launch-codex-exec.sh`, `launch-review.sh`, etc. is exempt for the whole file, not just canonical `scripts/` launchers. A future or mistaken copy under `skills/*/scripts/` would be fully ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-fidelity-output.txt: Restrict basename allowlisting to `scripts/*.sh` (top-level only), or require an exact relative-path allowlist for `skills/review-and-fix/scripts/review-and-fix.sh`; keep pragma/line rules for everything else.

### FINDING_13: `lint-codex-exec-auth.sh` misses variable-qualified `codex exec` spellings
- **Reviewer(s)**: dyn-linter-fidelity-output.txt
- **Severity**: important
- **Concern**: Detection is limited to the contiguous literal `codex[[:space:]]+exec`. Static lines that dispatch via a variable command word (`"$CODEX_BIN" exec …`, `"${CODEX_BIN:-codex}" exec` when `codex` is not immediately adjacent to `exec`, `exec "$codex_bin"`, etc.) never match, so unwired call sites can evade the guard while still running Codex. Path-qualified `/path/to/codex exec` is caught; variable-qualified forms are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-linter-fidelity-output.txt: Extend the matcher (or add a second rule) for common alternate spellings such as `"$…" exec` / `exec` immediately after a Codex-path variable when paired with Codex flags (`--full-auto`, `--sandbox`, `-C`, `--output-last-message`), and pin bypass cases in `scripts/test-lint-codex-exec-auth.sh`.

### FINDING_14: `launch-codex-exec.sh` lacks workdir/add-dir path canonicalization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--workdir`/`--add-dir` inputs at `scripts/launch-codex-exec.sh:119-187` lack `validate_meta_scalar_path` symlink and `..` rejection before `codex exec` and metadata serialization. Full-auto lanes can be aimed at symlinked or out-of-scope directories, widening write grants beyond `launch-review` hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse launch-review add-dir canonicalization for all workdir/add-dir inputs before dispatch and meta write

### FINDING_15: `collect-agent-results.sh` replays outer-retry metadata without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Outer-retry replays sandbox and add-dir JSON from `.meta` without path validation or `CMD_JSON` cross-check. Same-UID `.meta` tamper could escalate a read-only voter retry to full-auto or add arbitrary `--add-dir` paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate add-dir scalars and bind OUTER_LAUNCHER_* fields to CMD_JSON or signed metadata

### FINDING_16: [OUT_OF_SCOPE] Debate-phase Codex still uses pre-wired `launch-review.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Debate-phase Codex in `skills/design/references/dialectic-execution.md:55-62` still uses `launch-review.sh`, which was already pre-wired for auth. Not introduced by this PR; debate paths were out of the six-site sweep. No change required for #3475 acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Generic `run-external-agent.sh` Codex path remains unwired for env-key auth
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-linter-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-external-agent.sh` remains a generic `"$@"` wrapper with no `external_prepare_codex_auth` wiring. Callers invoking Codex through `run-external-agent.sh` outside allowlisted launchers bypass `OPENAI_API_KEY` preference and shared auth helpers. Matches plan intent that the launcher layer owns auth, but the surface still does not enforce env-key auth itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Follow-up sweep per OOS issue; not required in this PR.
  - From cursor-specialist-security-output.txt: Out of scope; future sweep or linter extension
  - From dyn-linter-fidelity-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] No focused unit test for codex-exec outer-meta helper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no direct unit test for the codex-exec outer-meta helper in `scripts/test-lib-external-launcher-common.sh`. Metadata serialization bugs might only surface in full collector retry integration tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: add focused cases to test-lib-external-launcher-common.sh per plan.

### FINDING_19: [OUT_OF_SCOPE] `lint-codex-exec-auth.sh` scan roots omit hooks/agents/.github
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The linter misses `hooks`, `agents`, and `.github` Codex exec sites. Future unwired exec in unscanned trees would not fail `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend scan roots or document explicit exclusion

---

**Subsumed without separate blocks** (positive validation or intentional scope, not actionable merge targets):

- FINDING_25: env-prefix skip regex behavior is correct and covered by tests
- FINDING_26: pragma suppression behavior is correct and covered by tests
- FINDING_27: prose/backtick `codex exec` mentions outside fenced shell blocks are intentionally out of scanner scope
