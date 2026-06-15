## Goal
Implement issue #3681: [IMPLEMENTING] sh-to-py C3b: design lifecycle and publish.

## Implementation Plan
## Plan

## Plan

## Scope notes

- `approach-synthesis.txt` was not present locally, but the provided synthesis is `NO_SKETCHES`.
- No approved local `design-outline.md` was present, so this plan is based on direct repository inspection plus the requested feature scope.
- Keep `/pause` markers and `docs/issue-anchored-plan.md` wire format byte-compatible.
- Gate script deletion on `make lint-retired-scripts` clean for every absorbed path and every surviving wrapper or harness that still references retired bash.
- **Pause-check exec contract**: every `.pause-requested` checkpoint in surviving wrappers must keep shell `exec` termination (or equivalent fail-closed `exit` immediately after `PAUSE_OK=true`). A plain subprocess call must not fall through. **Exception**: `design-step35-settle.sh`, which intentionally captures pause output for `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save`.
- **Result-env read contract**: retiring `lib-phase-driver.sh` must not break `scripts/read-result-env.sh` or any wrapper that sources it for allowlisted KV handoff.
- **CLI dispatch contract**: `python/cli.py` dispatches `(domain, verb)` pairs only. OOS filing uses flat verbs `design file-oos-prepare` and `design file-oos-annotate` everywhere (registry, `_MACHINE_STDOUT_KEYS`, wrappers, docs, tests). Do not use the invalid three-token shape `design file-oos prepare|annotate`.

## Approach

1. Port behavior in-place to stdlib-only Python modules.
   - Preserve exact exit codes, result-env keys, stdout KV contracts, pause marker shape, and operator text unless tests prove a current bug.
   - Use `logging_util.quiet_init`, `emit_kv`, and contract streams where shell used FD 3.
   - Use existing helpers in `proc.py`, `git.py`, `gh.py`, `run_logs.py`, `tracking_issue.py`, `plan_quality.py`, `rendering.py`, `redact.py`, and `session_env.py`.

2. Register direct CLI verbs.
   - Add `design parse-argv`.
   - Add `design route`.
   - Add `design init-runparams`.
   - Add `design driver`.
   - Add `design postplan-emit`.
   - Add `design publish`.
   - Add `design log-publish`.
   - Add `design pause-save`.
   - Add `design pause-load`.
   - Add `design render-final-summary`.
   - Add `design file-oos-prepare` and `design file-oos-annotate` (flat `(domain, verb)` tokens; no nested `file-oos` subcommand).
   - Add `design read-result-env` (thin CLI over the shared allowlist parser).
   - Add `plan step1-log` for the `/implement` Step 1 plan log helper.

3. Cut call sites directly to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" ...`.
   - Keep surviving `design-step*.sh` orchestration wrappers.
   - Do not add `.sh` shims for retired scripts.
   - Replace sourced `lib-phase-driver.sh` and `lib-design-reentry-guard.sh` usage with Python helpers inside the new modules.
   - Complete wrapper cutover inventory before deleting absorbed bash: every surviving wrapper that still `exec`s or invokes `scripts/design-pause-save.sh`, retired `file-design-oos.sh`, `render-final-summary.sh`, or sources deleted `lib-phase-driver.sh` via `read-result-env.sh` must be repointed in the same change set.
   - Repoint `scripts/read-result-env.sh` to the Python allowlist parser; do not leave it sourcing deleted bash.

4. Port harnesses to pytest before deleting shell.
   - Keep fixture behavior and names close to the current harness contracts.
   - Cover result-env symlink refusal, stdout fallback, pause/retry idempotency, quiet-mode routing, git/gh failure branches, stale reference lint, prelude `exec` pause termination, and `LARCH_DESIGN_LOG_PUBLISH` stub injection.
   - Port `scripts/test-design-reentry-guard.sh` into `python/test_design_lifecycle.py`.
   - Port `scripts/test-step0b-router-flag-recovery.sh` into `python/test_design_lifecycle.py` (or a focused pytest module) and retire the shell harness.
   - Repoint `scripts/test-render-run-summary-callsites.sh` to the Python `design render-final-summary` surface.

5. Repoint surviving offline wrapper harnesses before deleting absorbed bash.
   - Update every surviving `skills/*/scripts/test-*.sh` and `scripts/test-*-callsites.sh` that still stubs, `exec`s, or greps retired `.sh` paths while wrappers call Python.
   - Repoint `scripts/test-implement-fence-shape.sh` so `fake_run` stubs `python/cli.py plan step1-log` (or the exact launcher argv shape `bootstrap.py` emits) instead of `run-step1-plan-log.sh`.
   - Fold hard-size / drift-advisory postplan cases from `test-gate-b-apply-mode.sh` into `python/test_design_postplan.py` where practical; otherwise repoint the harness stub to `python3 python/cli.py design postplan-emit`.
   - Extend clarify harness coverage for `design log-publish` stub/assertion on the Python CLI invocation string.
   - Keep Makefile target names stable; only change underlying commands or grep pins.

