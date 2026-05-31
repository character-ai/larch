### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-cursor-implement.sh:291-326	Plan background and launch-cursor-implement step treat cursor-implement as capture-stdout with run-external-agent producing a good ${TRANSCRIPT_PATH}.stderr-tail; code uses --capture-stdout-only with run-external-agent backgrounded and agent I/O merged to SIDECAR_LOG (2>&1), so select_failed_agent_stderr_source never reads SIDECAR_LOG and may tail .diag or an empty/partial transcript instead of agent stderr.	Failed cursor implement runs surface transcript or generic diag in chat while real stderr stays in SIDECAR_LOG only; consumer-only step2 emit_bailed change is insufficient.	In launch-cursor-implement.sh failure block (mirror codex-implement), add write_failed_agent_stderr_tail from SIDECAR_LOG or _FAILURE_OUTPUT onto TRANSCRIPT_PATH; tighten plan Background and ### UPDATED: launch-cursor-implement.sh to require this producer unless a harness proves SIDECAR-sourced bytes in the tail file.
1	in_scope	important	correctness	scripts/ship-pr.sh:2049-2075	ship-pr.sh fix-loop passes --output "$tier_out" but the plan only names $output for _surface_ci_stderr_tail at the primary CI-launcher site.	Implementer passes recovery-waterfall $output at the fix-loop choke point; emit_failed_agent_stderr_tail_larch_err looks for the wrong stem and chat stays silent despite ${tier_out}.stderr-tail on disk.	Spell the fix-loop stem explicitly ($tier_out) in ### UPDATED: scripts/ship-pr.sh and call _surface_ci_stderr_tail "$tier_out" on the failure branch before _ci_fix_rollback/continue (including first-fixer-non-health return at ~2081 if that path skips the generic failure block).

**1. [correctness]** `scripts/launch-cursor-implement.sh:291-326` — The plan’s Background claims cursor-implement already gets `${TRANSCRIPT}.stderr-tail` via `--capture-stdout`. The launcher uses `--capture-stdout-only` and backgrounds `run-external-agent` with `>SIDECAR_LOG 2>&1`, so agent stderr lives in `SIDECAR_LOG`, not in paths `select_failed_agent_stderr_source` considers. Verification that only checks the flag name can skip the producer write; `step2-implement.sh` consumer-only work would then emit a missing or wrong tail. **Revision:** Add the same on-failure `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH"` pattern as codex-implement (or `_FAILURE_OUTPUT`), and update the plan so cursor-implement is not described as producer-complete by default.

**2. [correctness]** `scripts/ship-pr.sh:2049-2075` — Recovery waterfall correctly uses `$output`; the primary CI fix loop uses `$tier_out="${ci_fix_out_base}.${tier}"` for `--output`. The plan’s ship-pr helper call sites only reference `$output`. **Revision:** Document and implement `_surface_ci_stderr_tail "$tier_out"` on the fix-loop failure path before rollback/continue.

[OUT_OF_SCOPE] `scripts/ship-pr.sh:3278-3290` — `launch-*-ci.sh resolve-conflict` failures record via `record_failure` but are outside the plan’s “at minimum” choke points; same tail-swallow gap as other CI launchers if parity is wanted later.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/lint-fix-loop.sh:252-258	Planned `run_cursor` producer uses `cursor.wrapper.log` but `--capture-stdout` already tails `cursor.log`	`run-external-agent.sh` writes `${run_dir}/cursor.log.stderr-tail` from merged agent output; `write_failed_agent_stderr_tail` on `cursor.wrapper.log` can overwrite it with wrapper chatter only	After verifying non-zero exit, consumer-only `emit_failed_agent_stderr_tail_larch_err "$run_dir/cursor.log" || true`; add `write_failed_agent_stderr_tail` only if that tail file is missing, sourcing `cursor.log` not `cursor.wrapper.log`
1	in_scope	important	correctness	skills/implement/scripts/launch-cursor-implement.sh:291-303	Plan checks `--capture-stdout`; launcher uses `--capture-stdout-only` plus outer `>SIDECAR_LOG 2>&1`	Mis-verification may add `write_failed_agent_stderr_tail "$SIDECAR_LOG" …` and clobber a good `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`/transcript with wrapper noise	Verify `${TRANSCRIPT_PATH}.stderr-tail` after failure; if present, consumer-only via `step2-implement.sh`; if absent, write from `${TRANSCRIPT_PATH}.diag` or `$SIDECAR_LOG`, not assume `--capture-stdout`

1. **(correctness)** `scripts/lint-fix-loop.sh:252-258` — The plan’s `run_cursor` failure path would call `write_failed_agent_stderr_tail` on `cursor.wrapper.log`, but `run-external-agent.sh` with `--capture-stdout` already builds `${run_dir}/cursor.log.stderr-tail` from agent output. The outer `>cursor.wrapper.log 2>&1` redirect only captures the wrapper’s progress stream. A producer write from the wrapper log can replace a useful tail with weaker content. Prefer emit-only when the tail file exists; if a write is needed, use `cursor.log` (or skip write when REA already produced the tail).

