### FINDING_1: **Nit** `code-quality` `docs/linting.md:22`, `docs/linting.md:167-257` — The docs still describe CI as running `make test-harnesses-1` through `make test-harnesses-13`, and many command-table rows still name old exact shard assignments after the Makefile rebalance. I found 54 exact `via test-harnesses-N` mismatches against the new Makefile shard map, for example `test-upgrade-larch` now lives in `test-harnesses-9` but the docs say `test-harnesses-13`. Suggested fix: update line 22 to `test-harnesses-16`, and either refresh all exact per-target shard references from the Makefile or replace them with the existing generic `test-harnesses-N shard partition` wording to avoid future drift.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `docs/linting.md:22`, `docs/linting.md:167-257` — The docs still describe CI as running `make test-harnesses-1` through `make test-harnesses-13`, and many command-table rows still name old exact shard assignments after the Makefile rebalance. I found 54 exact `via test-harnesses-N` mismatches against the new Makefile shard map, for example `test-upgrade-larch` now lives in `test-harnesses-9` but the docs say `test-harnesses-13`. Suggested fix: update line 22 to `test-harnesses-16`, and either refresh all exact per-target shard references from the Makefile or replace them with the existing generic `test-harnesses-N shard partition` wording to avoid future drift.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: CHANGELOG.md (historical entries)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Changelog records past 11→13 rebalance; not updated for 16. Readers might confuse history with current layout; changelog is historical by design. Leave as-is or add a new changelog entry on release, outside this diff’s scope.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md (LPT snippet)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Quadratic bins.index in example snippet Unchanged algorithmic style aside from bin count 13→16 Accept as pre-existing doc example debt or rewrite LPT loop in a separate change
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: docs/linting.md:167-221 (representative)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Many reference-table `via test-harnesses-*` hints already mismatched `main`’s Makefile before this PR. Not introduced by this diff; broad pre-existing doc drift. Optional full-table regeneration from Makefile or drop hard-coded shard hints.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: docs/linting.md (various table rows)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Some via test-harnesses-N cells predated this branch and already disagreed with main Makefile assignments. Stale cross-refs pre-existed; not introduced solely by this PR’s edits to those lines. Track separately if you want the table mechanically synced to Makefile.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc still says test-harnesses-1 through test-harnesses-13. File not modified by this branch diff; stale after shard expansion. Update to sixteen shards in a separate doc pass if desired.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling contract still states umbrella spans test-harnesses-1..13 after branch moves to 16 shards. Same stale matrix-span risk as linting.md but file untouched by this diff/plan. Update line 27 when touching Makefile wiring docs next.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Contract doc still says umbrella spans shards 1–13 after Makefile moved to 16. Readers of the coverage-script contract doc get the wrong shard inventory; file not modified on this branch. Update to 1–16 when editing shard documentation.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: ~<TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale partial diff for docs/linting.md A reviewer using only the cached diff can miss CI Usage 13→16 and harness-table generalizations that exist on HEAD Prefer git diff main...HEAD or a refreshed session artifact for authoritative review
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: Makefile:32-33 Makefile:57-58
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Duplicate Shard-12 partition-guard comment before umbrella test-harnesses and before test-harnesses-12. Slight maintainer confusion about where the invariant is anchored. Keep one comment next to test-harnesses-12 only or only above the umbrella line.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: Makefile:32 Makefile:57
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Duplicate Shard-12 partition-guard comment appears above the umbrella test-harnesses line and again above test-harnesses-12. Minor maintainability noise and possible confusion about which stanza the comment describes. Remove the redundant copy; keep the comment immediately adjacent to test-harnesses-12 only.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: Makefile:32 and Makefile:57
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate Shard-12 partition-guard comment before umbrella and before test-harnesses-12. Minor reader confusion only; no runtime impact. Remove the redundant copy so the note sits only above test-harnesses-12.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: docs/linting.md:167-209 (examples docs/linting.md:186-188)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Manual harness table still lists old via test-harnesses-N for many targets after LPT reshuffle; verified mismatches include test-ship-pr test-upgrade-larch and launch CI harnesses vs Makefile:41 Makefile:51 Makefile:62-66. Operator reruns the documented shard to reproduce a failure and the named harness never runs on that shard. Regenerate per-harness shard suffixes from Makefile or remove exact shard numbers from the table.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: docs/linting.md:167-239 (Makefile Targets table; similar rows nearby)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Many explicit via test-harnesses-N annotations in the harness reference table still reflect the pre-reshuffle partition after Makefile LPT reassignment. Example: doc says test-upgrade-larch on shard 13 but Makefile assigns it to shard 9; doc says test-check-mid-run-dirty-tree on shard 3 but Makefile assigns shard 15—leads to wrong CI shard when triaging failures. Regenerate shard column from Makefile or drop fixed numbers for generic wording.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: docs/linting.md:187
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Upgrade-larch row claims make lint pulls test-upgrade-larch via test-harnesses-13. Makefile assigns test-upgrade-larch to test-harnesses-9; debugging or shard routing from the table points at the wrong GitHub Actions matrix cell. Change the referenced shard to test-harnesses-9 or generalize the wording to the sharded test-harnesses targets.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Usage CI bullet still documents harness matrix as test-harnesses-1..13 while CI and Makefile use 16 shards. Operators or docs consumers assume a 13-way matrix and mis-map failures or automation to non-existent shard identities. Update the bullet to test-harnesses-16 or otherwise match .github/workflows/ci.yaml.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Usage CI bullet still ends matrix range at test-harnesses-13 despite 16-shard CI and plan §3 sixteen-shard doc update. Readers believe CI only exposes 13 harness shards and misconfigure expectations or branch-protection mental model vs actual workflow. Update the sentence to test-harnesses-16 or otherwise describe sixteen matrix cells.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] CI Usage bullet still documents harness matrix as test-harnesses-1 through test-harnesses-13. Operators and contributors assume only 13 parallel harness shards exist and may misconfigure branch protection or misread CI behavior versus the actual 16-way matrix. Update the prose to test-harnesses-16 or describe shards 1-16 without a stale upper bound.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: docs/linting.md:187
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] `test-upgrade-larch` table row still claims lint coverage via `test-harnesses-13` but Makefile places the harness on `test-harnesses-9` (`Makefile:51`). Failure triage uses “Re-run failed jobs” on shard 13 and never exercises the failing harness, burning cycles and hiding signal. Set the suffix to `test-harnesses-9` or remove per-shard wording.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: docs/linting.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CI prose still caps the harness matrix at `make test-harnesses-13` while CI/Makefile implement 16 shards. Maintainers misread how many parallel `test-harnesses (N)` jobs exist or align automation with the wrong upper bound. Update the range to `test-harnesses-16` or describe the matrix without a hard-coded last index.
- **Suggested revision**: Address the concern above.

