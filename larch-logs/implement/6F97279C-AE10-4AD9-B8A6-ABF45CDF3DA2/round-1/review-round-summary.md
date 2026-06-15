# Review Round 1

- Mode: `diff`
- 17 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Committed unresolved merge conflict markers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The branch contains unresolved `<<<<<<<` / `=======` / `>>>>>>>` hunks in shipped surfaces including `python/stall_recovery.py` (SyntaxError at import), `agent-lint.toml`, `.claude/rules/launcher-argv-test-coverage.md`, `skills/design/references/flags.md`, and `skills/design/SKILL.md`. `py-lint`, `py-test`, agent-lint, and markdownlint cannot pass until every hunk is resolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Resolve every conflict marker and add a grep or lint gate for conflict markers.
  - From cursor-specialist-edge-cases-output.txt: Resolve all conflict hunks; grep for ^<<<<<<< and confirm clean tree.
  - From codex-specialist-testing-output.txt: Resolve every conflict marker and keep the intended merged content.


### FINDING_10: design file-oos-annotate incomplete; partial /issue failure can return success
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/design_oos.py` `file_oos_annotate_main` does not update accepted OOS blocks in `oos-accepted-design.md`, does not write `OOS_FILE_MAP` sentinel rows, and does not fail non-zero on reported `/issue` failures. A partial failure can write an empty or incomplete sentinel while leaving accepted blocks unannotated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Restore order-based annotation, atomic accepted-md updates, OOS_FILE_MAP sentinel rows, and non-zero returns for reported issue failures.


### FINDING_11: Migrated design pytest modules are registry smoke tests only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_design_publish.py`, `python/test_design_cli_ports.py`, and sibling `test_design_*` modules only assert CLI registry wiring. `make test-design-*` can pass while runtime handlers are broken stubs delegating to deleted scripts or emitting wrong contract tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port deleted shell harness cases into pytest.
  - From cursor-specialist-edge-cases-output.txt: Port shell harness scenarios into pytest before retiring bash tests.
  - From cursor-specialist-testing-output.txt: Port test-design-publish.sh cases into pytest before retiring harness.
  - From codex-specialist-testing-output.txt: Restore parity pytest cases for each retired harness before removing the shell harnesses.


### FINDING_13: design parse-argv stdout contract changed from legacy uppercase KVs
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When `--output` is absent, `parse_argv_main` prints lowercase quoted assignments (`partition_requested='false'`) instead of legacy uppercase stdout KVs (`PARTITION_REQUESTED=false`). Downstream parsers and harnesses expecting the legacy grammar break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit legacy uppercase stdout KVs when --output is absent and keep sourceable lowercase KVs only for the output file.


### FINDING_15: design render-final-summary omits failure-report gate and sidecar behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `python/design_summary.py` `render_final_summary_main` does not invoke the `design-failure-report` gate or emit `REPORT_GATE_SIDECARS_FILE` behavior from deleted `render-final-summary.sh`. Terminal design failures may not file stall-recovery reports; sidecar appendices may be omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port remaining render-final-summary.sh branches.
  - From cursor-specialist-edge-cases-output.txt: Port failure-report invocation from render-final-summary.sh.


### FINDING_16: design render-final-summary discards parsed --mode argument
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `render_final_summary_main` parses `--mode` into `mode_str` then assigns `_ = mode_str  # consumed for future use`. `design render-final-summary --outcome approved --mode "Direct draft"` renders `Mode: N/A` instead of the supplied mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Thread mode_str into invoke_render and pass --mode to render run-summary.


### FINDING_18: plan_quality default test driver points at deleted design-driver.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/plan_quality.py` defaults `LARCH_TEST_DESIGN_DRIVER` to `skills/design/scripts/design-driver.sh`, which is deleted. Revise-waterfall tests without an env override fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Default LARCH_TEST_DESIGN_DRIVER to python/cli.py design driver.


### FINDING_2: design publish CLI delegates to deleted design-publish.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/design_publish.py` calls `design_legacy.run_script("skills/design/scripts/design-publish.sh", …)` but that script is absent. `/design` Step 5c `design publish` exits 127; plan block write, rename, and log publish never run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement design_publish.py; remove bash delegation.
  - From cursor-specialist-testing-output.txt: Implement publish in Python; remove legacy subprocess to deleted script.


### FINDING_20: test-design-step5c.sh stubs deleted bash publish path instead of Python CLI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-design-step5c.sh` stubs bash `design-publish.sh` / render paths, but the live wrapper calls `python3 cli.py design publish` and `render-final-summary`. Publish-tail abort and rc=5 tests do not exercise the real code path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub python3 cli.py design publish and render-final-summary like test-design-clarify.sh.


