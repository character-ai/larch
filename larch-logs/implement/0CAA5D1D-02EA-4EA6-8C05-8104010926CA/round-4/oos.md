### FINDING_13: [OUT_OF_SCOPE] NEW_VERSION may preserve unpadded semver components
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` (lines 322–326) formats `NEW_VERSION` after partial `10#` arithmetic without normalizing all three components. Edge-case `plugin.json` versions with leading-zero components could yield non-normalized `NEW_VERSION` strings (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] classify-bump `--head` without `--base` idempotency mismatch (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: With `--head` set and `--base` omitted, `classify-bump.sh` (lines 90–95, 715–727) diffs via `HEAD_COMPARE` but the idempotency walk still uses symbolic `HEAD`. Direct callers can observe `BUMP_TYPE=NONE` while the diff still shows unreleased changes. `/release` path is safe via mandatory `--base`; fix is anchor idempotency on `HEAD_COMPARE` or fail closed without `--base` (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_15: [OUT_OF_SCOPE] Plan “byte-equivalent git mv” vs post-relocate classify-bump edits
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan section B called for byte-equivalent `git mv` of `classify-bump.sh`, but the diff rewrites the script (decimal-safe `10#` arithmetic, reasoning mktemp path, comment churn). Future auditors may flag plan noncompliance even when behavior is improved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters):** 19 raw slots → 15 aggregated blocks. Merged: registry 8/8a (inputs 7+19); CHANGELOG vendor/routing (inputs 10+12+13); harness fixtures (inputs 14+17). Kept separate: in-scope FINDING_4 vs OOS FINDING_14 (same HEAD/`HEAD_COMPARE` theme, different scope tags); OOS FINDING_8 (accept/document migration) vs in-scope FINDING_10 (actionable routing/security); FINDING_3 (rename) vs FINDING_10 (behavior). Inputs 8 and 10 overlap narratively but differ on required disposition (OOS acceptance vs in-scope fix).

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] Reasoning log still named bump-version-reasoning.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `classify-bump.sh` (lines 121–127) still writes a reasoning artifact named `bump-version-reasoning.md`. `/release` operators may search for `release-*` paths and miss the log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] step-name-registry still lists retired ship substeps 8 / 8a
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/step-name-registry.tsv` (rows 15–16) still label ship substeps `8` (version bump) and `8a` (release notes) even though Phase 1 retired per-PR bump/changelog on the ship path and `skills/implement/SKILL.md` suppresses orchestrator breadcrumbs for those substeps. Session-start registry reads can invite reintroducing retired steps or misread current behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] Legacy feature branches with CHANGELOG.md rebase conflicts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Removing `auto-resolve-changelog.sh` and dropping `CHANGELOG*` from `ship_pr_vendor_conflict_csv_is_non_bump_only` is correct for new runs without `CHANGELOG.md`, but in-flight feature branches that still contain `CHANGELOG.md` bump commits can hit rebase conflicts that previously auto-resolved and now fall through to vendor / Phase 1–4 / stall. Acceptable for Phase 5 acceptance if documented as a migration edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

