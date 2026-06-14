## Goal
Implement issue #3685: [IMPLEMENTING] sh-to-py C4c: implement OOS, finalize, reports.

## Implementation Plan
## Plan

## Plan

Approach synthesis is `NO_SKETCHES`. Draft from direct repository inspection plus accepted reviewer findings.

## Approach

- Keep the cutover **direct**: callers invoke `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" <domain> <verb> ...`.
- Do **not** add shell shims or `LARCH_*_IMPL` selectors.
- Add a **single Python Step 7a entrypoint** before deleting `step-7a.sh`.
- Cut over every live caller before deleting absorbed scripts.
- Extend current authorities:
  - `python/file_oos.py`: OOS disposition, manifest materialization, cap, conflict deps.
  - `python/finalize.py`: `implement-finalize` parity and cleanup helper parity.
  - `python/pr_body.py`: run summary, PR summary, final report, tracking issue, Slack, code-flow helpers.
  - `python/run_logs.py`: remove remaining final-report subprocess calls.
  - `python/ship.py`: enforce security-only OOS checkpoint before PR creation.
- Add focused modules where no Python authority exists:
  - `python/execution_issues.py`
  - `python/stall_recovery.py`
  - `python/step_7a.py`
- Keep `hook-stop-fail-close.sh` bash. It is out of scope.
- Before deleting old scripts, run their current harnesses once against the Python call path as parity gates.

## Files to modify/create

### UPDATED: python/file_oos.py

- Add importable functions and CLI mains for:
  - `materialize-manifest`
  - `issue-cap`
  - `file-conflict-deps`
  - `disposition-gate`
  - `disposition-checkpoint`
- Reuse existing OOS block counting and design path resolution.
- Fix security focus-area detection:
  - accept both `focus-area` and `Focus area`
  - strip Markdown emphasis
  - centralize on a shared `focus[- \t]*area` matcher
- Port `materialize-manifest-oos.sh` with stdlib `json`, no `jq`.
- Preserve `--count-only`.
- Preserve security routing into `security-oos-observations.md`.
- Preserve public redaction by calling existing `redact` helpers in-process where possible.
- Preserve idempotent title matching and `External implementer` attribution.
- Port `oos-issue-cap.sh` behavior:
  - validate positive `OOS_ISSUES_PER_RUN_CAP`
  - require OOS-shaped input when items exist
  - use existing `issue_create` parsing logic instead of shelling to `issue parse-input`
  - group conflicting same-file items
  - rewrite in place atomically when `--output` is omitted
  - preserve excerpt cap behavior currently split into `oos-issue-cap-excerpt.py`
- Port `oos-file-conflict-deps.sh` into the same range parser used by cap.
- Port disposition gate and checkpoint:
  - fork and repo-unavailable bypass
  - strict accepted-file validation
  - security sidecar fail-closed
  - `oos-issues.ndjson` discovery by `RUN_ID` or single-batch fallback
  - commit-range inline-triage count
  - filed URL union and structured `Filed URL` strict count
  - rejected-OOS marker count from NDJSON

### NEW: python/execution_issues.py

- Port:
  - `scripts/lib-execution-issues.sh`
  - `scripts/append-execution-issue.sh`
  - `skills/implement/scripts/flush-execution-issues.sh`
  - `skills/implement/scripts/refresh-execution-issues.sh`
- Add importable APIs:
  - `sha256_file`
  - `normalize_body_for_hash`
  - `execution_issues_batch_contains_all_sections`
  - `append_execution_issue`
  - `write_execution_issues_records`
  - `flush_execution_issues`
  - `refresh_execution_issues`
- Add CLI mains:
  - `execution-issues append`
  - `execution-issues flush`
  - `execution-issues refresh`
- Preserve fd-3 contract output:
  - `FLUSH_STATUS`
  - `RECORDS`
  - `APPEND_LOG_FILE`
  - `REFRESHED`
  - `ERROR`
- Use `run_logs` APIs directly when safe.
- Preserve best-effort failure append to `execution-issues.md`.

### NEW: python/stall_recovery.py

- Port `stall-recovery-report.sh` as a stdlib Python CLI surface.
- Keep the subcommand names stable:
  - `init-attempts`
  - `classify`
  - `record-escalation`
  - `normalize-outcome`
  - `compose-report`
  - `dedup-tier-a-report`
  - `normalize-file-failure-report-env`
  - `normalize-issue-env`
  - `validate-token`
  - `validate-terminal-state`
  - `validate-tier-b-public-file`
  - `populate-sensitive-corpus`
  - `chat-print`
  - `record-attempt`
  - `retry-policy`
  - `is-larch-dev-clone`
  - `clear-stall`
  - `seed-terminal-state`
  - `lint`
