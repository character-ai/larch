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


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_10: [OUT_OF_SCOPE] Step 3b entry pause guard lacks REPO passthrough
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The Step 3b entry pause-save path still omits `${REPO:+--repo "$REPO"}`, so a forked or explicit-repo design paused during 3b may write pause state to the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Thread ${REPO:+--repo "$REPO"} on 3b entry guard (separate change).


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] Pre-written triple-sentinel case also lacks load coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: The pre-written triple-sentinel `DESIGN_GATE_B_DONE` case is save-only and does not explicitly exercise load behavior, leaving resume regressions for that layout untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Label the case as pre-written layout and add a load assertion after save for DESIGN_GATE_B_DONE.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] Postplan helper failure can silently default HARD without WARN=
- **Reviewer(s)**: dyn-bash-contracts-output.txt, dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: If `read-design-classification.sh` exits non-zero without stderr, or is not executable, `design-postplan-emit.sh` can force `WORKFLOW_PATH=HARD` without emitting a corresponding `WARN=` under quiet mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contracts-output.txt: On `_classification_rc -ne 0`, append a synthetic `WARN_LINES` entry (for example noting non-zero exit and that classification defaulted to HARD) before forcing `WORKFLOW_PATH=HARD`, or document and test that the helper must never exit non-zero without stderr.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] Postplan quiet-mode test does not assert WARN in result env
- **Reviewer(s)**: dyn-kv-warnings-output.txt
- **Severity**: latent
- **Concern**: The quiet-mode test asserts `WARN=` on captured stdout only, not a matching row in `.design-postplan-emit-result.env`, even though Step 2b parsing is file-first.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated


### FINDING_2: [OUT_OF_SCOPE] Step 3.6 accepts rc=0 assessor runs without result env validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The Step 3.6 fence writes `step-3.6` after assessor exit `0` based only on `_assessor_rc`, without requiring a readable `.step3.6-assessor.env` or parsed `ASSESSOR_STATUS`. A stub or malformed driver that exits `0` with no output can be treated as success, although the real driver currently fail-closes this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Only if you want belt-and-suspenders: after rc `0`, require a readable result env with allowlisted keys before writing `step-3.6`.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_22: [OUT_OF_SCOPE] Unrelated larch-logs flush is mixed into the reviewed PR surface
- **Reviewer(s)**: dyn-grep-scope-output.txt
- **Severity**: nit
- **Concern**: Commit `77afb7125` is a committed `larch-logs/implement/...` flush unrelated to the Step 3.6 harness changes, expanding the review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-grep-scope-output.txt: consider keeping that out of the same PR as the structural/test changes if you want a review-only diff surface.

Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral


### FINDING_4: [OUT_OF_SCOPE] Gate-B bypass tests use helper behavior instead of production Step 3 routing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-state-machine-output.txt, dyn-grep-scope-output.txt
- **Severity**: latent
- **Concern**: The pause/resume coverage validates sentinel creation through a test helper and markdown pins, not through live production Step 3 / Gate-B bypass orchestration. Real bypass paths still depend on prompt-side SKILL prose being followed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Hermetic Step 3 handoff stub asserting tmpdir sentinels without calling apply_gate_b_bypass_sentinels


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


### FINDING_6: [OUT_OF_SCOPE] Postplan pause checkpoint lacks explicit --repo passthrough
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The internal `.pause-requested` path in `design-postplan-emit.sh` still calls `design-pause-save.sh` without `${REPO:+--repo "$REPO"}`. Cross-repo `/design` runs could save pause state against the default `gh` repo instead of the session repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: mirror the Step 3.6 `${REPO:+--repo "$REPO"}` passthrough on this pause checkpoint if cross-repo design is supported.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] design-pause-save trusts supplied --repo without local regex validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-pause-save.sh` returns a supplied `--repo` without revalidating the `OWNER/REPO` regex locally, relying on upstream validation from `write-design-current-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated


