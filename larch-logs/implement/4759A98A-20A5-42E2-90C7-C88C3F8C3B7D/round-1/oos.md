### FINDING_16: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `scripts/test-collect-agent-retry.sh:814-827` — The existing `corrupt-risk` case verifies outer-retry succeeds with invalid input `OUTER_LAUNCHER_RISK=medium` but does not assert the retry `.meta` records normalized `OUTER_LAUNCHER_RISK=high`. Pre-existing; not introduced by this diff. A follow-up assertion would close the collector→launcher→retry-meta loop for risk normalization.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `scripts/test-launch-review.sh` — No primary-path test that `--risk medium` (non-`high|low`) normalizes to `OUTER_LAUNCHER_RISK=high` in outer `.meta`. Plan edge case documents this via `external_launcher_append_outer_meta`; only `low` + default are required. Pre-existing gap, not amplified by this change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **risk-integration** `scripts/test-launch-cursor-ci.sh` / `scripts/test-launch-cursor-implement.sh` — No dedicated harness asserts FINDING_6 `.meta` byte-stability after adding explicit `"" ""` args. Coverage relies on `scripts/test-lib-external-launcher-common.sh` function-level tests; acceptable given behavior-neutral intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_19: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **risk-integration** `scripts/lib-external-launcher-common.sh:19` — Empty 5th positional to `external_launcher_append_outer_meta` uses `${5:-${RISK:-high}}`, so an exported `RISK` in the environment can influence `OUTER_LAUNCHER_RISK` without an explicit launcher `--risk`. Pre-existing; FINDING_6’s explicit `""` does not change that. **Suggested fix:** Only if you want to pin behavior: treat empty `$5` as “use default high” without env fallback (e.g. separate unset vs empty handling).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-review.sh:478` vs `launch-review.md:20-22` — Docs now state `--risk` drives “risk-gated effort” on collector replay, but Codex still always invokes `agent-model-args.sh --with-effort` and Cursor still wraps with `/max-mode on` regardless of parsed `RISK` (including on retry). Pre-existing execution gap; the PR improves meta fidelity but does not close it. **Impact:** Operational mismatch, not a privilege-escalation path (retries stay high-effort when meta says `low`). Narrow docs or gate effort on normalized `RISK` if you want meta and behavior aligned.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/collect-agent-results.sh:536-545` — `validate_retry_stderr_sink_or_mark` only rejects `..` in `META_STDERR_SINK`; full `[A-Za-z0-9._/-]` validation happens later when `launch-review.sh` / `run-external-agent.sh` receive `--stderr-sink`. Pre-existing; mitigated on the outer-retry path by launcher re-validation. **Suggested fix:** Optional defense-in-depth: call `validate_meta_scalar_path` in the collector before retry launch. Other branch commits (`cleanup.sh` enumeration warnings, `ship-pr.sh` errexit preservation, `review-and-fix.sh` pathspec-only staging) are reliability or fail-closed hardening, not new trust-boundary regressions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **risk-integration** `scripts/lib-external-launcher-common.sh:19` — Empty 5th arg uses `${5:-${RISK:-high}}`, so a shell `RISK` env var can influence `OUTER_LAUNCHER_RISK` when callers pass `""`; pre-existing contract, not introduced by this branch. **Why OOS:** unchanged semantics; FINDING_6 only makes empty slots explicit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **architecture** Branch vs `main` includes five additional commits (ship-pr errexit restore, review-and-fix dirty-tree, validate-research, cleanup, harness sharding) outside the stderr/risk plan. **Why OOS:** not modified by `33b85f448`; separate issues/PR scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_4: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Six commits vs main mix #3273 with unrelated fixes/docs/tests. Reviewers must mentally filter a large diff; bisecting a regression to stderr/risk work is harder. Prefer separate PRs or clearly separated commits when landing stacked work (observation only).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/launch-review.md:497-510
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Full-branch diff adds large #3283 degraded-response docs in the same file as the #3273 --risk bullet. Doc readers may conflate two features in one changelog-style edit. Keep #3273 doc delta minimal in the feature commit (already true in 33b85f448).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/lib-external-launcher-common.sh:26-32,scripts/collect-agent-results.sh:531
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Append path can write a second STDERR_SINK= after OUTER_LAUNCHER=; collector keeps the last value. If base and append sinks ever differed, retries could pick the wrong sink silently. Pre-existing; optional hardening is dedupe-on-read or omit 6th arg when run-external-agent already wrote base STDERR_SINK=.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