2. **(correctness)** `skills/implement/scripts/launch-cursor-implement.sh:291-303` — The plan tells implementers to verify `--capture-stdout`, but the launcher uses `--capture-stdout-only` and backgrounds `run-external-agent.sh` with `>SIDECAR_LOG 2>&1`. On failure, `run-external-agent.sh` should already write `${TRANSCRIPT_PATH}.stderr-tail` from `.diag`/transcript. Treating this like codex-implement and always writing from `$SIDECAR_LOG` risks clobbering that tail. Verification should be “tail file exists after failure,” not “uses `--capture-stdout`.”

[OUT_OF_SCOPE] `scripts/ship-pr.sh:3278-3290` — `launch-cursor-ci.sh` / `launch-codex-ci.sh` resolve-conflict failures capture to `fail_file` with `2>&1` but are outside the plan’s “at minimum” CI choke points; same stderr-tail surfacing gap as other CI paths if operators debug conflict resolution only.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	risk-integration	scripts/ship-pr.sh:123-127	`lint-fix-loop.sh` stderr is redirected to `fail_file`	`emit_failed_agent_stderr_tail_larch_err` inside `run_codex`/`run_cursor` lands in `fail_file`, not chat, for ship-pr CI/checks paths; isolated `test-lint-fix-loop.sh` can still pass	After the `lint-fix-loop.sh` call (or in `_rcc_handle_fix_status`), surface `${run_dir}/codex.log.stderr-tail` or `${run_dir}/cursor.log.stderr-tail` via `_surface_ci_stderr_tail` / `emit_failed_agent_stderr_tail_larch_err` using `LINT_FIX_RUN_DIR`/`CODER_LOG_FILE` from stdout when present; keep in-loop emit only for orchestrator-direct invocations
1	in_scope	important	correctness	scripts/lint-fix-loop.sh:252-258	`run_cursor` uses `--capture-stdout`	`run-external-agent.sh` already writes `${run_dir}/cursor.log.stderr-tail` on failure; an unconditional `write_failed_agent_stderr_tail` from `cursor.wrapper.log` can clobber with wrapper/progress noise	Match codex-ci/cursor-implement: verify mode first; on failure emit only if `${run_dir}/cursor.log.stderr-tail` is missing, then producer-write from the real capture path
1	in_scope	important	correctness	plan.txt:11-12	Background mislabels cursor lanes as `--capture-stdout`	`launch-cursor-implement.sh` and `launch-cursor-ci.sh` use `--capture-stdout-only`; implementer may add redundant/wrong producer writes	Fix the background bullet; in `launch-cursor-implement.sh` verification, require `--capture-stdout-only` and treat existing `${TRANSCRIPT_PATH}.stderr-tail` as sufficient before any producer edit
1	out_of_scope	latent	risk-integration	scripts/ship-pr.sh:3278-3290	Resolve-conflict CI launches omitted from `_surface_ci_stderr_tail`	Failed `launch-*-ci.sh resolve-conflict` runs capture launcher output to `fail_file` with the same swallow pattern as the fix loop	Extend the ship-pr helper call list to these failure choke points when #3227 scope is expanded

**1. ship-pr swallows lint-fix tails (risk-integration)**  
`ship-pr.sh` runs `lint-fix-loop.sh` with `2>"$fail_file"`. Any `emit_failed_agent_stderr_tail_larch_err` inside `run_codex`/`run_cursor` goes to `fail_file`, not chat. `/implement` Steps 3/5/6 call the loop directly and are fine; ship-pr CI paths are not. The plan’s `test-lint-fix-loop.sh` case won’t catch this.

**2. lint-fix `run_cursor` may clobber tails (correctness)**  
`run_cursor` uses `--capture-stdout`, so `run-external-agent.sh` should already write `${run_dir}/cursor.log.stderr-tail`. The plan’s unconditional write from `cursor.wrapper.log` conflicts with Failure mode #1 in the same plan.

**3. Plan background misstates cursor capture mode (correctness)**  
Background claims cursor-ci/implement use `--capture-stdout`; both launchers use `--capture-stdout-only`. The per-file verification step is right; the background line is misleading.