- Load `stall-recovery-report-allowlists.tsv` until the data is ported into constants or retained as non-shell data.
- Preserve generic profile support used by `/design`.
- Preserve path validation:
  - absolute paths
  - no symlinked public evidence
  - evidence under tmpdir
  - size caps
- Keep report bodies redacted and public-safe.

### NEW: python/step_7a.py

- Port the full `skills/implement/scripts/step-7a.sh` orchestration.
- Add importable API:
  - `run_step7a`
- Add CLI main:
  - `implement step-7a`
- Preserve the current Step 7a stdout KV tail:
  - `DIAGRAM_STATUS`
  - `DIAGRAM_PATH`
  - `COMMENT_URL`
  - `LOG_FLUSH_STATUS`
  - `STEP_7A_BAIL_REASON`
  - `REBASE_OUTCOME`
- Preserve current sub-behaviors:
  - small/non-runtime classifier
  - code-flow diagram generation
  - `larch:diagrams` upsert
  - embedded `7a.r` rebase relay
  - pre-ship run-log flush
  - execution-issues flush
  - transcript capture
  - best-effort run-log flush semantics
  - rebase exit behavior

### UPDATED: python/finalize.py

- Add CLI mains for:
  - `implement-finalize postbump`
  - `implement-finalize postmerge`
  - `implement-finalize teardown`
  - `implement cleanup`
- Reuse existing `postbump`, `postmerge`, `teardown`, and state helpers.
- Port `cleanup.sh` behavior or route it to the existing safe cleanup implementation.
- Preserve cleanup target validation:
  - approved tmp roots only
  - no deletion outside allowed roots
  - conservative failure behavior
- Fill remaining bash parity gaps:
  - stdout KV tails
  - validation exit code `2`
  - `FINALIZE_WARNINGS`
  - `LOG_WRITE_STATUS`
  - `REBASE_STATUS`
  - `FORCE_PUSH_STATUS`
  - `LOCAL_CLEANUP_STATUS`
  - `VERIFY_MAIN_STATUS`
  - `RENAME_BRANCH`
  - `RENAME_STATUS`
  - `ISSUE_URL`
  - `STASH_REF`
  - `SENTINEL_WRITTEN`
- Preserve best-effort posture for teardown.
- Preserve no-commit-after-post-merge behavior.
- Replace internal execution-issues safety-net helper with `python/execution_issues.py`.

### UPDATED: python/pr_body.py

- Port:
  - `scripts/render-run-summary.sh`
  - `scripts/compose-pr-summary.sh`
  - `skills/implement/scripts/write-final-report.sh`
  - `skills/implement/scripts/step-18b-final-report.sh`
  - `skills/implement/scripts/post-tracking-issue.sh`
  - `skills/implement/scripts/slack-issue-announce.sh`
  - `skills/implement/scripts/generate-code-flow-diagram.sh`
- Add importable APIs:
  - `render_run_summary`
  - `compose_summary_bullets`
  - `write_final_report`
  - `step18b_final_report`
  - `post_tracking_issue`
  - `slack_issue_announce`
  - `generate_code_flow_diagram`
- Add CLI-backed behavior for PR summary fallback used by `ship-pr.sh`.
- Preserve summary format exactly:
  - `## /<skill> run <run-id> — <outcome>`
  - `<!-- larch:run-summary v=1 -->`
  - dollar-primary cost line
  - omit PR line when `N/A`
- Replace `jq` and `curl` usage with stdlib `json` and `urllib.request`.
- Reuse existing Mermaid sanitizer functions.
- Keep `--comment-only` API-only. Do not commit after merge.
- Keep `--print-stdout` body and KV routing behavior.

### UPDATED: python/run_logs.py

- Replace `_write_final_report` and `write_final_report_comment` shell calls with `pr_body.write_final_report`.
- Keep existing error behavior:
  - raise `ShipError` for failed required final-report writes
  - preserve best-effort wrappers where current callers suppress failures
- Reuse `execution_issues` helpers instead of duplicated safety-net logic where practical.

### UPDATED: python/ship.py

- Enforce OOS checkpoint semantics before PR creation on the Python ship path.
- Detect security-only OOS evidence with `file_oos` or equivalent.
- When `OOS_PENDING=true` and `security-oos-observations.md` exists, return `needs_user_input=oos-filing` unless fork or repo-unavailable carve-outs apply.
- Preserve non-security accepted-file behavior.

