### FINDING_1: code-quality: skills/design/scripts/test-design-pause-resume.sh:261-291
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] The Step 4 FINALIZE compatibility guard bash block is duplicated three times verbatim. A future SKILL.md tweak to warn/exit semantics could update only one copy; pause/resume tests would still pass while no longer matching production orchestration. Extract a single run_step4_finalize_compat_guard helper and invoke it from all three test sites.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/SKILL.md:1291-1326
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 3b completion-boundary and Step 4 entry FINALIZE fences are near-duplicates. Drift between fresh-run and legacy-resume paths could reintroduce warning-only failure or missing step-3b ordering on one path only. Optional: centralize the fence body in a references/finalize-boundary.md byte-preserved block cited by both SKILL sites.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-design-structure.sh:276-305
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 4 region slicing uses two different HTML comment needles (<!-- step:4 — vs <!-- step:4 ). A marker rename could break one assertion while leaving another passing, masking structural regressions. Unify on one marker string or one region-extraction helper for all Step 3b/4 assertions.
- **Suggested revision**: Address the concern above.

### FINDING_4: architecture: skills/design/SKILL.md:1098-1105
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Gate-B-bypass branch-matrix lines route to Step 3b without naming the completion boundary. An orchestrator following only the matrix could run Step 3b diagram branches and jump to Step 4 without FINALIZE, recreating the missing rejected-findings.md failure on zero-voting paths. Append boundary-qualified wording to each short-circuit bullet, consistent with line 1116.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/test-design-structure.sh:307-333
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Routing guard omits run-step3-review.md despite it carrying updated normative routing prose. Future .md-only edits could reintroduce bare Step 3b→Step 4 chains that .sh guard would not catch. Add run-step3-review.md to assert_no_direct_step3b_step4_routes scan list.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/SKILL.md:689
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 2a.3 still gates SIMPLE skip on mental design_classification while 2a.2 uses sentinel/re-read. If run-params and entry-fence outcomes diverge on resume, 2a.2 could skip to 2b while 2a.3 prose still references a different classification source. Align 2a.3 and 2a.5 SIMPLE skip guards with the 2a.2 sentinel-or-re-read predicate.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/design/SKILL.md:1314
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 4 pause-save lacks REPO threading present on Step 3b completion fence. Fork/multi-repo pause saves at Step 4 may omit --repo while earlier steps include it; pre-existing inconsistency now more visible. Thread ${REPO:+--repo "$REPO"} on Step 4 entry pause-save in a separate hygiene PR.
- **Suggested revision**: Address the concern above.

### FINDING_8: `08a83a6b2` — Fold design setup into existing boundaries  
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `08a83a6b2` — Fold design setup into existing boundaries
- **Suggested revision**: Address the concern above.

### FINDING_9: `07ee0c2a1` — chore(larch-logs) flush (out of scope per instructions)  
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `07ee0c2a1` — chore(larch-logs) flush (out of scope per instructions)
- **Suggested revision**: Address the concern above.

### FINDING_10: `e7327f1e9` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `e7327f1e9` — Address code review feedback (round 1) **Verdict:** The refactor largely matches the plan — FINALIZE moved to the Step 3b completion boundary, SIMPLE sentinels folded into the Step 2a entry fence, cross-doc routing updated, and harness coverage expanded. One correctness gap remains around SIMPLE skip logic. ---
- **Suggested revision**: Address the concern above.

### FINDING_11: **Important** `correctness` `skills/design/SKILL.md:649-697` — **Plan-correctness / requirements (both):** Step 2a.2 allows skipping to Step 2b when a **re-read** of `read-design-classification.sh` returns `SIMPLE`, even if the entry fence did not write sentinels (because the entry fence uses `2>/dev/null || printf HARD` and defaults to `HARD` on read failure). If classification read fails transiently in the entry bash block but succeeds later, the orchestrator can skip sketches without writing `NO_SKETCHES_CLASSIFIED_SIMPLE`, `contested-decisions.md`, `dialectic-resolutions.md`, or `.completed/step-2a` / `.completed/step-2a.5`, breaking Step 2b assumptions and pause/resume sentinels. **Suggested fix:** Make 2a.2 skip require sentinel presence (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) or both `.completed/step-2a` and `.completed/step-2a.5` exist; treat a bare re-read of `SIMPLE` as insufficient unless the entry fence also succeeded (or re-run the guarded write block on miss).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Important** `correctness` `skills/design/SKILL.md:649-697` — **Plan-correctness / requirements (both):** Step 2a.2 allows skipping to Step 2b when a **re-read** of `read-design-classification.sh` returns `SIMPLE`, even if the entry fence did not write sentinels (because the entry fence uses `2>/dev/null || printf HARD` and defaults to `HARD` on read failure). If classification read fails transiently in the entry bash block but succeeds later, the orchestrator can skip sketches without writing `NO_SKETCHES_CLASSIFIED_SIMPLE`, `contested-decisions.md`, `dialectic-resolutions.md`, or `.completed/step-2a` / `.completed/step-2a.5`, breaking Step 2b assumptions and pause/resume sentinels. **Suggested fix:** Make 2a.2 skip require sentinel presence (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) or both `.completed/step-2a` and `.completed/step-2a.5` exist; treat a bare re-read of `SIMPLE` as insufficient unless the entry fence also succeeded (or re-run the guarded write block on miss).
- **Suggested revision**: Address the concern above.

