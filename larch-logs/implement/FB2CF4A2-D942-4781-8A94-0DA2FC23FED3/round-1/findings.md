### FINDING_1: [OUT_OF_SCOPE] Gate-B bypass sentinel structural pins cover only plan-size-trigger
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-contracts-output.txt, dyn-state-machine-output.txt, dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The structural regression checks pin the triple-sentinel prose for only the `plan-size-trigger` Gate-B-bypass branch. Other bypass statuses such as `cap-reached`, `tally-error`, `panel-failed`, and related paths could lose `step-3`, `step-3.5`, or `step-3.6` sentinel writes without CI failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend assert_gate_b_bypass_branch_sentinels to every Gate-B-bypass bullet or centralize one shared excerpt in SKILL.md and assert all branches reference it.
  - From cursor-specialist-correctness-output.txt: Add structural pins for other named bypass bullets if you want parity with original #3436 scope.
  - From cursor-specialist-testing-output.txt: Parameterize structural pin across all Gate-B-bypass anchors or add per-status checks
  - From cursor-specialist-edge-cases-output.txt: Parameterize branch pin or assert all bypass bullets in the post-loop matrix.
  - From dyn-state-machine-output.txt: Extend `assert_gate_b_bypass_branch_sentinels` (or add parallel assertions) for at least `panel-failed` and `cap-reached`, or factor a shared markdown excerpt and assert all bypass bullets reference it.

### FINDING_2: [OUT_OF_SCOPE] Step 3.6 accepts rc=0 assessor runs without result env validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The Step 3.6 fence writes `step-3.6` after assessor exit `0` based only on `_assessor_rc`, without requiring a readable `.step3.6-assessor.env` or parsed `ASSESSOR_STATUS`. A stub or malformed driver that exits `0` with no output can be treated as success, although the real driver currently fail-closes this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only if you want belt-and-suspenders: after rc `0`, require a readable result env with allowlisted keys before writing `step-3.6`.

### FINDING_3: Postplan quiet-mode WARN regression lacks present-but-invalid run-params coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The default-quiet `WARN=` regression covers absent `run-params.json`, but not a readable file with missing or invalid `design_classification`. A regression could prevent operators from seeing `WARN=` on stdout for incomplete run params while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: A second env -u LARCH_QUIET_DISABLE case with readable run-params missing/invalid design_classification asserting WARN= on stdout

### FINDING_4: [OUT_OF_SCOPE] Gate-B bypass tests use helper behavior instead of production Step 3 routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The pause/resume coverage validates sentinel creation through a test helper and markdown pins, not through live production Step 3 / Gate-B bypass orchestration. Real bypass paths still depend on prompt-side SKILL prose being followed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Hermetic Step 3 handoff stub asserting tmpdir sentinels without calling apply_gate_b_bypass_sentinels

### FINDING_5: Step 3.6 classification warning visibility is split between stderr and WARN= channels
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 surfaces classification warnings on stderr, while postplan uses stdout `WARN=` KVs. Automated or quiet consumers that parse only `WARN=` may miss Step 3.6 defaulting context, and coverage for the cheap gate warning path is weak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add apply_step3_6_handoff case asserting warning text on SIMPLE skip with bad classification
  - From cursor-specialist-edge-cases-output.txt: Document dual channels or emit WARN= at Step 3.6 cheap gate too.

### FINDING_6: [OUT_OF_SCOPE] Postplan pause checkpoint lacks explicit --repo passthrough
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The internal `.pause-requested` path in `design-postplan-emit.sh` still calls `design-pause-save.sh` without `${REPO:+--repo "$REPO"}`. Cross-repo `/design` runs could save pause state against the default `gh` repo instead of the session repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: mirror the Step 3.6 `${REPO:+--repo "$REPO"}` passthrough on this pause checkpoint if cross-repo design is supported.

