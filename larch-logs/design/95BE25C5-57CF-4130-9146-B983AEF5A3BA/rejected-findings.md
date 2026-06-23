### [Plan Review] FINDING_3

### FINDING_3: `--design-tmpdir` not forwarded through thin wrapper migration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned relay drops explicit `--design-tmpdir` forwarding. Today's bash wrapper passes `--design-tmpdir "$DESIGN_TMPDIR"` when the shell variable is set even if unexported; the Python helper only reads `os.environ`. Shell-local `DESIGN_TMPDIR` no longer reaches disposition-checkpoint, so `oos-accepted-design.md` may resolve from the wrong path and disposition can false-fail or false-pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin `step8_oos_checkpoint_main` argparse `--design-tmpdir` (optional) forwarded to the disposition-checkpoint subprocess, and have the thin bash wrapper pass the same conditional arg the current script uses at line 18


### [Plan Review] FINDING_4

### FINDING_4: `ship route-exit` lacks fail-closed handling for unsupported rc values
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The required-field table and action mapping cover only driver rc {0,1,3,4,6}. When `.step-8-ship-handoff.json` exists but `.rc` is outside that set (e.g. 2 from setup/`require_value`, stale sidecar, or partial trap failure), behavior is undefined and the router may emit the wrong `NEXT_ACTION` instead of absent-token Tool Failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin fail-closed: when rc sidecar value is not in {0,1,3,4,6}, emit stderr diagnostic, exit non-zero, emit no `NEXT_ACTION`, and write no `.ship-route-exit-handoff.env`; add one router test for rc=2 with parseable json
  - From Cursor-Pragmatic: After reading `.step-8-ship-handoff.rc`, fail closed (no `NEXT_ACTION`, non-zero exit) when rc is not in {0,1,3,4,6}; document the rule in `ship-pr-exit-matrix.md`; add a test with rc=2 plus valid JSON that asserts no routing output
  - From Cursor-Requirements: Pin explicit validation: if `.step-8-ship-handoff.rc` is not in {0,1,3,4,6}, emit stderr diagnostic, exit non-zero, emit no `NEXT_ACTION`, and do not write `.ship-route-exit-handoff.env`; add a router test for rc=2 with valid JSON


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:44-56
- **Concern**: [SCOPE-REDUCTION] Plan still maps handoff exit 0 with non-OK `outcome` to `reship` and adds a test for it.. Scenario: `python/ship.py` `main()` always returns `config.OUTCOME_EXIT_MAP[result.outcome]` and `OUTCOME_EXIT_MAP` pairs exit 0 only with `Outcome.OK`, so a single `ship pr` invocation cannot produce rc 0 with non-OK JSON. The branch, required-field row, and `exit 0 non-OK → reship` test add dead routing surface that misleads implementers and expands scope beyond the issue.
- **Proposed resolution**: Remove the exit-0 non-OK `reship` mapping from `ship_route_exit_main`, the per-exit required-field table, `ship-pr-exit-matrix.md`, and `test_implement_dispatch.py`; classify exit 0 with `outcome=OK` as `complete` only.