6. Delete absorbed bash, markdown contract siblings, and shell harnesses after parity tests pass.
   - Record every retired path in `python/migrated-scripts.tsv`.
   - Run `make lint-retired-scripts` to force call-site cleanup.

## Files to modify/create

### NEW: python/design_argv.py

- Port `skills/design/scripts/parse-design-argv.sh`.
- Export an importable parser that returns typed parse results.
- Implement `design parse-argv [--output PATH] <public argv...>`.
- Preserve the eight success KVs and `VALIDATION_ERROR=` failure contract.
- Preserve sourceable output quoting for leading internal `--output`.

### NEW: python/test_design_argv.py

- Port `test-parse-design-argv.sh`.
- Cover legacy stdout, sourceable output, public `--output` rejection, `--` handling, numeric issue tails, verbal tails, metacharacters, quotes, and newline rejection.

### NEW: python/design_lifecycle.py

- Port `design-route.sh`, `design-init-runparams.sh`, `design-driver.sh`, `lib-phase-driver.sh`, and `lib-design-reentry-guard.sh`.
- Provide shared helpers for:
  - safe result-env writes and reads,
  - `phase_driver_read_result_env` allowlist filtering, symlink refusal, and CR/LF rejection (consumed by `design read-result-env` and import tests),
  - plugin root resolution,
  - consumer repo resolution,
  - JSON boolean fallback reads,
  - step registry validation,
  - reentry marker write and TTL hit checks.
- Implement `design route`.
- Implement `design init-runparams`.
- Implement `design driver`.
- Implement `design read-result-env`.
- Preserve route verdicts and result-env allowlists.
- Preserve action dispatch semantics, replay guards, `--resume-from`, and unknown-action failures.
- Preserve cancel-route `render_cancel_summary` behavior by calling `design render-final-summary --post-publish-only` instead of the bash script.
- Use existing `session write-design-env`, `session write-run-params`, and `tracking-issue rename` verbs instead of shell helpers.

### NEW: python/test_design_lifecycle.py

- Port `test-design-driver.sh`, `test-lib-phase-driver.sh`, `scripts/test-design-reentry-guard.sh`, and `scripts/test-step0b-router-flag-recovery.sh`.
- Port route/init coverage currently asserted by `scripts/test-design-structure.sh`.
- Port `phase_driver_read_result_env` coverage currently exercised by `scripts/test-read-result-env.sh`.
- Cover route cancel paths, resume loader parsing, title filter, reentry guard TTL, router flag merge, init contract drift, env-refresh failure, action dispatch replay behavior, and allowlisted result-env parsing.

### NEW: python/design_postplan.py

- Port `skills/design/scripts/design-postplan-emit.sh`.
- Implement `design postplan-emit --design-tmpdir PATH [--snapshot-original] [--with-plan-size]`.
- Preserve merged-mode exit codes `0`, `1`, `2`, `10`, `11`, `12`, and `13`.
- Preserve result-env keys and legacy stdout KV behavior.
- Call `design driver` for `ACTION=EMIT_PLAN`.
- Call `plan validate` and `plan check-size` through importable helpers or CLI-compatible functions.
- **Pause checkpoint split (`_postplan_pause_checkpoint`)**:
  - **Merged `--with-plan-size`**: when `.pause-requested` exists, flush result-env, emit the pause breadcrumb, and **exit `11` without calling `design pause-save`** (orchestrator-owned pause-save via wrapper rc `11` handling).
  - **Standalone (no `--with-plan-size`)**: when `.pause-requested` exists, write result-env, invoke `design pause-save`, and terminate with pause-save outcome (shell `exec` equivalent).
  - Invalid-repo pause failures preserve the existing merged vs standalone stdout/result-env split.
- **Merged `--with-plan-size` rc 2/3 contract**: on `plan check-size` rc `2` or `3`, append the warning to `execution-issues.md`, emit `POSTPLAN_EMIT_STATUS=plan-size-failed`, and exit `1` via the merged failure path (matching `_postplan_exit_merged_failure` and `design-step2b-postplan.sh` abort semantics). Do not treat merged rc 2/3 as warn-and-continue exit `0`.
- **Standalone Step 2b.5** (`design-step2b5.sh` / `python/cli.py plan check-size` only): preserve warn-and-continue exit `0` with warning append when rc is `2` or `3`.

### NEW: python/test_design_postplan.py