### UPDATED: python/bootstrap.py

- Replace direct `post-tracking-issue.sh` subprocess calls with the new Python CLI or in-process `pr_body.post_tracking_issue`.
- Preserve emitted KVs:
  - `POSTED`
  - `COMMENT_URL`
  - `ERROR`
- Preserve success-only `parent-issue.md` sentinel write.
- Preserve deferred behavior on posting failure.

### UPDATED: python/cli.py

- Register new verbs:
  - `("oos", "materialize-manifest")`
  - `("oos", "issue-cap")`
  - `("oos", "file-conflict-deps")`
  - `("oos", "disposition-gate")`
  - `("oos", "disposition-checkpoint")`
  - `("execution-issues", "append")`
  - `("execution-issues", "flush")`
  - `("execution-issues", "refresh")`
  - `("stall-recovery", "<subcommand>")` through one dispatcher main
  - `("implement", "step-7a")`
  - `("implement", "cleanup")`
  - `("implement-finalize", "postbump")`
  - `("implement-finalize", "postmerge")`
  - `("implement-finalize", "teardown")`
  - `("final-report", "write")`
  - `("final-report", "step18b")`
  - `("tracking", "post-issue")`
  - `("slack", "issue-announce")`
  - `("diagram", "code-flow")`
  - `("render", "run-summary")`
  - `("pr", "compose-summary")`
- Keep lazy imports.
- Add every new stdout-contract verb to `_MACHINE_STDOUT_KEYS` unless that main writes directly to stdout and never calls quiet initialization.
- Include KVs such as:
  - `POSTED`
  - `COMMENT_URL`
  - `EMIT_BODY`
  - `WFR_RC`
  - `FLUSH_STATUS`
  - `DIAGRAM_STATUS`
  - `REBASE_OUTCOME`

### UPDATED: scripts/ship-pr.sh

- Replace direct calls to:
  - `scripts/implement-finalize.sh`
  - `skills/implement/scripts/write-final-report.sh`
  - `scripts/compose-pr-summary.sh`
- Use `python3 "$SCRIPT_DIR/../python/cli.py" ...` direct calls.
- Preserve manifest-summary fallback behavior during PR prep.
- Keep legacy bash driver behavior otherwise unchanged.
- Do not add compatibility wrappers.

### UPDATED: skills/implement/SKILL.md

- Replace retired script invocations with Python CLI invocations.
- Update Step 7a to call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement step-7a`.
- Update Step 8+ OOS checkpoint, Step 16a, Step 17, Step 18, and Step 18b prose.
- Keep orchestration semantics unchanged.
- Preserve NEVER rules, especially OOS disposition and no post-merge commits.

### UPDATED: skills/implement/references/oos-pipeline.md

- Replace retired script paths with the new `python/cli.py oos ...` verbs.
- Keep accepted-OOS order, security routing, strict disposition evidence, and run-statistics ownership unchanged.

### UPDATED: skills/implement/references/execution-issues-tracking.md

- Replace retired execution-issues and OOS helper references.
- Keep the terminal disposition invariant unchanged.

### UPDATED: skills/implement/references/rebase-checkpoint-routing.md

- Replace `step-7a.sh` references with `python/cli.py implement step-7a`.
- Preserve `7a.r` routing and rebase relay semantics.

### UPDATED: skills/implement/scripts/step2-implement.sh

- Replace both `materialize-manifest-oos.sh` calls with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" oos materialize-manifest`.
- Preserve:
  - `--count-only`
  - failure logging labels
  - `OOS_CHECKPOINT_RC=` relay
  - exit-code passthrough
  - `LARCH_TEST_MATERIALIZE_FORCE_FAIL` behavior

### UPDATED: skills/implement/scripts/step-8-oos-checkpoint.sh

- Replace `oos-disposition-checkpoint.sh` call with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" oos disposition-checkpoint`.
- Preserve:
  - `OOS_CHECKPOINT_RC`
  - Tool Failures behavior
  - `OOS_PENDING=false` update behavior
  - run-statistics behavior

### UPDATED: skills/implement/scripts/step-17.sh

- Replace absorbed helper calls with Python CLI verbs.
- Preserve current stdout contract and failure routing.

### UPDATED: skills/implement/scripts/step-18.sh

- Replace `implement-finalize.sh` and final-report helper calls with Python CLI verbs.
- Preserve current stdout contract, sentinel handling, and no-post-merge-commit behavior.

