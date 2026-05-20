### FINDING_1: [OUT_OF_SCOPE] **`correctness` / `risk-integration`** — `scripts/test-dispatch-code-voters.sh:20-24` (argv loop unchanged in substance): unknown tokens are still dropped with `*) shift ;;`, and `--section` without a value can still trip `set -u` on `"$2"`. This predates the reshard; `skills/review-and-fix/scripts/test-review-and-fix.sh` now uses stricter parsing for comparison.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **`correctness` / `risk-integration`** — `scripts/test-dispatch-code-voters.sh:20-24` (argv loop unchanged in substance): unknown tokens are still dropped with `*) shift ;;`, and `--section` without a value can still trip `set -u` on `"$2"`. This predates the reshard; `skills/review-and-fix/scripts/test-review-and-fix.sh` now uses stricter parsing for comparison.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] **`risk-integration`** — Expanding to 20 matrix jobs reuses the existing operational risk that branch protection / rulesets must list every `test-harnesses (N)` required check; the branch updates `docs/linting.md` accordingly, but misconfiguration remains an admin-side failure mode, not a logic bug in the diff.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **`risk-integration`** — Expanding to 20 matrix jobs reuses the existing operational risk that branch protection / rulesets must list every `test-harnesses (N)` required check; the branch updates `docs/linting.md` accordingly, but misconfiguration remains an admin-side failure mode, not a logic bug in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: Makefile (duplicate .PHONY lines near test-dispatch-code-voters targets)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Repeated `.PHONY` declarations for some test-* targets remain noisy; not introduced by this diff. Pre-existing clutter only. Clean up in a dedicated hygiene change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale harness names in committed run logs No impact on CI or product runtime None required for this PR
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: .github/workflows/ci.yaml (ripgrep install step, unchanged by this diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Pinned third-party tarball fetch for `rg` on cache miss; unchanged by the shard matrix edit. General CI supply-chain posture, not this PR’s delta. Track separately if hardening that install path is a goal.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-dispatch-code-voters.sh:19-24
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Option loop uses `*) shift ;;` so unknown flags are ignored and an empty SECTION runs all sections, while test-review-and-fix.sh in the same change rejects unknown argv. A developer or future Makefile wrapper passes e.g. `--sectoin regressions-r1-r2`; the harness runs everything and may appear green while not exercising the intended shard, lengthening runs and hiding typos. Align parsing with test-review-and-fix.sh: fail on unknown tokens and require an explicit value after `--section`.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/test-dispatch-code-voters.sh:20-24 vs skills/review-and-fix/scripts/test-review-and-fix.sh:11-26
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Inconsistent unknown-CLI handling across sectioned harnesses Minor contributor confusion when copying CLI patterns from one harness to the other Align behavior or note the difference in both sibling .md files
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: skills/review-and-fix/scripts/test-review-and-fix.sh:11-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unknown CLI arguments abort with ERROR, unlike test-dispatch-code-voters.sh which shifts and ignores extra tokens. A wrapper or ad-hoc invocation that passes benign extra argv (or a flag ordering mistake) fails this harness while the dispatch harness would still run. Align the loop with scripts/test-dispatch-code-voters.sh ( *) shift ;; ) or document strict argv in test-review-and-fix.md as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: Makefile:136-137
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-harnesses-3 gains test-review-and-fix-convergence without timing proof in diff CI shard 3 wall time could exceed the same ~40s ceiling if convergence is large vs assumed slack Re-bin using LARCH_HARNESS_TIMING per docs/linting.md or relocate convergence if shard 3 regresses
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:11-35
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Strict argv parsing rejects any non---section tokens Ad-hoc invocations with trailing args that previously no-op now fail with ERROR unknown argument Ignore unknown tokens or document supported argv to match callers
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.sh:22-25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Unknown argv is fatal; plan asked for same CLI pattern as test-dispatch-code-voters.sh which ignores extra args. A caller or wrapper passes a trailing flag; the harness exits 1 with ERROR unknown argument and runs zero tests. Mirror test-dispatch `*) shift ;;` or document strict argv and adjust plan wording.
- **Suggested revision**: Address the concern above.