### FINDING_12: **Latent** `correctness` `skills/design/SKILL.md:1098-1122` — **Plan-correctness (FM2 residual):** Several Gate-B-bypass branch-matrix bullets still say only “short-circuit to Step 3b” / “continue to Step 3b instead” without naming the completion boundary on the same line. The harness line-scoped guard only fires when a line mentions both Step 3b and Step 4, so these lines are not pinned. An orchestrator could treat Step 3b as terminal and skip FINALIZE before Step 4 (the failure mode the plan called out). **Suggested fix:** Add “then run the Step 3b completion boundary (FINALIZE + step-3b), then Step 4” to each bypass matrix line, or add a single mandatory sentence immediately after the matrix: “Every path that reaches Step 3b MUST run the Step 3b completion boundary before Step 4.”
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **Latent** `correctness` `skills/design/SKILL.md:1098-1122` — **Plan-correctness (FM2 residual):** Several Gate-B-bypass branch-matrix bullets still say only “short-circuit to Step 3b” / “continue to Step 3b instead” without naming the completion boundary on the same line. The harness line-scoped guard only fires when a line mentions both Step 3b and Step 4, so these lines are not pinned. An orchestrator could treat Step 3b as terminal and skip FINALIZE before Step 4 (the failure mode the plan called out). **Suggested fix:** Add “then run the Step 3b completion boundary (FINALIZE + step-3b), then Step 4” to each bypass matrix line, or add a single mandatory sentence immediately after the matrix: “Every path that reaches Step 3b MUST run the Step 3b completion boundary before Step 4.”
- **Suggested revision**: Address the concern above.

