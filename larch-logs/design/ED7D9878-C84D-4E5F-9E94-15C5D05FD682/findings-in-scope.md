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
