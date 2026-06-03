### FINDING_1: configuration-and-permissions.md still documents implement rebump path for LARCH_BUMP_FILES
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `LARCH_BUMP_FILES` prose still ties drop-bump-commit behavior to the retired Rebase + Re-bump Sub-procedure on `/implement`. Operators configure bump files expecting implement-time drop-before-rebase, but the implement hot path no longer runs that sub-procedure. Documentation should describe Phase 1 reality: dormant on the ship path; point operators to `/release` or manual `bump-version`; remove sub-procedure step-1 / rebump wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_2: linting.md misdocuments test-step-8a-changelog harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The `make test-step-8a-changelog` table row still describes old Step 8a changelog-positive harness behavior. Contributors expect manifest/fallback changelog tests; the harness now asserts absence of changelog writes. The `linting.md` row should match the repurposed negative postbump test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Postbump Step 8b rebase conflicts stall without automated conflict recovery
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Pre-PR postbump rebase conflicts in `implement-finalize.sh` emit `rebase-failed` and stall at Step 8b without `CONFLICT_FILES` or `conflict-resolution.md` handoff (exit-5 / `step8b_rebase` removed). When main advances during ship and a non-trivial file conflicts at first ship, the run exits with no automated Phase 1–4 recovery, unlike `run_rebase_rebump` on the CI-fix path which still has full recovery. This is a regression vs pre–Phase 1 exit 5 unless accepted as documented degradation. Options: align postbump conflicts with CI-fix conflict routing (e.g. keep-on-conflict + handoff mirroring `ship_pr_pre_push` without reintroducing bump/rebump), or document manual-only handling in `SKILL.md` / stall-recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: subskill-invocation.md documents obsolete Step 8+ bump verification
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The canonical mechanical-check example still documents `/bump-version` + `check-bump-version` for `/implement` Step 8+. New contributors (and orchestrators) may follow removed bump gates after `ship-pr` returns, causing stalls or confusing failures. Update the shared SSOT to Phase 1 ship-pr state-machine checks; demote the bump example to `/release`-only or replace with live checks (issue stdout, OOS checkpoint, ship-pr state parse).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: codex-manifest-schema.md still lists Step 8a CHANGELOG as implement consumer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The sync list still lists Step 8a (CHANGELOG) as a `/implement` consumer. Future schema edits may assume changelog still flows through implement Step 8a. Remove or retarget the Step 8a bullet to `/release`-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: python/rebase.py retains rebase_and_rebump name after rebump removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Function name `rebase_and_rebump` persists after rebump removal. Phase 7 Python cutover readers may assume rebump still exists in this module. Rename to `rebase_and_push` (alias if needed) in a small follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: ship-pr.sh PHASE=bump label mislabels postbump-only work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PHASE=bump` label survives though the phase only runs postbump ship path. Log grep and resume docs reference "bump" for non-bump work. Optional rename to pre-ship/postbump in a later cleanup PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] conflict-resolution.md pre-pass terminology drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: "Non-bump" / "deterministic pre-pass" wording predates Phase 1; pre-pass semantics changed but the file was only lightly touched. Pre-existing terminology drift; not a functional regression from this diff. Clarify pre-pass scope in a docs-only pass when `conflict-resolution.md` is next edited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] hook-stop-fail-close.sh header mentions post-bump-version protection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Shell header comment still mentions post-bump-version protection. Cosmetic only; hook behavior matches Phase 1. Update header to match `hook-stop-fail-close.md` on next hook touch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: SKILL.md Step 5 stall seed still sets HAS_BUMP=true
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Step 5 stall seed still writes `HAS_BUMP=true` while ship-pr state no longer defines or reads `HAS_BUMP`. Stalled pre-ship state misleads resume/debugging; harmless today because `run_bump_phase` ignores it. Remove `HAS_BUMP` from the seed list or set `HAS_BUMP=false` `BUMP_TYPE=NONE` to match postbump-state stubs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: write_postbump_checkpoint is dead code after conflict STATUS removal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `write_postbump_checkpoint` is dead code after conflict `STATUS` removal. New 8b conflicts never create `.postbump-phase`; only legacy files resume at the force-push gate. Delete the dead helper or document legacy-only checkpoint semantics in `implement-finalize.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] configuration-and-permissions.md rebump reference (outside Phase 1 diff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Same stale rebump reference as in-scope doc finding; file treated as outside the Phase 1 diff. Operator misconfiguration risk remains. Fix in a follow-up docs-only pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_13: No offline harness exercises ship-pr.sh after test-ship-pr removal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No sandbox harness executes `ship-pr.sh` after `test-ship-pr` removal; only grep-based pins in `test-implement-rebase-macro.sh`. A bug in ci-behind → `run_rebase_rebump` defer-push or `RESUME_PHASE=ship-pr-rrr-phase14` handoff could pass `make lint` while breaking CI-fix rebase in production. Add a focused offline ship-pr rebase harness with stubbed `rebase-push` / `ci-behind` / `git-force-push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Concurrency acceptance for no per-PR bump is manual-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan acceptance for concurrency (second PR merges without rebase/re-bump; no bump/CHANGELOG commits) is manual-only. Regression reintroducing per-PR bump or DIRTY hot-spot conflicts would not be caught by updated harnesses until operators hit it in parallel PRs. Add a scripted two-branch fixture or document mandatory manual repro in CI/release checklist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: run_rebase_rebump skips ship-branch-guard without documented/tested rationale
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_rebase_rebump` intentionally skips `ship-branch-guard`; no test documents the relaxation. Wrong-branch CI-fix rebase could force-push without the guard that lived in `run_bump_phase`. Add a structural test or relocate minimal branch guard to the CI rebase entrypoint if parity is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] PR bundles unrelated #3395 Codex quota changes with #3364
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: PR includes unrelated #3395 Codex quota launcher changes alongside #3364. Harder to bisect regressions and higher review noise for a subtractive versioning change. Split or clearly section the PR for reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] quota regex false-positive risk in external launcher events
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The recall-biased `quota` regex in `scripts/lib-external-launcher-common.sh:275-288` predates this branch; #3395 extends the same classifier to `${OUTPUT}.events.jsonl`. Unrelated echoed text containing `quota` could false-positive as a health/quota failure (vendor routing only). Trade-off is documented and low harm; not introduced as a new vulnerability class here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] FORKED_TARGET allows shipping on main/master (pre-existing)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `FORKED_TARGET=true` allows shipping on `main`/`master` when branch names align; pre-existing operator trust signal, unchanged by Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: run-logs.md still documents Step 8 bump batch and rebump sub-procedure
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan docs sweep updated `workflow-lifecycle` but not `run-logs.md`; the file still documents Step 8 version-bump batch and Re-bump Sub-procedure refresh. Operators and audit tooling may treat `version-bump-reasoning.md` as mandatory Step 8 output and mis-debug missing files on post–Phase 1 runs. Update `run-logs.md` for Phase 1: no ship-path bump batch; optional/release-only reasoning; pre-ship flush wording; CI refresh without rebump sub-procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