- Port `test-design-postplan-emit.sh`.
- Absorb hard-size and drift-advisory cases currently asserted by `skills/design/scripts/test-gate-b-apply-mode.sh`, or keep a thin harness that stubs `python3 python/cli.py design postplan-emit`.
- Cover pause checkpoint rc `11`, validator defects rc `10`, hard size rc `12`, partition rc `13`, drift advisory rc `0`, merged plan-size rc `2` and `3` exiting `1` with `POSTPLAN_EMIT_STATUS=plan-size-failed`, standalone Step 2b.5 warn-and-continue rc `0` for rc `2`/`3`, symlink result-env refusal, and quiet display separation.
- Cover **both pause branches**: merged `--with-plan-size` exits `11` without invoking pause-save; standalone path terminates through pause-save.

### NEW: python/design_publish.py

- Port `skills/design/scripts/design-publish.sh`.
- Implement `design publish`.
- Preserve composed-plan validation, redaction, named plan block write, diagram upsert, `[DESIGNED]` rename, design-log publish, final summary render, reentry marker write, and result-env write-once preservation.
- Preserve exit codes `0`, `1`, `2`, `3`, `4`, and **`5`** (`fail()` for argv/precondition/validator-infra/redaction failures).
- **In-driver pause checkpoint**: after Step 5b / `composed-plan.md` gates and **before** `plan validate`, redaction, plan write, rename, publish, or marker side effects, when `.pause-requested` exists invoke `design pause-save` and exit with pause-save outcome. Do not rely on wrapper-only pause behavior for direct publish invocations.
- Keep publish-tail failure handling fail-closed.
- Reuse `design render-final-summary`, `design log-publish`, `tracking-issue rename`, `named-block write`, `diagrams upsert`, and `redact secrets`.

### NEW: python/test_design_publish.py

- Port `test-design-publish.sh`.
- Cover validation defects, redaction failure, plan block write failure, diagram clear/update/no-op, publish skipped, publish failure with recovery branch, prior success preservation, rc `3` stdout fallback, **exit `5` cases** (missing argv, invalid repo, missing step-5b, empty plan, validator infra, redactor failure/empty output), terminal-state staging warnings, and **in-driver `.pause-requested` pause checkpoint** (publish must not run validation/redaction after pause request).

### NEW: python/design_log_publish_flow.py

- Port `scripts/design-log-publish.sh`.
- Implement `design log-publish`.
- Preserve run-id slug validation, worktree lifecycle, deny-only artifact staging, plan-review allowlist, render-cache copy, redaction pipeline, secret scrub gate, manifest refresh, pause/final reason differences, empty-porcelain final idempotency, force-with-lease behavior, PR creation, required-check registration, and `ship design-log` merge delegation.
- Use existing `git.py`, `gh.py`, `proc.py`, `run_logs.py`, `redact.py`, and `design_log_ship.py`.
- Keep subprocess boundaries for `git worktree`, `git push`, and `gh pr create`.

### NEW: python/test_design_log_publish_flow.py

- Port `scripts/test-design-log-publish.sh`.
- Cover final and pause publish paths, artifact exclusion, symlink fail-closed checks, final rebuild idempotency, manifest timestamp churn, push failure recovery branch, PR create recovery, required-check registration timeout, stale head check rows, and merge helper handoff.

### NEW: python/design_pause.py

- Port `scripts/design-pause-save.sh` and `scripts/design-pause-load.sh`.
- Implement `design pause-save`.
- Implement `design pause-load`.
- Preserve `PAUSE_OK`, `LOAD_OK`, marker payload fields, body hash behavior, marker-clear rules, cross-repo validation, recovery branch validation, local recovery branch restore, and `.pause-requested` cleanup.
- Preserve `LARCH_DESIGN_LOG_PUBLISH` override: default publish command is `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design log-publish`, but when `LARCH_DESIGN_LOG_PUBLISH` is set, use that command verbatim for pause snapshot publish (test stub injection).
- Publish pause snapshots through the resolved publish command with `--reason pause`.

### NEW: python/test_design_pause.py

- Port `test-design-pause-resume.sh`.
- Cover pause save success, publish failure, recovery-branch-only success, marker payload validation, body drift warning, retryable load failures that keep the marker, permanent failures that clear it, missing restored artifacts, local recovery branch restore, stale `.pause-requested` removal, `LARCH_DESIGN_LOG_PUBLISH` stub injection, and prelude `exec` termination (must not print a continuation marker after `PAUSE_OK=true`).

### NEW: python/design_summary.py

- Port `skills/design/scripts/render-final-summary.sh`.
- Implement `design render-final-summary`.
- Preserve outcome enum, pre/post phase behavior, final-summary file rendering, chat print path, summary upsert, degraded fallback, cost unavailable logic, Review Phase Detail appendix, OOS filed sentinel fallback, polling guard warning, and design failure report gate.
- Continue to call `scripts/render-run-summary.sh` and non-absorbed `design-failure-report.sh` out of process.