### UPDATED: skills/implement/scripts/step-18b-final-report.sh

- Replace implementation with Python CLI invocation or remove wrapper only if `SKILL.md` no longer calls it.
- Preserve the current `EMIT_BODY`, `WFR_RC`, and non-empty `summary-final.md` gating.

### UPDATED: skills/implement/scripts/cleanup.sh

- Replace implementation with Python CLI invocation or remove wrapper only if no live caller remains.
- Preserve `--help` smoke behavior until tests are updated.

### UPDATED: skills/design/scripts/file-design-oos.sh

- Replace `oos-issue-cap.sh` and `oos-file-conflict-deps.sh` calls with `python/cli.py oos issue-cap` and `oos file-conflict-deps`.

### UPDATED: skills/design/scripts/design-stage-terminal-state.sh

- Replace `stall-recovery-report.sh validate-token` and `validate-terminal-state` calls with `python/cli.py stall-recovery ...`.

### UPDATED: skills/design/scripts/design-failure-report.sh

- Replace generic `stall-recovery-report.sh` calls with `python/cli.py stall-recovery ...`.

### UPDATED: skills/design/scripts/review-design-step3-loop.sh

- Replace `stall-recovery-report.sh` calls with `python/cli.py stall-recovery ...`.

### UPDATED: skills/design/scripts/render-final-summary.sh

- Replace `scripts/render-run-summary.sh` calls with `python/cli.py render run-summary`.

### UPDATED: skills/implement/scripts/file-failure-report-cross-repo.sh

- Replace `stall-recovery-report.sh validate-tier-b-public-file` calls with `python/cli.py stall-recovery validate-tier-b-public-file`.
- Preserve profile and corpus arguments.
- Preserve unsafe Tier B fallback behavior only when validation truly fails.

### UPDATED: python/review_and_fix.py

- Replace `stall-recovery-report.sh` subprocess calls with `python/cli.py stall-recovery ...` or in-process `stall_recovery` APIs.
- Preserve escalation ledger paths and current failure handling.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh

- Replace `stall-recovery-report.sh` calls with `python/cli.py stall-recovery ...`.
- Preserve generic escalation behavior.

### UPDATED: docs/python-migration.md

- Add a C4c decision-log note:
  - back-half `/implement` helpers now use Python CLI verbs
  - Step 7a has a Python orchestration owner
  - hooks remain bash
  - no shim layer
  - `stall-recovery` serves both `/implement` and generic `/design` callers

### UPDATED: docs/run-log-cli.md

- Update final-summary and execution-issues references to Python CLI verbs.

### UPDATED: docs/run-logs.md

- Update committed run-log batch references if they mention retired helper paths.

### UPDATED: python/migrated-scripts.tsv

- Add every deleted shell, helper, contract-md, and harness path with the actual C4c tracking issue number.
- Include `scripts/append-execution-issue.sh`.
- Do not list `hook-stop-fail-close.sh`.

### UPDATED: python/test_file_oos.py

- Add OOS disposition gate/checkpoint tests.
- Add materialize manifest tests.
- Add issue cap tests.
- Add file conflict dep tests.
- Cover security sidecar, spaced `Focus area` security routing, legacy headers, malformed NDJSON, strict URLs, fork bypass, repo-unavailable bypass, and ambiguous run-log discovery.

### NEW: python/test_execution_issues.py

- Port `test-flush-execution-issues.sh` and `test-refresh-execution-issues.sh` coverage.
- Add coverage for append behavior.
- Cover empty skip, sentinel idempotency, section dedupe, append failure logging, invalid args, and refresh metadata.

### NEW: python/test_stall_recovery.py

- Port the three stall recovery harnesses.
- Cover classification, token validation, terminal-state validation, report composition, dedup, retry policy, clear-stall, and generic profile behavior.

### NEW: python/test_step_7a.py

- Port `test-step-7a.sh` coverage.
- Cover:
  - diagram generation and skip paths
  - larch diagrams upsert
  - pre-ship run-log flush
  - execution-issues flush
  - transcript capture
  - `7a.r` rebase relay
  - terminal KV tail
  - bail reasons
  - best-effort failure behavior

### UPDATED: python/test_finalize.py

- Extend current tests for CLI tail parity, cleanup parity, and teardown gaps.
- Cover state validation failures and best-effort warning cases.

### UPDATED: python/test_finalize_bash_parity.py

- Replace bash subprocess parity assertions with Python CLI subprocess assertions.
- Keep only parity data fixtures that do not reference retired paths literally.