**[OUT_OF_SCOPE]** Resolve-conflict launches at `ship-pr.sh:3278-3290` are not in the plan’s “at minimum” CI sites; same tail-swallow pattern as the fix loop.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/lint-fix-loop.sh:242-259	Plan adds on-failure tail write/emit inside run_cursor but the function never propagates run-external-agent exit status	Cursor agent failures still make run_cursor succeed; the proposed write/emit branch never runs and lint-fix cursor failures stay silent	Add cursor_rc capture and return (mirror run_codex: `|| cursor_rc=$?` then `return "$cursor_rc"`) before relying on in-function failure hooks
2	in_scope	important	risk-integration	scripts/lint-fix-loop.sh:252-258	Plan sources stderr tail from cursor.wrapper.log while run_cursor uses --capture-stdout on $run_dir/cursor.log	On failure, run-external-agent already builds ${run_dir}/cursor.log.stderr-tail from agent output; rewriting from wrapper.log can clobber a good tail with launcher progress noise	Prefer emit_failed_agent_stderr_tail_larch_err on the existing stem only; add write_failed_agent_stderr_tail from wrapper.log only if verification shows no usable .stderr-tail
3	in_scope	important	correctness	scripts/launch-cursor-implement.sh:291-326	skills/implement/scripts/step2-implement.sh:264-274	Plan verifies --capture-stdout but launcher uses --capture-stdout-only with cursor redirected to SIDECAR_LOG, not ${TRANSCRIPT}.sidecar	Implementer may skip producer work; run-external-agent may tail transcript/diag while real errors sit in SIDECAR, so step2 emit_bailed surfaces a weak or empty tail	In launch-cursor-implement.sh failure block, write_failed_agent_stderr_tail from SIDECAR_LOG or the same _FAILURE_OUTPUT used for append_launch_failure (mirror codex-implement); keep step2 consumer-only emit
4	out_of_scope	latent	architecture	scripts/ship-pr.sh:3278-3289	CI resolve-conflict launcher failures are not listed for _surface_ci_stderr_tail	Operators debugging merge-conflict CI tiers still get no chat tail while fix-loop and recovery-waterfall lanes do	Track separately; wire _surface_ci_stderr_tail at resolve-conflict failure exits if parity is desired
5	out_of_scope	latent	correctness	scripts/ship-pr.sh:2076-2082	first-fixer-non-health early return leaves CI fix loop before _surface_ci_stderr_tail	First-tier non-health bail returns without surfacing ${tier_out}.stderr-tail even when the launcher wrote one	Track separately; call _surface_ci_stderr_tail "$tier_out" before state_set_many/return 1

**1. [correctness]** `scripts/lint-fix-loop.sh:242-259` — The plan puts tail write/emit “on non-zero” inside `run_cursor`, but `run_cursor` never returns `run-external-agent`’s exit code (unlike `run_codex`, which uses `codex_rc`). Cursor failures still look successful to the `if run_cursor …; then` caller, so the new failure branch is dead code until return propagation is fixed.

**2. [risk-integration]** `scripts/lint-fix-loop.sh:252-258` — `run_cursor` already passes `--capture-stdout` with stem `$run_dir/cursor.log`, so `run-external-agent.sh` should produce `${run_dir}/cursor.log.stderr-tail` on agent failure. The plan’s producer step uses `cursor.wrapper.log`, which mostly holds the wrapper’s merged stdout/stderr, matching the plan’s own “wrong-source tail” failure mode. Prefer consumer-only emit unless verification proves the file is missing.

**3. [correctness]** `scripts/launch-cursor-implement.sh:291-326` / `skills/implement/scripts/step2-implement.sh:264-274` — Background plan text says cursor-implement uses `--capture-stdout`; the launcher uses `--capture-stdout-only` and sends agent output to `SIDECAR_LOG`, not `${TRANSCRIPT_PATH}.sidecar`. Verification keyed only to `--capture-stdout` risks a no-op producer while `select_failed_agent_stderr_source` tails transcript/diag. Add an explicit failure-block `write_failed_agent_stderr_tail` from `SIDECAR_LOG` / `_FAILURE_OUTPUT` (same sources as `append_launch_failure`), then keep `emit_failed_agent_stderr_tail_larch_err` in `emit_bailed`.

**[OUT_OF_SCOPE] 4.** `scripts/ship-pr.sh:3278-3289` — `launch-cursor-ci.sh` / `launch-codex-ci.sh` resolve-conflict paths are outside the plan’s choke-point list; tails may still be missing there.

**[OUT_OF_SCOPE] 5.** `scripts/ship-pr.sh:2076-2082` — `first-fixer-non-health` returns before any `_surface_ci_stderr_tail` call at the normal `record_failure` sites (~2074).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/review-and-fix/scripts/review-implement-step5-loop.sh:241-244	Plan does not require capturing STDERR_TAIL_PATH before lint_out is removed	Implementer may parse STDERR_TAIL_PATH only inside case branches after `rm -f "$lint_out"`, losing the KV and skipping caller-scope tail emit on step5 lint-fix failures	Add an explicit plan step: parse STDERR_TAIL_PATH (and optional CODER_LOG_FILE fallback) into a variable during or immediately after `step5_parse_lint_capture_file`, before `rm -f "$lint_out"`, then call `emit_failed_agent_stderr_tail_larch_err` from that stem on terminal statuses

