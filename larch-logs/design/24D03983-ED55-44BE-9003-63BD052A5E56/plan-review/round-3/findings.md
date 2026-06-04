### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:14
- **Concern**: Load-bearing Critical boundary still mandates post-ship-pr.sh ship-pr-state.sh parsing. Scenario: After default flip agents follow line 14 over Step 8+ selector and re-parse state / bash exit matrix on every Python return
- **Proposed resolution**: Add a Critical boundary branch: default path routes only from exit code + JSON per selector; bash-only path keeps ship-pr-state parse

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:14
- **Concern**: The plan does not update the top-level anti-halt critical boundary, which still says every ship-pr exit must parse ship-pr-state.sh and re-enter the Step 8+ bash exit table.. Scenario: On the new default Python path, this load-bearing instruction conflicts with the selector’s JSON-only routing and can send continuations back through stale bash state.
- **Proposed resolution**: Add the same bash-only qualifier here, or rewrite this sentence to say the active Step 8+ driver routes by Python JSON unless LARCH_SHIP_PR_IMPL=bash.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-scope-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:34-34
- **Concern**: Step 9 still mandates unconditional restore-finalize-state.sh before teardown. Scenario: After step8-shippr succeeds on the default Python path, Step 18a step 9 can rebuild finalize-state.sh from ship-pr-state.sh and mask keys python/ship.py wrote during postmerge
- **Proposed resolution**: Same gate as SKILL.md Step 18: run restore only when LARCH_SHIP_PR_IMPL=bash; on the default Python path go straight to implement-finalize.sh teardown

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:14
- **Concern**: Plan leaves the global anti-halt boundary on bash state routing outside the selector rewrite. Scenario: Default Python run can still be guided by the top-level reminder to parse ship-pr-state.sh and re-invoke ship-pr.sh after the ship step, contradicting the proposed JSON-only Python routing
- **Proposed resolution**: Add this line to the SKILL.md update: after the active Step 8+ driver exits, use Python JSON routing unless LARCH_SHIP_PR_IMPL=bash; only the bash opt-in path parses ship-pr-state.sh and re-invokes ship-pr.sh

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:409-418,477-478; skills/implement/SKILL.md:1281-1293
- **Concern**: Plan skips restore on every Python path but does not ensure Python writes finalize-state.sh on exception exits. Scenario: If rebase or another phase raises NeedsUserInput, Stalled, or TransientNetworkError, ship.py returns JSON from the outer handler without writing finalize-state.sh; proposed Step 18 then skips restore and teardown can fail or lose stall cleanup state
- **Proposed resolution**: Add a minimal Python terminal-state write for the outer exception path before returning JSON, or only skip restore after validating that Python already wrote a complete finalize-state.sh for that terminal outcome

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1281-1290
- **Concern**: Step 18 restore gated only on bash opt-in. Scenario: Step 5 stall (and other skip-to-16/18 paths) seed ship-pr-state.sh but never run python/ship.py, so finalize-state.sh is absent; bash-only restore skip leaves teardown without required keys
- **Proposed resolution**: Skip restore only when default Python path and finalize-state.sh already exists; still run restore-finalize-state.sh when ship-pr-state.sh exists and finalize-state.sh is missing (regardless of LARCH_SHIP_PR_IMPL)

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:781,1281-1293
- **Concern**: Step 18 restore is gated only on bash opt-in, but pre-Step-8 stalls still seed ship-pr-state.sh and rely on restore-finalize-state.sh. Scenario: With default Python, a Step 5 or other pre-ship stall can create ship-pr-state.sh without finalize-state.sh; the proposed Step 18 skip then calls implement-finalize.sh teardown with a missing state file and fails cleanup/title transition
- **Proposed resolution**: Change the plan so Python skips restore only when python/ship.py has produced a valid finalize-state.sh; if finalize-state.sh is absent and ship-pr-state.sh exists, still run restore-finalize-state.sh for pre-driver seeded stalls

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:14; skills/shared/subskill-invocation.md:59-65
- **Concern**: High-salience continuation guidance remains bash-only outside the selector paragraph. Scenario: The orchestrator may follow the top anti-halt/shared guidance after a default Python return, parse ship-pr-state.sh, and re-enter ship-pr.sh despite the selector text later saying JSON routing is authoritative
- **Proposed resolution**: Add minimal selector-aware edits to those two guidance sites: default Python uses process rc plus JSON and re-invokes python/ship.py; ship-pr-state.sh and ship-pr.sh re-entry apply only when LARCH_SHIP_PR_IMPL=bash

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:188-228
- **Concern**: Plan mandates `--state-file` on the default Python argv, but `_write_ship_state` replaces the whole file with a ~20-key subset instead of merging the orchestrator seed. Scenario: Step 5 (or 18a) seeds `STALL_TRACKING`, bail keys, `NO_LOGS_COMMIT`, `TOOL_LABEL`, etc.; first Python write drops them. That is worse than today's opt-in path, which omits `--state-file` and leaves the seed intact. Edge case "OOS may still read ship-pr-state.sh" is unsafe on the proposed default path
- **Proposed resolution**: Do not add `--state-file` until `_write_ship_state` key-merges an existing file (small Python change), or keep argv without `--state-file` and narrow the plan/edge-case text. Drop the structure-test `--state-file` pin if you defer

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1042
- **Concern**: OOS checkpoint re-entry remains bash-resume shaped. Scenario: The plan says not to rewrite OOS checkpoint mechanics, but the existing text still says to re-enter with `--resume-phase pr-create`; the default Python driver does not accept that flag and should be re-invoked through the selector with the same Python argv.
- **Proposed resolution**: Qualify that final re-entry clause: default Python path re-invokes the selector's `python/ship.py` argv without `--resume-phase`; only `LARCH_SHIP_PR_IMPL=bash` uses `ship-pr.sh --resume-phase pr-create`.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:34
- **Concern**: Stall-recovery teardown still names unconditional restore. Scenario: The plan updates Step 18 restore gating in SKILL.md, but this reference still directs `restore-finalize-state.sh` before teardown; on a Python-path stalled recovery this can contradict the new skip-restore rule and rebuild `finalize-state.sh` from bash-shaped state.
- **Proposed resolution**: Update this line to defer to Step 18b's active-driver restore gate: bash opt-in may run `restore-finalize-state.sh`; Python default skips restore and proceeds to teardown with Python-written `finalize-state.sh`.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:34-39
- **Concern**: Step 9 and Safety Constraints still mandate unconditional restore-finalize-state.sh. Scenario: After stall recovery on the default Python path Step 18a can follow stall-recovery.md and run restore before teardown, rebuilding finalize-state.sh from ship-pr-state.sh and masking python/ship.py postmerge output
- **Proposed resolution**: Gate Step 9 teardown bullets and the restore Safety Constraint the same way as SKILL.md Step 18: skip restore unless LARCH_SHIP_PR_IMPL=bash

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1042
- **Concern**: OOS checkpoint still says re-enter with --resume-phase pr-create with no Python mapping. Scenario: After OOS disposition on the default Python path the orchestrator may pass a ship-pr.sh-only resume flag or invoke bash instead of re-invoking python/ship.py with --state-file
- **Proposed resolution**: Add a default-path sentence: after OOS_PENDING=false re-invoke the selector python3 foreground argv (including --state-file); reserve --resume-phase pr-create for bash opt-in only

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:957
- **Concern**: 8-pre-ship phantom probe lead-in remains before first foreground ship-pr.sh invocation only. Scenario: Plan marks phantom probe as shared prep but does not reword line 957, so default Python runs may skip the 8-pre-ship probe
- **Proposed resolution**: Reword the phantom-probe lead-in to run immediately before the active Step 8+ driver (Python selector or bash Invoke)

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:14
- **Concern**: The plan omits the top-level anti-halt critical boundary that still says to parse ship-pr-state.sh and re-invoke by the Step 8+ exit-code table after ship-pr.sh exits.. Scenario: A default Python Step 8+ run can return through the foreground Bash tool, but this high-level instruction remains stale and can route the orchestrator back to bash/state-file handling instead of python/ship.py JSON routing.
- **Proposed resolution**: Add a SKILL.md edit for this sentence: describe the active Step 8+ driver boundary, route default Python by process rc plus JSON stdout, and scope ship-pr-state.sh/bash table parsing to LARCH_SHIP_PR_IMPL=bash; add a structure pin rejecting the old unqualified sentence.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:94-97,271-297
- **Concern**: The docs plan adds an upgrade notice but leaves Python 3.12+ documented only for /report-tokens or contributor pre-commit, not for default /implement.. Scenario: After upgrade, a consumer without Python 3.12 on python3 hits the new default python/ship.py path and fails despite the prerequisites not saying /implement now needs it or that bash opt-out avoids it.
- **Proposed resolution**: Add one minimal prerequisite/operator-notice sentence: default /implement Step 8+ requires Python 3.12+ available as python3; set LARCH_SHIP_PR_IMPL=bash before starting the session if that prerequisite is not met.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:953-955
- **Concern**: Planned Step 8+ prose uses driven by the **Python driver selector** and Unless `LARCH_SHIP_PR_IMPL=bash`, (comma) but structure-test pins require delegated by the **Python driver selector** or Unless `LARCH_SHIP_PR_IMPL=bash` (space after closing backtick). Scenario: Implementer follows the plan SKILL.md bullets verbatim; grep -Fq routing pins fail even though the flip is correct, or pins are rewritten ad hoc and drift from the authored prose
- **Proposed resolution**: Lock one side: either change planned SKILL.md to emit the exact pin substrings (pre-Invoke Unless line with trailing space if that is the chosen token; delegation sentence with delegated by) or define pins from the plan phrases (driven by the **Python driver selector**; Unless `LARCH_SHIP_PR_IMPL=bash`,)

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:72-77 / skills/implement/SKILL.md:955-1003
- **Concern**: Positive --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" pin is file-wide; that exact substring already exists in the byte-stable bash Invoke: block at line 1003 and is not yet in the Python selector paragraph at line 955. Scenario: Python selector can omit --state-file while the pin passes via the bash fence, recreating FINDING_2 stale seeded ship-pr-state.sh on the default path
- **Proposed resolution**: Scope the assertion to the Python driver selector region (awk between **Python driver selector:** and Invoke:) or add a selector-only sentinel phrase copied byte-for-byte into both SKILL.md and the pin; do not rely on whole-file grep

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:72-78 / skills/implement/SKILL.md:~1020
- **Concern**: Matrix-gate pin token only when `LARCH_SHIP_PR_IMPL=bash` also appears in other planned bash-only qualifiers (NEVER #13 recovery bullet) so it does not uniquely prove the exit-matrix gate sentence exists. Scenario: Exit-matrix gate edit is skipped while NEVER #13 or another bash-only line satisfies the pin; default-path orchestrators may still treat ship-pr-state.sh / bash exit-matrix bullets as authoritative
- **Proposed resolution**: Use the matrix-specific substring from the plan, e.g. Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**, or awk-anchor the pin immediately before Parse the process exit code and then read `$IMPLEMENT_TMPDIR/ship-pr-state.sh`

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:989-1018; scripts/test-implement-structure.sh planned selector pins
- **Concern**: F1: planned state-file pin is not scoped to the Python selector; the exact literal --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" already exists in the preserved bash Invoke block. Scenario: A plain grep -Fq state-file pin can pass without adding --state-file to the Python argv, missing the seeded-state refresh regression
- **Proposed resolution**: Scope the assertion to the Python selector paragraph/window and require the exact --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" token there alongside the python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py" invocation

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:953-957; scripts/test-implement-structure.sh planned routing pin
- **Concern**: F2: proposed routing pin alternatives do not match the planned SKILL wording character-for-character; the plan writes driven by the **Python driver selector** below and Unless `LARCH_SHIP_PR_IMPL=bash`, but the pin offers delegated by the **Python driver selector** or a token with a space after the backtick. Scenario: A correct minimum SKILL edit can fail the structure test, or the implementer may change wording only to satisfy the test
- **Proposed resolution**: Use an exact planned token such as driven by the **Python driver selector** below or Unless `LARCH_SHIP_PR_IMPL=bash`, do not run

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:56,987,1020-1024; scripts/test-implement-structure.sh planned matrix pin
- **Concern**: F3: planned matrix-gate pin is malformed and generic; only when `LARCH_SHIP_PR_IMPL=bash is missing the closing inner backtick and can match other bash-only qualifier sentences the plan adds outside the exit matrix. Scenario: A global grep-Fq can pass on NEVER #13, recovery, or Step 18 wording while the exit matrix itself remains ungated
- **Proposed resolution**: Scope the check to the exit-matrix insertion window and pin the exact gate phrase Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-scope-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/subskill-invocation.md:59-68
- **Concern**: Plan omits a shared prompt-policy file that still frames Step 8+ as foreground ship-pr.sh stdout plus ship-pr-state routing and tells the orchestrator to re-invoke ship-pr.sh --resume-phase. Scenario: After the default flips to python/ship.py this shared anti-halt example can steer a default-path continuation back to bash/state-file routing; the plan's stale-reference sweep does not match this file because it only contains generic ship-pr.sh wording
- **Proposed resolution**: Update this example to say the default path parses python/ship.py JSON and only the bash opt-in path parses ship-pr.sh stdout/state and re-invokes ship-pr.sh
