### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `sorted_changed_files` UTF-8 byte sort vs bash `LC_ALL=C`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `sorted_changed_files` uses UTF-8 byte sort, not `LC_ALL=C` sort used by `drop-bump-commit.sh` guard 4. Custom `LARCH_BUMP_FILES` paths with non-ASCII characters can sort differently; `drop_bump_commit` guard 4 may disagree with bash on whether to drop. Use locale-aware C-sort parity or restrict documented bump file paths to ASCII.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: `git.add` / `git.commit` lack direct StubRunner argv tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `git.add` and `git.commit` lack direct StubRunner argv tests per plan. Argv regression in commit/`only=` path can break bump/changelog without failing `test_git`. Add minimal `test_git` cases for `add`, `commit -m`, and `only` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Harness path loaded but `test-classify-bump.sh` not run
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness path is loaded but `test-classify-bump.sh` is never run. Misleading signal that the offline harness backs pytest parametrization. Run the harness, remove the unused path, or implement fixtures inline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `implement_tmpdir` sentinel touch not confined to session tmp
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `implement_tmpdir` sentinel touch is not confined to a trusted session directory. At Phase 7, poisoned or mis-set `IMPLEMENT_TMPDIR` can create `.bump-version-armed` outside the intended session tmp tree. Resolve `implement_tmpdir` and reject paths outside the session tmp root before touch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Error/stall strings bypass `_redact_outbound`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ShipError`/stalled messages bypass `redact.py` for git paths and branch names. Uncaught errors or stall logs in CI/run logs may emit sensitive branch names or path fragments. Route all outbound error/stall strings through `_redact_outbound` before raise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate `_redact_outbound` across Phase 2 modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate `_redact_outbound` in `python/changelog.py` and `python/version_bump.py`. Redaction policy changes require two edits; risk of inconsistent error strings. Prefer a single helper in `redact.py` imported by both modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `commit_changelog` lacks rollback on git failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `commit_changelog` writes the file then fails without rollback on `git add`/`commit` errors. Failed commit leaves dirty CHANGELOG; retry may confuse the Phase 7 driver. Restore from HEAD on failure or document caller reset contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: `apply_bump` `rev_parse` failure after successful commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `apply_bump` uses `rev_parse` after commit; `ShipError` escapes on rev-parse failure. Bump commit may have landed but caller gets an exception instead of `ApplyResult`. Use `try_rev_parse`; return `applied=True` with empty SHA or `applied=False` with error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: No stderr logging on `apply_bump` origin/main race retries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No stderr logging on `apply_bump` `origin/main` race retries. Operators lack retry visibility during version races. Mirror `apply-bump.sh` `larch_err` retry lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Missing bash parity for successful plugin.json-only bump drop
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `drop-bump-commit.sh` lacks bash parity for successful default plugin.json-only drop. Guard-4 or drop mechanics could drift on the common rebase+re-bump path. Add twin-repo parity test for successful plugin.json-only bump drop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated test runner doubles
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated `ProcRunner` and `StubRunner` test doubles in `test_version_bump.py` and `test_changelog.py`. Runner behavior changes need parallel edits in two large test files. Extract a shared fixtures module imported by both.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Oversized single `changelog.py` module
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Single very large changelog module (MD+RST+git). Harder review and higher risk of subtle RST vs MD regressions as Phase 3+ adds behavior. Defer split until needed; plan a facade plus format-specific modules before Phase 7 cutover if growth continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Nested closures in `apply_bump` retry loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply_bump` uses nested closures for backup/rollback inside the retry loop. Same-version-race fixes are harder to reason about and unit-test in isolation. Lift helpers to module-level functions with explicit parameters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

