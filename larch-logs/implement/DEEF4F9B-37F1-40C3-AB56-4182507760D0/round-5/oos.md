### FINDING_23: [OUT_OF_SCOPE] **Pre-existing sentinel symlink semantics** (`skills/design/scripts/design-driver.sh:178`) — `design-driver.sh` writes completion sentinels with `: > "$sentinel"` without rejecting symlinked sentinel paths under `.completed/`. A local actor who can plant symlinks in a session tmpdir before FINALIZE could cause truncation of the symlink target on success. This behavior predates this PR; `finalize-plan.sh` already rejects symlinked artifact files, but sentinel paths are not similarly checked.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Pre-existing sentinel symlink semantics** (`skills/design/scripts/design-driver.sh:178`) — `design-driver.sh` writes completion sentinels with `: > "$sentinel"` without rejecting symlinked sentinel paths under `.completed/`. A local actor who can plant symlinks in a session tmpdir before FINALIZE could cause truncation of the symlink target on success. This behavior predates this PR; `finalize-plan.sh` already rejects symlinked artifact files, but sentinel paths are not similarly checked.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] **Session tmpdir trust model** — All new fences assume `DESIGN_TMPDIR` and its `.completed/*` markers are controlled by the same local `/design` session (or faithfully restored pause state). Cross-user or remote tmpdir tampering is outside the plugin’s stated threat model; the allowlist validator addresses path escape, not marker spoofing within an allowed directory.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Session tmpdir trust model** — All new fences assume `DESIGN_TMPDIR` and its `.completed/*` markers are controlled by the same local `/design` session (or faithfully restored pause state). Cross-user or remote tmpdir tampering is outside the plugin’s stated threat model; the allowlist validator addresses path escape, not marker spoofing within an allowed directory.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] **`skills/design/SKILL.md:729`** — Step 2a.3 still says `If design_classification == SIMPLE, skip this section` using the orchestrator tier variable, while Step 2a.2 now uses the full entry-fence package check (`read-design-classification.sh` + sentinel files + both completion markers). The plan only required retargeting 2a.2; 2a.3 was left on the older predicate. On a mis-ordered resume that lands in 2a.3 with `design_classification == SIMPLE` but an incomplete sentinel package, collection could be skipped incorrectly. Low probability given 2a.2 routing, but slightly inconsistent with the plan’s “follow entry-fence outcome” edge-case note.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **`skills/design/SKILL.md:729`** — Step 2a.3 still says `If design_classification == SIMPLE, skip this section` using the orchestrator tier variable, while Step 2a.2 now uses the full entry-fence package check (`read-design-classification.sh` + sentinel files + both completion markers). The plan only required retargeting 2a.2; 2a.3 was left on the older predicate. On a mis-ordered resume that lands in 2a.3 with `design_classification == SIMPLE` but an incomplete sentinel package, collection could be skipped incorrectly. Low probability given 2a.2 routing, but slightly inconsistent with the plan’s “follow entry-fence outcome” edge-case note.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **Acceptance testing** — The plan requires `make lint` and several harnesses to be green. This review did not execute those commands; fidelity is based on diff and file reads only.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Acceptance testing** — The plan requires `make lint` and several harnesses to be green. This review did not execute those commands; fidelity is based on diff and file reads only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] **Branch commits (6 implementation + 1 log):** `08a83a6b2` folds FINALIZE into the Step 3b boundary and SIMPLE sentinels into the Step 2a entry fence; `e7327f1e9`–`e757acadd` are review-feedback rounds. The relocation itself is sound: the Step 3b fence runs `ACTION=FINALIZE` under `set +e` with hard `exit "$_finalize_rc"`, writes `.completed/step-3b` only after success, and Step 4’s `.completed/finalize` compatibility guard matches the pause/resume fixtures in `skills/design/scripts/test-design-pause-resume.sh`.
- **Reviewer**: dyn-workflow-resume-output.txt
- **Concern**: - **Branch commits (6 implementation + 1 log):** `08a83a6b2` folds FINALIZE into the Step 3b boundary and SIMPLE sentinels into the Step 2a entry fence; `e7327f1e9`–`e757acadd` are review-feedback rounds. The relocation itself is sound: the Step 3b fence runs `ACTION=FINALIZE` under `set +e` with hard `exit "$_finalize_rc"`, writes `.completed/step-3b` only after success, and Step 4’s `.completed/finalize` compatibility guard matches the pause/resume fixtures in `skills/design/scripts/test-design-pause-resume.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] Gate-B bypass branches (cap-reached, panel-failed, tally-error, etc.) are boundary-qualified in Step 3 and write the triple bypass sentinels before jumping to Step 3b; cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` was updated consistently.
- **Reviewer**: dyn-workflow-resume-output.txt
- **Concern**: - Gate-B bypass branches (cap-reached, panel-failed, tally-error, etc.) are boundary-qualified in Step 3 and write the triple bypass sentinels before jumping to Step 3b; cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` was updated consistently.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] The Step 2a entry fence’s conflict detection and fail-fast artifact writes before completion markers match the plan’s FM1/FM11 intent; HARD zero-sketch degraded paths remain separate and are not incorrectly short-circuited by the SIMPLE entry guard.
- **Reviewer**: dyn-workflow-resume-output.txt
- **Concern**: - The Step 2a entry fence’s conflict detection and fail-fast artifact writes before completion markers match the plan’s FM1/FM11 intent; HARD zero-sketch degraded paths remain separate and are not incorrectly short-circuited by the SIMPLE entry guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `skills/design/references/approval-gates.md:61` — Gate B’s **When** paragraph still ends at “before Step 3b” and points readers at `SKILL.md` for the matrix, while neighboring sections (e.g. line 169) spell out `Step 3b completion boundary → Step 4`. That is a doc consistency gap the new harness does not enforce because of the line-1733 positive pin; worth aligning in a follow-up even though `bash scripts/test-design-structure.sh` passes today.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] Branch commits (6 since `main`): `08a83a6b2` (fold design setup), four review-feedback commits, `07ee0c2a1` (implement run log). Harness work is concentrated in `scripts/test-design-structure.sh` (+~140 lines of assertions) and matching pins in `skills/design/scripts/test-design-pause-resume.sh`.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - Branch commits (6 since `main`): `08a83a6b2` (fold design setup), four review-feedback commits, `07ee0c2a1` (implement run log). Harness work is concentrated in `scripts/test-design-structure.sh` (+~140 lines of assertions) and matching pins in `skills/design/scripts/test-design-pause-resume.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_47: [OUT_OF_SCOPE] **Harness coverage gap (amplified, not fixed):** `scripts/test-design-structure.sh` now guards Step 3b→Step 4 routing across eight normative surfaces (`approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `plan-review.md`, `run-step3-review.sh`, `run-step3-review.md`, etc.) but does not scan `docs/collaborative-sketches.md`. The branch partially updated that consumer doc, so the “sole/only write site” drift above can persist despite green structure tests.
- **Reviewer**: dyn-contract-sync-output.txt
- **Concern**: - **Harness coverage gap (amplified, not fixed):** `scripts/test-design-structure.sh` now guards Step 3b→Step 4 routing across eight normative surfaces (`approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `plan-review.md`, `run-step3-review.sh`, `run-step3-review.md`, etc.) but does not scan `docs/collaborative-sketches.md`. The branch partially updated that consumer doc, so the “sole/only write site” drift above can persist despite green structure tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_48: [OUT_OF_SCOPE] **Pre-existing ambiguity in `skills/design/references/sketch-launch.md:7`:** “Step 2a falls through to the no-sketches path” still does not distinguish HARD degraded (Step 2a.3 guard) from SIMPLE (entry fence). The branch retargeted SIMPLE ownership but did not clarify this HARD path line; lower severity than the explicit “only write site” claims above.
- **Reviewer**: dyn-contract-sync-output.txt
- **Concern**: - **Pre-existing ambiguity in `skills/design/references/sketch-launch.md:7`:** “Step 2a falls through to the no-sketches path” still does not distinguish HARD degraded (Step 2a.3 guard) from SIMPLE (entry fence). The branch retargeted SIMPLE ownership but did not clarify this HARD path line; lower severity than the explicit “only write site” claims above.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_49: [OUT_OF_SCOPE] **Normative FINALIZE / Step 3b routing sync looks complete** on the guarded surfaces: `skills/design/SKILL.md` (Step 3b completion boundary + Step 4 compatibility guard), `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, `skills/design/scripts/design-driver.md`, and `skills/design/scripts/finalize-plan.md` all consistently name the Step 3b completion boundary as the primary FINALIZE caller and Step 4 entry as the paused-session compatibility guard.
- **Reviewer**: dyn-contract-sync-output.txt
- **Concern**: - **Normative FINALIZE / Step 3b routing sync looks complete** on the guarded surfaces: `skills/design/SKILL.md` (Step 3b completion boundary + Step 4 compatibility guard), `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, `skills/design/scripts/design-driver.md`, and `skills/design/scripts/finalize-plan.md` all consistently name the Step 3b completion boundary as the primary FINALIZE caller and Step 4 entry as the paused-session compatibility guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_53: [OUT_OF_SCOPE] `skills/design/scripts/test-design-pause-resume.sh:486-503` — The Step 3b FINALIZE-failure fixture asserts non-zero exit and the repair warning but does not assert that `.completed/step-3b` remains absent when FINALIZE fails (FM6 ordering). The harness uses a tmpdir that already has `step-3b` from `complete_design_steps`, so it cannot catch a regression that writes `step-3b` before checking `_finalize_rc`.
- **Reviewer**: dyn-shell-failfast-output.txt
- **Concern**: - `skills/design/scripts/test-design-pause-resume.sh:486-503` — The Step 3b FINALIZE-failure fixture asserts non-zero exit and the repair warning but does not assert that `.completed/step-3b` remains absent when FINALIZE fails (FM6 ordering). The harness uses a tmpdir that already has `step-3b` from `complete_design_steps`, so it cannot catch a regression that writes `step-3b` before checking `_finalize_rc`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_54: [OUT_OF_SCOPE] `skills/design/scripts/design-driver.sh:141-143,178` — Pre-existing behavior: when `.completed/finalize` already exists, `ACTION=FINALIZE` returns exit 0 with `STEP_SKIPPED` without re-validating or recreating `rejected-findings.md` et al. The Step 3b boundary treats that as success and still writes `step-3b`; Step 4’s compatibility guard also skips FINALIZE when the finalize sentinel exists. This branch did not change `design-driver.sh`, but the earlier FINALIZE fold makes stale-sentinel exposure slightly more likely on re-entry at Step 3b.
- **Reviewer**: dyn-shell-failfast-output.txt
- **Concern**: - `skills/design/scripts/design-driver.sh:141-143,178` — Pre-existing behavior: when `.completed/finalize` already exists, `ACTION=FINALIZE` returns exit 0 with `STEP_SKIPPED` without re-validating or recreating `rejected-findings.md` et al. The Step 3b boundary treats that as success and still writes `step-3b`; Step 4’s compatibility guard also skips FINALIZE when the finalize sentinel exists. This branch did not change `design-driver.sh`, but the earlier FINALIZE fold makes stale-sentinel exposure slightly more likely on re-entry at Step 3b.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **code-quality** `skills/design/scripts/test-design-pause-resume.sh` — The new SIMPLE/FINALIZE fixtures embed production fence bodies inline rather than sourcing from SKILL or a shared helper. This follows an older copy-paste style but diverges from the `apply_gate_b_bypass_sentinels` precedent introduced in the same test file family. Out of scope because the duplication in the harness amplifies findings 1–2 rather than introducing new production behavior. **Summary:** The fold achieves the plan’s turn-reduction goal and the routing retarget is thorough. The main maintainability risk is duplicated shell contracts (SIMPLE sentinels and FINALIZE wrappers) without the shared-helper pattern the repo already uses for similar fence logic. Consolidating those into thin scripts or sourced helpers would better match KISS and reduce drift risk on the next design refactor round.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