### FINDING_13: **Nit** `correctness` `skills/design/SKILL.md:782` — Step 2a success-boundary prose says it applies “including the zero-sketch sentinel path,” but the HARD zero-sketches guard at 2a.3 routes directly to Step 2b and bypasses 2a.4, so that boundary write is never reached on that path. This is pre-existing misleading prose, not introduced by the fold, but it can confuse resume debugging. **Suggested fix:** Clarify that the zero-sketch path must explicitly write `.completed/step-2a` in its own branch, or remove “including the zero-sketch sentinel path” from the 2a.4 boundary line.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Nit** `correctness` `skills/design/SKILL.md:782` — Step 2a success-boundary prose says it applies “including the zero-sketch sentinel path,” but the HARD zero-sketches guard at 2a.3 routes directly to Step 2b and bypasses 2a.4, so that boundary write is never reached on that path. This is pre-existing misleading prose, not introduced by the fold, but it can confuse resume debugging. **Suggested fix:** Clarify that the zero-sketch path must explicitly write `.completed/step-2a` in its own branch, or remove “including the zero-sketch sentinel path” from the 2a.4 boundary line. ---
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] **Out-of-scope** `skills/design/scripts/run-step3-review.md:31` — Documents routing as `Step 3b → Step 3b completion boundary → Step 4`, but this file is outside the six surfaces scanned by `assert_no_direct_step3b_step4_routes`. Stale routing here would not fail CI. Worth aligning if you extend the guard later.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **Out-of-scope** `skills/design/scripts/run-step3-review.md:31` — Documents routing as `Step 3b → Step 3b completion boundary → Step 4`, but this file is outside the six surfaces scanned by `assert_no_direct_step3b_step4_routes`. Stale routing here would not fail CI. Worth aligning if you extend the guard later. --- ### What looks correct
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Step 3b completion boundary runs FINALIZE under `set +e`, prints repair warning, and `exit "$_finalize_rc"` on failure; writes `.completed/step-3b` only after success (`skills/design/SKILL.md:1290-1305`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 3b completion boundary runs FINALIZE under `set +e`, prints repair warning, and `exit "$_finalize_rc"` on failure; writes `.completed/step-3b` only after success (`skills/design/SKILL.md:1290-1305`).
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Step 4 compatibility guard mirrors that pattern and gates on missing `.completed/finalize` (`skills/design/SKILL.md:1316-1325`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 4 compatibility guard mirrors that pattern and gates on missing `.completed/finalize` (`skills/design/SKILL.md:1316-1325`).
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] SIMPLE sentinels are guard-scoped in the entry fence with fail-fast `set -e` and completion markers after artifact writes (`skills/design/SKILL.md:649-658`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - SIMPLE sentinels are guard-scoped in the entry fence with fail-fast `set -e` and completion markers after artifact writes (`skills/design/SKILL.md:649-658`).
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Step 2a.5 resume compatibility guard runs **before** the SIMPLE skip prose (fixed in round 1).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Step 2a.5 resume compatibility guard runs **before** the SIMPLE skip prose (fixed in round 1).
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` uses boundary-qualified wording.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Cross-doc routing in `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, and `run-step3-review.sh` uses boundary-qualified wording.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Harness adds region pins for FINALIZE placement, SIMPLE entry-fence guards, routing guards, and pause/resume fixtures for legacy `.completed/step-3b` without `.completed/finalize` and legacy SIMPLE `.completed/step-2a` without `.completed/step-2a.5`.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Harness adds region pins for FINALIZE placement, SIMPLE entry-fence guards, routing guards, and pause/resume fixtures for legacy `.completed/step-3b` without `.completed/finalize` and legacy SIMPLE `.completed/step-2a` without `.completed/step-2a.5`.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Anti-halt literal `Continue to Step 4 IMMEDIATELY` preserved (`skills/design/SKILL.md:1288`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - Anti-halt literal `Continue to Step 4 IMMEDIATELY` preserved (`skills/design/SKILL.md:1288`). I did not run `make lint` or the harness scripts in this read-only review. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	important	correctness	skills/design/SKILL.md:649-697	Step 2a.2 skip allows proceeding to Step 2b when a later re-read returns SIMPLE even if the Step 2a entry fence defaulted to HARD on read failure and never wrote SIMPLE sentinels or completion markers. If read-design-classification.sh fails transiently in the entry bash block (stderr suppressed, HARD default) but succeeds when the orchestrator re-reads at 2a.2, the run skips sketches without NO_SKETCHES artifacts or .completed/step-2a / step-2a.5 markers; Step 2b and pause/resume can proceed with missing or stale synthesis files.	Require 2a.2 skip only when approach-synthesis.txt contains NO_SKETCHES_CLASSIFIED_SIMPLE or both step-2a and step-2a.5 completion markers exist; do not treat a bare re-read SIMPLE as sufficient unless entry-fence writes succeeded or are re-executed. 1	in_scope	latent	correctness	skills/design/SKILL.md:1098-1122	Gate-B-bypass branch-matrix lines say short-circuit to Step 3b or continue to Step 3b instead without naming the Step 3b completion boundary on the same line; the harness guard only catches lines mentioning both Step 3b and Step 4. An orchestrator following only the matrix could reach Step 4 without FINALIZE after the standalone Step 4 FINALIZE turn was removed.	Add completion-boundary wording to each bypass matrix bullet or a mandatory post-matrix sentence that every Step 3b arrival must run the completion boundary before Step 4. 1	in_scope	nit	correctness	skills/design/SKILL.md:782	Step 2a success-boundary prose claims to include the zero-sketch sentinel path but the HARD zero-sketches guard bypasses 2a.4 and never reaches that boundary write.	M Clarify zero-sketch path must write step-2a explicitly or remove including the zero-sketch sentinel path from the 2a.4 boundary line. 1	out_of_scope	latent	architecture	skills/design/scripts/run-step3-review.md:31	run-step3-review.md documents Step 3b routing but is excluded from the six-surface routing guard in test-design-structure.sh.	Extend assert_no_direct_step3b_step4_routes to include run-step3-review.md or add a dedicated contains pin for its routing prose. ```
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-design-structure.sh:52-80
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] assert_step2a_entry_simple_guard checks guard line precedes sentinel writes but not that writes are inside the SIMPLE branch before fi HARD-tier run could write NO_SKETCHES_CLASSIFIED_SIMPLE sentinels if writes move outside the if block while staying after the guard line Extract the Step 2a entry fence and assert sentinel and completion-marker line numbers lie strictly between the SIMPLE if and matching fi
- **Suggested revision**: Address the concern above.

### FINDING_23: `08a83a6b2` — Fold design setup into existing boundaries
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `08a83a6b2` — Fold design setup into existing boundaries
- **Suggested revision**: Address the concern above.

### FINDING_24: `07ee0c2a1` — chore(larch-logs) flush (run log only; not reviewed as a security surface)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `07ee0c2a1` — chore(larch-logs) flush (run log only; not reviewed as a security surface)
- **Suggested revision**: Address the concern above.

### FINDING_25: `e7327f1e9` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `e7327f1e9` — Address code review feedback (round 1) **Changed surfaces:** orchestration prose and bash fences in `skills/design/SKILL.md`, routing docs (`approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `sketch-launch.md`), caller docs (`design-driver.md`, `finalize-plan.md`), one stdout breadcrumb in `run-step3-review.sh`, and harness updates (`test-design-structure.sh`, `test-design-pause-resume.sh`). No changes to `design-driver.sh`, `finalize-plan.sh`, or other runtime validators. ## Security assessment This is a caller-relocation refactor: two trivial file-setup turns are folded into existing fences. From a security/trust-boundary lens:
- **Suggested revision**: Address the concern above.

### FINDING_26: **No new command injection.** New bash fences pipe a literal `ACTION=FINALIZE` into `design-driver.sh` with `"$DESIGN_TMPDIR"` quoted. `design-driver.sh` and `finalize-plan.sh` are unchanged; `larch_design_tmpdir_validate` still gates tmpdir paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new command injection.** New bash fences pipe a literal `ACTION=FINALIZE` into `design-driver.sh` with `"$DESIGN_TMPDIR"` quoted. `design-driver.sh` and `finalize-plan.sh` are unchanged; `larch_design_tmpdir_validate` still gates tmpdir paths.
- **Suggested revision**: Address the concern above.

### FINDING_27: **No new untrusted-input handling.** Issue/ballot/reviewer trust-boundary prose is untouched. The 2a.2 skip heuristic (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) operates on session-local artifacts, same trust model as before.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new untrusted-input handling.** Issue/ballot/reviewer trust-boundary prose is untouched. The 2a.2 skip heuristic (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) operates on session-local artifacts, same trust model as before.
- **Suggested revision**: Address the concern above.

### FINDING_28: **Integrity improved on failure paths.** Both the Step 3b completion boundary and the Step 4 compatibility guard now hard-halt with `exit "$_finalize_rc"` after the repair warning, rather than allowing a warning-only continue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Integrity improved on failure paths.** Both the Step 3b completion boundary and the Step 4 compatibility guard now hard-halt with `exit "$_finalize_rc"` after the repair warning, rather than allowing a warning-only continue.
- **Suggested revision**: Address the concern above.

### FINDING_29: **No secrets, auth, crypto, SSRF, deserialization, or dependency changes** in the functional diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No secrets, auth, crypto, SSRF, deserialization, or dependency changes** in the functional diff. The Step 4 guard’s `[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]` check follows the same sentinel pattern `design-driver.sh` already used for idempotent FINALIZE skips; it does not introduce a new remote trust boundary. Local tmpdir tampering (empty/symlink sentinel) could skip validation, but that threat model predates this PR and requires write access to the session directory.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/SKILL.md:697
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 2a.2 can skip to Step 2b on SIMPLE re-read alone without verifying sentinel artifacts were written. On resume@2b or any path that skips the Step 2a entry fence, classification may be SIMPLE while approach-synthesis.txt and sibling sentinels are absent; Step 2b still expects approach-synthesis.txt. Tighten 2a.2 to require NO_SKETCHES_CLASSIFIED_SIMPLE in approach-synthesis.txt, or add a Step 2b entry compatibility fence that writes SIMPLE sentinels when classification is SIMPLE and artifacts are missing; add pause/resume fixture.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/design/SKILL.md:1098-1118
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Gate-B-bypass LOOP_STATUS matrix rows route to Step 3b without naming the completion boundary. Orchestrator following matrix bullets (tally-error, panel-failed, etc.) may run Step 3b diagram branches and continue to Step 4 without FINALIZE, reproducing FM2 missing rejected-findings.md. Append completion-boundary reminder to each matrix row or add an explicit post-matrix invariant before Step 3b.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/SKILL.md:649-650
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Entry fence defaults classification read failure to HARD while 2a.2 re-read can later return SIMPLE without sentinel files. Transient run-params read failure at entry writes no SIMPLE sentinels; later 2a.2 re-read succeeds as SIMPLE and skips sketches with missing artifacts. Unify classification source and fail-closed defaults; require sentinel presence before 2a.2 skip.
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: scripts/test-design-structure.sh:288-304
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Structure harness does not pin FINALIZE repair warning text on Step 3b boundary failure. Step 3b boundary could regress to exit-only failure without operator-visible repair breadcrumb; only Step 4 compatibility failure is tested in pause-resume harness. Add grep pin for repair warning in assert_step3b_finalize_boundary for Step 3b and Step 4 regions.
- **Suggested revision**: Address the concern above.

### FINDING_34: architecture: skills/design/SKILL.md:104
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] NEVER anti-pattern #1 claims the Step 2a entry fence is the only write site for NO_SKETCHES_CLASSIFIED_SIMPLE and step-2a/2a.5 completion markers, but HARD paths still write those elsewhere. On a HARD run where both Cursor and Codex are unavailable, the orchestrator may follow NEVER #1 and skip Step 2a.3 sentinel writes and/or HARD success-boundary completion markers, leaving missing artifacts or broken pause/resume state. Scope NEVER #1 to SIMPLE-tier only (matching sketch-launch.md / collaborative-sketches.md) and explicitly preserve the HARD zero-sketches and Step 2a/2a.5 success-boundary write sites.
- **Suggested revision**: Address the concern above.

### FINDING_35: **risk-integration** `skills/design/SKILL.md:697` — Step 2a.2 allows a direct jump to Step 2b when a *re-read* of `read-design-classification.sh` returns `SIMPLE`, even if the Step 2a entry fence never wrote the no-sketch sentinel artifacts (for example, the entry fence was skipped on resume, the fence failed before the guarded branch, or classification read failed once and fell through to the `HARD` default). That breaks the new invariant that the entry fence is the sole SIMPLE sentinel write site and can leave Step 2b without `approach-synthesis.txt` / `contested-decisions.md` / `dialectic-resolutions.md`. **Suggested fix:** Gate the 2a.2 short-circuit on sentinel presence only (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`, or all three artifact files exist with expected content); if classification is `SIMPLE` but sentinels are absent, re-run the entry-fence SIMPLE write block (or fail closed) instead of proceeding to Step 2b on classification alone.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:697` — Step 2a.2 allows a direct jump to Step 2b when a *re-read* of `read-design-classification.sh` returns `SIMPLE`, even if the Step 2a entry fence never wrote the no-sketch sentinel artifacts (for example, the entry fence was skipped on resume, the fence failed before the guarded branch, or classification read failed once and fell through to the `HARD` default). That breaks the new invariant that the entry fence is the sole SIMPLE sentinel write site and can leave Step 2b without `approach-synthesis.txt` / `contested-decisions.md` / `dialectic-resolutions.md`. **Suggested fix:** Gate the 2a.2 short-circuit on sentinel presence only (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`, or all three artifact files exist with expected content); if classification is `SIMPLE` but sentinels are absent, re-run the entry-fence SIMPLE write block (or fail closed) instead of proceeding to Step 2b on classification alone.
- **Suggested revision**: Address the concern above.

### FINDING_36: **risk-integration** `skills/design/SKILL.md:794-806` — The Step 2a.5 SIMPLE resume compatibility guard repairs only `.completed/step-2a.5` when `.completed/step-2a` exists, and explicitly does not re-write SIMPLE artifacts. A legacy or corrupted paused snapshot can therefore resume at Step 2a.5 with completion markers satisfied but missing `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinels, then proceed to Step 2b. The pause/resume harness fixture at `skills/design/scripts/test-design-pause-resume.sh:232-248` exercises marker repair only and would not catch this. **Suggested fix:** Before the SIMPLE skip, require the three sentinel artifacts (or `NO_SKETCHES_CLASSIFIED_SIMPLE` in `approach-synthesis.txt`); if absent, invoke the same guarded write block as the Step 2a entry fence (fail-fast, then write completion markers), not just the missing `step-2a.5` marker.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:794-806` — The Step 2a.5 SIMPLE resume compatibility guard repairs only `.completed/step-2a.5` when `.completed/step-2a` exists, and explicitly does not re-write SIMPLE artifacts. A legacy or corrupted paused snapshot can therefore resume at Step 2a.5 with completion markers satisfied but missing `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinels, then proceed to Step 2b. The pause/resume harness fixture at `skills/design/scripts/test-design-pause-resume.sh:232-248` exercises marker repair only and would not catch this. **Suggested fix:** Before the SIMPLE skip, require the three sentinel artifacts (or `NO_SKETCHES_CLASSIFIED_SIMPLE` in `approach-synthesis.txt`); if absent, invoke the same guarded write block as the Step 2a entry fence (fail-fast, then write completion markers), not just the missing `step-2a.5` marker.
- **Suggested revision**: Address the concern above.

### FINDING_37: **risk-integration** `skills/design/SKILL.md:1098-1118` — Gate-B-bypass statuses (`tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`) still say only “short-circuit to Step 3b”, while `cap-reached` at line 1116 was updated to the full chain through the Step 3b completion boundary and Step 4. The line-scoped routing guard in `scripts/test-design-structure.sh:127-151` does not flag these lines because they omit “Step 4” on the same line, so an orchestrator can treat bypass as “enter Step 3b diagram work” and, if `.completed/step-3b` already exists from an earlier loop, skip the FINALIZE fence. Step 4’s `.completed/finalize` compatibility guard mitigates first-time misses, but this leaves a resume/re-entry hole and is inconsistent with the plan’s FM2/FM3 mitigation. **Suggested fix:** Retarget each Gate-B-bypass branch-matrix bullet (and the summary at line 1118) to the same boundary-qualified wording used for `cap-reached`, e.g. “Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4”; optionally extend the routing guard to fail “short-circuit/proceed to Step 3b” lines in the Step 3 slice unless they also name the completion boundary.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:1098-1118` — Gate-B-bypass statuses (`tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`) still say only “short-circuit to Step 3b”, while `cap-reached` at line 1116 was updated to the full chain through the Step 3b completion boundary and Step 4. The line-scoped routing guard in `scripts/test-design-structure.sh:127-151` does not flag these lines because they omit “Step 4” on the same line, so an orchestrator can treat bypass as “enter Step 3b diagram work” and, if `.completed/step-3b` already exists from an earlier loop, skip the FINALIZE fence. Step 4’s `.completed/finalize` compatibility guard mitigates first-time misses, but this leaves a resume/re-entry hole and is inconsistent with the plan’s FM2/FM3 mitigation. **Suggested fix:** Retarget each Gate-B-bypass branch-matrix bullet (and the summary at line 1118) to the same boundary-qualified wording used for `cap-reached`, e.g. “Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4”; optionally extend the routing guard to fail “short-circuit/proceed to Step 3b” lines in the Step 3 slice unless they also name the completion boundary.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] The Step 3b completion-boundary FINALIZE fence (`skills/design/SKILL.md:1290-1306`) and Step 4 compatibility guard (`skills/design/SKILL.md:1316-1326`) are correctly ordered: `step-3b` is written only after successful FINALIZE, and Step 4 re-runs FINALIZE when `.completed/finalize` is absent. Pause/resume fixtures for legacy `step-3b` without `finalize` look sound.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - The Step 3b completion-boundary FINALIZE fence (`skills/design/SKILL.md:1290-1306`) and Step 4 compatibility guard (`skills/design/SKILL.md:1316-1326`) are correctly ordered: `step-3b` is written only after successful FINALIZE, and Step 4 re-runs FINALIZE when `.completed/finalize` is absent. Pause/resume fixtures for legacy `step-3b` without `finalize` look sound.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] `design-driver.sh` idempotency via `.completed/finalize` is appropriate for Gate C re-runs; `finalize-plan.sh` still materializes missing may-be-empty artifacts, which preserves the pre-change guarantee that Step 4 can read `rejected-findings.md` on voting-skipped paths.
- **Reviewer**: dyn-state-machine-output.txt
- **Concern**: - `design-driver.sh` idempotency via `.completed/finalize` is appropriate for Gate C re-runs; `finalize-plan.sh` still materializes missing may-be-empty artifacts, which preserves the pre-change guarantee that Step 4 can read `rejected-findings.md` on voting-skipped paths.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `skills/design/SKILL.md:1098-1105` — The Step 3 post-loop branch matrix still tells the orchestrator to “short-circuit to Step 3b” for `tally-error`, `degraded-empty-collector`, `plan-validator-defects`, and `panel-failed` without naming the Step 3b completion boundary (FINALIZE + `step-3b`) before Step 4. `cap-reached` was updated at line 1116, but these sibling bypass paths were not. With FINALIZE removed from Step 4, an orchestrator that follows only the branch-matrix bullets can enter Step 3b and then continue to Step 4 without running the fence at lines 1292–1306, leaving `rejected-findings.md` / `accepted-plan-findings.md` / `oos.md` uncreated on panel-skipped paths (the failure mode the plan calls FM2). **Suggested fix:** Retarget every Gate-B-bypass bullet in the Step 3 slice (1098–1105 and the summary at 1118) to the same boundary-qualified chain used at 1116 — e.g. “short-circuit to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4” — and extend `assert_no_direct_step3b_step4_routes` or add a dedicated pin so bypass-matrix lines cannot regress without naming the boundary.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1098-1105` — The Step 3 post-loop branch matrix still tells the orchestrator to “short-circuit to Step 3b” for `tally-error`, `degraded-empty-collector`, `plan-validator-defects`, and `panel-failed` without naming the Step 3b completion boundary (FINALIZE + `step-3b`) before Step 4. `cap-reached` was updated at line 1116, but these sibling bypass paths were not. With FINALIZE removed from Step 4, an orchestrator that follows only the branch-matrix bullets can enter Step 3b and then continue to Step 4 without running the fence at lines 1292–1306, leaving `rejected-findings.md` / `accepted-plan-findings.md` / `oos.md` uncreated on panel-skipped paths (the failure mode the plan calls FM2). **Suggested fix:** Retarget every Gate-B-bypass bullet in the Step 3 slice (1098–1105 and the summary at 1118) to the same boundary-qualified chain used at 1116 — e.g. “short-circuit to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4” — and extend `assert_no_direct_step3b_step4_routes` or add a dedicated pin so bypass-matrix lines cannot regress without naming the boundary.
- **Suggested revision**: Address the concern above.

### FINDING_41: **correctness** `skills/design/SKILL.md:796-804` — The new Step 2a.5 legacy-SIMPLE compatibility fence writes `.completed/step-2a.5` with plain `mkdir` / `: >` and no `set -e` or non-zero exit on failure. If `mkdir -p "$DESIGN_TMPDIR/.completed"` fails, the subshell still exits 0 and line 806 proceeds to Step 2b, so pause-save can keep resuming at `STEP=2a.5` even though the repair marker was never written. That is a new path introduced by this branch for pre-PR paused SIMPLE sessions. **Suggested fix:** Mirror the Step 2a SIMPLE entry fail-fast pattern: wrap the marker write in `set -e` (or explicit `if ! mkdir …; then exit 1; fi`) and halt before the SIMPLE skip prose when the repair write fails.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:796-804` — The new Step 2a.5 legacy-SIMPLE compatibility fence writes `.completed/step-2a.5` with plain `mkdir` / `: >` and no `set -e` or non-zero exit on failure. If `mkdir -p "$DESIGN_TMPDIR/.completed"` fails, the subshell still exits 0 and line 806 proceeds to Step 2b, so pause-save can keep resuming at `STEP=2a.5` even though the repair marker was never written. That is a new path introduced by this branch for pre-PR paused SIMPLE sessions. **Suggested fix:** Mirror the Step 2a SIMPLE entry fail-fast pattern: wrap the marker write in `set -e` (or explicit `if ! mkdir …; then exit 1; fi`) and halt before the SIMPLE skip prose when the repair write fails.
- **Suggested revision**: Address the concern above.

### FINDING_42: **correctness** `skills/design/SKILL.md:649-650` — The Step 2a entry fence classifies tier via `read-design-classification.sh … 2>/dev/null || printf '%s\n' HARD)`. If the helper is missing, not executable, or otherwise fails before emitting stdout, stderr is discarded and the fallback silently treats the run as HARD, so a SIMPLE design skips sentinel writes and launches the full sketch path instead. The old SIMPLE sentinel fence lived behind SIMPLE-only prose and did not depend on this reader. **Suggested fix:** Do not swallow classification failures into HARD on the SIMPLE write path: run the reader without `2>/dev/null`, or on non-zero exit print a loud warning and `exit 1` (or re-read `run-params.json` with an explicit SIMPLE/HARD test) before deciding whether to write sentinels; only default to HARD when the script itself documents that default on stdout with exit 0.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:649-650` — The Step 2a entry fence classifies tier via `read-design-classification.sh … 2>/dev/null || printf '%s\n' HARD)`. If the helper is missing, not executable, or otherwise fails before emitting stdout, stderr is discarded and the fallback silently treats the run as HARD, so a SIMPLE design skips sentinel writes and launches the full sketch path instead. The old SIMPLE sentinel fence lived behind SIMPLE-only prose and did not depend on this reader. **Suggested fix:** Do not swallow classification failures into HARD on the SIMPLE write path: run the reader without `2>/dev/null`, or on non-zero exit print a loud warning and `exit 1` (or re-read `run-params.json` with an explicit SIMPLE/HARD test) before deciding whether to write sentinels; only default to HARD when the script itself documents that default on stdout with exit 0.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] **Pre-existing / not amplified:** The HARD zero-sketches degraded path (line 717) still jumps to Step 2b without writing `.completed/step-2a`, while line 782 claims the zero-sketch sentinel path writes that marker; that inconsistency predates this branch’s SIMPLE entry-fence work.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Pre-existing / not amplified:** The HARD zero-sketches degraded path (line 717) still jumps to Step 2b without writing `.completed/step-2a`, while line 782 claims the zero-sketch sentinel path writes that marker; that inconsistency predates this branch’s SIMPLE entry-fence work.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] **Harness gap:** `assert_no_direct_step3b_step4_routes` only flags lines that mention both Step 3b and Step 4, so it does not catch the incomplete bypass-matrix retarget at 1098–1105 (which mention Step 3b alone). That explains why CI can pass while FM2 prose remains partially unfixed.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Harness gap:** `assert_no_direct_step3b_step4_routes` only flags lines that mention both Step 3b and Step 4, so it does not catch the incomplete bypass-matrix retarget at 1098–1105 (which mention Step 3b alone). That explains why CI can pass while FM2 prose remains partially unfixed.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] **Otherwise sound:** The Step 3b FINALIZE fence (1295–1305) and Step 4 compatibility guard (1316–1325) correctly use `set +e` / `_finalize_rc=$?` / `set -e` / `exit "$_finalize_rc"`, write `step-3b` only after success, and gate on `.completed/finalize`. The SIMPLE entry fence orders artifact writes before completion markers under `set -e` as intended.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **Otherwise sound:** The Step 3b FINALIZE fence (1295–1305) and Step 4 compatibility guard (1316–1325) correctly use `set +e` / `_finalize_rc=$?` / `set -e` / `exit "$_finalize_rc"`, write `step-3b` only after success, and gate on `.completed/finalize`. The SIMPLE entry fence orders artifact writes before completion markers under `set -e` as intended.
- **Suggested revision**: Address the concern above.

### FINDING_46: **architecture** `skills/design/references/plan-review.md:129,183` — Both post-review exit paths still describe the zero-findings flow as “pass straight through to Step 3b, with Step 3.6 still firing first on HARD runs per `approval-gates.md`,” but they never name the Step 3b completion boundary (`ACTION=FINALIZE` + `.completed/step-3b`) before Step 4. That matters because this branch moved FINALIZE out of Step 4 item 1 into the Step 3b boundary, and `skills/design/SKILL.md` still mandates reading `plan-review.md` completely before Step 3. An orchestrator treating `plan-review.md` as the Step 3 normative source can reasonably stop routing at Step 3b and miss the new mandatory FINALIZE convergence point, especially on Gate-B-bypass paths where tally artifacts may not exist until FINALIZE runs. **Suggested fix:** Update both sentences to match `approval-gates.md:84` — e.g. “Step 3.6 → Step 3b → Step 3b completion boundary (FINALIZE + step-3b) → Step 4 → Step 4b” — and add `plan-review.md` to the line-scoped routing guard in `scripts/test-design-structure.sh`.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - **architecture** `skills/design/references/plan-review.md:129,183` — Both post-review exit paths still describe the zero-findings flow as “pass straight through to Step 3b, with Step 3.6 still firing first on HARD runs per `approval-gates.md`,” but they never name the Step 3b completion boundary (`ACTION=FINALIZE` + `.completed/step-3b`) before Step 4. That matters because this branch moved FINALIZE out of Step 4 item 1 into the Step 3b boundary, and `skills/design/SKILL.md` still mandates reading `plan-review.md` completely before Step 3. An orchestrator treating `plan-review.md` as the Step 3 normative source can reasonably stop routing at Step 3b and miss the new mandatory FINALIZE convergence point, especially on Gate-B-bypass paths where tally artifacts may not exist until FINALIZE runs. **Suggested fix:** Update both sentences to match `approval-gates.md:84` — e.g. “Step 3.6 → Step 3b → Step 3b completion boundary (FINALIZE + step-3b) → Step 4 → Step 4b” — and add `plan-review.md` to the line-scoped routing guard in `scripts/test-design-structure.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_47: **architecture** `scripts/test-design-structure.sh:879-884` — The new `assert_no_direct_step3b_step4_routes` guard only scans six surfaces (`SKILL.md` Step 3b slice, `SKILL.md` Gate-B-bypass slice, `approval-gates.md`, `run-step3-review.sh`, `flags.md`, `configuration-and-permissions.md`) and deliberately omits `plan-review.md`, even though `SKILL.md` labels that file normative for Step 3 and `docs/configuration-and-permissions.md:274` still points operators at `plan-review.md` § Multi-round loop. The branch therefore locks routing sync on the updated docs but leaves the highest-traffic Step 3 reference able to drift again without CI failure, which is exactly the class of stale-route regression this refactor is trying to prevent. **Suggested fix:** Extend `assert_no_direct_step3b_step4_routes` to include `skills/design/references/plan-review.md` (and optionally `skills/design/scripts/run-step3-review.md` for parity with its updated cap-route prose), then fix the stale lines at `plan-review.md:129,183`.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - **architecture** `scripts/test-design-structure.sh:879-884` — The new `assert_no_direct_step3b_step4_routes` guard only scans six surfaces (`SKILL.md` Step 3b slice, `SKILL.md` Gate-B-bypass slice, `approval-gates.md`, `run-step3-review.sh`, `flags.md`, `configuration-and-permissions.md`) and deliberately omits `plan-review.md`, even though `SKILL.md` labels that file normative for Step 3 and `docs/configuration-and-permissions.md:274` still points operators at `plan-review.md` § Multi-round loop. The branch therefore locks routing sync on the updated docs but leaves the highest-traffic Step 3 reference able to drift again without CI failure, which is exactly the class of stale-route regression this refactor is trying to prevent. **Suggested fix:** Extend `assert_no_direct_step3b_step4_routes` to include `skills/design/references/plan-review.md` (and optionally `skills/design/scripts/run-step3-review.md` for parity with its updated cap-route prose), then fix the stale lines at `plan-review.md:129,183`.
- **Suggested revision**: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] `skills/design/references/assessor.md:37,46-50,77` still says “Continue → Step 3b unchanged” / “continues to Step 3b” without naming the completion boundary. That predates this branch and is lower risk because those lines do not route directly to Step 4; entering Step 3b still implies executing the Step 3b region in `SKILL.md`, which ends with the completion-boundary fence.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - `skills/design/references/assessor.md:37,46-50,77` still says “Continue → Step 3b unchanged” / “continues to Step 3b” without naming the completion boundary. That predates this branch and is lower risk because those lines do not route directly to Step 4; entering Step 3b still implies executing the Step 3b region in `SKILL.md`, which ends with the completion-boundary fence.
- **Suggested revision**: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] The anti-halt step chain `3b→4→4b` in `skills/design/SKILL.md:29` remains a coarse transition list and is intentionally pinned by `scripts/test-design-structure.sh`. It is not a bare “Step 3b → Step 4” bypass line, and the Step 3b section itself now makes the completion boundary explicit before Step 4.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - The anti-halt step chain `3b→4→4b` in `skills/design/SKILL.md:29` remains a coarse transition list and is intentionally pinned by `scripts/test-design-structure.sh`. It is not a bare “Step 3b → Step 4” bypass line, and the Step 3b section itself now makes the completion boundary explicit before Step 4.
- **Suggested revision**: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] Within the six guarded surfaces, the retargeted routes in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, and `skills/design/scripts/run-step3-review.md` are aligned on boundary-qualified wording. The Step 3b completion-boundary fence and Step 4 compatibility guard in `skills/design/SKILL.md:1290-1326` match the plan’s ordering and fail-fast semantics.
- **Reviewer**: dyn-routing-sync-output.txt
- **Concern**: - Within the six guarded surfaces, the retargeted routes in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, `skills/design/references/flags.md`, `docs/configuration-and-permissions.md`, `skills/design/scripts/run-step3-review.sh`, and `skills/design/scripts/run-step3-review.md` are aligned on boundary-qualified wording. The Step 3b completion-boundary fence and Step 4 compatibility guard in `skills/design/SKILL.md:1290-1326` match the plan’s ordering and fail-fast semantics.
- **Suggested revision**: Address the concern above.

