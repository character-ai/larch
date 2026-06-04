### FINDING_1: Stale anti-halt/shared guidance still routes default Python runs through bash state
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements, Codex-dyn-scope-gap
- **Severity**: important
- **Concern**: High-salience Step 8+ continuation guidance still tells agents to parse `ship-pr-state.sh`, use the bash exit matrix, and re-invoke `ship-pr.sh`, conflicting with the new default Python JSON routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a Critical boundary branch: default path routes only from exit code + JSON per selector; bash-only path keeps ship-pr-state parse
  - From Codex-Arch: Add the same bash-only qualifier here, or rewrite this sentence to say the active Step 8+ driver routes by Python JSON unless LARCH_SHIP_PR_IMPL=bash.
  - From Codex-Edge: Add this line to the SKILL.md update: after the active Step 8+ driver exits, use Python JSON routing unless LARCH_SHIP_PR_IMPL=bash; only the bash opt-in path parses ship-pr-state.sh and re-invokes ship-pr.sh
  - From Codex-Innovation: Add minimal selector-aware edits to those two guidance sites: default Python uses process rc plus JSON and re-invokes python/ship.py; ship-pr-state.sh and ship-pr.sh re-entry apply only when LARCH_SHIP_PR_IMPL=bash
  - From Codex-Requirements: Add a SKILL.md edit for this sentence: describe the active Step 8+ driver boundary, route default Python by process rc plus JSON stdout, and scope ship-pr-state.sh/bash table parsing to LARCH_SHIP_PR_IMPL=bash; add a structure pin rejecting the old unqualified sentence.
  - From Codex-dyn-scope-gap: Update this example to say the default path parses python/ship.py JSON and only the bash opt-in path parses ship-pr.sh stdout/state and re-invokes ship-pr.sh


### FINDING_2: Stall-recovery reference still restores bash state unconditionally
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-scope-gap, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `stall-recovery.md` still mandates `restore-finalize-state.sh` before teardown, which can rebuild `finalize-state.sh` from bash-shaped `ship-pr-state.sh` and mask Python-written postmerge state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Cursor-dyn-scope-gap: Same gate as SKILL.md Step 18: run restore only when LARCH_SHIP_PR_IMPL=bash; on the default Python path go straight to implement-finalize.sh teardown
  - From Codex-Pragmatic: Update this line to defer to Step 18b's active-driver restore gate: bash opt-in may run `restore-finalize-state.sh`; Python default skips restore and proceeds to teardown with Python-written `finalize-state.sh`.
  - From Cursor-Requirements: Gate Step 9 teardown bullets and the restore Safety Constraint the same way as SKILL.md Step 18: skip restore unless LARCH_SHIP_PR_IMPL=bash


### FINDING_3: Python exception exits may skip finalize-state writes
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: If `python/ship.py` exits through outer exception handlers, Step 18 may skip restore even though Python never wrote a complete `finalize-state.sh`, causing teardown failure or lost stall cleanup state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a minimal Python terminal-state write for the outer exception path before returning JSON, or only skip restore after validating that Python already wrote a complete finalize-state.sh for that terminal outcome


### FINDING_4: Step 18 restore gate breaks pre-Step-8 seeded stalls
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: Pre-ship stalls can seed `ship-pr-state.sh` before Python ever runs; a bash-only restore gate can leave `finalize-state.sh` absent during teardown on the default Python path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Skip restore only when default Python path and finalize-state.sh already exists; still run restore-finalize-state.sh when ship-pr-state.sh exists and finalize-state.sh is missing (regardless of LARCH_SHIP_PR_IMPL)
  - From Codex-Innovation: Change the plan so Python skips restore only when python/ship.py has produced a valid finalize-state.sh; if finalize-state.sh is absent and ship-pr-state.sh exists, still run restore-finalize-state.sh for pre-driver seeded stalls