### FINDING_7: [OUT_OF_SCOPE] design-pause-save trusts supplied --repo without local regex validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-save.sh` returns a supplied `--repo` without revalidating the `OWNER/REPO` regex locally, relying on upstream validation from `write-design-current-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_8: Gate-B bypass helper rejects the realistic pre-existing step-3 layout
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: `apply_gate_b_bypass_sentinels` aborts if `step-3` already exists, but production Gate-B bypass normally occurs after Step 3 has already written `step-3`. CI therefore misses the realistic state where `step-3` exists and only `step-3.5` / `step-3.6` must be added before pausing at `3b`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Allow pre-existing step-3; write only missing 3.5/3.6; add pause/resume case asserting STEP=3b.
  - From dyn-state-machine-output.txt: Split the helper into a supplemental writer (`! -f step-3.5` / `! -f step-3.6`, optionally requiring pre-existing `step-3`) and add a pause/resume case that seeds only `step-3` before invoking it; keep the all-empty helper only as an additional negative or isolation test.

### FINDING_9: Step 3.6 region marker selection does not detect duplicate markers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: Region bounds use the first matching start/end marker without asserting uniqueness. Duplicate or partial marker collisions could silently shrink or mis-aim the guarded region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail unless exactly one start marker (or use paired anchor logic).
  - From dyn-grep-scope-output.txt: After resolving line numbers, assert uniqueness (`grep -cF` equals 1 for each marker) or fail when multiple start matches exist.

### FINDING_10: [OUT_OF_SCOPE] Step 3b entry pause guard lacks REPO passthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Step 3b entry pause-save path still omits `${REPO:+--repo "$REPO"}`, so a forked or explicit-repo design paused during 3b may write pause state to the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Thread ${REPO:+--repo "$REPO"} on 3b entry guard (separate change).

### FINDING_11: Empty-state Gate-B bypass pause/resume test lacks load round-trip
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-contracts-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: The new empty-state Gate-B-bypass case runs `design-pause-save.sh` and asserts `STEP=3b`, but never runs `design-pause-load.sh`. This misses regressions where save succeeds but restore/re-entry mis-derives `STEP` from the triple-sentinel layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: After the save assertions on DESIGN_GATE_B, run design-pause-load.sh into a fresh restore tmpdir and assert LOAD_OK=true and STEP=3b, mirroring the Step 3.6 save/load pattern above.
  - From cursor-specialist-plan-fidelity-output.txt: Update the doc after adding the load step, or temporarily narrow the prose to match current save-only coverage.
  - From dyn-bash-contracts-output.txt: After a successful save, run `design-pause-load.sh` into a fresh restore tmpdir (same pattern as the Step 3.6 case above) and assert `LOAD_OK=true` plus `STEP=3b`.
  - From dyn-state-machine-output.txt: After a successful save, run load into a fresh restore tmpdir (mirror the `design-36` pattern at `skills/design/scripts/test-design-pause-resume.sh:237-238`) and assert `LOAD_OK=true` and `STEP=3b`.

### FINDING_12: [OUT_OF_SCOPE] Pre-written triple-sentinel case also lacks load coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: The pre-written triple-sentinel `DESIGN_GATE_B_DONE` case is save-only and does not explicitly exercise load behavior, leaving resume regressions for that layout untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Label the case as pre-written layout and add a load assertion after save for DESIGN_GATE_B_DONE.

### FINDING_13: [OUT_OF_SCOPE] Postplan helper failure can silently default HARD without WARN=
- **Reviewer(s)**: dyn-bash-contracts-output.txt, dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: If `read-design-classification.sh` exits non-zero without stderr, or is not executable, `design-postplan-emit.sh` can force `WORKFLOW_PATH=HARD` without emitting a corresponding `WARN=` under quiet mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contracts-output.txt: On `_classification_rc -ne 0`, append a synthetic `WARN_LINES` entry (for example noting non-zero exit and that classification defaulted to HARD) before forcing `WORKFLOW_PATH=HARD`, or document and test that the helper must never exit non-zero without stderr.

