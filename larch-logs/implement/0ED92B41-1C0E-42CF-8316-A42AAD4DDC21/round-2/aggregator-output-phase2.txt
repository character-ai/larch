Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; verbatim revision bullets per slot).

### FINDING_1: Health-class dispatch failures return `failed` instead of `main-agent-required`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: important
- **Concern**: When codex and/or cursor dispatch both fail, `run_lint_fix` branches on `agents.classify_launch_failure()` and returns `FixOutcome(status="failed", failure_reason="dispatch-failed")` if any attempt has `failure_class == "health"`. Bash `lint-fix-loop.sh` (#3207, lines 414–429) always emits `main-agent-required` with `FAILURE_REASON=dispatch-failed` for the same case. `_handle_fix_outcome` maps `failed` → loop status `dispatch-failed`, and `escalate()` maps that to `Outcome.TRANSIENT` instead of `Outcome.NEEDS_USER_INPUT`, so infra/auth/empty-output health-class failures take transient retry semantics instead of the main-agent / recovery-waterfall path used in production bash. `classify_launch_failure` on the all-failed dispatch path only feeds this erroneous branch; bash does not classify local dispatch failures for status selection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the health branch; always return main-agent-required with failure_reason=dispatch-failed when both present tiers fail; add a unit test stubbing classify_launch_failure to health.
  - From cursor-specialist-correctness-output.txt: Remove health branch; always return main-agent-required with failure_reason=dispatch-failed when present tiers exhaust; test NEEDS_USER_INPUT.
  - From cursor-specialist-correctness-output.txt: Drop classification on all-failed dispatch or use only for logging; align FixOutcome with bash.
  - From cursor-specialist-testing-output.txt: Remove the health-only branch or emit main-agent-required; add a unit test with a health-classified stub failure asserting NEEDS_USER_INPUT end-to-end.
  - From cursor-specialist-edge-cases-output.txt: Always return main-agent-required with failure_reason=dispatch-failed when both tiers fail; use classify_launch_failure for logging only unless product explicitly wants health→TRANSIENT.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the health-only branch; always return main-agent-required with failure_reason=dispatch-failed when both present tiers fail
  - From dyn-parity-drift-output.txt: Remove the health-only branch and always return `FixOutcome(status="main-agent-required", failure_reason="dispatch-failed", …)` when `coder_tool is None` and at least one external was present, matching `lint-fix-loop.sh`; keep `classify_launch_failure` only for logging/tests if needed, not for status selection.

### FINDING_2: `_compose_prompt` omits submodule-prohibition parity from bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_compose_prompt` omits `emit_submodule_prohibition` parity from `lib-submodule-prohibition.sh` and shortens final-line contract text. Fixer prompts lack bulleted submodule guardrails and `.git`/`.gitmodules` prohibition present in bash `compose_prompt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Port emit_submodule_prohibition text verbatim into _compose_prompt or shell out to the existing bash helper.

### FINDING_3: `run_lint_fix` is an oversized god function with duplicated post-dispatch logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` (~325 lines) duplicates forbidden-revert/violation blocks across branches, making parity auditing, CI-fixer extension, and isolated unit testing of post-dispatch paths difficult.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _finalize_dispatch_delta(...) for forbidden revert, delta capture, and commit; keep run_lint_fix as thin orchestration.

### FINDING_4: `checks.py` monolith should split after Phase 4 acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: ~1421-line module with ~25 private helpers and four embedded `bash -c` wrappers exceeds sibling `python/` modules; future phases (CI fixer) will increase merge-conflict and review cost in one file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: After Phase 4 acceptance, split dispatch helpers into a flat sibling module (e.g. checks_dispatch.py).

### FINDING_5: Missing forbidden-path and dispatch regression tests required by plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan testing strategy and bash `test-lint-fix-loop.sh` case 1b require forbidden-path reversion + violation coverage; Python only tests `forbidden-path-reset-failed` today. Gaps include committed forbidden submodule delta after successful reset, working-tree forbidden-path violation, and (per structure reviewer) health-class dispatch and related scenarios—regressions in dispatch escalation or forbidden-path handling can ship without pytest signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add stubbed scenarios for health-class failure, .gitmodules working-tree revert, and committed forbidden delta per plan testing strategy.
  - From cursor-specialist-testing-output.txt: Add StubRunner test: dispatch moves HEAD, committed diff touches forbidden path, reset succeeds, assert failed and forbidden-path-violation.
  - From cursor-specialist-plan-fidelity-output.txt: Add stub-Runner test asserting failure_reason=forbidden-path-violation after forbidden delta is reverted

### FINDING_6: Cursor dispatch test lacks full `run-external-agent.sh` argv parity
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires cursor leaf argv parity with `lint-fix-loop.sh:290-296` (unlike codex, which has fuller assertions). Current cursor test checks wrap/cwd and partial argv only; wrapper flag regressions (`--capture-stdout`, timeout, tool routing) could ship while codex parity test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend cursor test to find run-external-agent.sh argv and assert --tool cursor, --timeout 1800, --capture-stdout, and leaf cursor agent shape per lint-fix-loop.sh:290-296.
  - From cursor-specialist-plan-fidelity-output.txt: Extend cursor test to assert full run-external-agent.sh wrapper argv and no launch-*-ci.sh

### FINDING_7: Missing `run_relevant_checks` edge-case tests from plan
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed `run_relevant_checks` edge cases (broken symlink, agent-lint-missing warn, post-check-only coverage) have no tests. Parser/coverage regressions for partial runs or missing agent-lint would not fail `py-test` until production logs mis-classify failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add three focused tmp_path tests with canned log bodies and symlink fixture.

### FINDING_8: Check-first loop lacks inline redaction fallback when only `raw_log_path` is set
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: In `run_check_fix_loop` check-first branch, a failing `ChecksResult` with non-empty `raw_log_path` but `redacted_log_path=None` terminates with `dispatch-failed` without on-the-fly redaction. Bash `run_captured_cmd_then_fix_loop` (`ship-pr.sh:314-317`) always builds a `.redacted` file via `redact-secrets.sh`; Python dispatch-first branch already has fallback redaction (`checks.py:1317-1328`). Redaction `OSError` or a runner that only sets `raw_log_path` cannot enter the fix loop even though bash would; silent redaction changes could turn fixable failures into `dispatch-failed`/TRANSIENT without targeted signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub failing ChecksResult with raw_log_path set and redacted_log_path None; assert loop status dispatch-failed.
  - From cursor-specialist-plan-fidelity-output.txt: Mirror dispatch-first redaction fallback in check-first branch when raw_log_path exists
  - From dyn-parity-drift-output.txt: Mirror the dispatch-first fallback in the check-first path—when `redacted_log_path` is missing but `raw_log_path` is a non-empty file, write `Path(raw_path).with_suffix(suffix + ".redacted")` via `redact.redact()` (or reuse a small shared helper) and proceed to `fixer()`; only set `dispatch-failed` if that write fails.

### FINDING_9: `checks_log` path not confined to validated session tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `run_lint_fix` and the dispatch-first loop accept any readable `checks_log` path without confining it to the validated session tmpdir (unlike `ship-pr.sh` `resolve_checks_log_path`). At Phase 7 cutover a buggy or compromised caller could pass sensitive paths (e.g. `~/.ssh/id_rsa`); tail content is redacted but still fed to codex/cursor and may leak material redact patterns miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Port resolve_checks_log_path semantics: realpath the candidate require it under canonical_tmp from validate_tmpdir apply in run_lint_fix run_check_fix_loop for initial_redacted_log and fallback redacted writes.

### FINDING_10: `target_cmd_display` embedded in prompts without validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `target_cmd_display` is embedded unvalidated in backtick-delimited prompt text and `run_checks_phase` allows it for any site. A caller passing newlines or instruction-like text can manipulate the codex/cursor fixer prompt beyond what bash allows for non per-job sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Match bash: allow only for ship-pr-ci-per-job reject control characters and newlines before interpolation or load via target_cmd_display_from_file parity.

### FINDING_11: `run_checks_phase` uses one `site` for checks and lint-fix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run_checks_phase` uses one site (default `step6`) for both checks and lint-fix; bash `run_checks_phase` uses step6 checks and `ship-pr-ci-initial` fix. Phase 7 drop-in without site override changes commit messages and prompt labels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document split or add checks_site/fix_site parameters.

### FINDING_12: `ship-pr-ci-per-job` site lacks `target_cmd_display` fail-closed validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No validation that `ship-pr-ci-per-job` has `target_cmd_display`. A caller using that site without `target_cmd_display` gets `relevant-checks.sh` prompt text instead of the failing CI command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fail closed when site is ship-pr-ci-per-job and target_cmd_display is absent.

### FINDING_13: `is_transient_infra_failure` unused; plan/acceptance mismatch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `is_transient_infra_failure` is never called though the plan lists it alongside `classify_launch_failure`. Acceptance/plan mismatch unless the health branch is kept.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire is_transient_infra_failure per plan or remove unused classification on local-fix path.

### FINDING_14: Unreachable prefix membership check after basename-derived prefix
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Redundant guard after basename-derived prefix is unreachable dead code only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove redundant guard.

### FINDING_15: `_scripts_dir(repo_root)` ignores `repo_root` (misleading signature)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_scripts_dir(repo_root)` always resolves plugin scripts via `__file__`, ignoring `repo_root`. Misleading signature suggests consumer-repo script lookup during Phase 7 wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename to _plugin_scripts_dir() without repo_root or add a comment documenting plugin-root resolution.

### FINDING_16: Unused `baseline_tracked` / `baseline_untracked` in `_post_dispatch_forbidden_revert`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_post_dispatch_forbidden_revert` accepts `baseline_tracked`/`baseline_untracked` but never uses them. Dead parameters add noise and suggest unfinished baseline-scoped revert logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove unused parameters or implement baseline-scoped revert if required for parity.

### FINDING_17: Truncation banner hardcodes `60000` instead of `_PROMPT_TAIL_BYTES`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Changing the tail limit requires two edits; banner could lie if the constant changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Interpolate _PROMPT_TAIL_BYTES into the truncation message.

### FINDING_18: `normalize_max_iter` parametrization omits explicit multi-digit strings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Parametrization omits explicit two-digit strings like `10`/`12` though the plan table includes multi-digit clamp (unlikely bug since `99` covers length>1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ("10", 6) and ("12", 6) to parametrize.

### FINDING_19: `ChecksResult.raw_log_path` is an undeclared extension field
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Extra field beyond plan dataclass spec may surprise Phase 7 consumers expecting exact machine record.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Document as extension or move raw path handling out of ChecksResult

### FINDING_20: Missing `errors` import listed in plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan specifies `errors` sibling import; module omits it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Import errors where appropriate or update plan import list

### OOS_1: [OUT_OF_SCOPE] StubRunner duplicates pattern in `test_git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: StubRunner duplicates the pattern in test_git.py with call recording. Minor DRY violation across test files; pre-existing convention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared test helper module if test duplication becomes painful repo-wide.

### OOS_2: [OUT_OF_SCOPE] Bash `compose_prompt` does not re-redact log tails (Python is stricter)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Bash compose_prompt does not re-redact log tails; Python `_compose_prompt` does. No breakage; Python is stricter. Optional documentation only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Submodule paths inlined into prompts without newline sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Submodule paths from repo metadata are inlined into prompts without newline sanitization. Malicious `.gitmodules` path values could attempt prompt-structure injection; same broad trust model as consumer-repo fixer runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Strip or reject control characters in submodule path lists if hardening consumer-repo threat model.

### OOS_4: [OUT_OF_SCOPE] Unplanned harness/version changes on branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Changes outside Phase 4 plan file list (`scripts/test-lint-literal-counts.sh`, `skills/design/scripts/test-plan-review-loop.sh`, `.claude-plugin/plugin.json`, commit `abfbc565c` lint-literal-counts / plan-review-loop poll / version bump) are unrelated review surface; no action required for Phase 4 fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: No action required for Phase 4 fidelity
  - From dyn-parity-drift-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Implement self-fix / run-log commits outside planned deliverables
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Commits `cee777a21` / `f44395376` (run logs / implement commit) and similar implement self-fix work are not part of checks.py Phase 4 scope unless they touch checks.py.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Ignore for Phase 4 plan fidelity unless it touches checks.py
  - From dyn-parity-drift-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] `_scripts_dir` ignoring `repo_root` matches bash plugin-script resolution
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: nit
- **Concern**: Ignoring `repo_root` and resolving `Path(__file__).parents[1] / "scripts"` matches bash `lint-fix-loop.sh` (`SCRIPT_DIR` / plugin scripts), not `repo_root/scripts`. Consumer `relevant-checks.sh` is correctly resolved under `repo_root` in `run_relevant_checks`. Not a production parity defect; tests that monkeypatch `_scripts_dir` to the consumer tree exercise a different layout.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] `_post_dispatch_forbidden_revert` unused baselines match bash
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: nit
- **Concern**: Bash `post_dispatch_forbidden_revert` also ignores pre-dispatch baselines and reverts any current tracked/untracked path matching the forbidden list (`scripts/lint-fix-loop.sh:170-199`). Python’s discard of `baseline_tracked` / `baseline_untracked` matches that behavior.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] `run_checks_phase` single-site wiring relevant only at full ship-pr cutover
- **Reviewer(s)**: dyn-parity-drift-output.txt
- **Severity**: latent
- **Concern**: Python uses one `site` for both checks and fix (default `step6`). Bash uses step6 checks and `ship-pr-ci-initial` fix. Relevant only when this API replaces ship-pr’s custom checks loop at cutover; plan positions `run_checks_phase` as `run_captured_cmd_then_fix_loop` wiring, not a full port of bash `run_checks_phase`.
- **Suggested revisions (informational for voters; coder decides)**:
