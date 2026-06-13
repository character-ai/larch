### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	scripts/ship-pr.sh:1720-1721	Plan closes Item 4 without bash LAUNCHER_EXIT fail-closed fix	The combined issue requires mirroring resolve_launcher_exit when LARCH_SHIP_PR_IMPL=bash; ship-pr.sh still uses launcher_exit=${launcher_exit:-0} at CI-fix (~1720) and recovery-waterfall (~2493) and conflict-resolution (~2876), so a non-zero wrapper exit with no LAUNCHER_EXIT KV is treated as success	Add a ### UPDATED: scripts/ship-pr.sh section: replace ${launcher_exit:-0} defaults with fail-closed semantics (prefer .done sidecar, parsed stdout, then max(wrapper_rc,1)), or delegate to python/cli.py agent resolve-launcher-exit at each of the three call sites
2	in_scope	important	completeness	scripts/test-ship-pr-rebase.sh:155-232	Plan closes Item 5 by citing Python checks.py tests only	Item 5 requires a bash harness case that drives run_checks_with_lint_fix_loop end-to-end; D1-runtime cases inline the ledger handoff after run_captured_cmd_then_fix_loop (lines 183-188) and stub run_checks_with_lint_fix_loop to no-op (line 491), so wrapper regressions would still pass	Add ### UPDATED: scripts/test-ship-pr-rebase.sh with a case that stubs run_lint_fix_loop_capture / failure_capture_path, invokes run_checks_with_lint_fix_loop, and asserts all SHIP_PR_LEDGER_* KVs on main-agent-required return
3	in_scope	important	correctness	skills/implement/scripts/test-step2-dispatch.sh:278-286	Planned Test 13a-scout-cursor uses Codex-style scout path, not Cursor same-path	Item 3 targets Cursor where LAUNCH_SCOUT_MANIFEST_PATH equals SCOUT_CODER_MANIFEST at $TMPDIR/scout-coder-manifest.json; Codex alone uses codex-step2-out/scout-coder-manifest.json. Plan sets STUB_EXPECT_SCOUT_PATH to cursor-step2-out/scout-coder-manifest.json while asserting $TMPDIR/scout-coder-manifest.json, so the stub would not exercise production same-path normalization	Retarget the new test to STUB_EXPECT_SCOUT_PATH=$TMPDIR/scout-coder-manifest.json, STEP2_MANIFEST_PATH=$TMPDIR/manifest.json, and a cursor stub wired like Test 3e (no codex-step2-out subdirectory)

### FINDING_1: Item 4 bash ship-pr LAUNCHER_EXIT fix omitted
- **Focus**: completeness / risk-integration
- **Location**: `scripts/ship-pr.sh:1720-1721`, `2493-2494`, `2876-2877`
- **Concern**: The binding scope lists Item 4 as a runtime bug in bash ship-pr. The plan’s “Items 4 and 5 — Python-side verification (no code changes)” section drops that work because `python/agents.py::resolve_launcher_exit` is correct on the default Python driver path. Legacy `LARCH_SHIP_PR_IMPL=bash` remains documented and supported; the bash bug is still present.
- **Suggested fix**: Add an `### UPDATED: scripts/ship-pr.sh` step that fail-closes missing `LAUNCHER_EXIT` on non-zero wrapper exit at all three cited sites.

### FINDING_2: Item 5 bash wrapper-path test omitted
- **Focus**: completeness
- **Location**: `scripts/test-ship-pr-rebase.sh:155-232`, `491`
- **Concern**: Item 5 asks for coverage of `run_checks_with_lint_fix_loop` in the bash ship-pr harness. Existing D1-runtime tests duplicate the ledger handoff inline; they do not call the wrapper. Pointing at `python/test_checks.py` does not exercise `scripts/ship-pr.sh::run_checks_with_lint_fix_loop`.
- **Suggested fix**: Add the end-to-end wrapper test described in Item 5 to the plan’s file list and testing strategy.

### FINDING_3: Cursor same-path scout test targets wrong filesystem layout
- **Focus**: correctness
- **Location**: Plan `### UPDATED: skills/implement/scripts/test-step2-dispatch.sh`; production path in `skills/implement/scripts/step2-implement.sh:278-286`
- **Concern**: For `--coder cursor`, `LAUNCH_SCOUT_MANIFEST_PATH` and `SCOUT_CODER_MANIFEST` both resolve to `$TMPDIR/scout-coder-manifest.json` (same path). The plan’s Test 13a-scout-cursor uses a `cursor-step2-out/` subdirectory pattern copied from the Codex Test 13a layout. That would not hit the same-path normalization path Item 3 requires.
- **Suggested fix**: Use `$TMPDIR/scout-coder-manifest.json` for both stub output and assertions; set `STEP2_MANIFEST_PATH` to `$TMPDIR/manifest.json` per existing Test 3e.

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-requirements
  ```
### Warnings

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=281 (baseline 96, ratio 2.93) / DIFF_LINES=340 (baseline 205, ratio 1.66) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=338 (baseline 96, ratio 3.52) / DIFF_LINES=385 (baseline 205, ratio 1.88) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=358 (baseline 96, ratio 3.73) / DIFF_LINES=415 (baseline 205, ratio 2.02) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=387 (baseline 96, ratio 4.03) / DIFF_LINES=440 (baseline 205, ratio 2.15) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=425 (baseline 96, ratio 4.43) / DIFF_LINES=450 (baseline 205, ratio 2.2) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=251 (baseline 96, ratio 2.61) / DIFF_LINES=205 (baseline 205, ratio 1) ≥ ×2, under absolute limits; proceeding.**
  ```