1. **correctness** (`skills/review-and-fix/scripts/review-implement-step5-loop.sh:241-244`): The plan says to parse `STDERR_TAIL_PATH=` from `$lint_out` on terminal lint-fix outcomes, but the script deletes `$lint_out` right after `step5_parse_lint_capture_file` and before the `case` on `STEP5_LINT_STATUS`. `emit_failed_agent_stderr_tail_larch_err` needs the stem from stdout KV, not the capture file, so the stem must be saved before `rm -f "$lint_out"`. Revise the plan to require parsing `STDERR_TAIL_PATH` (or the `CODER_LOG_FILE` fallback) into a shell variable before removing `$lint_out`, then emit from that stem in each terminal branch.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/review-and-fix/scripts/review-implement-step5-loop.sh:243-245	Step5 deletes lint capture before tail stem can be read	Plan says parse STDERR_TAIL_PATH from $lint_out on terminal failure, but the script removes $lint_out immediately after step5_parse_lint_capture_file (which only reads LINT_FIX_STATUS). Emitting in the case arms after rm -f leaves no capture file to parse; CODER_LOG_FILE fallback is absent on dispatch-failed.	main-agent-required / failed / lint-fix terminal exits never surface stderr tails in Step 5	Extend step5_parse_lint_capture_file to stash STEP5_STDERR_TAIL_STEM from STDERR_TAIL_PATH (and optional CODER_LOG_FILE) while $lint_out still exists, then rm; call emit_failed_agent_stderr_tail_larch_err on that stem in each terminal case arm (or one shared helper) before step5_emit_final_envelope / exit 2.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:2728-2747	Recovery waterfall gates `_surface_ci_stderr_tail` on `tier_rc -ne 0`, but `launch-codex-ci.sh` / `launch-cursor-ci.sh` always `exit 0` and encode agent failure in `LAUNCHER_EXIT` KV on stdout (discarded via `>/dev/null`)	Agent failure in recovery still leaves `${output}.stderr-tail` on disk (from `run-external-agent.sh`) while `tier_rc` stays 0, so the planned surfacing never runs and chat stays silent on a documented lane	Surface when `${output}.stderr-tail` is non-empty after each tier attempt (or capture launcher stdout and treat non-zero `LAUNCHER_EXIT` like the CI fix-loop), not only when `tier_rc -ne 0`
2	in_scope	latent	correctness	scripts/ship-pr.sh:2728-2747	Testing strategy covers CI fix-loop `$tier_out` and `run_lint_fix_loop_capture` but not recovery-waterfall tail surfacing	No regression if recovery trigger logic is wrong or regresses to `tier_rc`-only	Add a `test-ship-pr.sh` case: stub recovery-tier launcher that exits 0 with non-zero `LAUNCHER_EXIT` and a prebuilt `${output}.stderr-tail`; assert fenced tail reaches caller stderr

**1. [correctness]** `scripts/ship-pr.sh:2728-2747` — Recovery waterfall gates `_surface_ci_stderr_tail` on `tier_rc -ne 0`, but CI launchers always `exit 0` and put failure in `LAUNCHER_EXIT` on stdout (which recovery discards with `>/dev/null`). Agent failure can leave `${output}.stderr-tail` on disk while `tier_rc` stays 0, so planned surfacing never runs. **Suggested revision:** surface when `${output}.stderr-tail` is non-empty after each tier attempt, or capture launcher stdout and treat non-zero `LAUNCHER_EXIT` like the CI fix-loop.

**2. [correctness]** `scripts/ship-pr.sh:2728-2747` — Tests cover fix-loop `$tier_out` and `run_lint_fix_loop_capture` but not recovery-waterfall surfacing. **Suggested revision:** add a `test-ship-pr.sh` recovery case with exit-0 launcher, non-zero `LAUNCHER_EXIT`, and a prebuilt `.stderr-tail`.

Against the filed feature description (`description.txt` Gap 1–2): implement codex/cursor producer + `step2-implement.sh` consumer, plan-review FD-2 harness, and CI fix-loop `$tier_out` surfacing (including first-fixer-non-health `return 1`) are covered. Gap 2’s “panel reviewer” wording is looser than the collector-tee test, but the test matches the real regression at `plan-review-loop.sh:752-762`. Lint-fix producer/consumer split, `STDERR_TAIL_PATH`, `run_cursor` rc propagation, and `SECURITY.md` are aligned. No material scope-creep findings beyond the expanded CI/lint-fix scope already stated in the plan title.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-routing-chain-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-codex-implement.sh:290-300	Producer write only after auth-retry loop; MODEL_ARGS preflight exits early	MODEL_ARGS failure fills SIDECAR_LOG but never writes ${TRANSCRIPT_PATH}.stderr-tail; step2 emit_bailed only emits from that file	Add write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true on the MODEL_ARGS_RC exit path (same as post-loop failure block)
2	in_scope	important	correctness	scripts/launch-cursor-implement.sh:237-272	Plan marks cursor-implement producer no-op; early exits skip run-external-agent	MODEL_ARGS and auth preflight failures populate SIDECAR_LOG and exit 0 with non-zero LAUNCHER_EXIT but run-external-agent never runs, so no ${TRANSCRIPT_PATH}.stderr-tail; step2 consumer-only emit stays silent	Add the same explicit write_failed_agent_stderr_tail from SIDECAR_LOG (or preflight err source) on those early-exit paths, or document them as intentionally tail-less
3	in_scope	important	correctness	skills/implement/scripts/step2-implement.sh:606	Pre-launch cleanup drops transcript and sidecar but not .stderr-tail	Resume or retry after a failed run can leave ${TRANSCRIPT_PATH}.stderr-tail; emit_bailed then surfaces a prior attempt tail on unrelated bails (including paths that skip a fresh producer write)	Add rm -f "${TRANSCRIPT_PATH}.stderr-tail" to the Step 3 pre-launch rm list alongside TRANSCRIPT_PATH and SIDECAR_LOG

