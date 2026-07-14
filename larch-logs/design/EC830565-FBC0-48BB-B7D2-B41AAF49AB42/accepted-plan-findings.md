### FINDING_2: Baseline path-prefix mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The committed baseline uses `python/`-relative `file` values while engine findings and selectors use repo-relative paths, so naive projection will fail matching and rewrite every row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify codec mapping: serialize file as Finding.path removeprefix python/; parse baseline file back to Finding.path with python/ prefix; add round-trip and no-op regen tests.
  - From Cursor-Pragmatic: Add to the occurrence codec plan: `OccurrenceBaselineRow.path` is repo-relative (`python/<file>`) for engine filtering while JSON keeps python/-relative `file`; or pin check-mode `paths=None` and document why. Add a regression test mirroring `test_paths_outside_scope_are_excluded_even_when_tracked`.
  - From Cursor-Requirements: Specify in the occurrence codec that baseline file is Finding.path with a leading python/ stripped, and add a round-trip test from repo-relative Finding.path to baseline file and back.


### FINDING_5: Production scope must filter before source loading
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Engine discovery and source loading can process tracked files that legacy production-scope filtering would exclude, including tests, support files, non-Python paths, and symlinks; malformed or unreadable excluded files can therefore cause false failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add rule-owned pre-load discovery scope, including Python pathspecs and safe exclusion of legacy paths and symlinks, for both check and write modes. Define the compatibility treatment for the existing pylint engine client and cover scoped write discovery with an injected runner.
  - From Cursor-Pragmatic: Document check/write `paths=` and discovery behavior in the REWRITTEN rule module plan (for example: `paths=["python"]` only with repo-relative occurrence row `.path`, or `paths=None` with detector-side production scope filtering and a test that untracked `test_*.py` fixtures stay excluded). Reuse `_git_ok_runner` patterns from `test_lint_pylint_skip_file.py`.
  - From Codex-Pragmatic: Name an engine-level pre-load path filter or rule pathspec/filter contract that excludes the legacy paths and symlinks before `_load_source` and `_scan_source`, and cover it through the rule main with the injected runner.
  - From Codex-Requirements: Add rule-level pre-load source selection or pathspec filtering for `python/**/*.py` plus legacy exclusions, and test that malformed excluded files do not affect check or write modes.


### FINDING_8: Missing-baseline clean-state behavior is unspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The engine may reject an absent baseline before scanning, changing the legacy behavior where a clean scan without a baseline succeeds while live findings without a baseline fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an occurrence-codec baseline flow that defers a missing-baseline error until after scanning: return 0 for no live findings and no baseline, retain exit 2 for live findings without one, and test both cases.


### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:964-976
- **Concern**: [SCOPE-REDUCTION] Write-mode discovery is wider than legacy python/-only scope. Scenario: G-Enf-2 / acceptance require byte-identical regen of python/markdown-heading-fence-state-baseline.json. Legacy _collect_all only walks root/python via iter_source_files. run_rule forbids paths on --write, so paths=None makes _discover_tracked_paths enumerate every tracked file (skills/*.py, scripts/*.py, etc.). Syntax policy raise and detect then run on out-of-scope .py files; regen can exit 2 or emit rows legacy never saw.
- **Proposed resolution**: Add rule-owned discovery pathspecs (default python) applied inside _scan_findings even when write_baseline=true and paths is None; pin the thin main adapter to that contract and add a test that tracked scripts/*.py or skills/*.py does not affect check/write.