### FINDING_51: **code-quality** `scripts/test-design-structure.sh:52-79` — `assert_step2a_entry_simple_guard` only checks that the SIMPLE `if` line precedes the first artifact line and that the last artifact line precedes the first `.completed/step-2a` line; it never requires completion-marker writes to stay inside the `if`/`fi` block. A regression that moves `mkdir -p "$DESIGN_TMPDIR/.completed"` and the `step-2a` / `step-2a.5` writes after `fi` would still pass while writing those markers on HARD runs. **Suggested fix:** After extracting the entry fence, also assert every `: > "$DESIGN_TMPDIR/.completed/step-2a"` / `step-2a.5` line number is less than the closing `fi` line number (or parse the guarded block with awk and require completion writes only between the SIMPLE guard and `fi`).
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:52-79` — `assert_step2a_entry_simple_guard` only checks that the SIMPLE `if` line precedes the first artifact line and that the last artifact line precedes the first `.completed/step-2a` line; it never requires completion-marker writes to stay inside the `if`/`fi` block. A regression that moves `mkdir -p "$DESIGN_TMPDIR/.completed"` and the `step-2a` / `step-2a.5` writes after `fi` would still pass while writing those markers on HARD runs. **Suggested fix:** After extracting the entry fence, also assert every `: > "$DESIGN_TMPDIR/.completed/step-2a"` / `step-2a.5` line number is less than the closing `fi` line number (or parse the guarded block with awk and require completion writes only between the SIMPLE guard and `fi`).
- **Suggested revision**: Address the concern above.

### FINDING_52: **code-quality** `scripts/test-design-structure.sh:96-124` — `assert_step3b_finalize_boundary` uses region-wide `grep -Fq` presence checks for `exit "$_finalize_rc"` and `: > "$DESIGN_TMPDIR/.completed/step-3b"` but does not assert ordering. A fence that wrote `step-3b` before running FINALIZE, or before the non-zero exit branch, would still satisfy the harness while reintroducing FM6 (Step 4 reads before artifacts exist). **Suggested fix:** Add line-number ordering inside the Step 3b completion bash fence: `_finalize_rc=$?` / failure `exit` must precede the `step-3b` sentinel write, mirroring the SIMPLE artifact/completion ordering checks.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:96-124` — `assert_step3b_finalize_boundary` uses region-wide `grep -Fq` presence checks for `exit "$_finalize_rc"` and `: > "$DESIGN_TMPDIR/.completed/step-3b"` but does not assert ordering. A fence that wrote `step-3b` before running FINALIZE, or before the non-zero exit branch, would still satisfy the harness while reintroducing FM6 (Step 4 reads before artifacts exist). **Suggested fix:** Add line-number ordering inside the Step 3b completion bash fence: `_finalize_rc=$?` / failure `exit` must precede the `step-3b` sentinel write, mirroring the SIMPLE artifact/completion ordering checks.
- **Suggested revision**: Address the concern above.

