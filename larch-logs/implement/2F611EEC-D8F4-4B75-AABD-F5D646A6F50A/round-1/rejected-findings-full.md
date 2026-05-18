### [rejected] FINDING_1

### FINDING_1: **Nit** `code-quality` `docs/linting.md:22`, `docs/linting.md:167-257` — The docs still describe CI as running `make test-harnesses-1` through `make test-harnesses-13`, and many command-table rows still name old exact shard assignments after the Makefile rebalance. I found 54 exact `via test-harnesses-N` mismatches against the new Makefile shard map, for example `test-upgrade-larch` now lives in `test-harnesses-9` but the docs say `test-harnesses-13`. Suggested fix: update line 22 to `test-harnesses-16`, and either refresh all exact per-target shard references from the Makefile or replace them with the existing generic `test-harnesses-N shard partition` wording to avoid future drift.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `docs/linting.md:22`, `docs/linting.md:167-257` — The docs still describe CI as running `make test-harnesses-1` through `make test-harnesses-13`, and many command-table rows still name old exact shard assignments after the Makefile rebalance. I found 54 exact `via test-harnesses-N` mismatches against the new Makefile shard map, for example `test-upgrade-larch` now lives in `test-harnesses-9` but the docs say `test-harnesses-13`. Suggested fix: update line 22 to `test-harnesses-16`, and either refresh all exact per-target shard references from the Makefile or replace them with the existing generic `test-harnesses-N shard partition` wording to avoid future drift.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_13

### FINDING_13: correctness: docs/linting.md:167-209 (examples docs/linting.md:186-188)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Manual harness table still lists old via test-harnesses-N for many targets after LPT reshuffle; verified mismatches include test-ship-pr test-upgrade-larch and launch CI harnesses vs Makefile:41 Makefile:51 Makefile:62-66. Operator reruns the documented shard to reproduce a failure and the named harness never runs on that shard. Regenerate per-harness shard suffixes from Makefile or remove exact shard numbers from the table.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_14

### FINDING_14: correctness: docs/linting.md:167-239 (Makefile Targets table; similar rows nearby)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Many explicit via test-harnesses-N annotations in the harness reference table still reflect the pre-reshuffle partition after Makefile LPT reassignment. Example: doc says test-upgrade-larch on shard 13 but Makefile assigns it to shard 9; doc says test-check-mid-run-dirty-tree on shard 3 but Makefile assigns shard 15—leads to wrong CI shard when triaging failures. Regenerate shard column from Makefile or drop fixed numbers for generic wording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_15

### FINDING_15: correctness: docs/linting.md:187
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Upgrade-larch row claims make lint pulls test-upgrade-larch via test-harnesses-13. Makefile assigns test-upgrade-larch to test-harnesses-9; debugging or shard routing from the table points at the wrong GitHub Actions matrix cell. Change the referenced shard to test-harnesses-9 or generalize the wording to the sharded test-harnesses targets.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_16

### FINDING_16: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Usage CI bullet still documents harness matrix as test-harnesses-1..13 while CI and Makefile use 16 shards. Operators or docs consumers assume a 13-way matrix and mis-map failures or automation to non-existent shard identities. Update the bullet to test-harnesses-16 or otherwise match .github/workflows/ci.yaml.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_17

### FINDING_17: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Usage CI bullet still ends matrix range at test-harnesses-13 despite 16-shard CI and plan §3 sixteen-shard doc update. Readers believe CI only exposes 13 harness shards and misconfigure expectations or branch-protection mental model vs actual workflow. Update the sentence to test-harnesses-16 or otherwise describe sixteen matrix cells.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_18

### FINDING_18: correctness: docs/linting.md:22
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] CI Usage bullet still documents harness matrix as test-harnesses-1 through test-harnesses-13. Operators and contributors assume only 13 parallel harness shards exist and may misconfigure branch protection or misread CI behavior versus the actual 16-way matrix. Update the prose to test-harnesses-16 or describe shards 1-16 without a stale upper bound.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: docs/linting.md:187
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] `test-upgrade-larch` table row still claims lint coverage via `test-harnesses-13` but Makefile places the harness on `test-harnesses-9` (`Makefile:51`). Failure triage uses “Re-run failed jobs” on shard 13 and never exercises the failing harness, burning cycles and hiding signal. Set the suffix to `test-harnesses-9` or remove per-shard wording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: docs/linting.md:22
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CI prose still caps the harness matrix at `make test-harnesses-13` while CI/Makefile implement 16 shards. Maintainers misread how many parallel `test-harnesses (N)` jobs exist or align automation with the wrong upper bound. Update the range to `test-harnesses-16` or describe the matrix without a hard-coded last index.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0

