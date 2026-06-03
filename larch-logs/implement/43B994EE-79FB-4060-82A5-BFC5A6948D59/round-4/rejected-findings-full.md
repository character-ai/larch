### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: release-already-cut guard too narrow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `release-already-cut` (167–168) matches only exact `Release vX.Y.Z` commit subjects. Non-standard squash titles can skip the guard while `origin/main` `plugin.json` is already ahead, allowing duplicate cut proposals; should also consider version on `origin/main` vs proposed `NEW_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add version-based or PR-metadata guard.
  - From cursor-specialist-edge-cases-output.txt: Also fail when origin/main plugin.json version is already >= proposed NEW_VERSION.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: LLM release-note composition prompt-only
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: SKILL Step 3 treats untrusted PR titles in prose but lacks mechanical enforcement beyond operator discipline; malicious PR titles can manipulate preview or confirmed public notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Enforce injection envelope; show raw titles in Step 4 preview; optional length caps.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Test env vars can override production paths in release-finish
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `release-finish.sh` test env vars can override origin repo and promote script in any shell; poisoned env in shared CI/operator shell could weaken repo coupling or run an arbitrary promote helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict overrides to test mode or document never export in production shells.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: Tag push stderr discarded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `release-finish.sh` (283–291) discards push stderr; auth/network failures surface only as generic tag push failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface push stderr in the ERROR line.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: No handling for existing release/v* branch on retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Partial Step 5 can leave `release/v*`. A second `/release` run fails at `git checkout -b` with no documented cleanup/reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document branch cleanup or reuse existing release branch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: Live tag push and gh release only partially fixture-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Per plan, live `git push` tag and `gh release create/edit` are only partially covered; `gh` flag/API drift could break release cut without automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: PR test-plan checklist or future gated integration smoke.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: Baseline docs/API mismatch (gh api vs gh release list)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Implementation uses `gh api /releases` + `is_latest` instead of plan-specified `gh release list --json tagName,isLatest`; future CLI/API differences could diverge from documented operator expectations (related to FINDING_3).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Align implementation with gh release list or update plan and release-prepare.md to name the REST API as canonical.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated `--bump` NEW_VERSION math vs classify-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` (247–258) recomputes `NEW_VERSION` for `--bump` override separately from `classify-bump.sh` / `apply-bump.sh`. Future bump-rule changes in one path only can break the operator override path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend classify-bump with forced bump type or shared lib-semver helper


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `--bump` override can emit non-canonical versions (leading zeros)
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `--bump` override (253–257) uses `10#` arithmetic for increments but concatenates raw `ver_maj` / `ver_min` from `IFS='.' read` without normalizing components. Versions matching `[0-9]+\.[0-9]+\.[0-9]+$` with leading-zero segments (e.g. `01.2.3`) can produce non-canonical `NEW_VERSION` (e.g. `01.3.0`) or octal pitfalls where `10#` is not applied on output components.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: After `read`, normalize with `10#` for all three components when building `NEW_VERSION`, matching the semver compare block at lines 162–166.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate semver_lt in release scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-set-version.sh` defines a third copy of semver comparison logic already duplicated elsewhere in the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract scripts/lib-semver.sh


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Repetitive per-PR jq blocks in release-prepare
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-prepare.sh` (187–220) repeats similar jq extraction per PR field, increasing maintenance cost for PR metadata columns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single jq-to-TSV pass or small helper


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Redundant notes redaction in release-finish
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-finish.sh` (129–133) runs `redact-secrets.sh` again after SKILL Step 3 and `create-pr.sh` may already have redacted notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Skip when pre-redacted or document-only


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