### FINDING_21: test_design_argv.py has only happy-path coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Retired `test-parse-design-argv.sh` had many rejection cases; `python/test_design_argv.py` has one happy-path test. Public `--output`, duplicate flags, and metacharacter regressions lack CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port test-parse-design-argv.sh cases into test_design_argv.py.


### FINDING_3: design pause save/load delegate to deleted bash scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/design_pause.py` delegates `pause-save` and `pause-load` to `scripts/design-pause-save.sh` and `scripts/design-pause-load.sh`, which are deleted. Every `python3 … design pause-save` / `pause-load` fails; `/design` cannot pause or resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port pause save/load into design_pause.py.
  - From cursor-specialist-testing-output.txt: Port pause-save/load into design_pause.py before script deletion.


### FINDING_4: design lifecycle verbs delegate to deleted route/init/driver scripts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/design_lifecycle.py` `route_main`, `init_runparams_main`, and `driver_main` call deleted `design-route.sh`, `design-init-runparams.sh`, and `design-driver.sh` via `design_legacy.run_script`. Step 0b route and diagram driver paths exit 127; `/design` cannot start or route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port lifecycle verbs into design_lifecycle.py.
  - From codex-specialist-correctness-output.txt: Replace compatibility wrappers with real Python implementations or keep scripts until ports are complete.
  - From codex-specialist-edge-cases-output.txt: Replace legacy shims with real Python ports or keep the scripts until no CLI verb depends on them.


### FINDING_5: design log-publish delegates to deleted design-log-publish.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/design_log_publish_flow.py` delegates to deleted `scripts/design-log-publish.sh`. Design run-log PR publish and pause snapshots fail at runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port design_log_publish_flow.py fully.


### FINDING_6: plan step1-log delegates to deleted run-step1-plan-log.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/design_step_log.py` delegates to deleted `scripts/run-step1-plan-log.sh`. `/implement` bootstrap Step 1 plan-log fails after cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wire step1_log_main to Python implementation.


### FINDING_7: design postplan-emit is incomplete stub forwarding to plan-review emit
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/design_postplan.py` `postplan_emit_main` only subprocesses `plan-review emit` instead of implementing the full `design-postplan-emit.sh` contract. Step 2b.5 and Gate B post-apply paths miss validator rc 10, pause rc 11, size rc 12/13, result-env keys, and merged failure semantics; plan gates silently mis-route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement full design postplan-emit contract in Python.
  - From codex-specialist-correctness-output.txt: Port the full postplan behavior including validation, size checks, result-env, and pause rc handling.
  - From codex-specialist-edge-cases-output.txt: Implement postplan directly with the documented validation, plan-size, pause, result-env, and merged-mode rc contracts.
  - From cursor-specialist-testing-output.txt: Port design-postplan-emit.sh semantics with plan exit-code matrix and pytest per branch.


### FINDING_8: design-step1d5.sh still execs deleted design-pause-save.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-step1d5.sh` line 89 `design_pause_check()` still `exec`s deleted `scripts/design-pause-save.sh` when `.pause-requested` exists. Pause during brainstorm entry fails instead of saving resumable state; peer wrappers already call `python3 … design pause-save`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace with exec python3 ... design pause-save like other wrappers.
  - From codex-specialist-correctness-output.txt: Change the gate to exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save with the existing args.
  - From codex-specialist-edge-cases-output.txt: Repoint the checkpoint to exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save with the same args.


### FINDING_9: design file-oos-prepare contract mismatch breaks Step 5b OOS filing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/design_oos.py` `file_oos_prepare_main` is an incomplete port. It emits `FILE_DESIGN_OOS_STATUS=ok` but `design-step5b-prepare.sh` only routes `ready` (and related skip statuses) to `STEP5B_NEEDS_ANNOTATE`; it omits `FILE_DESIGN_OOS_COMBINED`, `FILE_DESIGN_OOS_DEPS_TSV`, and `FILE_DESIGN_OOS_DEPS_AVAILABLE`; it calls `oos issue-cap` with invalid `--design-tmpdir` instead of required `--input-file` / `--output`; and it lacks file-conflict-deps and cross-session cache behavior from the absorbed bash helper. Accepted OOS items never reach `/larch:issue`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align status tokens and KV output with design-step5b-prepare.sh contract.
  - From codex-specialist-correctness-output.txt: Build the combined OOS input and call oos issue-cap with --input-file and --output, then run deps and emit handoff KVs.
  - From codex-specialist-edge-cases-output.txt: Emit the old ready and skip statuses and preserve combined, deps, and order path outputs.
  - From cursor-specialist-edge-cases-output.txt: Port remaining file-design-oos.sh prepare logic.
  - From cursor-specialist-testing-output.txt: Port remaining file-design-oos.sh prepare/annotate behavior and add pytest.


