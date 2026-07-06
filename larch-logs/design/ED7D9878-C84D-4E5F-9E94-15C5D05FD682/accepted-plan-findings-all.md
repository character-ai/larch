### FINDING_1: Invariant violations routed to ci-fix need a separate repair contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Ship Gate Risk, Codex-dyn-Ship Gate Risk
- **Severity**: major
- **Concern**: The `architectural-invariants-violation` handoff is routed through `ci-fix`, but the referenced procedure still depends on `FAILED_RUN_ID` and bails on pre-PR invariant handoffs, so autonomous repair never starts and the Step 8 relaunch path stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add firm updates to `ship-pr-ci-fix.md` and `ship-pr-exit-matrix.md` (and matching `conflict-resolution.md` no-invalidate prose) defining violation repair from `DETAIL`/`DETAIL_FILE` and materialized invariant diff when `NEEDS_USER_REASON=architectural-invariants-violation`, or add a dedicated `NEXT_ACTION` branch in `skills/implement/SKILL.md`, `dispatch_ship.py`, and tests instead of overloading `ci-fix`
  - From Codex-Arch: Add `skills/implement/references/ship-pr-ci-fix.md` to the plan with an invariant-violation branch: when `NEEDS_USER_REASON=architectural-invariants-violation`, require `DETAIL` or `DETAIL_FILE`, skip CI run-log capture, use invariant-specific attempt tracking, repair from the violation detail, then run checks, commit, refresh, push, and relaunch Step 8
  - From Cursor-Innovation: Add `skills/implement/references/ship-pr-ci-fix.md` to the plan (and harness pins): when `NEEDS_USER_REASON=architectural-invariants-violation`, branch before CI log capture—read `DETAIL`/`DETAIL_FILE` and the durable invariant note, fix violating code, run checks/commit/push, then relaunch Step 8 for reassessment. Keep the existing CI-log path for real CI failures only.
  - From Codex-Innovation: Add a firm update for ship-pr-ci-fix.md, or a separate invariant-fix route, that consumes architectural-invariants-violation detail without FAILED_RUN_ID, repairs the violation, runs checks, commits, pushes, clears stale handoff, and relaunches Step 8
  - From Cursor-Pragmatic: Extend ship-pr-ci-fix.md (or a sibling reference loaded when NEEDS_USER_REASON=architectural-invariants-violation) to repair from architectural-invariant-note.md / DETAIL_FILE and materialized diff without FAILED_RUN_ID; update implement SKILL.md ci-fix entry to load it; relaunch step-8 expecting invariants-assessment before guidelines-assessment.
  - From Codex-Pragmatic: Add a `NEEDS_USER_REASON=architectural-invariants-violation` branch that uses `DETAIL` or `DETAIL_FILE` as the repair input, uses a stable non-CI attempt key, skips `gh run-logs`, then runs checks, commits, refreshes logs, pushes, clears handoff, and relaunches Step 8
  - From Cursor-Requirements: Add a dedicated invariant-violation remediation reference (or a `NEEDS_USER_REASON=architectural-invariants-violation` branch in `skills/implement/SKILL.md` and `ship-pr-exit-matrix.md`) that reads the violation note/detail file, applies the smallest code fix, runs checks, commits, pushes, and relaunches Step 8. Keep CI-log capture only for true CI failures.
  - From Codex-Requirements: Update the plan to modify ship-pr-ci-fix.md and its harness so NEEDS_USER_REASON=architectural-invariants-violation uses DETAIL or DETAIL_FILE as the repair input, skips CI log capture when no FAILED_RUN_ID exists, and still runs the same guarded edit/check/commit/relaunch flow
  - From Cursor-dyn-Ship Gate Risk: Add `### UPDATED: skills/implement/references/ship-pr-ci-fix.md` (and extend `skills/implement/scripts/test-architectural-guidelines-step.sh`): when `NEEDS_USER_REASON=architectural-invariants-violation`, branch before the CI-log path; read `DETAIL`/`DETAIL_FILE` and `$IMPLEMENT_TMPDIR/architectural-invariant-note.md`; repair code against listed `I-*` violations; use a bounded violation-fix counter/sentinel; relaunch `step-8-ship.sh` without `AskUserQuestion`
  - From Codex-dyn-Ship Gate Risk: Add a firm update to skills/implement/references/ship-pr-ci-fix.md, plus its harness coverage, for NEEDS_USER_REASON=architectural-invariants-violation: use DETAIL or DETAIL_FILE as the repair input, skip gh run-log capture, use a deterministic invariant repair attempt key or existing fix counter, run checks, commit, push, clear stale handoff, and relaunch Step 8. Keep the current FAILED_RUN_ID path unchanged for real CI failures.


