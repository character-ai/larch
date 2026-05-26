### FINDING_13: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-implement-step5-loop.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Strict > prevents mav-resume at STARTING_ROUND equal to base cap. STARTING_ROUND=5 base_cap=5 after 4 MAV rounds gets round 5 not mav-resume-past-cap per deferred MAV-as-degraded decision. Future issue if cap-hit must short-circuit at equality.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_17: risk-integration: skills/review-and-fix/scripts/test-review-and-fix.md:11
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness doc omits new step5-starting-round section Contributors running --section step5-starting-round may not find it documented Update test-review-and-fix.md --section list and one-line case summary
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration: scripts/test-run-step5-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No E2E loop --starting-round integration test IMPLEMENT_TMPDIR path mismatch between writer and reader would not be caught by unit tests Add deferred integration harness when touching run-step5-review.sh tmpdir resolution
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_21: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:142-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] In-loop mav-resume-past-cap largely unreachable post-hoist Low risk; hoisted path is tested; in-loop branch is defense-in-depth only Keep COVERAGE_NOTE or add opt-in test seam if in-loop coverage becomes required
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_24: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:81` — On artifact miss, `step5_probe_prior_round_env` invokes the global `sync` utility (best-effort, once per miss). That is not a privilege boundary escape, but on a shared host it can add brief system-wide flush latency during Step 5 restarts. **Suggested fix:** None required for this bugfix; if latency becomes an issue, consider a narrower retry (e.g., `fsync` on a known file descriptor) in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:114` — The new `larch_err` diagnostic prints `IMPLEMENT_TMPDIR` and `expected_env_path` to stderr. That aids debugging path mismatches but may surface full local paths in CI logs or shared run artifacts. **Suggested fix:** If logs are widely published, a follow-up could redact home-directory prefixes using existing redaction helpers elsewhere in larch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **architecture** `scripts/lib-implement-round-cap.sh:28-37` — `count_prior_degraded_rounds` trusts `DEGRADED_ROUND=true` in prior `review-and-fix.env` files under `IMPLEMENT_TMPDIR`. Anyone who can write that tmpdir during a run could inflate the effective cap (pre-existing behavior; this branch does not worsen it beyond computing cap math earlier at loop entry). **Suggested fix:** Out of scope here; tmpdir integrity is already part of the implement session trust model.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] architecture: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR pwd -P resolution unchanged. Path mismatch between writer and reader would still fail after sync retry; diagnostics are the mitigation. Address in a follow-up if production diagnostics show mismatched IMPLEMENT_TMPDIR paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_32: [OUT_OF_SCOPE] correctness: scripts/lib-implement-round-cap.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] MAV rounds do not set DEGRADED_ROUND=true. effective_round_cap stays at base_cap after four MAV rounds; cap-hit via hoisted mav-resume requires STARTING_ROUND strictly greater than cap. Deferred per plan; future MAV-as-degraded change would touch hoisted and in-loop checks together.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-bash-stub-mechanics-output.txt
- **Concern**: - **risk-integration** — The branch diff includes committed implement run artifacts under `larch-logs/implement/242C658E-7737-4872-B28C-B78C7A473889/` (breadcrumbs, manifest, plan copy). These are outside the six-file scope in the plan and should not ship with the fix. **Commits on branch:** `6b382278` (fix), `a42811d4` (larch-logs flush).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] `scripts/test-harness-shards-coverage.md:19` still names only `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` as CI section variants (predating `parsers`; now further behind with `step5-starting-round`). Worth a follow-up doc pass, not introduced solely by the Makefile target wiring.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - `scripts/test-harness-shards-coverage.md:19` still names only `test-review-and-fix-dispatch` and `test-review-and-fix-convergence` as CI section variants (predating `parsers`; now further behind with `step5-starting-round`). Worth a follow-up doc pass, not introduced solely by the Makefile target wiring.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_40: [OUT_OF_SCOPE] The branch also commits `larch-logs/implement/242C658E-.../` artifacts (`diff.txt` hunks ~119–510). That is unrelated to harness integration and widens the PR surface beyond the six scoped implementation files.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - The branch also commits `larch-logs/implement/242C658E-.../` artifacts (`diff.txt` hunks ~119–510). That is unrelated to harness integration and widens the PR surface beyond the six scoped implementation files.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_41: [OUT_OF_SCOPE] Case 1 in the plan used `STARTING_ROUND=4`; the landed test uses `STARTING_ROUND=5` (`skills/review-and-fix/scripts/test-review-and-fix.sh:2237`), which still exercises sync-retry for the missing prior round but is a mild acceptance/doc drift item, not a Makefile harness defect.
- **Reviewer**: dyn-harness-shard-target-output.txt
- **Concern**: - Case 1 in the plan used `STARTING_ROUND=4`; the landed test uses `STARTING_ROUND=5` (`skills/review-and-fix/scripts/test-review-and-fix.sh:2237`), which still exercises sync-retry for the missing prior round but is a mild acceptance/doc drift item, not a Makefile harness defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-implement-step5-loop.sh:142-145
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] In-loop vs hoisted flush/envelope order differs Pre-existing; hoisted order matches plan FINDING_16 Unify ordering in a separate refactor if desired
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] correctness: scripts/run-step5-review.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] IMPLEMENT_TMPDIR path normalization not in this PR Hypothesis B path mismatch may still defeat sync retry Address in follow-up if diagnostics show mismatch
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