### NEW: python/test_design_summary.py

- Port `test-render-final-summary.sh`.
- Absorb the Bash 3.2 empty-array regression into Python tests where relevant.
- Cover approved, cancelled, failed, publish-skipped, fallback, cost unavailable, review detail, OOS URL fallback, accepted finding counts, and summary upsert gates.

### NEW: python/design_oos.py

- Port `skills/design/scripts/file-design-oos.sh`.
- Implement `design file-oos-prepare ...` and `design file-oos-annotate ...` as separate flat CLI verbs (not nested `file-oos` subcommands).
- Preserve cross-session cache, `oos-issues-created.md` precedence, `/issue` sentinel fallback, cap/deps pre-pass subprocess calls, atomic annotation, partial failure rc `1`, and graceful empty stdout skip.
- Preserve `oos-issue.stdout.txt` stdout handoff contract currently pinned by structure lint.
- Reuse existing `python/file_oos.py` parsing/count helpers where possible instead of duplicating them.

### NEW: python/test_design_oos.py

- Port `test-file-design-oos.sh`.
- Cover cross-session recovery, sentinel precedence, clear-cache behavior, unwritable cache warnings, annotate skip, partial failures, duplicate URLs, malformed sentinels, prepare status KVs, and `oos-issue.stdout.txt` handoff.
- Assert CLI invocation shape uses `design file-oos-prepare` / `design file-oos-annotate`.

### NEW: python/design_step_log.py

- Port `scripts/run-step1-plan-log.sh`.
- Implement `plan step1-log --implement-tmpdir PATH --goal-text TEXT`.
- Reuse `plan compose-goals-test` and `run-log write`.
- Preserve parent-issue batch refresh and best-effort failure logging.

### NEW: python/test_design_step_log.py

- Port `scripts/test-run-step1-plan-log.sh`.
- Cover run-id resolution, explicit empty goal text, missing plan, plan-goals-test output, parent-issue refresh, and log write failure diagnostics.

### UPDATED: python/cli.py

- Register all new `design` verbs and `plan step1-log`.
- Add exact `_MACHINE_STDOUT_KEYS` tuples for every KV-emitting ported verb:
  - `("design", "parse-argv")`
  - `("design", "route")`
  - `("design", "init-runparams")`
  - `("design", "driver")`
  - `("design", "postplan-emit")`
  - `("design", "publish")`
  - `("design", "pause-save")`
  - `("design", "pause-load")`
  - `("design", "log-publish")`
  - `("design", "render-final-summary")`
  - `("design", "read-result-env")`
  - `("design", "file-oos-prepare")`
  - `("design", "file-oos-annotate")`
  - `("plan", "step1-log")`
- Keep lazy imports.

### UPDATED: python/test_cli.py

- Add regression asserting every new `(design, …)` and `("plan", "step1-log")` registry entry above is present in `_MACHINE_STDOUT_KEYS`.
- Extend quiet-bypass coverage to at least one representative `design` KV verb.

### UPDATED: python/bootstrap.py

- Replace `scripts/run-step1-plan-log.sh` invocation with `python3 python/cli.py plan step1-log`.
- Preserve `run-step1-plan-log.out` capture.

### UPDATED: python/test_bootstrap.py

- Update expected Step 1 plan-log command.

### UPDATED: python/migrated-scripts.tsv

- Add every retired absorbed script, markdown sibling, and shell harness path.
- Include `scripts/test-design-reentry-guard.sh`, `scripts/test-design-reentry-guard.md`, `scripts/test-step0b-router-flag-recovery.sh`, and `scripts/test-step0b-router-flag-recovery.md`.
- Use the implementing issue id in the second column.

### UPDATED: docs/python-migration.md

- Add the C3b decision-log entry.
- State that `/design` lifecycle is now direct Python CLI.
- Note that pause/resume wire format stayed compatible.

### UPDATED: docs/issue-anchored-plan.md

- Replace pause save/load script references with `python/cli.py design pause-save` and `design pause-load`.
- Do not change marker bytes or payload fields.

### UPDATED: docs/run-logs.md

- Update design log publish references to `python/cli.py design log-publish`.

### UPDATED: docs/linting.md

- Update retired harness target descriptions where shell harnesses become pytest targets.
- Note `test-design-reentry-guard` and `test-step0b-router-flag-recovery` pytest successors.
- Note surviving wrapper harness repoint expectations for `test-design-step5c`, `test-design-step6`, `test-design-clarify`, `test-pause-skill`, `test-gate-b-apply-mode`, `test-design-step2b-drafter`, `test-design-step3-mav`, and `test-implement-fence-shape`.

