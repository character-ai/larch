### [Plan Review] FINDING_5

### FINDING_5: Env Output subsection omits warn-for-baselined vs fail-for-new-live
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The env module **Output** subsection only lists message fields and omits subprocess-parity warn-for-baselined versus fail-for-new-live behavior. Implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows, diverging from keyword-only and subprocess ratchet behavior operators expect from `make py-lint-main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an **Output:** subsection matching subprocess: warn for baselined findings, fail only for live findings absent from baseline and exemptions, and reference shared exit 0/1/2 semantics from Approach
  - From Cursor-Innovation: Implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows, diverging from keyword-only and subprocess ratchet behavior operators expect from make py-lint-main. Add **Output:** matching subprocess: warn for baselined findings; fail only for live findings absent from baseline and exemptions; exit 0 vs 1 vs 2 aligned with Approach.


### [Plan Review] FINDING_6

### FINDING_6: Subprocess baseline load omits structural value validation
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Subprocess baseline load still omits structural value validation. A malformed baseline row with empty `file` or `qualified_symbol` would load successfully, then never match live findings or preserve reasons, so the ratchet can drift silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Validate non-empty POSIX-relative file and non-empty qualified_symbol on load, matching the existing ratchet pattern before comparing or writing.


### [Plan Review] FINDING_7

### FINDING_7: Subprocess duplicate live and baseline identity checks missing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, callee, occurrence)` key. A malformed baseline or a collector bug that emits the same subprocess call site twice can silently drop one row or misapply a reason instead of aborting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.


### [Plan Review] FINDING_8

### FINDING_8: Env duplicate live and baseline identity checks missing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, env_name, constant, access, occurrence)` key. A malformed baseline or collector bug can silently collapse two env findings that share the same identity, hiding or misattributing a ratchet row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.


### [Plan Review] FINDING_9

### FINDING_9: Subprocess pytest omits absent-baseline `--initial-reason` bootstrap path
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Subprocess regression coverage omits the absent-baseline `--initial-reason` bootstrap path. The plan validates normal `--write` regeneration but never exercises the case the Makefile regen target depends on: baseline file absent and bootstrap reason supplied. That leaves a new baseline-creation path untested, so a regression there could ship while the listed tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a pytest that deletes the subprocess baseline file, runs `lint subprocess-via-runner --write --initial-reason ...`, and asserts bootstrap succeeds and writes canonical JSON.