1. **correctness** — `scripts/launch-codex-implement.sh:290-300`: The plan adds `write_failed_agent_stderr_tail` only inside the post-auth-retry `LAUNCHER_EXIT != 0` block. The `agent-model-args.sh` failure path exits earlier with stderr already in `$SIDECAR_LOG` but never produces `${TRANSCRIPT_PATH}.stderr-tail`, so the proposed `emit_failed_agent_stderr_tail_larch_err` in `emit_bailed` cannot surface that failure.

2. **correctness** — `scripts/launch-cursor-implement.sh:237-272`: Verification of `--capture-stdout-only` covers agent-run failures only. `MODEL_ARGS` and auth-preflight exits populate `$SIDECAR_LOG` and return `LAUNCHER_EXIT` without invoking `run-external-agent`, so the plan’s “no producer edit” leaves the same chat gap for common setup failures.

3. **correctness** — `skills/implement/scripts/step2-implement.sh:606`: Pre-launch cleanup removes transcript and sidecar but not `${TRANSCRIPT_PATH}.stderr-tail`. A later `emit_bailed` can emit a stale tail when the current path did not refresh it (notably combined with finding 1).

[OUT_OF_SCOPE] **risk-integration** — `skills/review-and-fix/scripts/review-implement-step5-loop.sh:245-290` / plan Testing strategy ~139: Terminal `step5_surface_lint_stderr_tail` behavior is specified but dedicated harness coverage is optional (“document in harness notes”). Acceptable for SIMPLE tier; track if `test-review-and-fix.sh` parsers section is not extended.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:2745-2802	Recovery waterfall has multiple `continue` paths after a tier launcher can exit 0 while still leaving `${output}.stderr-tail`	The plan’s ship-pr edit window (~2728–2747) and failure-mode #4 focus on `tier_rc` / `LAUNCHER_EXIT` immediately after the launcher call, but the loop also `continue`s on detached-HEAD (2754–2756) and verify failure (2800–2802) with `tier_rc=0`. Surfacing only in the `tier_rc -ne 0` block drops CI agent tails on those paths.	Add one shared post-launcher gate (parse `LAUNCHER_EXIT` from captured stdout when the launcher ran; then `_surface_ci_stderr_tail "$output"` when `tier_rc -ne 0`, `LAUNCHER_EXIT -ne 0`, or `[[ -s "${output}.stderr-tail" ]]`) and call it before every `recovery_waterfall_paths_delta_revert` / `continue` in the tier loop, not only before the `tier_rc -ne 0` branch.
2	in_scope	important	integration	skills/implement/scripts/step2-implement.sh:264-274	`emit_bailed()` will emit stderr tails for every bail reason, not only external runtime failures	Placing `emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH"` unconditionally in `emit_bailed()` also runs for mechanical bails (`branch-changed`, `protected-path-modified`, `submodule-dirty`, `manifest-schema-invalid`, etc.) where no failed-agent tail exists; usually a no-op, but if a stale `${TRANSCRIPT_PATH}.stderr-tail` remains in the tmpdir from an earlier attempt, chat can show a misleading tail on an unrelated bail.	Restrict the emit to external runtime bails (e.g. only when `REASON` is the runtime-failure token / `cap_hit`, or when `TOOL` is set and `LAUNCHER_EXIT` was non-zero) or delete any existing `${TRANSCRIPT_PATH}.stderr-tail` on mechanical bail paths before emit.

