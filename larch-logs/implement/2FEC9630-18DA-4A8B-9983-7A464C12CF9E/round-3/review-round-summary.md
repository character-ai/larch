# Review Round 3

- Mode: `diff`
- 14 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: `_allow_flag` false unknown-flag on `./`-prefixed script paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_allow_flag` uses exact `script_path` match while invocations may retain a `./` prefix. A plan with `### UPDATED: scripts/foo.sh` and fenced `./scripts/foo.sh --new-flag` can emit a false unknown-flag defect. Normalize script paths in `_allow_flag` the same way as `_is_new_script` (e.g. `lstrip ./`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Normalize script paths in _allow_flag the same way as _is_new_script (lstrip ./)


### FINDING_10: `test-run-step1-plan-log.sh` never exercises default compose CLI path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: All cases override `RUN_STEP1_COMPOSE_CMD` spy; the default `python3 PLUGIN_ROOT/python/cli.py plan compose-goals-test` path is never exercised. Default composer wiring can break while the harness passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one case without compose override that asserts real CLI invocation


### FINDING_11: Orphaned shell harnesses still invoke deleted migrated scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: Retained shell harnesses (`test-invoke-plan-validator.sh`, `test-parse-plan-commands.sh`, `test-validate-plan-commands.sh`, `test-check-plan-size.sh`, `scripts/test-revise-plan-with-waterfall.sh`) still execute deleted migrated subjects; `agent-lint.toml` may pin stale harnesses; retired harness paths are not listed in `migrated-scripts.tsv`, so `lint-retired-scripts` may miss stale references. Direct harness runs fail before exercising the Python port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Delete or retarget harness and update test-invoke-plan-validator.md and docs/linting.md
  - From cursor-specialist-testing-output.txt: Append harness paths to manifest and remove orphaned shell harness files
  - From codex-generic-output.txt: Delete the absorbed harnesses, or turn each retained harness into a thin pytest/Python CLI wrapper, then update the agent-lint pins and harness docs.


### FINDING_12: Auto-fix dirty-tree snapshot omits untracked file content hashes
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The auto-fix dirty-tree snapshot no longer hashes untracked file contents; it records `git status` plus untracked names only. If an external auto-fix agent changes contents of a pre-existing untracked repo file while fixing the plan, `_check_repo_dirty_delta` can see identical before/after snapshots and let the mutation survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Hash untracked regular files and symlink targets in `_git_status_snapshot`, matching the retired guard.


### FINDING_13: Weak default repo-root resolution in `validate_plan_main` and `validate_plan_commands_main`
- **Reviewer(s)**: dyn-plan-cli-contracts-output.txt
- **Severity**: important
- **Concern**: `validate_plan_main` (`python/plan_quality.py:850`) and `validate_plan_commands_main` (`829-834`) resolve repo root with `_repo_root_from(...)` when `--repo-root` is omitted instead of `_repo_root_for_plan`. For a session plan under non-git `DESIGN_TMPDIR`, that can fall back to orchestrator cwd, not the plugin checkout, causing false `missing-script` defects or missed real ones. Production callers usually pass `--repo-root "$PLUGIN_ROOT"`, but direct CLI/harness calls without `--repo-root` are affected. The standalone `validate-commands` stdout shape also differs from `plan validate` KV lines, which is easy to confuse when debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-plan-cli-contracts-output.txt: Replace line 850 with `repo = _repo_root_for_plan(plan, args.repo_root)` and add a pytest case that validates a known plugin script without passing `--repo-root` while the plan file lives in an isolated tmpdir outside git.
  - From dyn-plan-cli-contracts-output.txt: If the standalone verb remains public, resolve repo root through `_repo_root_for_plan` using a sibling plan path or document that `--repo-root` is required; align or document the two stdout shapes in `design-postplan-emit.md`.


### FINDING_14: Auto-fix missing `LARCH_QUIET_DISABLE=1` under quiet parent
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Postplan and publish wrap `plan validate` with `LARCH_QUIET_DISABLE=1` so contract KVs stay on stdout under a quiet parent, but `design-step-validator-autofix.sh` does not for `plan auto-fix-commands`. Under an active quiet parent, `AUTOFIX_STATUS` and related keys can land on FD 3 instead of captured stdout, so auto-fix can look like `failed` even when Python succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Match postplan/publish and invoke auto-fix as `env LARCH_QUIET_DISABLE=1 python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan auto-fix-commands ...`, and add a harness case with quiet-parent capture.