### UPDATED: skills/pause/SKILL.md

- Replace `scripts/design-pause-save.sh` with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save`.
- Preserve displayed success and failure parsing.

### UPDATED: skills/design/SKILL.md

- Replace absorbed script references with Python CLI commands.
- Keep `/design` inline-only.
- Update Step 0, Step 2b, Step 5b, Step 5c, final summary, and contract catalog text.
- Use flat OOS verbs `design file-oos-prepare` and `design file-oos-annotate` in Step 5b examples.
- Keep operator-visible flow unchanged.

### UPDATED: skills/design/references/flags.md

- Replace parser and postplan script references with Python CLI equivalents.
- Keep public flag semantics unchanged.

### UPDATED: skills/design/references/approval-gates.md

- Replace postplan and publish script references with Python CLI equivalents.
- Preserve Gate B and Gate C behavior.

### UPDATED: skills/design/references/discussion-rounds.md

- Update postplan re-emit references.

### UPDATED: skills/design/references/decompose-panel.md

- Update postplan plan-size handoff references if present.

### UPDATED: skills/design/references/design-outline.md

- Update final-summary guidance to name the Python CLI helper.

### UPDATED: scripts/read-result-env.sh

- Remove `source` of `skills/design/scripts/lib-phase-driver.sh`.
- Delegate allowlisted KV parsing to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design read-result-env` (or an importable helper with identical semantics).
- Preserve fallback-input logic, WARN/ERROR stdout replay, single-quote encoding, usage text, and exit behavior consumed by route/init/publish/clarify/mav wrappers.

### UPDATED: scripts/test-read-result-env.sh

- Repoint subject behavior checks to the Python-backed parser while preserving symlink refusal, allowlist filtering, fallback-input, and sourceable output contracts.

### UPDATED: skills/design/scripts/design-step0-parse.sh

- **Remove** the `-x` executable guard on retired `parse-design-argv.sh`.
- Invoke `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design parse-argv --output "$_argv_env" ...` with the same stdout/stderr capture and env sourcing.
- Refresh operator error strings to name the Python CLI surface.
- Preserve the contract pin comment shape for `test-design-structure.sh`.

### UPDATED: skills/design/scripts/design-step0-route.sh

- Call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design route`.
- Replace the `.pause-requested` pause-check line with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Keep `read-result-env.sh` handoff unchanged aside from the Python-backed parser.

### UPDATED: skills/design/scripts/design-step0-init.sh

- Call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design init-runparams`.
- Replace the `.pause-requested` pause-check line with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step-prelude.sh

- Replace pause-check `exec` of `scripts/design-pause-save.sh` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step2a.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step1d7.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step2b5.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step2b-postplan.sh

- Call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design postplan-emit`.
- Preserve wrapper-owned pause routing:
  - Pre-delegation `.pause-requested` and postplan rc `11` from merged `--with-plan-size` still emit `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save` then `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save ...`.
  - Do **not** move merged-mode pause-save into postplan; Python merged postplan exits `11` for orchestrator-owned pause-save.
- Preserve rc handling for `10`, `11`, `12`, and `13`.

### UPDATED: skills/design/scripts/design-step3-entry-state.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3-entry-preview.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3-continuation-entry.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3-review.sh

- Replace both pause-check `exec` sites with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3b-entry.sh

- Replace `design-driver.sh` call with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design driver`.
- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3b-sanitize.sh

- Replace `design-driver.sh` call with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design driver`.
- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3b-tail.sh

- Replace `design-driver.sh` call with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design driver`.
- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step5b-prepare.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Replace `file-design-oos.sh prepare` with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design file-oos-prepare`.
- Preserve stdout capture to `oos-filing-prepare.env`, stderr log, `STEP5B_STATUS` rows, and prepare-failed-continue semantics.

### UPDATED: skills/design/scripts/design-step5b-annotate.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Replace `file-design-oos.sh annotate` with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design file-oos-annotate`.
- Preserve stdout capture, `STEP5B_STATUS=annotate-failed` on non-zero, and `.completed/step-5b` withholding on failure.

### UPDATED: skills/design/scripts/design-step5c.sh

- Call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design publish`.
- Replace wrapper pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Replace **both** direct `render-final-summary.sh` invocations (publish-tail abort path and any remaining wrapper-owned render) with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design render-final-summary`.
- Preserve rc `1`, `2`, `3`, `4`, and **hard-abort semantics for rc `5`** (publish-tail abort via `abort_failed_publish_tail`).
- Rely on `design publish` in-driver pause checkpoint for publish-side validation/redaction gates.