### FINDING_53: **code-quality** `scripts/test-design-structure.sh:127-153` — The new `assert_no_direct_step3b_step4_routes` awk has no negative self-tests, unlike the existing `run_thin_fence_self_tests` / `run_gate_b_bypass_branch_sentinel_self_tests` helpers. A regex edit that stops matching `Step 3b, Step 4` or starts false-positiving on innocent prose will not be caught until someone edits `SKILL.md` and runs the full harness. **Suggested fix:** Add a `run_step3b_route_guard_self_tests` block with minimal temp files: one bare `Step 3b → Step 4` line (must fail), one boundary-qualified line (must pass), and one split across two lines if you want to document that limitation explicitly.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:127-153` — The new `assert_no_direct_step3b_step4_routes` awk has no negative self-tests, unlike the existing `run_thin_fence_self_tests` / `run_gate_b_bypass_branch_sentinel_self_tests` helpers. A regex edit that stops matching `Step 3b, Step 4` or starts false-positiving on innocent prose will not be caught until someone edits `SKILL.md` and runs the full harness. **Suggested fix:** Add a `run_step3b_route_guard_self_tests` block with minimal temp files: one bare `Step 3b → Step 4` line (must fail), one boundary-qualified line (must pass), and one split across two lines if you want to document that limitation explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_54: **code-quality** `scripts/test-design-structure.sh:140-149` — The route guard is strictly line-scoped and the verb alternation is substring-based (`go` matches inside `Go through each`, `undergo`, etc.). It also misses routes that omit the chosen verbs (`run`, `follow`, `advance`) or split `Step 3b` and `Step 4` across adjacent lines. That leaves real bypass blind spots the six-surface scan cannot catch, even though current files happen to pass. **Suggested fix:** Tighten verb matching with word boundaries (`\\<go\\>`), add the plan’s missing verb forms if needed, and either scan a paragraph window or add positive `contains` pins for the highest-risk multi-line routes (Gate-B-bypass matrix bullets in `skills/design/SKILL.md:1096-1118`).
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:140-149` — The route guard is strictly line-scoped and the verb alternation is substring-based (`go` matches inside `Go through each`, `undergo`, etc.). It also misses routes that omit the chosen verbs (`run`, `follow`, `advance`) or split `Step 3b` and `Step 4` across adjacent lines. That leaves real bypass blind spots the six-surface scan cannot catch, even though current files happen to pass. **Suggested fix:** Tighten verb matching with word boundaries (`\\<go\\>`), add the plan’s missing verb forms if needed, and either scan a paragraph window or add positive `contains` pins for the highest-risk multi-line routes (Gate-B-bypass matrix bullets in `skills/design/SKILL.md:1096-1118`).
- **Suggested revision**: Address the concern above.

### FINDING_55: **code-quality** `scripts/test-design-structure.sh:871,99,335` — Step 4 region slicing uses three different marker needles in one file: `<!-- step:4 ` (architecture-diagram pin and `assert_step3b_entry_guard_threads_repo`), `<!-- step:4 —` (FINALIZE boundary + route-guard end), and a loose `<!-- step:4 /` awk end test. All work on today’s `skills/design/SKILL.md:1308`, but the inconsistent pins make the harness brittle if the HTML comment format changes slightly. **Suggested fix:** Centralize one `STEP4_MARKER` constant (or helper) and reuse it for `sed` slices, route-guard end detection, and entry-guard awk.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:871,99,335` — Step 4 region slicing uses three different marker needles in one file: `<!-- step:4 ` (architecture-diagram pin and `assert_step3b_entry_guard_threads_repo`), `<!-- step:4 —` (FINALIZE boundary + route-guard end), and a loose `<!-- step:4 /` awk end test. All work on today’s `skills/design/SKILL.md:1308`, but the inconsistent pins make the harness brittle if the HTML comment format changes slightly. **Suggested fix:** Centralize one `STEP4_MARKER` constant (or helper) and reuse it for `sed` slices, route-guard end detection, and entry-guard awk.
- **Suggested revision**: Address the concern above.

### FINDING_56: [OUT_OF_SCOPE] `skills/design/scripts/run-step3-review.md:31` still documents cap routing (`Step 3b → Step 3b completion boundary → Step 4`) but is outside the six scanned surfaces; it is correctly worded today, yet doc drift there would not trip `assert_no_direct_step3b_step4_routes`.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - `skills/design/scripts/run-step3-review.md:31` still documents cap routing (`Step 3b → Step 3b completion boundary → Step 4`) but is outside the six scanned surfaces; it is correctly worded today, yet doc drift there would not trip `assert_no_direct_step3b_step4_routes`.
- **Suggested revision**: Address the concern above.

### FINDING_57: [OUT_OF_SCOPE] Pause/resume compatibility for legacy `.completed/step-3b` without `.completed/finalize` is exercised in `skills/design/scripts/test-design-pause-resume.sh:250-296`, which is stronger coverage than the structure harness alone provides.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - Pause/resume compatibility for legacy `.completed/step-3b` without `.completed/finalize` is exercised in `skills/design/scripts/test-design-pause-resume.sh:250-296`, which is stronger coverage than the structure harness alone provides.
- **Suggested revision**: Address the concern above.