### UPDATED: python/test_pr_body.py

- Add render-run-summary tests.
- Add compose-pr-summary tests.
- Add write-final-report tests.
- Add post-tracking issue, Slack announce, and code-flow diagram tests.
- Cover cost unavailable, corrupt zero token report, Step 17/18 body emission, repo unavailable, issue `0`, and `--comment-only`.

### UPDATED: python/test_run_logs.py

- Update final-report call tests to assert in-process `pr_body.write_final_report`.
- Remove expectations that shell scripts exist.

### UPDATED: python/test_ship.py

- Add security-only OOS checkpoint coverage for the Python ship path.
- Cover fork and repo-unavailable carve-outs.
- Cover non-security accepted-file behavior remains unchanged.

### UPDATED: python/test_bootstrap.py

- Replace shell-path mocks for `post-tracking-issue.sh` with Python CLI or in-process `pr_body.post_tracking_issue` mocks.
- Cover `POSTED`, `COMMENT_URL`, `ERROR`, deferred behavior, and success-only `parent-issue.md` sentinel writes.

### UPDATED: skills/implement/scripts/test-step2-dispatch.sh

- Update expectations for `python/cli.py oos materialize-manifest`.
- Preserve force-failure coverage.

### UPDATED: skills/implement/scripts/test-step-8-oos-checkpoint.sh

- Update expectations for `python/cli.py oos disposition-checkpoint`.
- Preserve `OOS_CHECKPOINT_RC` coverage.

### UPDATED: scripts/test-implement-structure.sh

- Replace `step-7a.sh` structural expectations with `python/cli.py implement step-7a` expectations.

### UPDATED: Makefile

- Replace shell harness targets for absorbed scripts with pytest targets or remove them from aggregate harness groups.
- Keep `make py-test`, `make py-lint`, and `make lint-retired-scripts` authoritative.

## Retired files to delete

Delete absorbed shell surfaces and their `.md` siblings after call-site cutover:

- `skills/implement/scripts/oos-disposition-gate.sh`
- `skills/implement/scripts/oos-disposition-gate.md`
- `skills/implement/scripts/oos-disposition-checkpoint.sh`
- `skills/implement/scripts/oos-disposition-checkpoint.md`
- `skills/implement/scripts/oos-issue-cap.sh`
- `skills/implement/scripts/oos-issue-cap.md`
- `skills/implement/scripts/oos-issue-cap-excerpt.py`
- `skills/implement/scripts/oos-issue-cap-excerpt.md`
- `skills/implement/scripts/oos-file-conflict-deps.sh`
- `skills/implement/scripts/oos-file-conflict-deps.md`
- `skills/implement/scripts/materialize-manifest-oos.sh`
- `skills/implement/scripts/materialize-manifest-oos.md`
- `skills/implement/scripts/flush-execution-issues.sh`
- `skills/implement/scripts/flush-execution-issues.md`
- `skills/implement/scripts/refresh-execution-issues.sh`
- `skills/implement/scripts/refresh-execution-issues.md`
- `skills/implement/scripts/stall-recovery-report.sh`
- `skills/implement/scripts/stall-recovery-report.md`
- `skills/implement/scripts/write-final-report.sh`
- `skills/implement/scripts/write-final-report.md`
- `skills/implement/scripts/step-18b-final-report.sh`
- `skills/implement/scripts/step-18b-final-report.md`
- `skills/implement/scripts/step-7a.sh`
- `skills/implement/scripts/step-7a.md`
- `skills/implement/scripts/post-tracking-issue.sh`
- `skills/implement/scripts/post-tracking-issue.md`
- `skills/implement/scripts/slack-issue-announce.sh`
- `skills/implement/scripts/slack-issue-announce.md`
- `skills/implement/scripts/generate-code-flow-diagram.sh`
- `skills/implement/scripts/generate-code-flow-diagram.md`
- `skills/implement/scripts/cleanup.sh`
- `skills/implement/scripts/cleanup.md`
- `scripts/append-execution-issue.sh`
- `scripts/append-execution-issue.md`
- `scripts/lib-execution-issues.sh`
- `scripts/lib-execution-issues.md`
- `scripts/implement-finalize.sh`
- `scripts/implement-finalize.md`
- `scripts/render-run-summary.sh`
- `scripts/render-run-summary.md`
- `scripts/compose-pr-summary.sh`
- `scripts/compose-pr-summary.md`

Delete absorbed harnesses after pytest replacement:

