### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Monolithic `python/checks.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: A single ~1544-line module owns capture parsing, dispatch, git commit, and loop escalation. Phase 7+ fixes require navigating one file; regressions in unrelated areas become more likely. Split into focused modules or add an extraction milestone before cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No `run_checks_phase` happy-path integration without monkeypatching sub-calls
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No `run_checks_phase` happy-path integration without monkeypatching `run_relevant_checks` / `run_lint_fix`; wiring bugs (site split, tmpdir guard ordering) could slip past loop-only unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one StubRunner-backed fail→fix→pass `run_checks_phase` test without monkeypatching `run_relevant_checks`/`run_lint_fix`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: No umask 077 / chmod on raw capture log
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: No `umask 077` or post-write chmod on raw capture log (redacted log chmods only). Under a loose umask, pre-redaction failure logs in shared `/tmp` or cache sessions may be readable by other local users.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Match `run-relevant-checks-captured.sh`: umask 077 around write; chmod 600 raw log; fail closed on chmod error.
  - From cursor-specialist-plan-fidelity-output.txt: Wrap allocation/redaction with `os.umask(0o077)` like `run-relevant-checks-captured.sh`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: `mkdtemp` `run_dir` per lint-fix dispatch never removed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `mkdtemp` `run_dir` per lint-fix dispatch is never removed; long `/implement` runs with many fix attempts can fill session tmpdir with codex/cursor artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: `rmtree` in `finally` after dispatch completes or gate retention behind debug env.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Dispatch-first loop uses `is_file()` without symlink-safe re-resolve
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Dispatch-first loop checks `is_file()` without symlink-safe re-resolve; race in session dir could redirect fixer input after path validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Re-call `_resolve_checks_log_path` each iteration before `fixer(log_path)`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `run_check_fix_loop` skips tmpdir confinement when `allowed_tmpdir` is unset
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On the check-first path, `run_check_fix_loop` skips log-path confinement when `allowed_tmpdir` is `None`. Direct API misuse (or crafted `ChecksResult` paths) could pass fixer logs outside the session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require `allowed_tmpdir` for any fixer invocation.
  - From cursor-specialist-correctness-output.txt: Require `allowed_tmpdir` for any iteration that invokes fixer, or always resolve logs with `_resolve_checks_log_path`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated test patterns in `python/test_checks.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Large duplicated `StubRunner` and closure patterns across ~50 tests; each new parity case copies long scripted response lists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Shared pytest fixtures and table-driven loop transition tests.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Mutable `LoopResult` vs frozen result dataclasses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `LoopResult` is mutable while other Phase 4 result dataclasses are frozen—inconsistent immutability conventions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Freeze `LoopResult` or document intentional mutation.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