### FINDING_5: `--state-file` default Python path can drop seeded state keys
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Adding `--state-file` to default Python argv is unsafe unless `_write_ship_state` merges existing keys; otherwise Python overwrites orchestrator-seeded `ship-pr-state.sh` keys with a smaller subset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Do not add `--state-file` until `_write_ship_state` key-merges an existing file (small Python change), or keep argv without `--state-file` and narrow the plan/edge-case text. Drop the structure-test `--state-file` pin if you defer


### FINDING_6: OOS checkpoint re-entry remains bash-resume shaped
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: OOS checkpoint recovery still instructs re-entry with `ship-pr.sh --resume-phase pr-create`, which the default Python driver does not accept.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Qualify that final re-entry clause: default Python path re-invokes the selector's `python/ship.py` argv without `--resume-phase`; only `LARCH_SHIP_PR_IMPL=bash` uses `ship-pr.sh --resume-phase pr-create`.
  - From Cursor-Requirements: Add a default-path sentence: after OOS_PENDING=false re-invoke the selector python3 foreground argv (including --state-file); reserve --resume-phase pr-create for bash opt-in only


### FINDING_7: Phantom probe lead-in remains tied to `ship-pr.sh`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The 8-pre-ship phantom probe is still described as running before the first foreground `ship-pr.sh` invocation, so default Python runs may skip shared prep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reword the phantom-probe lead-in to run immediately before the active Step 8+ driver (Python selector or bash Invoke)


### FINDING_8: Consumer prerequisites omit Python 3.12+ for default `/implement`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Installation docs still frame Python 3.12+ as needed for `/report-tokens` or contributor tooling, not the new default `/implement` Step 8+ path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add one minimal prerequisite/operator-notice sentence: default /implement Step 8+ requires Python 3.12+ available as python3; set LARCH_SHIP_PR_IMPL=bash before starting the session if that prerequisite is not met.


### FINDING_9: Routing structure-test pins do not match planned prose
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity, Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Concern**: Planned SKILL wording and planned grep tokens differ character-for-character, so correct implementation can fail tests or force wording drift just to satisfy pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pin-token-fidelity: Lock one side: either change planned SKILL.md to emit the exact pin substrings (pre-Invoke Unless line with trailing space if that is the chosen token; delegation sentence with delegated by) or define pins from the plan phrases (driven by the **Python driver selector**; Unless `LARCH_SHIP_PR_IMPL=bash`,)
  - From Codex-dyn-pin-token-fidelity: Use an exact planned token such as driven by the **Python driver selector** below or Unless `LARCH_SHIP_PR_IMPL=bash`, do not run


### FINDING_10: `--state-file` structure pin is not scoped to Python selector
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity, Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Concern**: A file-wide grep for `--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"` can pass from the preserved bash Invoke block without proving the Python selector argv includes it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pin-token-fidelity: Scope the assertion to the Python driver selector region (awk between **Python driver selector:** and Invoke:) or add a selector-only sentinel phrase copied byte-for-byte into both SKILL.md and the pin; do not rely on whole-file grep
  - From Codex-dyn-pin-token-fidelity: Scope the assertion to the Python selector paragraph/window and require the exact --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" token there alongside the python3 "${CLAUDE_PLUGIN_ROOT}/python/ship.py" invocation


### FINDING_11: Exit-matrix gate pin is generic or malformed
- **Reviewer(s)**: Cursor-dyn-pin-token-fidelity, Codex-dyn-pin-token-fidelity
- **Severity**: important
- **Concern**: The planned matrix-gate assertion can match unrelated bash-only qualifiers, and one token variant is malformed, so the exit matrix may remain ungated while tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pin-token-fidelity: Use the matrix-specific substring from the plan, e.g. Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**, or awk-anchor the pin immediately before Parse the process exit code and then read `$IMPLEMENT_TMPDIR/ship-pr-state.sh`
  - From Codex-dyn-pin-token-fidelity: Scope the check to the exit-matrix insertion window and pin the exact gate phrase Apply the following exit matrix **only when `LARCH_SHIP_PR_IMPL=bash`**