### UPDATED: skills/design/scripts/design-step-final-summary.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Replace `render-final-summary.sh` with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design render-final-summary`.
- Preserve stdout capture to `render-final-summary.stdout.log`, marker emission, and report-gate sidecar handoff.

### UPDATED: skills/design/scripts/design-clarify.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.
- Replace design log publish calls with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design log-publish`.
- Preserve clarify failure logging and `read-result-env.sh` handoff.

### UPDATED: skills/design/scripts/design-step0-ap-continue.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step0-clarify-hard-halt.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step0c.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step1d5.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step1e-reentry.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step2b-drafter.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step2b-prelude.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3-gate-b-bypass.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step3-mav.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step35.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step35-settle.sh

- Replace direct `design-pause-save.sh` invocation with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save` **without** `exec` (capture stdout for `POSTPLAN_RC=11` / `POSTPLAN_STATUS=pause-save`).
- Preserve pause-signal semantics.

### UPDATED: skills/design/scripts/design-step6-cleanup.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step6-prelude.sh

- Replace both pause-check `exec` sites with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh

- Replace pause-check `exec` with `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}`.

### UPDATED: skills/design/scripts/test-design-step5c.sh

- Repoint publish/render stubs from `design-publish.sh` / `render-final-summary.sh` to CLI-shaped stubs or greps for `python/cli.py design publish` and `design render-final-summary`.
- Preserve result-env fallback, publish-tail abort, and `read-result-env.sh` symlink handoff cases.

### UPDATED: skills/design/scripts/test-design-step6.sh

- Repoint pause stub from `scripts/design-pause-save.sh` to a `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save` stub path (or monkeypatched launcher) that preserves `PAUSE_OK` parsing.

### UPDATED: skills/design/scripts/test-design-clarify.sh

- Repoint pause/log-publish stubs to Python CLI invocation strings.
- Add or refresh a `design log-publish` stub case and assertions for the `python3 ... design log-publish` command shape.

### UPDATED: skills/design/scripts/test-design-step2b-drafter.sh

- Repoint pause/postplan stubs from retired bash paths to `design pause-save` / `design postplan-emit` CLI stubs.
- Preserve assertion that the drafter wrapper does not call absorbed postplan bash directly.

### UPDATED: skills/design/scripts/test-design-step3-mav.sh

- Repoint `design-pause-save.sh` fake plugin stubs to `python/cli.py design pause-save` stubs.

### UPDATED: skills/design/scripts/test-gate-b-apply-mode.sh

- Repoint `design-postplan-emit.sh` subject/stub to `python3 python/cli.py design postplan-emit` (or retire duplicated cases once folded into `python/test_design_postplan.py`).
- Preserve hard-size and drift-advisory result-env assertions.

### UPDATED: skills/pause/scripts/test-pause-skill.sh

- Repoint fake `scripts/design-pause-save.sh` stubs to a `python/cli.py design pause-save` stub surface while preserving SKILL.md success/failure parsing behavior.

### UPDATED: scripts/test-implement-fence-shape.sh

- Repoint `fake_run` stub from `run-step1-plan-log.sh` to `python/cli.py plan step1-log` (match the argv shape `bootstrap.py` emits after cutover).
- Preserve resume-bootstrap fence-shape assertions.

### UPDATED: Makefile

- Switch migrated harness targets to `pytest` modules through `timing harness-mark`.
- Repoint `test-design-reentry-guard` to `python/test_design_lifecycle.py`.
- Repoint `test-step0b-router-flag-recovery` to `python/test_design_lifecycle.py`.
- Remove `test-render-final-summary-bash32` or make it an alias to `python/test_design_summary.py` if target stability is needed.
- Keep shard membership stable where possible; surviving wrapper harness targets keep their names but run repointed scripts.

### UPDATED: scripts/relevant-checks.sh

- Route changed Python modules and surviving wrappers to the new pytest-backed targets.
- Map `python/design_lifecycle.py` for router-flag recovery, reentry-guard, and read-result-env coverage.
- Map `python/bootstrap.py` changes to `test-implement-fence-shape` (in addition to existing bootstrap targets).
- Map surviving wrapper harness edits (`test-design-step5c`, `test-design-step6`, `test-design-clarify`, `test-pause-skill`, `test-gate-b-apply-mode`, `test-design-step2b-drafter`, `test-design-step3-mav`, `test-implement-fence-shape`) to their Make targets.
- Remove retired shell path cases after manifest entries land.

### UPDATED: scripts/test-relevant-checks.sh

- Update fixtures and assertions for the new relevant-check mappings (including bootstrap → `test-implement-fence-shape`).

### UPDATED: scripts/test-design-structure.sh

