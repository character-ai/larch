### FINDING_1: Runtime SUSPECT incorrectly counts as verified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Runtime failures downgraded to `SUSPECT` may still enter verified-issue accounting, snapshots, and newly-verified deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend verified-issue accounting explicitly: runtime SUSPECT (and any other non-certifying runtime outcome) must be excluded from _verified_issue, snapshot verified_issues, and confirmed-fixed counts. Add a focused test that a runtime failure keeps the issue out of verified accounting.
  - From Cursor-Innovation: Extend _verified_issue (or runtime overlay) so runtime SUSPECT is not verified; bump VERIFIED_PREDICATE_VERSION if snapshot semantics change; add report test for verified_issues after runtime downgrade
  - From Cursor-Pragmatic: Define verified accounting explicitly: runtime SUSPECT (and any runtime-downgraded row) stays non-verified; update _verified_issue or a runtime-aware wrapper and add a regression in test_analyze_bugs_runtime.py
  - From Cursor-Requirements: Extend the plan to tighten `_verified_issue` (and snapshot accounting) so runtime `SUSPECT` and other non-certified verdicts are excluded; add a regression test in `test_analyze_bugs_runtime.py`


### FINDING_2: Runtime pytest can dirty the repository
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Pytest cache output can violate the skill’s clean-tree preflight on subsequent runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin pytest argv in the plan to disable on-repo cache writes (for example -p no:cacheprovider and/or --basetemp under $RUN_DIR). Test the exact argv in test_analyze_bugs_runtime.py and document the constraint in SKILL.md.


### FINDING_3: Runtime budget is not forwarded
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: A parsed `--runtime-max` value other than the CLI default may not reach the runtime subcommand.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an explicit runtime invocation with `--runtime-max "$RUNTIME_MAX"` and retain the parsed value through Stage 3.


### FINDING_4: Empty discovered-test lists may run the full suite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Invoking pytest without discovered paths can collect the full suite, violating the runtime budget and per-fix execution contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Plan requires one pytest invocation per selected fix but does not skip fixes with zero AM paths under python/tests/; python3 -m pytest with no paths after -- can collect the full suite and destroy the runtime budget contract Skip pytest when the validated discovered-test list is empty; record tests as absent-only; promote to RUNTIME only from executed checks that actually ran


### FINDING_5: Deep truncation can clobber runtime SUSPECT
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `DEEP_TRUNCATED` handling may overwrite runtime failure verdicts and discard bounded runtime evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Apply runtime overlay after the truncation block, or preserve runtime SUSPECT verdict and evidence when truncation applies; document precedence in _final_verdict_with_tier integration


### FINDING_6: HARNESS_MAP seed rows are underspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Naming harness authorities without concrete path-prefix-to-target mappings leaves harness execution ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Required design item 2 needs prefix-to-make-target rows; naming three authorities without concrete prefixes leaves harness execution undefined until implementer guesses Seed explicit prefix-to-target rows (e.g. skills/implement/ to test-architectural-guidelines-step, scripts/ and skills/ bash surfaces to test-lint-bash32, anti-halt skill paths to test-anti-halt) in the plan or a frozen fixture table the tests import
  - From Cursor-Pragmatic: Seed HARNESS_MAP with explicit entries (for example skills/implement/ to test-architectural-guidelines-step, scripts/ and skills/*/scripts/ to test-lint-bash32, skills/implement/ to test-implement-anti-halt) and lock them in test_analyze_bugs_runtime.py
  - From Cursor-Requirements: Add an explicit seed table (e.g. `skills/implement/` -> `test-architectural-guidelines-step`, `scripts/` -> `test-lint-bash32`, anti-halt surfaces -> `test-implement-anti-halt`) and a test asserting those production entries


### FINDING_8: Orchestration zones and labels are unspecified
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan does not define orchestration-zone prefixes or a shared method for deriving zone labels and coverage-gap annotations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit ORCHESTRATION_ZONE_PREFIXES constant (skills/, scripts/, hooks/, agents/, python/larch/implement/, python/larch/design/, etc.) and a single zone-label helper reused by annotations and the coverage-gap section; test exact annotation text
  - From Cursor-Requirements: Seed prefixes aligned to the issue failure domain (`skills/`, `hooks/`, `python/larch/implement`, `scripts/`) and test that a touched unmapped prefix yields the exact `UNVERIFIED_RUNTIME: no harness covers <zone>` string


### FINDING_16: Runtime budget should be keyed by unique fix SHA
- **Reviewer(s)**: Codex-dyn-Runtime Evidence Integrity
- **Severity**: minor
- **Concern**: Budgeting issue bundles instead of distinct fix commits can consume multiple slots for one SHA or inconsistently verify issues sharing a commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Runtime Evidence Integrity: Run and budget unique resolved SHAs, then fan the shared result out to every matching manifest issue/cache-key row; add a duplicate-SHA budget test


### FINDING_17:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:2773-2786
- **Concern**: [SCOPE-REDUCTION] Runtime stage must not follow an initial analyze-bugs report. Scenario: render_report is not read-only: it appends analytics hydrated_records to ledger.jsonl, writes run-state.json, report.md, and sweep-state.json. The plan runs Stage 3 report, then runtime, then report again, so the first pass can persist wrong verified_issues and duplicate ledger hydration before runtime evidence exists.
- **Proposed resolution**: Move the runtime stage to immediately before the single analyze-bugs report invocation (after ledger/deep, before Stage 3). Update SKILL.md to call analyze-bugs runtime once, then report once; do not print or persist an interim report.


### FINDING_1: RUNTIME promotion can certify non-fixed verdicts
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: RUNTIME promotion and verified accounting do not pin a certifiable verdict set. A passing pytest or mapped harness could assign `RUNTIME` to `NOT_FIXED`, `REGRESSED`, `INCOMPLETE`, or `UNVERIFIABLE`, causing failed fixes to appear verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin promotion to the same fixed-family verdicts used elsewhere (CONFIRMED_FIXED, FIXED_CLEAR, FIXED_LIKELY). Absent or non-qualifying static verdicts keep their tier; runtime failure still downgrades to SUSPECT/RUNTIME.
  - From Cursor-Pragmatic: Pin one shared certifiable verdict set (at least `{FIXED_CLEAR, FIXED_LIKELY, CONFIRMED_FIXED}`) for both RUNTIME tier promotion and runtime-aware `_verified_issue`; add a negative test that passing runtime on `NOT_FIXED` does not promote or verify.


### FINDING_4: Anti-halt harness mapping uses the wrong prefix
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Mapping `test-implement-anti-halt` to `skills/implement/` misses fixes that only touch `scripts/test-implement-anti-halt.sh`, so those changes resolve to the wrong harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit `scripts/test-implement-anti-halt.sh` (or `scripts/test-implement-anti-halt`) → `test-implement-anti-halt` seed row, or otherwise ensure scripts-only anti-halt edits resolve that make target; extend harness-map tests for this path.