- `skills/implement/scripts/test-oos-disposition-gate.sh`
- `skills/implement/scripts/test-oos-issue-cap.sh`
- `skills/implement/scripts/test-oos-file-conflict-deps.sh`
- `skills/implement/scripts/test-materialize-manifest-oos.sh`
- `skills/implement/scripts/test-flush-execution-issues.sh`
- `skills/implement/scripts/test-refresh-execution-issues.sh`
- `skills/implement/scripts/test-stall-recovery-report-1.sh`
- `skills/implement/scripts/test-stall-recovery-report-2.sh`
- `skills/implement/scripts/test-stall-recovery-report-3.sh`
- `skills/implement/scripts/test-write-final-report.sh`
- `skills/implement/scripts/test-step-18b-final-report.sh`
- `skills/implement/scripts/test-step-7a.sh`
- `skills/implement/scripts/test-post-tracking-issue.sh`
- `skills/implement/scripts/test-slack-issue-announce.sh`
- `skills/implement/scripts/test-generate-code-flow-diagram.sh`
- `skills/implement/scripts/test-cleanup.sh`
- `scripts/test-append-execution-issue.sh`
- `scripts/test-implement-finalize.sh`
- `scripts/test-render-run-summary.sh`
- `scripts/test-compose-pr-summary.sh`

If a listed file is already retired or absent, do not recreate it. Only update stale references and the manifest as needed.

## Edge cases

- Treat `security-oos-observations.md` as fail-closed for all-clear checkpoints and Python ship pre-PR checks.
- Preserve fork and repo-unavailable carve-outs.
- Preserve all-already-filed OOS recovery so it still writes checkpoint-visible evidence.
- Preserve strict URL evidence. Do not count incidental issue links in prose.
- Preserve rejected-OOS marker counting from NDJSON.
- Preserve spaced `Focus area` security routing.
- Keep final-report rendering valid when token data is absent or corrupt.
- Keep Step 18 body emission gated by `EMIT_BODY=true`, `WFR_RC=0`, and non-empty `summary-final.md`.
- Skip Slack cleanly when `LARCH_SLACK_WEBHOOK_URL` is unset.
- Keep cleanup target validation conservative. Do not delete outside approved tmp roots.
- Do not commit after `post-merge-sentinel` exists.

## Failure modes

- If OOS disposition has accepted non-security blocks and no terminal evidence, return the same failing status and append Tool Failures.
- If security-only OOS is pending on the Python ship path, stop before PR creation with `needs_user_input=oos-filing` unless a carve-out applies.
- If checkpoint setup is invalid, return validation failure, not missing-disposition failure.
- If Step 7a diagram or log flush fails in a best-effort section, preserve the current KV and bail behavior.
- If final report cannot render, append Tool Failures and preserve existing orchestrator continuation semantics.
- If tracking issue summary upsert fails, keep local summary files and emit the current failure KV shape.
- If stall report validation sees unsafe paths, fail closed.
- If run-log append or commit fails in best-effort teardown, warn and continue only where the current script does.

## Testing strategy

- Run current shell harnesses once after Python call-site cutover and before deletion.
- Add focused pytest coverage for each absorbed script contract.
- Run:
  - `python3 -m pytest python/test_file_oos.py python/test_execution_issues.py python/test_stall_recovery.py python/test_step_7a.py python/test_finalize.py python/test_pr_body.py python/test_run_logs.py python/test_ship.py python/test_bootstrap.py`
  - `make py-lint`
  - `make py-test`
  - `make lint-retired-scripts`
  - `bash scripts/relevant-checks.sh`
- Run a stale-reference sweep:
  - grep for every retired path
  - confirm only `python/migrated-scripts.tsv` contains retired path literals, excluding allowed linter fixtures built dynamically

diff_added: 5800
diff_deleted: 7000
mechanical_churn: true
diff_lines: 12800

## Acceptance

- [ ] New Python modules: execution_issues.py, stall_recovery.py, step_7a.py implemented
- [ ] Extended modules: file_oos.py, finalize.py, pr_body.py, run_logs.py, ship.py, bootstrap.py updated
- [ ] ~30 new CLI verbs registered in python/cli.py
- [ ] All live callers cut over before bash deletion
- [ ] Bash scripts, .md siblings, and harnesses deleted
- [ ] python/migrated-scripts.tsv updated
- [ ] make lint, py-lint, py-test, lint-retired-scripts, relevant-checks.sh green

diff_lines: 12800

## Test plan
(no test plan section in plan-file)