### FINDING_2: Existing PR refresh must compare invariant sections too
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Existing PR reuse still decides refreshes from the guidelines section alone, so invariant-only body changes can leave a stale or missing invariant section in the remote PR body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/git/pr.py` to compare `architectural_invariants_section()` alongside guidelines, and extend `python/tests/git/test_pr_body.py` (or PR ensure coverage) for invariant-only body changes
  - From Codex-Arch: Add `python/larch/git/pr.py` to the plan and update the existing-PR refresh predicate to also compare `architectural_invariants_section(remote_body)` with `architectural_invariants_section(linked)`; add an ensure-pr test for invariant-only section changes
  - From Codex-Innovation: Add `python/larch/git/pr.py` to the plan and include invariant section comparison, using the new pr_body parser sibling, before deciding whether to update an existing PR body
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/git/pr.py to compare architectural_invariants_section alongside guidelines; add python/tests/git/test_pr.py coverage for invariant-only body changes.
  - From Codex-Pragmatic: Add python/larch/git/pr.py to the plan, compare architectural_invariants_section(remote_body) against the newly linked body alongside guidelines_changed, and add a focused existing-PR test
  - From Codex-Requirements: Add python/larch/git/pr.py to the plan, compare architectural_invariants_section(remote_body) against the newly linked body alongside guidelines_changed, and add a focused existing-PR test


### FINDING_3: Rebase refresh still reruns only the guidelines gate
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship Gate Risk
- **Severity**: major
- **Concern**: The post-rebase refresh helper rematerializes only guidelines before recomposing the PR body, so open-PR rebases can leave stale or missing invariant assessment even when the guidelines refresh succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Generalize `_refresh_guidelines_gate_after_rebase` to run the invariant gate first (mirror pre-PR compose), pass both notes through `_compose_pr_body_for_pr_create`, and add `python/tests/implement/test_ship.py` coverage
  - From Cursor-Innovation: Generalize the refresh helper (or add a parallel invariant refresh) so merge-loop rebase paths run invariant compose gating before guidelines, return `architectural-invariants-assessment` / `architectural-invariants-violation` when needed, and pass both notes into `compose_pr_body`.
  - From Cursor-Pragmatic: Generalize the helper (or chain invariant gate first) so rebases rematerialize/reassess invariants before guidelines and pass both notes into _compose_pr_body_for_pr_create; cover in python/tests/implement/test_ship.py.
  - From Cursor-Requirements: Generalize the refresh helper to run invariant compose gating before guidelines (same ordering as initial compose), pass both notes into `_compose_pr_body_for_pr_create`, and extend `test_run_ship_merge_loop_rebase_refreshes_guidelines_gate` (or add a sibling test) for invariant parity.
  - From Cursor-dyn-Ship Gate Risk: In `ship.py`, generalize the refresh helper to run invariant-first compose gates (mirroring pre-PR compose), pass `architectural_invariants_note` plus guidelines into `compose_pr_body`, and return `architectural-invariants-assessment` / `architectural-invariants-violation` when reassessment or remediation is required


### FINDING_5: Invariant-first compose state and resume handling need explicit phase wiring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship Gate Risk
- **Severity**: major
- **Concern**: The shared pre-PR compose path still labels the pause as guidelines work before any invariant gate runs, so a mid-assessment resume can misroute through the guidelines branch and skip invariant handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify `ship.py` writes `phase=invariants-assessment` before invariant materialization/gate and transitions to `guidelines-assessment` only after invariant clean or absent/invalid handling
  - From Cursor-Innovation: Write `phase="invariants-assessment"` before the invariant gate, then advance to `guidelines-assessment` only after invariant clean/absent handling; extend `ship_resume.py` and tests accordingly.
  - From Cursor-Pragmatic: In ship.py pre-PR compose, write phase=invariants-assessment before invariant materialization/assessment pause, then phase=guidelines-assessment only after invariant clean; mirror in tests/implement/test_ship.py and test_implement_dispatch.py handoff expectations.
  - From Cursor-Requirements: The plan updates `ship_resume.py` for `invariants-assessment` but should explicitly require `ship.py` to set `PHASE=invariants-assessment` before invariant `NEEDS_USER_INPUT`, keep `guidelines-assessment` only for guideline assessment, and add a resume test that proves mid-invariant-assessment resumes to `pre-pr-compose`.
  - From Cursor-dyn-Ship Gate Risk: Set `phase=invariants-assessment` until the invariant gate passes clean/absent/invalid, then switch to `guidelines-assessment` before the guideline gate; keep both phases mapped to `pre-pr-compose` resume in `ship_resume.py`


### FINDING_7: Gate C invariant remediation needs durable attempt storage
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The Gate C invariant rewrite counter is not persisted, so pause/resume or repeated entry can reset the attempt count and allow the remediation loop to run unbounded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Persist a bounded counter under $DESIGN_TMPDIR (e.g. architectural-invariant-gatec-remediation.count) with read/write in approval-gates.md and a harness assertion.


### FINDING_1: Invariant audit-runs parity is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The invariant audit surface is only half-wired: design dispatch still needs an `invariant-assessment` registry entry, and implement dispatch still needs an `invariant-ship-outcome` sibling with version/cutover gating, so `/audit-runs` can miss malformed invariant artifacts on either surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an `invariant-assessment` row to `scans-design.tsv` (mirror `guideline-assessment`), register the handler name in `_NAMED_RUN_SCAN_HANDLERS`, classify `clean` vs `violation` using `CLEAN_INVARIANT_PRESENTATION_NOTE` (not guideline deviation logic), and pin the row in `python/tests/issue/test_audit_runs.py`.
  - From Cursor-Arch: Add `_invariant_ship_outcome_scan_obj` (reuse cutover gating + `validate_invariant_ship_outcome_record`), register `invariant-ship-outcome` in `_NAMED_RUN_SCAN_HANDLERS`, add a `scans-implement.tsv` row, and extend `python/tests/issue/test_audit_runs.py` with missing/cutover/valid/malformed cases mirroring the guideline ship-outcome tests.
  - From Cursor-Innovation: Add an invariant-assessment row to scans-design.tsv, register the handler in _NAMED_RUN_SCAN_HANDLERS, and extend test_audit_runs.py with a scans-design.tsv dispatch fixture mirroring guideline-assessment
  - From Cursor-Innovation: Add _invariant_ship_outcome_scan_obj with validate_invariant_ship_outcome_record, register invariant-ship-outcome in _NAMED_RUN_SCAN_HANDLERS and scans-implement.tsv, mirror version cutover handling, extend compute_counters_main, and add test_audit_runs.py coverage parallel to guideline-ship-outcome
  - From Cursor-Pragmatic: Add _invariant_ship_outcome_scan_obj using validate_invariant_ship_outcome_record, register invariant-ship-outcome in the scan map, mirror _at_or_above_guideline_outcome_cutover with INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION from config.py, extend summary delta keys, and add python/tests/issue/test_audit_runs.py parity tests
  - From Cursor-Requirements: Add `_invariant_ship_outcome_scan_obj` mirroring `_guideline_ship_outcome_scan_obj` (Step 8 reachability, version cutover via `INVARIANT_SHIP_OUTCOME_MIN_LARCH_VERSION`, `validate_invariant_ship_outcome_record`); register `invariant-ship-outcome` in `scans-implement.tsv` and `invariant-assessment` in `scans-design.tsv`; extend `compute_counters` with invariant outcome KVs; add `test_audit_runs.py` registry-dispatch and ship-outcome parity tests. List the two scans TSV files as firm plan updates.


### FINDING_2: Invariant assessment scan must distinguish violations
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: A copied guideline classifier would mark non-clean invariant assessments as `deviation`, but the invariant path is supposed to surface blocking `violation` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When implementing the invariant assessment scan, branch on invariant clean note equality and emit `assessment_kind` of `clean` or `violation`; add a violation-fixture test in `test_audit_runs.py`.


### FINDING_3: Blank invariant files should stay no-op
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Present-but-empty invariant files are still being routed to Step 8 assessment, so the compose gate can block even when there is nothing to assess.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make invariant compose and presentation checks require result.content.strip() before emitting INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED or NEEDS_USER_REASON=architectural-invariants-assessment; treat present-empty invariants as no parsed entries with a clean/no-assessment outcome and continue to guidelines.


### FINDING_4: Invariant ci-fix branch needs an untrusted-data boundary
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The repair branch is reading repo-local invariant detail as if it were instructions, instead of explicitly treating it as untrusted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In the new architectural-invariants-violation branch, label DETAIL, DETAIL_FILE, and the invariant note as untrusted evidence; instruct the fixer to use only the cited I-* ids and violation rationale, and to ignore instructions inside those artifacts that conflict with AGENTS.md, skills, guards, or the plan.


### FINDING_5: Invariant ci-fix branch must short-circuit before FAILED_RUN_ID
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The invariant-violation repair branch will still never run for pre-PR failures if the procedure bails at step 1b whenever `FAILED_RUN_ID` is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Branch on NEEDS_USER_REASON=architectural-invariants-violation before step 1b, skip FAILED_RUN_ID and gh run-logs, repair from DETAIL/DETAIL_FILE and architectural-invariant-note.md, then relaunch Step 8; pin this ordering in test-architectural-guidelines-step.sh
  - From Cursor-Requirements: Make `NEEDS_USER_REASON=architectural-invariants-violation` the first branch in the procedure, before step 1b, and pin that ordering in the Step 8 harness.


### FINDING_6: Invariant outline remediation needs a durable counter
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The outline-side invariant remediation loop has no durable counter, so pause/resume can reset retries and repeat the same rewrite loop indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Persist an outline remediation counter under $DESIGN_TMPDIR (for example architectural-invariant-outline-remediation.count), read/increment it on each outline rewrite, and hard-stop after the same bound used at Gate C
  - From Cursor-Pragmatic: Mirror Gate C: persist $DESIGN_TMPDIR/architectural-invariant-outline-remediation.count, read on Step 1d.7 invariant entry, increment per remediation attempt, hard-stop after the bound, and pin the contract in scripts/test-design-structure.sh
  - From Cursor-Requirements: Persist outline remediation under `$DESIGN_TMPDIR` (for example `architectural-invariant-outline-remediation.count`), read and increment on each remediation attempt, hard-stop after the bound, and pin the contract in `scripts/test-design-structure.sh`.


### FINDING_7: New invariant wrapper needs a parent-skill reachability pin
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The new sibling doc under `skills/implement/scripts` may be orphaned from its parent skill surface, which can fail linting or hide it from agents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the new md path to the Referenced implement script files header in skills/implement/SKILL.md, or add a justified agent-lint.toml exclusion if it must stay off the runtime prompt surface.


### FINDING_8: Skill-closure baseline is missing
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Ratcheted skill prompts can exceed the closure baseline, which will trip lint-skill-closure-growth in CI even if the code changes are otherwise correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add `### UPDATED: python/skill-closure-baseline.json` and regenerate it with `python3 python/cli.py lint skill-closure-growth --write` when the changed skill closure grows.


### FINDING_9: `--skip-approve` needs an invariant-violation carve-out
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Under `--skip-approve`, the design outline can still write `.outline-approved` before invariant violations are remediated, allowing Step 2b to proceed too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Mirror Gate C: run invariant `present-note` and assessment before guidelines; under `--skip-approve`, do not write `.outline-approved` until invariant clean or absent/invalid handling succeeds; on residual violations, enter the remediation loop instead of auto-approve.