### FINDING_15: Call sites disagree on validation `--repo-root` authority
- **Reviewer(s)**: dyn-design-callsite-cutover-output.txt
- **Severity**: important
- **Concern**: Postplan, publish, and `design-driver.sh` pass `--repo-root "$PLUGIN_ROOT"` (plugin tree); auto-fix passes `--repo-root` from `git rev-parse --show-toplevel` (consumer checkout). The Python port uses one `repo` for parsing, script probes, `dry-runnable-scripts.tsv`, and Tier 3 redaction. Auto-fix revalidation can therefore diverge from the initial gate: empty/missing dry-run registry (Tier 3 skipped), wrong script paths, and unredacted Tier 3 captures when `repo/python/cli.py` is absent in the consumer tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-callsite-cutover-output.txt: Pick one authority (plugin root via `CLAUDE_PLUGIN_ROOT`/`PLUGIN_ROOT`, or consumer git root via `git rev-parse`) and pass it from postplan, publish, driver, and auto-fix; resolve `dry-runnable-scripts.tsv` and redaction from `_plugin_root(...)`, not the consumer repo alone.


### FINDING_2: SECURITY.md points at deleted `validate-plan-commands.md`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md` still references deleted `validate-plan-commands.md` after migration; manifest lists it retired, so `make lint-retired-scripts` may fail and the security doc points at a missing authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Repoint Tier 3 reference to python/plan_quality.py or surviving Python CLI contract doc


### FINDING_3: Failed revise-waterfall leaves corrupted `plan.txt`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On failed revise-waterfall, `plan.txt` is not restored from the before-revise snapshot. An external reviewer can mutate `plan.txt`; the loop reports `failed-*` but leaves a corrupted plan for Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Call restore() from snapshot whenever not winner before emitting failure REVISE_* keys


### FINDING_4: `test-design-driver.sh` stale SKILL pin and missing `CLAUDE_PLUGIN_ROOT` bootstrap test
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The SKILL pin test still greps for an `invoke-plan-validator.sh` substring (regression can pass via HTML comment only). Python `plan validate` dispatch and `PLUGIN_ROOT` bootstrap are unguarded; checkout validation can regress to the wrong CLI path without CI failure when `CLAUDE_PLUGIN_ROOT` is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Assert python/cli.py plan validate in SKILL and add CLAUDE_PLUGIN_ROOT unset driver test
  - From cursor-specialist-testing-output.txt: Add unset-CLAUDE_PLUGIN_ROOT case asserting REPO_ROOT/python/cli.py plan validate and remove obsolete invoke-plan-validator pin


### FINDING_5: `_redact_capture` leaks raw capture on redact CLI failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_redact_capture` returns raw subprocess capture when the redact CLI fails. Tier 3 dry-run secrets may appear in validator logs and auto-fix prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: On redact failure emit placeholder text instead of raw capture up to 64KB


### FINDING_7: `relevant-checks.sh` missing plan-required survivor-harness triggers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required survivor-harness triggers for `design-postplan-emit`, `design-driver`, `gate-b-dedup`, `design-step2b5`, and `run-step1-plan-log` were not added; only autofix and revise-waterfall routes exist for `plan_quality.py`. Shell-only integration fixes can merge without running `test-design-postplan-emit`, `test-design-driver`, `test-gate-b-dedup-plan`, or `test-run-step1-plan-log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add case arms per plan and extend scripts/test-relevant-checks.sh routing assertions


### FINDING_8: Missing pytest coverage for `plan check-size` rc/status branches
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest for `plan check-size` rc 2 statuses (`missing-plan`, `missing-diff-lines`, `invalid-mechanical-churn`) and hard `SIZE_TRIGGER_FIRED=true`. Postplan emit and Step 2b.5 rc branches can break silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port retired check-plan-size harness scenarios into pytest with rc and KV assertions


### FINDING_9: Missing pytest for `plan validate` / `validate-commands` infrastructure failures
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test for `plan validate` or `validate-commands` infrastructure failures (unreadable inputs, nonzero rc). Infrastructure failures may be mis-routed as defects-found or lose log evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add subprocess tests for missing plan file and missing TSV asserting nonzero rc and log behavior


