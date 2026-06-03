### FINDING_1: configuration-and-permissions.md still documents implement rebump path for LARCH_BUMP_FILES
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `LARCH_BUMP_FILES` prose still ties drop-bump-commit behavior to the retired Rebase + Re-bump Sub-procedure on `/implement`. Operators configure bump files expecting implement-time drop-before-rebase, but the implement hot path no longer runs that sub-procedure. Documentation should describe Phase 1 reality: dormant on the ship path; point operators to `/release` or manual `bump-version`; remove sub-procedure step-1 / rebump wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.


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


### FINDING_13: No offline harness exercises ship-pr.sh after test-ship-pr removal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No sandbox harness executes `ship-pr.sh` after `test-ship-pr` removal; only grep-based pins in `test-implement-rebase-macro.sh`. A bug in ci-behind → `run_rebase_rebump` defer-push or `RESUME_PHASE=ship-pr-rrr-phase14` handoff could pass `make lint` while breaking CI-fix rebase in production. Add a focused offline ship-pr rebase harness with stubbed `rebase-push` / `ci-behind` / `git-force-push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: run-logs.md still documents Step 8 bump batch and rebump sub-procedure
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan docs sweep updated `workflow-lifecycle` but not `run-logs.md`; the file still documents Step 8 version-bump batch and Re-bump Sub-procedure refresh. Operators and audit tooling may treat `version-bump-reasoning.md` as mandatory Step 8 output and mis-debug missing files on post–Phase 1 runs. Update `run-logs.md` for Phase 1: no ship-path bump batch; optional/release-only reasoning; pre-ship flush wording; CI refresh without rebump sub-procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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