[OUT_OF_SCOPE] Prompt-side `/implement` Step 3 / Step 6 (and Step 5 MAV) invoke `scripts/lint-fix-loop.sh` directly per `skills/implement/SKILL.md`, not via `run_lint_fix_loop_capture` or `review-implement-step5-loop.sh`. This plan adds `STDERR_TAIL_PATH` and caller-scope emit only for ship-pr / step5 loop; orchestrator-driven lint-fix failures will still expose the KV in tool stdout but not the fenced tail on chat unless the SKILL is updated later (`skills/implement/SKILL.md` ~844, ~1072).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-codex-implement.sh:290-300	Producer write is only planned inside the post-auth `if (( LAUNCHER_EXIT != 0 ))` block at ~347; the model-args failure path exits at ~300 with SIDECAR_LOG populated but never reaches that block.	`agent-model-args.sh` failure is a common implementer failure; step2 `emit_failed_agent_stderr_tail_larch_err "$TRANSCRIPT_PATH"` no-ops because `${TRANSCRIPT_PATH}.stderr-tail` was never written despite actionable text in `$SIDECAR_LOG`.	Also call `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the model-args failure path before its `exit 0`, or extract a small shared helper invoked from every non-success launcher exit that has sidecar content.
2	in_scope	important	integration	scripts/launch-cursor-implement.sh:237-272	Plan limits `launch-cursor-implement.sh` to capture-mode verification and relies on step2 consumer emit only; early model-args and auth-preflight exits populate `SIDECAR_LOG` and emit non-zero `LAUNCHER_EXIT` but never run `run-external-agent`, so no `${TRANSCRIPT_PATH}.stderr-tail` is produced.	Same class as codex model-args failures: step2 surfaces `SIDECAR_LOG=` KV but chat gets no redacted stderr tail for preflight failures that never reach the agent subprocess.	Mirror the codex-implement producer on each early `exit 0` path that sets `SIDECAR_LOG` (model-args ~237-247, preflight ~262-272), or document an explicit exception and add a targeted harness case if intentionally out of scope.

1. **[correctness]** `scripts/launch-codex-implement.sh:290-300` — The proposed producer write sits only in the post-loop failure block (~347), but model-args resolution fails earlier (~290-300) after copying errors into `$SIDECAR_LOG` and exiting. step2’s planned consumer emit will not surface anything for that path. Add `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the early path (or a shared helper used by all failure exits with sidecar content).

2. **[integration]** `scripts/launch-cursor-implement.sh:237-272` — The plan treats cursor-implement as consumer-only via step2, which is fine for `--capture-stdout-only` agent failures (run-external-agent already writes `${TRANSCRIPT_PATH}.stderr-tail`), but model-args and auth-preflight failures exit before the agent runs. Those paths need the same explicit producer write on `$SIDECAR_LOG` or tails will stay silent in chat despite being the failures called out in launcher comments for step2.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-dyn-kv-protocol-drift-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:2724-2758	Recovery waterfall edit anchored only on tier_rc!=0 continue path	CI launchers exit 0 and encode agent failure in LAUNCHER_EXIT while tier_rc stays 0; surfacing only inside the block at 2745-2747 never runs and verify runs on a failed tier	After each launcher esac (~2744), capture stdout, parse LAUNCHER_EXIT, and when tier_rc!=0 OR LAUNCHER_EXIT!=0 OR -s ${output}.stderr-tail: call _surface_ci_stderr_tail then recovery_waterfall_paths_delta_revert and continue before detached-head/verify

1. **correctness** (`scripts/ship-pr.sh:2724-2758`): The recovery-waterfall section cites ~2728-2747, which is only the `tier_rc -ne 0` branch. Codex/cursor CI launchers always `exit 0` and report failure via `LAUNCHER_EXIT` on stdout (currently discarded at 2728-2735). On agent failure, `tier_rc` is usually 0, so the loop falls through to verify (2758+) without surfacing `${output}.stderr-tail`. Failure mode #4 and the Approach bullets state the right predicates; tighten the ship-pr plan step to require a new post-launcher gate (surface + revert + `continue`) before detached-head/verify, not only edits inside the existing `tier_rc != 0` block.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/implement/scripts/step2-implement.sh:606-606	Step 3 cleanup omits `${TRANSCRIPT_PATH}.stderr-tail`	Reusing the same `IMPLEMENT_TMPDIR`, a prior failed implement run can leave `*.stderr-tail` on disk; a later step2 invocation can `emit_bailed` before line 606 (resume/`--answers`, qa-loop, branch guards) and the planned `emit_failed_agent_stderr_tail_larch_err` inside `emit_bailed()` would surface the previous run’s tail as current failure context (misleading chat diagnostics).	Add `rm -f "${TRANSCRIPT_PATH}.stderr-tail"` (and optionally `${TRANSCRIPT_PATH}.diag`) to the Step 3 cleanup at 606 and once right after `TRANSCRIPT_PATH`/`SIDECAR_LOG` are defined (~258); or gate tail emit to `RUNTIME_FAILURE_TOKEN` only.
1	in_scope	important	correctness	scripts/launch-cursor-implement.sh:262-272	Cursor auth preflight early exit has no producer write	After `MODEL_ARGS_RC`, `cursor_launcher_setup_auth_argv` failures append to `$SIDECAR_LOG` and exit before `run-external-agent`; the plan only adds `write_failed_agent_stderr_tail` for `MODEL_ARGS_RC`, so `LAUNCHER_EXIT=2` preflight failures never create `${TRANSCRIPT_PATH}.stderr-tail` and step2 consumer surfacing stays silent despite actionable sidecar stderr.	Mirror the `MODEL_ARGS_RC` branch: `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` before timing/KV emit on the `PREFLIGHT_RC != 0` path (with `lib-failed-agent-stderr-tail.sh` sourced earlier).

