Reviewing the cited code paths to confirm merge boundaries and severity.
### FINDING_1: release-prepare --bump override duplicates classify-bump arithmetic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` applies `--bump major|minor|patch` via an inline semver increment `case` block (lines 259–270) instead of delegating to `classify-bump.sh`. If either block changes independently, operator overrides can produce a different `NEW_VERSION` than the classifier for the same `CURRENT_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Stale `run_rebase_rebump` name after rebump removal
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` still names the CI-fix rebase helper `run_rebase_rebump` (lines 2646–2894) though rebump/version logic was removed. Grep and readers can misread the flow as still re-bumping versions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Stale `ship_pr_vendor_conflict_csv_is_non_bump_only` identifier
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The function name `ship_pr_vendor_conflict_csv_is_non_bump_only` (lines 2481–2536) still encodes bump/changelog semantics removed in Phase 5. New contributors grepping `non_bump` may assume CHANGELOG/bump routing still exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: classify-bump idempotency walk uses HEAD when `--head` is set
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: In `classify-bump.sh` (lines 176–188), the idempotency walk anchors on symbolic `HEAD` rather than `HEAD_COMPARE` when `--head` is supplied without a matching base semantics. Standalone `--head` callers can get `BUMP_TYPE=NONE` while the diff still shows public-surface changes. `/release` is safe when `--base` is mandatory; direct harness or CLI callers are not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: `RebaseResult.new_version` is always None in Python port
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/rebase.py` (lines 25–32) defines `RebaseResult.new_version` but never populates it. Callers and tests carry dead surface area for the Phase 7 port.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Reasoning log still named bump-version-reasoning.md
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `classify-bump.sh` (lines 121–127) still writes a reasoning artifact named `bump-version-reasoning.md`. `/release` operators may search for `release-*` paths and miss the log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] step-name-registry still lists retired ship substeps 8 / 8a
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/step-name-registry.tsv` (rows 15–16) still label ship substeps `8` (version bump) and `8a` (release notes) even though Phase 1 retired per-PR bump/changelog on the ship path and `skills/implement/SKILL.md` suppresses orchestrator breadcrumbs for those substeps. Session-start registry reads can invite reintroducing retired steps or misread current behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Legacy feature branches with CHANGELOG.md rebase conflicts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Removing `auto-resolve-changelog.sh` and dropping `CHANGELOG*` from `ship_pr_vendor_conflict_csv_is_non_bump_only` is correct for new runs without `CHANGELOG.md`, but in-flight feature branches that still contain `CHANGELOG.md` bump commits can hit rebase conflicts that previously auto-resolved and now fall through to vendor / Phase 1–4 / stall. Acceptable for Phase 5 acceptance if documented as a migration edge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: agent-lint S030 exclusions reference deleted or typo paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Phase 5 churn in `agent-lint.toml` (lines 1015–1018, 1400) pins non-existent S030 exclusion paths, including `scripts/test-git-stage.sh` and a typo filename `scripts/test-auto-resolve-release notes.md`. Contributors treating exclusions as authoritative may reference missing files; orphan detection for real harnesses can be misconfigured.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: CHANGELOG rebase conflicts routed to external vendors with full hunks
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After deleting `auto-resolve-changelog.sh` and removing `CHANGELOG*` from the non-bump-only vendor conflict classifier (`scripts/ship-pr.sh` roughly 2481–2788), `CHANGELOG.md` rebase conflicts on branches rebasing onto mains that still have changelog history are no longer auto-resolved locally. They enter the vendor conflict path (Codex/Cursor) with full hunks—raising stall rate on legacy branch shapes and potentially exposing sensitive release-note text externally. Related routing change: dropping CHANGELOG basename exclusion from `ship_pr_vendor_conflict_csv_is_non_bump_only` alters CI-fix conflict classification vs pre-Phase-5 behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Tmpdir resolver dropped dual-read for `.bump-version-armed`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `lib-resolve-implement-tmpdir.sh` (lines 42–43) renamed the eligibility sentinel from `.bump-version-armed` to `.release-armed` without accepting the legacy file. Pre-Phase-5 interrupted `/implement` runs that armed `.bump-version-armed` via `check-bump-version.sh` may no longer resolve after upgrade; Stop/SessionStart hooks can fail open without recovery guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: Relocated classify-bump harness dropped CHANGELOG idempotency fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `.claude/skills/release/scripts/test-classify-bump.sh` (lines 55–89) removed CHANGELOG-transparent idempotency fixtures while `classify-bump.sh` and `classify-bump.md` still implement and document that walk. A regression breaking transparent “Update CHANGELOG” commit detection could pass `make test-classify-bump` and mis-classify `/release` on legacy bump-pipeline commit stacks (including CHANGELOG-only transparency and CHANGELOG-subject spoofing over `skills/**`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] NEW_VERSION may preserve unpadded semver components
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh` (lines 322–326) formats `NEW_VERSION` after partial `10#` arithmetic without normalizing all three components. Edge-case `plugin.json` versions with leading-zero components could yield non-normalized `NEW_VERSION` strings (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] classify-bump `--head` without `--base` idempotency mismatch (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: With `--head` set and `--base` omitted, `classify-bump.sh` (lines 90–95, 715–727) diffs via `HEAD_COMPARE` but the idempotency walk still uses symbolic `HEAD`. Direct callers can observe `BUMP_TYPE=NONE` while the diff still shows unreleased changes. `/release` path is safe via mandatory `--base`; fix is anchor idempotency on `HEAD_COMPARE` or fail closed without `--base` (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Plan “byte-equivalent git mv” vs post-relocate classify-bump edits
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan section B called for byte-equivalent `git mv` of `classify-bump.sh`, but the diff rewrites the script (decimal-safe `10#` arithmetic, reasoning mktemp path, comment churn). Future auditors may flag plan noncompliance even when behavior is improved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters):** 19 raw slots → 15 aggregated blocks. Merged: registry 8/8a (inputs 7+19); CHANGELOG vendor/routing (inputs 10+12+13); harness fixtures (inputs 14+17). Kept separate: in-scope FINDING_4 vs OOS FINDING_14 (same HEAD/`HEAD_COMPARE` theme, different scope tags); OOS FINDING_8 (accept/document migration) vs in-scope FINDING_10 (actionable routing/security); FINDING_3 (rename) vs FINDING_10 (behavior). Inputs 8 and 10 overlap narratively but differ on required disposition (OOS acceptance vs in-scope fix).
