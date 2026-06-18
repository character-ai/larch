### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:40-49
- **Concern**: Shared wrapper must export rehydrated session keys into os.environ before in-process postplan_emit_main or pause_save_main. Scenario: plan_quality.py and design_postplan.py read ISSUE_NUMBER, DESIGN_TMPDIR, and CLAUDE_PLUGIN_ROOT from os.environ (and subprocess env copies). A local-only overlay without os.environ export breaks pause-save (ISSUE_NUMBER empty), plan validate repo-root resolution, and token sidecar subprocesses even when session-env.sh was parsed correctly.
- **Proposed resolution**: After allowlisted session-env parse, write merged defaults into os.environ (same effective surface as Bash source) before any in-process postplan_emit_main or pause_save_main call; add pytest that sets keys only in session-env file and asserts postplan pause arm sees ISSUE_NUMBER.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:40-49
- **Concern**: In-process postplan helper must capture postplan_emit_main stdout, not rely on process stdout alone. Scenario: postplan_emit_main emits POSTPLAN_EMIT_STATUS and plan-size KVs via print() in flush(). Calling it in-process without capturing stdout yields empty captured postplan_stdout while still returning rc 10/12/13; orchestrator then hits the missing POSTPLAN_RC fail-closed path after DRAFTER_STATUS=succeeded.
- **Proposed resolution**: Wrap postplan_emit_main in redirect_stdout (or equivalent), store lines in stdout_lines, re-print them after nonfatal arms; add pytest asserting rc 10 returns POSTPLAN_RC rows in captured output when invoked from design step2b-drafter.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/session_env.py:687-716
- **Concern**: Launcher must route retired Step 2 wrapper names to Python before the generic skills/design/scripts exec fallback. Scenario: _design_run_launcher_text currently always execs "$PLUGIN_ROOT/skills/design/scripts/$script". If retired names are not handled in a preceding case arm, deleting design-step2a.sh et al. makes fences fail at runtime despite the port.
- **Proposed resolution**: Add explicit case arms for the five retired wrapper basenames that exec python3 "$PLUGIN_ROOT/python/cli.py" design … or plan validator-autofix with "$@" before the generic script exec; extend python/test_session_env.py to assert ordering and that deleted basenames never reach the fallback path.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:62-111
- **Concern**: design step2b-drafter must preserve repair then pause then timing then launch ordering. Scenario: scripts/test-design-structure.sh enforces repair < pause-save < timing mark < launch-codex-drafter.sh with exactly one pre-launch pause boundary. Reordering in Python (e.g., timing before pause rows) changes pause semantics and fails structure tests.
- **Proposed resolution**: Port with the same linear order as design-step2b-drafter.sh; add a pytest order assertion mirroring the harness check.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:836-909
- **Concern**: assert_step2b_drafter_folded_postplan_contract still greps design-step2b-drafter.sh and design-step2b-postplan.sh for sentinel helpers, repair→pause→timing→launch ordering (878-892), delegated postplan exec (894), and postplan rc case arms (906-909). Scenario: Plan item 6 retargets some pins to python/design_lifecycle.py but does not list the embedded Python ordering probe or the postplan rc-matrix greps inside assert_step2b_drafter_folded_postplan_contract. After launcher cutover and bash deletion, make test-design-structure either fails on missing files or stops enforcing Python Step 2 contracts.
- **Proposed resolution**: Extend the harness checklist to retarget or remove every grep in assert_step2b_drafter_folded_postplan_contract: move sentinel/order/postplan pins to python/design_lifecycle.py (or drop duplicates already covered by assert_postplan_thin_fence) and update the SKILL terminal-postplan fence probe (866-869) to accept launcher-mapped python/cli.py design step2b-postplan wording.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:design step2b-drafter
- **Concern**: [SCOPE-REDUCTION] Fatal in-process postplan should not sys.exit with raw emit rc 2. Scenario: Bash delegates via exec to design-step2b-postplan.sh which maps postplan_emit rc 2 to wrapper exit 1 (design-step2b-postplan.sh:230-232). Plan says drafter exits with the fatal postplan rc (plan.txt:108), so emit rc 2 would yield process exit 2 and change orchestrator/harness expectations vs today.
- **Proposed resolution**: Reuse the postplan wrapper fatal mapping: on emit rc 1 or 2 exit the drafter fence with 1 after diagnostics; reserve returning raw emit rc for the standalone design step2b-postplan CLI only if needed.

### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py (planned from plan.txt:59-60)
- **Concern**: Step 2a plan makes plugin-root validation fatal before the best-effort timing mark. Scenario: Bash Step 2a repairs sentinels and exits successfully on the non-pause path even when the timing command cannot run because CLAUDE_PLUGIN_ROOT is empty; the proposed fatal validation before timing would regress that path
- **Proposed resolution**: Keep pause-save root validation fatal, but make the non-pause timing mark best-effort: skip timing or ignore root-validation failure before timing while returning success after sentinel repair

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py (planned from plan.txt:124-128)
- **Concern**: Postplan rc 10 inline-retry condition is inverted in the parenthetical. Scenario: The plan says fallback is not already used while pointing at .step2b-postplan-fallback-used=true; implementing that literal condition skips the required first inline retry or repeats the wrong branch
- **Proposed resolution**: Change the condition text to .step2b-postplan-fallback-used is absent or not true, matching the Bash != true check

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/plan_quality.py (planned from plan.txt:151-160)
- **Concern**: Validator autofix plan does not pin the required in-process delegation. Scenario: The issue asks for an in-process port, but “Call existing plan auto-fix-commands” can be implemented as a subprocess back into cli.py, leaving the wrapper body only partially ported
- **Proposed resolution**: State that plan validator-autofix calls auto_fix_plan_commands_main(...) directly, captures its stdout and rc in-process, and add the planned pytest assertion for that direct delegation

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Port adds design_require_plugin_root before step2b5 pause and check-size but design-step2b5.sh never calls it. Scenario: Empty or template CLAUDE_PLUGIN_ROOT today still reaches pause-save or plan check-size the same way Bash does today; adding validation is a behavioral change beyond the listed bodies to port
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:design step2b5
- **Phase**: design