1. **correctness** — `skills/implement/scripts/step2-implement.sh:606` — Step 3 cleanup drops manifest/transcript/sidecar but not `${TRANSCRIPT_PATH}.stderr-tail`. With the planned tail emit inside `emit_bailed()` for every bail reason, a later step2 entry in the same tmpdir (especially pre-606 bails on resume) can surface a prior run’s redacted tail as if it belonged to the current failure. Extend cleanup (and/or gate emit to `RUNTIME_FAILURE_TOKEN`).

2. **correctness** — `scripts/launch-cursor-implement.sh:262-272` — Auth preflight populates `$SIDECAR_LOG` and exits before `run-external-agent`, but the plan only adds producer writes for `MODEL_ARGS_RC` and post-loop agent failure. Add the same `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH"` on the `PREFLIGHT_RC` branch.

[OUT_OF_SCOPE] **architecture** — Prompt-side Step 3/6 `lint-fix-loop.sh` invocations from `skills/implement/SKILL.md` (not `run_lint_fix_loop_capture` / step5 loop) are outside the plan’s caller-scope surfacing; tails may remain on disk under `lint-fix-loop/` without reaching chat unless a follow-up wires the same `STDERR_TAIL_PATH` + caller emit pattern.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-cursor-implement.sh:262-272	Cursor auth preflight failure exits with SIDECAR_LOG populated but no write_failed_agent_stderr_tail	LAUNCHER_EXIT=2 preflight failures (e.g. missing keychain/API key) reach step2 via emit_bailed while ${TRANSCRIPT_PATH}.stderr-tail was never written; consumer emit is a no-op	Mirror the MODEL_ARGS_RC branch: after appending PREFLIGHT_ERR to SIDECAR_LOG call write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before timing/KV emit / exit 0
2	in_scope	important	correctness	scripts/lint-fix-loop.sh:242-258	run_cursor early returns before run-external-agent skip cursor_rc tail bookkeeping	When cursor_launcher_load_model_args or cursor_launcher_setup_auth_argv fails (or wrap fails), run_cursor returns 1 without setting _LINT_FIX_STDERR_TAIL_STEM; cursor-only repos or codex-skipped paths emit dispatch-failed with no STDERR_TAIL_PATH and no .stderr-tail for ship-pr/step5 to surface	Refactor early failures to set cursor_rc and funnel through the same post-call block as agent failure (optional write from MODEL_ARGS_ERR/auth capture into a temp file, or append to a known capture path, then write_failed_agent_stderr_tail + set stem); do not rely on cursor.wrapper.log
3	out_of_scope	latent	architecture	scripts/launch-claude-ci.sh:176-202	CI fix/recovery surfacing assumes ${stem}.stderr-tail but claude-ci only writes ${OUTPUT}.stderr	Claude tier failures in run_ci_fix_vendor / run_recovery_waterfall call _surface_ci_stderr_tail on a missing artifact; codex/cursor tails surface, claude stays silent	Add a one-line producer on claude-ci failure (write_failed_agent_stderr_tail from ${OUTPUT}.stderr to $OUTPUT) or document claude-ci as out of scope for #3227
4	out_of_scope	latent	risk-integration	skills/implement/SKILL.md:844-1072	Step 3/6 call lint-fix-loop.sh directly from orchestration, not via run_lint_fix_loop_capture	FD-2 redirected prompt-side lint-fix runs never get ship-pr/step5 caller-scope emit; STDERR_TAIL_PATH/KV surfacing does not reach chat on those implement paths unless orchestrator is extended separately	Track follow-up for step3/step6 orchestrator surfacing, or accept as known gap in #3227 scope

1. **[correctness]** `scripts/launch-cursor-implement.sh:262-272` — Auth preflight failures populate `$SIDECAR_LOG` and exit before `run-external-agent`, but the plan only adds `write_failed_agent_stderr_tail` for `MODEL_ARGS_RC`. `step2-implement.sh` will call `emit_failed_agent_stderr_tail_larch_err` from `emit_bailed` with no `${TRANSCRIPT_PATH}.stderr-tail` on this path.

2. **[correctness]** `scripts/lint-fix-loop.sh:242-258` — Planned `run_cursor` changes capture `run-external-agent` exit status only; `cursor_launcher_load_model_args`, `cursor_launcher_setup_auth_argv`, and wrap failures still `return 1` without `_LINT_FIX_STDERR_TAIL_STEM` or a producer write, so `STDERR_TAIL_PATH=` stays empty on dispatch-failed when the agent never ran.

3. **[OUT_OF_SCOPE] [architecture]** `scripts/launch-claude-ci.sh:176-202` — Consumer surfacing reads `${tier_out}.stderr-tail`, but claude-ci writes `${OUTPUT}.stderr` and never uses `lib-failed-agent-stderr-tail.sh`; claude waterfall tiers stay silent.

