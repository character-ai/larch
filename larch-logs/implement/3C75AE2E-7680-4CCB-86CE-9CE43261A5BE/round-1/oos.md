### FINDING_1: **Important** risk-integration: Makefile:15 wires `lint-bash32` only into the aggregate `make lint`, but CI does not run that target; `.github/workflows/ci.yaml:52-63` runs `make lint-only`, and `.github/workflows/ci.yaml:186-187` runs only the harness shards. Concrete scenario: a later PR adds `declare -A cache` to `scripts/foo.sh`; CI runs pre-commit plus `test-lint-bash32`, but never runs the full-tree `scripts/lint-bash32.sh`, so the Bash-4-only construct can merge and then fail for consumers on macOS Bash 3.2. Fix by adding a CI step/target that runs `make lint-bash32` over the full repo, or by making one CI shard depend on `lint-bash32` instead of only `test-lint-bash32`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** risk-integration: Makefile:15 wires `lint-bash32` only into the aggregate `make lint`, but CI does not run that target; `.github/workflows/ci.yaml:52-63` runs `make lint-only`, and `.github/workflows/ci.yaml:186-187` runs only the harness shards. Concrete scenario: a later PR adds `declare -A cache` to `scripts/foo.sh`; CI runs pre-commit plus `test-lint-bash32`, but never runs the full-tree `scripts/lint-bash32.sh`, so the Bash-4-only construct can merge and then fail for consumers on macOS Bash 3.2. Fix by adding a CI step/target that runs `make lint-bash32` over the full repo, or by making one CI shard depend on `lint-bash32` instead of only `test-lint-bash32`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] architecture: .claude-plugin/plugin.json; larch-logs/implement/*; version bump commits
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Version bumps and implement run logs ride along the branch Expected repo workflow noise for this plugin, not bash32 plan incompleteness No action required for plan fidelity
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_20: risk-integration: .github/workflows/ci.yaml:52-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] CI lint job never runs make lint-bash32; only local make lint does. A PR can merge Bash 4+ syntax into tracked *.sh; test-lint-bash32 fixtures still pass; full-tree bash32 guard from feature_description is not enforced on CI. Add make lint-bash32 (or equivalent pre-commit hook) to CI and document it in docs/linting.md CI section.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 NEUTRAL=0 Result=exonerated

### FINDING_21: risk-integration: .github/workflows/ci.yaml:63 and .claude/skills/relevant-checks/scripts/run-checks.sh:116-134
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Full-repo lint-bash32 is not part of CI or /relevant-checks; only fixture harness runs. Contributor adds Bash 4+ to tracked scripts/foo.sh; CI (lint-only + harness shards) and /relevant-checks stay green; macOS bash 3.2 users hit runtime syntax errors. Add make lint-bash32 (or bash scripts/lint-bash32.sh) to CI lint job and relevant-checks after pre-commit (or add pre-commit hook).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 NEUTRAL=0 Result=exonerated

### FINDING_22: risk-integration: .github/workflows/ci.yaml:63,Makefile:lint
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] target CI runs make lint-only and sharded test-harnesses; full-repo lint-bash32 is not invoked in ci.yaml A contributor adds declare -A to a real tracked script; test-lint-bash32 still passes because fixtures-only; Bash4+ ships to main Add make lint-bash32 to CI (or pre-commit) so every PR scans all tracked *.sh at repo root
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 NEUTRAL=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] architecture: branch commits (e.g. e9a74a2d a83cd1dc 8ea4de6c)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Version bump and larch-logs flush commits ride with bash32 work; orthogonal to bash32 test coverage. Reviewer noise when reading PR scope only; no bash32 CI gap by themselves. None required for bash32 feature; optional history cleanup for PR authors.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] architecture: larch-logs/implement/* flush
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large implement run logs committed By design per docs/run-logs.md; optional path scrub policy only if org requires cleaner archives N/A unless policy changes
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] code-quality: .git history e9a74a2d a83cd1dc
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Standalone version bump commits appear in the same branch range as the portability work. PR reviewers see extra noise unrelated to bash32 semantics. No code change required for bash32 feature; optional branch hygiene only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 NEUTRAL=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.sh:327-373 (cited in logs)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] NOT_SUBSTANTIVE visibility on zero-findings path may remain unresolved Only noted via larch-logs review text in this diff bundle; not re-derived from minimal code read here Confirm in a follow-up code pass if review-core changed outside logs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0 Result=rejected