### FINDING_14: Postplan early fail paths drop already-captured classification warnings
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: important
- **Concern**: `design-postplan-emit.sh` captures classification stderr into `WARN_LINES` before later guards, but fatal `fail()` exits after that point do not write the result env or emit stdout `WARN=` records. Classification warnings can disappear on early failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-warnings-output.txt: On fatal exits after the classification read, either invoke a small helper that writes/emits `WARN_LINES` (with a terminal `POSTPLAN_EMIT_STATUS` such as `emit-failed` / `missing-plan`) or emit each warning via `larch_err` / `emit_kv WARN` before `exit 2`.

### FINDING_15: Multiline WARN values can diverge result-env and stdout contracts
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: `WARN=` values are written to the result env without the same newline validation enforced by stdout `emit_kv`. A multiline warning could leave a complete env file but abort stdout emission under `set -euo pipefail`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-warnings-output.txt: Sanitize or split warning text before appending to `WARN_LINES`, validate when building `_kvs`, and/or wrap the WARN `emit_kv` loop in `set +e` with explicit handling so one bad line cannot truncate the contract stream.

### FINDING_16: [OUT_OF_SCOPE] Postplan quiet-mode test does not assert WARN in result env
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: The quiet-mode test asserts `WARN=` on captured stdout only, not a matching row in `.design-postplan-emit-result.env`, even though Step 2b parsing is file-first.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: Scoped thin-fence temp file is not cleaned up on failure
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: `assert_thin_fence` writes a scoped slice to an `mktemp` file but removes it only on the success path. Failing assertions can leave debris under `${TMPDIR:-/tmp}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Use a `trap` on the scoped path (`trap 'rm -f "$subject"' RETURN` or an ERR trap) so cleanup runs on every exit from the function, or wrap scoped checks in a subshell whose temp file is always removed.

### FINDING_18: Assessor-env read-loop anti-shape can false-negative on incidental “done”
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The awk guard clears `in_read_loop` on any line containing `done`, so a comment or string inside the loop can reset state before the real `done <...assessor.env` redirect and hide a banned file-first read loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Only clear `in_read_loop` when `done` is a statement terminator (e.g. match `^[[:space:]]*done([[:space:]]|$)`), or require the redirect match on the same `done` line and drop the generic `done` reset rule.

### FINDING_19: Thin-fence positive checks are too broad
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The thin-fence positives grep the whole extracted Step 3.6 region for `set +e` and `$?`, including prose after the bash fence. Documentation text could satisfy the check while the real assessor handoff loses rc capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Narrow the positive checks to the first fenced bash block (extract lines between the opening and closing ` ```bash ` pair inside the region) or anchor greps near `_assessor_out` / `_assessor_rc`.

### FINDING_20: Gate-B bypass helper and markdown pin can drift independently
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: Gate-B bypass coverage is split across hand-maintained copies: the test helper and the markdown substring structural pin. CI does not assert that they remain identical, so one can drift while the other still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Have the structural pin source the same literal array the helper uses (shared bash fragment), or add a self-test that runs `assert_gate_b_bypass_branch_sentinels` on a synthetic SKILL snippet with a deliberately stripped bullet and expects failure (mirroring `run_thin_fence_self_tests`).

### FINDING_21: Gate-B bypass structural pin lacks a negative self-test
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: `assert_gate_b_bypass_branch_sentinels` lacks a controlled negative fixture, so delimiter typos or overly narrow extraction could weaken the pin without an explicit sensitivity test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: Add a minimal synthetic markdown fixture to `run_thin_fence_self_tests` (or a sibling function) that must fail when the three `: >` lines are removed from the `plan-size-trigger` bullet only.

### FINDING_22: [OUT_OF_SCOPE] Unrelated larch-logs flush is mixed into the reviewed PR surface
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: Commit `77afb7125` is a committed `larch-logs/implement/...` flush unrelated to the Step 3.6 harness changes, expanding the review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: consider keeping that out of the same PR as the structural/test changes if you want a review-only diff surface.