4. **[OUT_OF_SCOPE] [risk-integration]** `skills/implement/SKILL.md` (Step 3/6 lint-fix guidance) — Caller-scope surfacing is limited to `run_lint_fix_loop_capture` and step5; prompt-side step3/step6 `lint-fix-loop.sh` invocations are outside the plan.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-cursor-implement.sh:262-272	Plan covers MODEL_ARGS_RC producer write but not auth preflight early exit	PREFLIGHT_RC failure appends to SIDECAR_LOG and exits before run-external-agent; no write_failed_agent_stderr_tail and step2 only surfaces via emit_bailed reading ${TRANSCRIPT}.stderr-tail	Mirror the MODEL_ARGS_RC branch: after cat PREFLIGHT_ERR into SIDECAR_LOG call write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before timing/KV emit
1	in_scope	important	risk-integration	scripts/ship-pr.sh:2728-2757	Recovery-waterfall surfacing trigger is clear but insertion point is ambiguous	CI launchers exit 0 while LAUNCHER_EXIT is non-zero; today only tier_rc -ne 0 reverts/continues—implementer who only augments that block never surfaces tails before verify	Add an explicit post-launcher block (after capturing/parsing stdout, before detached-head/verify): if LAUNCHER_EXIT -ne 0 or -s "${output}.stderr-tail" then _surface_ci_stderr_tail "$output" and continue

1. **[correctness]** `scripts/launch-cursor-implement.sh:262-272` — The plan’s producer work for cursor implement covers `MODEL_ARGS_RC` (~237–248) but not the auth **preflight** branch that also fills `$SIDECAR_LOG` and exits before `run-external-agent`. That is the same early-exit class as model-args; without a `write_failed_agent_stderr_tail` there, `${TRANSCRIPT_PATH}.stderr-tail` stays missing and `step2-implement.sh` consumer emit is a no-op. **Suggested revision:** Add the same `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` in the `PREFLIGHT_RC` block (after appending `$PREFLIGHT_ERR`).

2. **[risk-integration]** `scripts/ship-pr.sh:2728-2757` — Recovery waterfall correctly requires surfacing when `LAUNCHER_EXIT!=0` or `${output}.stderr-tail` exists, not only when `tier_rc!=0`, but the only existing failure `continue` today is under `tier_rc -ne 0`. Codex/cursor CI launchers always exit 0 on agent failure, so tails can remain on disk while verify runs and nothing calls `_surface_ci_stderr_tail`. **Suggested revision:** Name a dedicated post-launcher stanza (capture launcher stdout → parse `LAUNCHER_EXIT` → surface → `continue`) before detached-head/verify, instead of relying on edits inside the `tier_rc -ne 0` branch alone.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-cursor-implement.sh:262-272	Plan adds MODEL_ARGS_RC producer write but not PREFLIGHT_RC early exit	Auth preflight fails after model-args succeeds: stderr lands in SIDECAR_LOG, run-external-agent never runs, no ${TRANSCRIPT_PATH}.stderr-tail; step2 emit_bailed tail emit is a no-op	Mirror the MODEL_ARGS_RC branch: after appending PREFLIGHT_ERR to SIDECAR_LOG, call write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true before timing/KV emit / exit 0 (source lib before both early exits)

1. **correctness** `scripts/launch-cursor-implement.sh:262-272` — The plan’s cursor-implement producer coverage matches `MODEL_ARGS_RC` (~237–248) but omits the separate **`PREFLIGHT_RC` early exit** where `cursor_launcher_setup_auth_argv` appends to `$SIDECAR_LOG` and exits before `run-external-agent --capture-stdout-only` (lines 257–272). That is the same pre-agent failure class as model-args (plan Failure modes 1b): `step2-implement.sh` `emit_failed_agent_stderr_tail_larch_err` in `emit_bailed()` only reads `${TRANSCRIPT_PATH}.stderr-tail` on disk, so auth-preflight failures stay silent in chat despite the new consumer. **Suggested revision:** Add the same `write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true` on the `PREFLIGHT_RC` branch (lib sourced before both early exits, as already planned).

**FD / emit-placement review (no additional in-scope defects):** Caller-scope vs in-loop placement is consistent across the cited lanes: `emit_bailed` / `step5_surface_lint_stderr_tail` / `_surface_ci_stderr_tail` / `run_lint_fix_loop_capture` post-`$(… 2>"$fail_file")` run in processes with `larch_quiet_init` and use `larch_err` (FD 4), not inside the launcher or lint-fix subprocess redirects (`step2-implement.sh:645` `2>&1` only wraps the launcher; `ship-pr.sh:2058` `2>&1` and `:2729` `2>>"$wf_log"` only wrap CI launchers; `lint-fix-loop.sh` correctly limits in-loop work to `write_failed_agent_stderr_tail` + `STDERR_TAIL_PATH` KV, not `emit_failed_agent_stderr_tail_larch_err`; step5 parses stems before `rm -f "$lint_out"` at `review-implement-step5-loop.sh:243-244`). Recovery waterfall’s `>/dev/null` discard of contract fd3 is correctly called out for stdout capture before `_surface_ci_stderr_tail "$output"`.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.stderr-tail)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.launch-stderr)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-chain-tracer-output.txt.launch-stderr)

  ```

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
