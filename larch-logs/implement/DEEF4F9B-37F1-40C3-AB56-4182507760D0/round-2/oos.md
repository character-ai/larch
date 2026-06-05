### FINDING_14: [OUT_OF_SCOPE] **Out-of-scope** `skills/design/scripts/run-step3-review.md:31` — Documents routing as `Step 3b → Step 3b completion boundary → Step 4`, but this file is outside the six surfaces scanned by `assert_no_direct_step3b_step4_routes`. Stale routing here would not fail CI. Worth aligning if you extend the guard later.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Out-of-scope** `skills/design/scripts/run-step3-review.md:31` — Documents routing as `Step 3b → Step 3b completion boundary → Step 4`, but this file is outside the six surfaces scanned by `assert_no_direct_step3b_step4_routes`. Stale routing here would not fail CI. Worth aligning if you extend the guard later. --- ### What looks correct
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Step 3b completion boundary runs FINALIZE under `set +e`, prints repair warning, and `exit "$_finalize_rc"` on failure; writes `.completed/step-3b` only after success (`skills/design/SKILL.md:1290-1305`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 3b completion boundary runs FINALIZE under `set +e`, prints repair warning, and `exit "$_finalize_rc"` on failure; writes `.completed/step-3b` only after success (`skills/design/SKILL.md:1290-1305`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] Step 4 compatibility guard mirrors that pattern and gates on missing `.completed/finalize` (`skills/design/SKILL.md:1316-1325`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 4 compatibility guard mirrors that pattern and gates on missing `.completed/finalize` (`skills/design/SKILL.md:1316-1325`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] SIMPLE sentinels are guard-scoped in the entry fence with fail-fast `set -e` and completion markers after artifact writes (`skills/design/SKILL.md:649-658`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - SIMPLE sentinels are guard-scoped in the entry fence with fail-fast `set -e` and completion markers after artifact writes (`skills/design/SKILL.md:649-658`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] Step 2a.5 resume compatibility guard runs **before** the SIMPLE skip prose (fixed in round 1).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 2a.5 resume compatibility guard runs **before** the SIMPLE skip prose (fixed in round 1).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] Cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` uses boundary-qualified wording.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` uses boundary-qualified wording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] Harness adds region pins for FINALIZE placement, SIMPLE entry-fence guards, routing guards, and pause/resume fixtures for legacy `.completed/step-3b` without `.completed/finalize` and legacy SIMPLE `.completed/step-2a` without `.completed/step-2a.5`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Harness adds region pins for FINALIZE placement, SIMPLE entry-fence guards, routing guards, and pause/resume fixtures for legacy `.completed/step-3b` without `.completed/finalize` and legacy SIMPLE `.completed/step-2a` without `.completed/step-2a.5`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Anti-halt literal `Continue to Step 4 IMMEDIATELY` preserved (`skills/design/SKILL.md:1288`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Anti-halt literal `Continue to Step 4 IMMEDIATELY` preserved (`skills/design/SKILL.md:1288`). I did not run `make lint` or the harness scripts in this read-only review. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	correctness	skills/design/SKILL.md:649-697	Step 2a.2 skip allows proceeding to Step 2b when a later re-read returns SIMPLE even if the Step 2a entry fence defaulted to HARD on read failure and never wrote SIMPLE sentinels or completion markers. If read-design-classification.sh fails transiently in the entry bash block (stderr suppressed, HARD default) but succeeds when the orchestrator re-reads at 2a.2, the run skips sketches without NO_SKETCHES artifacts or .completed/step-2a / step-2a.5 markers; Step 2b and pause/resume can proceed with missing or stale synthesis files.	Require 2a.2 skip only when approach-synthesis.txt contains NO_SKETCHES_CLASSIFIED_SIMPLE or both step-2a and step-2a.5 completion markers exist; do not treat a bare re-read SIMPLE as sufficient unless entry-fence writes succeeded or are re-executed. 1	in_scope	latent	correctness	skills/design/SKILL.md:1098-1122	Gate-B-bypass branch-matrix lines say short-circuit to Step 3b or continue to Step 3b instead without naming the Step 3b completion boundary on the same line; the harness guard only catches lines mentioning both Step 3b and Step 4. An orchestrator following only the matrix could reach Step 4 without FINALIZE after the standalone Step 4 FINALIZE turn was removed.	Add completion-boundary wording to each bypass matrix bullet or a mandatory post-matrix sentence that every Step 3b arrival must run the completion boundary before Step 4. 1	in_scope	nit	correctness	skills/design/SKILL.md:782	Step 2a success-boundary prose claims to include the zero-sketch sentinel path but the HARD zero-sketches guard bypasses 2a.4 and never reaches that boundary write.	M Clarify zero-sketch path must write step-2a explicitly or remove including the zero-sketch sentinel path from the 2a.4 boundary line. 1	out_of_scope	latent	architecture	skills/design/scripts/run-step3-review.md:31	run-step3-review.md documents Step 3b routing but is excluded from the six-surface routing guard in test-design-structure.sh.	Extend assert_no_direct_step3b_step4_routes to include run-step3-review.md or add a dedicated contains pin for its routing prose. ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] The Step 3b completion-boundary FINALIZE fence (`skills/design/SKILL.md:1290-1306`) and Step 4 compatibility guard (`skills/design/SKILL.md:1316-1326`) are correctly ordered: `step-3b` is written only after successful FINALIZE, and Step 4 re-runs FINALIZE when `.completed/finalize` is absent. Pause/resume fixtures for legacy `step-3b` without `finalize` look sound.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - The Step 3b completion-boundary FINALIZE fence (`skills/design/SKILL.md:1290-1306`) and Step 4 compatibility guard (`skills/design/SKILL.md:1316-1326`) are correctly ordered: `step-3b` is written only after successful FINALIZE, and Step 4 re-runs FINALIZE when `.completed/finalize` is absent. Pause/resume fixtures for legacy `step-3b` without `finalize` look sound.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] `design-driver.sh` idempotency via `.completed/finalize` is appropriate for Gate C re-runs; `finalize-plan.sh` still materializes missing may-be-empty artifacts, which preserves the pre-change guarantee that Step 4 can read `rejected-findings.md` on voting-skipped paths.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - `design-driver.sh` idempotency via `.completed/finalize` is appropriate for Gate C re-runs; `finalize-plan.sh` still materializes missing may-be-empty artifacts, which preserves the pre-change guarantee that Step 4 can read `rejected-findings.md` on voting-skipped paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] **Pre-existing / not amplified:** The HARD zero-sketches degraded path (line 717) still jumps to Step 2b without writing `.completed/step-2a`, while line 782 claims the zero-sketch sentinel path writes that marker; that inconsistency predates this branch’s SIMPLE entry-fence work.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Pre-existing / not amplified:** The HARD zero-sketches degraded path (line 717) still jumps to Step 2b without writing `.completed/step-2a`, while line 782 claims the zero-sketch sentinel path writes that marker; that inconsistency predates this branch’s SIMPLE entry-fence work.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_44: [OUT_OF_SCOPE] **Harness gap:** `assert_no_direct_step3b_step4_routes` only flags lines that mention both Step 3b and Step 4, so it does not catch the incomplete bypass-matrix retarget at 1098–1105 (which mention Step 3b alone). That explains why CI can pass while FM2 prose remains partially unfixed.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Harness gap:** `assert_no_direct_step3b_step4_routes` only flags lines that mention both Step 3b and Step 4, so it does not catch the incomplete bypass-matrix retarget at 1098–1105 (which mention Step 3b alone). That explains why CI can pass while FM2 prose remains partially unfixed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] **Otherwise sound:** The Step 3b FINALIZE fence (1295–1305) and Step 4 compatibility guard (1316–1325) correctly use `set +e` / `_finalize_rc=$?` / `set -e` / `exit "$_finalize_rc"`, write `step-3b` only after success, and gate on `.completed/finalize`. The SIMPLE entry fence orders artifact writes before completion markers under `set -e` as intended.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Otherwise sound:** The Step 3b FINALIZE fence (1295–1305) and Step 4 compatibility guard (1316–1325) correctly use `set +e` / `_finalize_rc=$?` / `set -e` / `exit "$_finalize_rc"`, write `step-3b` only after success, and gate on `.completed/finalize`. The SIMPLE entry fence orders artifact writes before completion markers under `set -e` as intended.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_48: [OUT_OF_SCOPE] `skills/design/references/assessor.md:37,46-50,77` still says “Continue → Step 3b unchanged” / “continues to Step 3b” without naming the completion boundary. That predates this branch and is lower risk because those lines do not route directly to Step 4; entering Step 3b still implies executing the Step 3b region in `SKILL.md`, which ends with the completion-boundary fence.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - `skills/design/references/assessor.md:37,46-50,77` still says “Continue → Step 3b unchanged” / “continues to Step 3b” without naming the completion boundary. That predates this branch and is lower risk because those lines do not route directly to Step 4; entering Step 3b still implies executing the Step 3b region in `SKILL.md`, which ends with the completion-boundary fence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_49: [OUT_OF_SCOPE] The anti-halt step chain `3b→4→4b` in `skills/design/SKILL.md:29` remains a coarse transition list and is intentionally pinned by `scripts/test-design-structure.sh`. It is not a bare “Step 3b → Step 4” bypass line, and the Step 3b section itself now makes the completion boundary explicit before Step 4.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - The anti-halt step chain `3b→4→4b` in `skills/design/SKILL.md:29` remains a coarse transition list and is intentionally pinned by `scripts/test-design-structure.sh`. It is not a bare “Step 3b → Step 4” bypass line, and the Step 3b section itself now makes the completion boundary explicit before Step 4.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_50: [OUT_OF_SCOPE] Within the six guarded surfaces, the retargeted routes in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, and `skills/design/scripts/run-step3-review.md` are aligned on boundary-qualified wording. The Step 3b completion-boundary fence and Step 4 compatibility guard in `skills/design/SKILL.md:1290-1326` match the plan’s ordering and fail-fast semantics.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - Within the six guarded surfaces, the retargeted routes in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, and `skills/design/scripts/run-step3-review.md` are aligned on boundary-qualified wording. The Step 3b completion-boundary fence and Step 4 compatibility guard in `skills/design/SKILL.md:1290-1326` match the plan’s ordering and fail-fast semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_56: [OUT_OF_SCOPE] `skills/design/scripts/run-step3-review.md:31` still documents cap routing (`Step 3b → Step 3b completion boundary → Step 4`) but is outside the six scanned surfaces; it is correctly worded today, yet doc drift there would not trip `assert_no_direct_step3b_step4_routes`.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - `skills/design/scripts/run-step3-review.md:31` still documents cap routing (`Step 3b → Step 3b completion boundary → Step 4`) but is outside the six scanned surfaces; it is correctly worded today, yet doc drift there would not trip `assert_no_direct_step3b_step4_routes`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_57: [OUT_OF_SCOPE] Pause/resume compatibility for legacy `.completed/step-3b` without `.completed/finalize` is exercised in `skills/design/scripts/test-design-pause-resume.sh:250-296`, which is stronger coverage than the structure harness alone provides.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - Pause/resume compatibility for legacy `.completed/step-3b` without `.completed/finalize` is exercised in `skills/design/scripts/test-design-pause-resume.sh:250-296`, which is stronger coverage than the structure harness alone provides.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/design/SKILL.md:1314
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 4 pause-save lacks REPO threading present on Step 3b completion fence. Fork/multi-repo pause saves at Step 4 may omit --repo while earlier steps include it; pre-existing inconsistency now more visible. Thread ${REPO:+--repo "$REPO"} on Step 4 entry pause-save in a separate hygiene PR.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

