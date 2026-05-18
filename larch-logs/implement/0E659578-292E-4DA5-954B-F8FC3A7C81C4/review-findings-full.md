### FINDING_1: panel [code-review/accepted]

## **Nit** `risk-integration` [docs/installation-and-setup.md:40](<OPERATOR_REPO_PATH>/docs/installation-and-setup.md:40) still documents the old pruning policy: `docs/installation-and-setup.md:40` says `/upgrade-larch` keeps the verified stable release plus one rollback candidate, but the changed script now keeps the 8 most recent cached versions. Update this paragraph to match `skills/upgrade-larch/scripts/upgrade-larch.sh:179-201` and `skills/upgrade-larch/scripts/upgrade-larch.md:18`.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `risk-integration` [docs/installation-and-setup.md:40](<OPERATOR_REPO_PATH>/docs/installation-and-setup.md:40) still documents the old pruning policy: `docs/installation-and-setup.md:40` says `/upgrade-larch` keeps the verified stable release plus one rollback candidate, but the changed script now keeps the 8 most recent cached versions. Update this paragraph to match `skills/upgrade-larch/scripts/upgrade-larch.sh:179-201` and `skills/upgrade-larch/scripts/upgrade-larch.md:18`.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/test-upgrade-larch.sh:102-238

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Regression harness dropped bounded-prune-fallback and does not assert verified-stable cache preservation. Bogus high-version cache interactions or accidental deletion of LATEST_STABLE would not fail skills/upgrade-larch/scripts/test-upgrade-larch.sh. Add tests for the chosen invariant (pin verified dir and/or stray-newer semantics).
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:179-201

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Pruning removes lowest semver slice without exempting LATEST_STABLE; old code never deleted the verified stable cache dir. After verify of 31.0.0, cache dirs include 31.0.0 plus 32.0.0-39.0.0 (nine dirs). PRUNE_COUNT=1 removes 31.0.0 first, leaving 32.0.0-39.0.0 and deleting the verified release cache tree. Always retain LATEST_STABLE in the keeper set (and adjust tests), or document and accept with explicit tests if intentional.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:179-200

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Prune block only removes oldest entries when VERSION_COUNT>8; no pass removes semver-newer-than-verified-stable dirs when VERSION_COUNT<=8, and with>8 newest-eight retention can keep bogus high semver trees that old logic always pruned. Cache has e.g. 99.0.0 beside verified 31.0.0 with few other dirs; after verify the script emits No old versions to prune and leaves 99.0.0 forever, reintroducing misleading rollback content that bounded-prune-fallback used to assert away. Add a sanitization pass deleting cached dirs strictly newer than LATEST_STABLE regardless of count (or equivalent invariant) and extend tests for the <=8-cache stray-newer case.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: skills/upgrade-larch/scripts/test-upgrade-larch.sh:104-124

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Removal of bounded-prune-fallback drops regression coverage for newer-than-stable stray caches under the 8-version cap. A regression like bogus 99.0.0 surviving when only three cache dirs exist ships without failing tests. Add a focused test mirroring the old three-directory stray-newer scenario.
- **Suggested revision**: Address the concern above.

