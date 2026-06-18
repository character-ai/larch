### [Plan Review] FINDING_2

### FINDING_2: In-process `postplan_emit_main` must capture stdout, not rely on process stdout alone
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The in-process postplan helper must capture `postplan_emit_main` stdout. `postplan_emit_main` emits `POSTPLAN_EMIT_STATUS` and plan-size KVs via `print()` in `flush()`. Calling it in-process without capturing stdout yields empty captured `postplan_stdout` while still returning rc 10/12/13; the orchestrator then hits the missing `POSTPLAN_RC` fail-closed path after `DRAFTER_STATUS=succeeded`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap postplan_emit_main in redirect_stdout (or equivalent), store lines in stdout_lines, re-print them after nonfatal arms; add pytest asserting rc 10 returns POSTPLAN_RC rows in captured output when invoked from design step2b-drafter.


### [Plan Review] FINDING_3

### FINDING_3: Launcher must route retired Step 2 wrapper names to Python before generic script exec
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The launcher must route retired Step 2 wrapper names to Python before the generic `skills/design/scripts` exec fallback. `_design_run_launcher_text` currently always execs `"$PLUGIN_ROOT/skills/design/scripts/$script"`. If retired names are not handled in a preceding case arm, deleting `design-step2a.sh` et al. makes fences fail at runtime despite the port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit case arms for the five retired wrapper basenames that exec python3 "$PLUGIN_ROOT/python/cli.py" design … or plan validator-autofix with "$@" before the generic script exec; extend python/test_session_env.py to assert ordering and that deleted basenames never reach the fallback path.


### [Plan Review] FINDING_4

### FINDING_4: Step 2b drafter port must preserve repair → pause → timing → launch ordering
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `design step2b-drafter` must preserve repair, then pause, then timing, then launch ordering. `scripts/test-design-structure.sh` enforces repair < pause-save < timing mark < launch-codex-drafter.sh with exactly one pre-launch pause boundary. Reordering in Python (e.g., timing before pause rows) changes pause semantics and fails structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Port with the same linear order as design-step2b-drafter.sh; add a pytest order assertion mirroring the harness check.


### [Plan Review] FINDING_5

### FINDING_5: Structure harness must retarget Step 2b drafter/postplan contract greps after bash deletion
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `assert_step2b_drafter_folded_postplan_contract` still greps `design-step2b-drafter.sh` and `design-step2b-postplan.sh` for sentinel helpers, repair→pause→timing→launch ordering (878-892), delegated postplan exec (894), and postplan rc case arms (906-909). Plan item 6 retargets some pins to `python/design_lifecycle.py` but does not list the embedded Python ordering probe or the postplan rc-matrix greps inside `assert_step2b_drafter_folded_postplan_contract`. After launcher cutover and bash deletion, `make test-design-structure` either fails on missing files or stops enforcing Python Step 2 contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the harness checklist to retarget or remove every grep in assert_step2b_drafter_folded_postplan_contract: move sentinel/order/postplan pins to python/design_lifecycle.py (or drop duplicates already covered by assert_postplan_thin_fence) and update the SKILL terminal-postplan fence probe (866-869) to accept launcher-mapped python/cli.py design step2b-postplan wording.