- Replace script-path greps with CLI-command shape checks for surviving wrappers.
- Update Step 0 parse wrapper pins (`design parse-argv`, no `-x` guard on retired bash).
- Repoint `FILE_OOS_MD` (or equivalent contract grep) from retired `skills/design/scripts/file-design-oos.md` to `python/design_oos.py` and/or `skills/design/scripts/design-step5b-prepare.sh`, preserving the `oos-issue.stdout.txt` handoff invariant.
- Add grep pins that Step 5b wrappers call `design file-oos-prepare` / `design file-oos-annotate` (flat verbs).
- Add grep pins that pause-check sites use `exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save` (excluding `design-step35-settle.sh`).
- Remove assertions against deleted absorbed scripts.
- Keep pause-ordering pins against surviving wrappers.

### UPDATED: scripts/test-design-multi-round-integration.sh

- Replace design log publish script invocations with `python3 python/cli.py design log-publish`.

### UPDATED: scripts/test-design-multi-round-integration.md

- Update referenced helper names.

### UPDATED: scripts/test-render-cost-line-callsites.sh

- Update render-final-summary call-site checks to the Python CLI surface or remove obsolete Bash-specific checks.

### UPDATED: scripts/test-render-run-summary-callsites.sh

- Repoint greps from `skills/design/scripts/render-final-summary.sh` to `python/design_summary.py` or the `design render-final-summary` CLI registration.
- Preserve `--claude-input-tokens` forwarding contract pins against `render-run-summary.sh`.

## Retired paths

Delete these after call-site cutover and pytest parity:

- `skills/design/scripts/parse-design-argv.sh`
- `skills/design/scripts/parse-design-argv.md`
- `skills/design/scripts/test-parse-design-argv.sh`
- `skills/design/scripts/test-parse-design-argv.md`
- `skills/design/scripts/design-route.sh`
- `skills/design/scripts/design-route.md`
- `skills/design/scripts/design-init-runparams.sh`
- `skills/design/scripts/design-init-runparams.md`
- `skills/design/scripts/design-driver.sh`
- `skills/design/scripts/design-driver.md`
- `skills/design/scripts/test-design-driver.sh`
- `skills/design/scripts/test-design-driver.md`
- `skills/design/scripts/lib-phase-driver.sh`
- `skills/design/scripts/lib-phase-driver.md`
- `skills/design/scripts/test-lib-phase-driver.sh`
- `skills/design/scripts/test-lib-phase-driver.md`
- `skills/design/scripts/design-postplan-emit.sh`
- `skills/design/scripts/design-postplan-emit.md`
- `skills/design/scripts/test-design-postplan-emit.sh`
- `skills/design/scripts/test-design-postplan-emit.md`
- `skills/design/scripts/design-publish.sh`
- `skills/design/scripts/design-publish.md`
- `skills/design/scripts/test-design-publish.sh`
- `skills/design/scripts/test-design-publish.md`
- `scripts/design-log-publish.sh`
- `scripts/design-log-publish.md`
- `scripts/test-design-log-publish.sh`
- `scripts/test-design-log-publish.md`
- `scripts/design-pause-save.sh`
- `scripts/design-pause-save.md`
- `scripts/design-pause-load.sh`
- `scripts/design-pause-load.md`
- `skills/design/scripts/test-design-pause-resume.sh`
- `skills/design/scripts/test-design-pause-resume.md`
- `scripts/lib-design-reentry-guard.sh`
- `scripts/lib-design-reentry-guard.md`
- `scripts/test-design-reentry-guard.sh`
- `scripts/test-design-reentry-guard.md`
- `scripts/test-step0b-router-flag-recovery.sh`
- `scripts/test-step0b-router-flag-recovery.md`
- `skills/design/scripts/render-final-summary.sh`
- `skills/design/scripts/render-final-summary.md`
- `skills/design/scripts/test-render-final-summary.sh`
- `skills/design/scripts/test-render-final-summary.md`
- `scripts/test-render-final-summary-bash32.sh`
- `scripts/test-render-final-summary-bash32.md`
- `skills/design/scripts/file-design-oos.sh`
- `skills/design/scripts/file-design-oos.md`
- `skills/design/scripts/test-file-design-oos.sh`
- `skills/design/scripts/test-file-design-oos.md`
- `scripts/run-step1-plan-log.sh`
- `scripts/run-step1-plan-log.md`
- `scripts/test-run-step1-plan-log.sh`
- `scripts/test-run-step1-plan-log.md`

## Edge cases

