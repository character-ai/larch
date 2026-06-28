### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Step 1d.7 adds PAUSE_OK=true stop but not PAUSE_OK=false fail-closed after brainstorm-off elision. Scenario: Eliding step1d5 --mode entry removes the indirect abort when pause-save prints PAUSE_OK=false and omits STEP1D5_ACTION. step1d7_main still exits via check_pause_and_exit with PAUSE_OK=false and no SKIP_APPROVE_REQUESTED. The planned Step 1d.7 prose only stops on PAUSE_OK=true, so the orchestrator can enter design-outline.md after a failed pause save.
- **Proposed resolution**: Add Step 1d.7 handling: if fence output has whole-line PAUSE_OK=false, abort /design before SKIP_APPROVE_REQUESTED binding and outline work (mirror Step 1d.5 missing-directive abort). Add test_step1d7_brainstorm_off_pause_ok_false_aborts with monkeypatched pause_save_main emitting PAUSE_OK=false.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: Planned structure pins use contains-only and cannot prove brainstorm-off guard precedes the entry fence. Scenario: contains only checks that elision prose and the step1d5 --mode entry launcher line both exist. Misplaced guard text below the fence still passes while the dominant path keeps invoking step1d5, defeating the turn-count goal.
- **Proposed resolution**: Swap the planned contains assertion for check_context_before on skills/design/SKILL.md anchored at step1d5 --mode entry, requiring run-params / brainstorm_requested elision prose in the preceding context (same pattern as Step 0b and Step 3 pause contracts at lines 213-219). ### FINDING_1 — Step 1d.7 missing `PAUSE_OK=false` fail-closed (correctness) **Focus:** correctness / risk-integration **Location:** `skills/design/SKILL.md` (Step 1d.7 section), `python/larch/design/design_lifecycle.py:3041-3055` On the brainstorm-on path, a failed pause at `step1d5 --mode entry` still fails closed: `PAUSE_OK=false` means `PAUSE_OK=true` is absent, `STEP1D5_ACTION` is missing, and SKILL.md aborts. The revised plan elides that fence on brainstorm-off and only adds an explicit `PAUSE_OK=true` terminal stop at Step 1d.7. It does not handle `PAUSE_OK=false`. `check_pause_and_exit` raises `SystemExit` after `pause_save_main` prints `PAUSE_OK=false` with exit code 0 (`python/larch/design/design_pause.py:247-250`). The planned Step 1d.7 flow would treat that as a normal fence return and continue into `design-outline.md`. **Suggested revision:** After the `step1d7` fence, branch on `PAUSE_OK=false` and abort before `SKIP_APPROVE_REQUESTED` / outline work. Add a lifecycle test mirroring `test_step2b_postplan_rc_11_pause_save_gates_terminal`. --- ### FINDING_2 — Structure test cannot enforce guard-before-fence ordering (risk-integration) **Focus:** risk-integration **Location:** `scripts/test-design-structure.sh` Round 1 raised this; the plan still proposes `contains` assertions only. The harness already has `check_context_before` (used for Step 0b / Step 3 pause ordering at lines 213-219) and `assert_line_precedes` (line 69). `contains` cannot catch a guard placed after the `step1d5 --mode entry` fence. **Suggested revision:** Replace the planned `contains` pin with `check_context_before "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode entry"' <N> '<elision-authority literal>'` so CI enforces prose-before-fence ordering for the dominant path.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Step 1d.7 pause contract mirrors only the PAUSE_OK=true stop, not the Step 1d.5 fail-closed path. Scenario: `check_pause_and_exit` prints `PAUSE_OK=false` and exits before `SKIP_APPROVE_REQUESTED=`; proposed text stops only on `PAUSE_OK=true` and otherwise continues outline binding. `PAUSE_OK=false` counts as "PAUSE_OK=true absent," so elision drops the Step 1d.5 missing-directive abort that today blocks outline after a failed pause save.
- **Proposed resolution**: Add explicit `PAUSE_OK=false` stop (or abort when `SKIP_APPROVE_REQUESTED=` is missing after the fence), mirroring the Step 1d.5 `missing STEP1D5_ACTION` abort; pin it in `scripts/test-design-structure.sh` beside the existing Step 1d.5 pause/fail-closed contains.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh
- **Concern**: Planned `contains` checks cannot prove brainstorm-off elision precedes the Step 1d.5 entry fence. Scenario: The turn-count lever fails if elision prose sits below `step1d5 --mode entry`; substring `contains` assertions still pass while the dominant path keeps invoking the entry fence.
- **Proposed resolution**: Use existing `assert_line_precedes` or `check_context_before` (same harness used for Step 3/5c load-before-fence pins) to require elision/run-params authority text before the bare `step1d5 --mode entry` launcher line. ### 1. correctness — `skills/design/SKILL.md` The proposed Step 1d.7 pause handling stops on `PAUSE_OK=true` but does not fail closed on `PAUSE_OK=false`. That is a regression relative to the brainstorm-off path today: Step 1d.5 aborts when `STEP1D5_ACTION` is missing after a failed pause save, and elision removes that guard. **Revision:** Add symmetric fail-closed handling at Step 1d.7 and a structure-test pin matching lines 315–316 for Step 1d.5. ### 2. risk-integration — `scripts/test-design-structure.sh` The planned `contains` assertions verify elision text exists, not that it appears **before** the entry fence. Misordered SKILL prose would preserve the extra turn this issue exists to remove. **Revision:** Pin ordering with `assert_line_precedes` or `check_context_before`, using the same pattern as other load-before-fence structure checks in that script.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:45-48
- **Concern**: [ALREADY_ADDRESSED] The new pause-path test never states that the fake `pause_save_main` must emit `PAUSE_OK=true`, and it does not name a stdout capture fixture.. Scenario: The planned assertion on `stdout contains PAUSE_OK=true` is untestable as written. A bare monkeypatch that only checks the sentinels will not produce the pause marker, so this test would fail to verify the Step 1d.7 pause-stop contract.
- **Proposed resolution**: In the fake `pause_save_main`, print `PAUSE_OK=true` and add `capsys` or `redirect_stdout` so the test can actually observe the marker before asserting `SKIP_APPROVE_REQUESTED=` is absent.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Step 1d.7 pause contract treats all non-PAUSE_OK=true output as continue. Scenario: The plan adds only a PAUSE_OK=true terminal stop and then says when PAUSE_OK=true is absent continue with SKIP_APPROVE_REQUESTED binding and outline work. That groups the normal no-pause path with pause-save failure: pause_save_main emits PAUSE_OK=false with exit 0 and step1d7_main prints neither PAUSE_OK=true nor SKIP_APPROVE_REQUESTED=. On the brainstorm-off path elision removes the Step 1d.5 entry fence whose missing-STEP1D5_ACTION abort is the current fail-closed guard for this failure mode. The orchestrator can enter design-outline.md after a failed pause save.
- **Proposed resolution**: Split Step 1d.7 handling into three branches mirroring Step 1d.5: PAUSE_OK=true stops /design; if SKIP_APPROVE_REQUESTED= is missing or empty (including PAUSE_OK=false) print a fail-closed abort before outline work; otherwise bind skip_approve_requested and continue. Add a matching scripts/test-design-structure.sh contains pin parallel to the existing Step 1d.5 missing-STEP1D5_ACTION assertion.
