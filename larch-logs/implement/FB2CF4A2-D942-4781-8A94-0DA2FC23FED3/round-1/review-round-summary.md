# Review Round 1

- Mode: `diff`
- 5 accepted, 7 rejected (7 exonerated)

## Accepted Findings

### FINDING_11: Empty-state Gate-B bypass pause/resume test lacks load round-trip
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: The new empty-state Gate-B-bypass case runs `design-pause-save.sh` and asserts `STEP=3b`, but never runs `design-pause-load.sh`. This misses regressions where save succeeds but restore/re-entry mis-derives `STEP` from the triple-sentinel layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: After the save assertions on DESIGN_GATE_B, run design-pause-load.sh into a fresh restore tmpdir and assert LOAD_OK=true and STEP=3b, mirroring the Step 3.6 save/load pattern above.
  - From cursor-specialist-plan-fidelity-output.txt: Update the doc after adding the load step, or temporarily narrow the prose to match current save-only coverage.
  - From dyn-bash-contracts-output.txt: After a successful save, run `design-pause-load.sh` into a fresh restore tmpdir (same pattern as the Step 3.6 case above) and assert `LOAD_OK=true` plus `STEP=3b`.
  - From dyn-state-machine-output.txt: After a successful save, run load into a fresh restore tmpdir (mirror the `design-36` pattern at `skills/design/scripts/test-design-pause-resume.sh:237-238`) and assert `LOAD_OK=true` and `STEP=3b`.


### FINDING_14: Postplan early fail paths drop already-captured classification warnings
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` captures classification stderr into `WARN_LINES` before later guards, but fatal `fail()` exits after that point do not write the result env or emit stdout `WARN=` records. Classification warnings can disappear on early failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-warnings-output.txt: On fatal exits after the classification read, either invoke a small helper that writes/emits `WARN_LINES` (with a terminal `POSTPLAN_EMIT_STATUS` such as `emit-failed` / `missing-plan`) or emit each warning via `larch_err` / `emit_kv WARN` before `exit 2`.


### FINDING_18: Assessor-env read-loop anti-shape can false-negative on incidental “done”
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The awk guard clears `in_read_loop` on any line containing `done`, so a comment or string inside the loop can reset state before the real `done <...assessor.env` redirect and hide a banned file-first read loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Only clear `in_read_loop` when `done` is a statement terminator (e.g. match `^[[:space:]]*done([[:space:]]|$)`), or require the redirect match on the same `done` line and drop the generic `done` reset rule.


### FINDING_3: Postplan quiet-mode WARN regression lacks present-but-invalid run-params coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The default-quiet `WARN=` regression covers absent `run-params.json`, but not a readable file with missing or invalid `design_classification`. A regression could prevent operators from seeing `WARN=` on stdout for incomplete run params while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: A second env -u LARCH_QUIET_DISABLE case with readable run-params missing/invalid design_classification asserting WARN= on stdout


### FINDING_8: Gate-B bypass helper rejects the realistic pre-existing step-3 layout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `apply_gate_b_bypass_sentinels` aborts if `step-3` already exists, but production Gate-B bypass normally occurs after Step 3 has already written `step-3`. CI therefore misses the realistic state where `step-3` exists and only `step-3.5` / `step-3.6` must be added before pausing at `3b`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Allow pre-existing step-3; write only missing 3.5/3.6; add pause/resume case asserting STEP=3b.
  - From dyn-state-machine-output.txt: Split the helper into a supplemental writer (`! -f step-3.5` / `! -f step-3.6`, optionally requiring pre-existing `step-3`) and add a pause/resume case that seeds only `step-3` before invoking it; keep the all-empty helper only as an additional negative or isolation test.