- Result-env paths may be symlinks, directories, unwritable, or concurrently written.
- `DESIGN_TMPDIR` and `IMPLEMENT_TMPDIR` may fail allowlist validation.
- Pause markers may have body drift, repo mismatch, missing snapshots, local recovery branches, or stale `.pause-requested`.
- Design log publish may race default-branch movement, stale PR heads, missing required checks, branch reuse, or worktree collisions.
- Plan-review and render-cache trees may contain symlinks or unexpected files.
- Redaction may produce empty output or fail on binary-like content.
- Existing `PUBLISH_OK=true` must preserve authoritative publish metadata without skipping required current-side effects.
- Merged postplan plan-size rc `2`/`3` must abort `/design`; standalone Step 2b.5 must continue.
- Merged postplan pause must exit `11` without in-driver pause-save; standalone postplan and `design publish` must invoke pause-save before side effects.
- `design publish` exit `5` must reach Step 5c publish-tail hard abort, not be treated as a soft continuation code.
- `LARCH_DESIGN_LOG_PUBLISH` must continue to override the pause publish command for harness stubbing.
- OOS wrappers must use flat `design file-oos-prepare` / `design file-oos-annotate`; three-token `design file-oos prepare` will not dispatch.
- Pause-check subprocess fall-through after `PAUSE_OK=true` breaks `/design` resume semantics; only `design-step35-settle.sh` may capture pause output without `exec`.

## Failure modes

- Treat GitHub, git, and validation infrastructure failures fail-closed where current shell does.
- Keep expected pause/load failures structured as `PAUSE_OK=false` or `LOAD_OK=false`.
- Keep postplan drift advisory non-fatal.
- Keep OOS annotate partial failure as rc `1`.
- Keep design-log publish with `PUBLISH_OK=false` plus recovery metadata resumable for pause.
- Do not make final summary rendering failure fatal when the current fallback writes a valid degraded summary.
- Incomplete wrapper cutover before deletion leaves runtime `exec` failures across `/design` pause checkpoints, Step 5b OOS, terminal final-summary fences, and result-env reads on route/init/publish/clarify/mav paths.
- Missing `_MACHINE_STDOUT_KEYS` entries silently swallow KV stdout under quiet wrappers, causing Step 0/2b/5c mis-routing without loud failure.
- Surviving harnesses that still grep or stub retired bash fail `make test-harnesses` even when Python ports are correct.
- `test-implement-fence-shape.sh` still stubbing `run-step1-plan-log.sh` after bootstrap cutover causes silent resume-bootstrap coverage drift.

## Testing strategy

- Run focused pytest:
  - `python3 -m pytest python/test_design_argv.py`
  - `python3 -m pytest python/test_design_lifecycle.py`
  - `python3 -m pytest python/test_design_postplan.py`
  - `python3 -m pytest python/test_design_publish.py`
  - `python3 -m pytest python/test_design_log_publish_flow.py`
  - `python3 -m pytest python/test_design_pause.py`
  - `python3 -m pytest python/test_design_summary.py`
  - `python3 -m pytest python/test_design_oos.py`
  - `python3 -m pytest python/test_design_step_log.py`
  - `python3 -m pytest python/test_cli.py -k machine_stdout`
- Run affected Make targets:
  - `make test-parse-design-argv`
  - `make test-design-driver`
  - `make test-lib-phase-driver`
  - `make test-design-reentry-guard`
  - `make test-step0b-router-flag-recovery`
  - `make test-design-postplan-emit`
  - `make test-design-publish`
  - `make test-design-log-publish`
  - `make test-design-pause-resume`
  - `make test-render-final-summary`
  - `make test-render-run-summary-callsites`
  - `make test-render-cost-line-callsites`
  - `make test-file-design-oos`
  - `make test-run-step1-plan-log`
  - `make test-read-result-env`
  - `make test-design-structure`
  - `make test-relevant-checks`
  - `make test-design-step5c`
  - `make test-design-step6`
  - `make test-design-clarify`
  - `make test-pause-skill`
  - `make test-gate-b-apply-mode`
  - `make test-design-step2b-drafter`
  - `make test-design-step3-mav`
  - `make test-implement-fence-shape`
- Run migration and full gates:
  - `make lint-retired-scripts`
  - `make py-lint`
  - `make py-test`
  - `bash scripts/relevant-checks.sh`
  - `make lint`
  - `make test-harnesses`

diff_added: 12050
diff_deleted: 15250
mechanical_churn: true
diff_lines: 27300

## Acceptance

- All 9 Python modules importable and registered in `python/cli.py`.
- All call sites in surviving wrapper `.sh` files cut to `python3 python/cli.py design <verb>`.
- All absorbed bash scripts + `.md` siblings + test harnesses deleted.
- `python/migrated-scripts.tsv` updated with all retired paths.
- `make lint-retired-scripts` exits 0.
- `make py-lint` exits 0.
- `make py-test` exits 0.
- `make lint` exits 0.

diff_lines: 27300

## Test plan
(no test plan section in plan-file)
