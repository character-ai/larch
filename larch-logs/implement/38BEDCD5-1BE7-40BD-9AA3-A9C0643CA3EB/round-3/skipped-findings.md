### FINDING_1: code-quality: skills/implement/scripts/write-final-report.sh:119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Branch bundles compute-pr-line-counts.sh and final-report line-count rendering not listed in the #3511 plan. Unrelated /implement feature ships in the same PR as plan-review anchoring; reviewers must audit two features; future reverts are coupled. Split line-count work to a separate PR or remove from this branch.
- **Suggested revision**: Address the concern above.



### FINDING_10: risk-integration: skills/review/scripts/test-collect-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Missing collect-to-check-scope-reduction-marker regression for TSV what prefixed with [SCOPE-REDUCTION] becoming severity-prefixed Concern. Collect formatting could change so the marker is no longer leading after [important] prefix; dedup/aggregation would stop recognizing scope cuts while unit tests on raw blocks still pass. Add collect fixture and assert check-scope-reduction-marker.sh exit 0 on emitted Concern line.
- **Suggested revision**: Address the concern above.



### FINDING_11: risk-integration: skills/design/scripts/test-run-step3-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Only SCOPE_ANCHOR_FILE key presence was added; plan-required IMPLEMENT_TMPDIR precedence and CR/LF sanitation tests are absent. Stale implement sessions could again supply the wrong feature file or inject path bytes into result env without harness failure. Add seam-stub cases binding DESIGN_TMPDIR/feature-description.txt over IMPLEMENT_TMPDIR and rejecting CR/LF in SCOPE_ANCHOR_FILE emission.
- **Suggested revision**: Address the concern above.



### FINDING_12: risk-integration: skills/design/scripts/test-plan-review-scope-anchor.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New harness is far thinner than plan acceptance listed (scout/panel/tally/revise wiring, dedup/aggregation survival). Acceptance criteria claim comprehensive offline regression but most wiring is unverified outside one loop brainstorm case; regressions in revise/tally handoff could ship unnoticed. Expand harness or distribute missing assertions across loop/tally/aggregate tests until every acceptance bullet is mechanically pinned.
- **Suggested revision**: Address the concern above.



### FINDING_13: risk-integration: skills/review/scripts/test-aggregate-findings.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan-mode marker-loss fallback, inline emitter, and code-mode non-preservation tests are missing. Aggregator validation changes could strip [SCOPE-REDUCTION] during LLM merge and fall back incorrectly; only the happy-path preservation case is covered. Add fixtures for validation-failed fallback, inline Severity/Concern emitter, and code-mode showing no special preservation.
- **Suggested revision**: Address the concern above.



### FINDING_14: risk-integration: skills/design/scripts/test-dispatch-plan-review-panel.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness checks --feature-file argv forwarding but not untrusted scope block content in rendered prompts. render-plan-review-prompt.sh regressions could remove binding scope instructions while dispatch argv tests still pass. Assert rendered prompt contains Binding issue scope anchor and untrusted evidence framing substrings.
- **Suggested revision**: Address the concern above.



### FINDING_15: risk-integration: Makefile / branch composition
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unrelated #3506 compute-pr-line-counts and write-final-report changes are bundled with scope-anchor work. CI failures or review churn on unrelated surfaces block merge of the anchor feature; bisecting regressions is harder. Split unrelated commits to a separate PR or document explicit coupling and ensure offline harness stability.
- **Suggested revision**: Address the concern above.



### FINDING_22: risk-integration: skills/design/scripts/test-plan-review-scope-anchor.sh:1-55
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plan-listed dedup/parity/ballot regressions are largely absent from harnesses Marker-loss or parity-fallback regressions can ship without CI coverage Add plan-promised fixtures for tagged dedup merge parity fallback and ballot renumber
- **Suggested revision**: Address the concern above.



### FINDING_29: **risk-integration** `skills/design/scripts/run-step3-review.sh:290-305` — The driver correctly pins plan review to `$DESIGN_TMPDIR/feature-description.txt` (removing the old `IMPLEMENT_TMPDIR` fallback in `plan-review-loop.sh`), but `skills/design/scripts/test-run-step3-review.sh` never regression-tests that binding when `IMPLEMENT_TMPDIR` points at a different tmpdir with its own `feature-description.txt`. The plan called for that fixture; without it, a future revert could reintroduce stale implement-session scope without CI catching it. **Suggested fix:** Add a harness case that sets `IMPLEMENT_TMPDIR` to a decoy tmpdir, runs the launcher, and asserts the loop stub receives `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` (argv log or seam stub), plus a positive `SCOPE_ANCHOR_FILE` emit when the loop stub returns it.
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/run-step3-review.sh:290-305` — The driver correctly pins plan review to `$DESIGN_TMPDIR/feature-description.txt` (removing the old `IMPLEMENT_TMPDIR` fallback in `plan-review-loop.sh`), but `skills/design/scripts/test-run-step3-review.sh` never regression-tests that binding when `IMPLEMENT_TMPDIR` points at a different tmpdir with its own `feature-description.txt`. The plan called for that fixture; without it, a future revert could reintroduce stale implement-session scope without CI catching it. **Suggested fix:** Add a harness case that sets `IMPLEMENT_TMPDIR` to a decoy tmpdir, runs the launcher, and asserts the loop stub receives `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` (argv log or seam stub), plus a positive `SCOPE_ANCHOR_FILE` emit when the loop stub returns it.
- **Suggested revision**: Address the concern above.



### FINDING_34: **risk-integration** `skills/design/scripts/test-plan-review-loop.sh` — The branch adds substantial marker-aware dedup/parity logic in `plan-review-loop.sh` (pre-dedup snapshot, subprocess calls to `check-scope-reduction-marker.sh`, post-dedup parity gate, ballot renumber fallback), but the loop harness only asserts scope-anchor argv wiring and artifact layout (`findings-in-scope.pre-dedup.md` in the golden file list). There is no stubbed case that feeds a tagged `[SCOPE-REDUCTION]` finding plus a near-duplicate untagged twin through collect → dedup → aggregation → ballot and asserts the marker survives and/or parity fallback fires. Regressions in the dedup merge branches above could ship without CI signal. **Suggested fix:** Add the plan-promised loop fixtures: tagged+untagged Jaccard merge keeps a leading marker, parity failure copies `findings-in-scope.pre-dedup.md`, inline-emitter `Severity`/`Concern` shape survives detection, and (optionally) two tagged near-duplicates merge reviewers without duplicating ballot IDs.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/test-plan-review-loop.sh` — The branch adds substantial marker-aware dedup/parity logic in `plan-review-loop.sh` (pre-dedup snapshot, subprocess calls to `check-scope-reduction-marker.sh`, post-dedup parity gate, ballot renumber fallback), but the loop harness only asserts scope-anchor argv wiring and artifact layout (`findings-in-scope.pre-dedup.md` in the golden file list). There is no stubbed case that feeds a tagged `[SCOPE-REDUCTION]` finding plus a near-duplicate untagged twin through collect → dedup → aggregation → ballot and asserts the marker survives and/or parity fallback fires. Regressions in the dedup merge branches above could ship without CI signal. **Suggested fix:** Add the plan-promised loop fixtures: tagged+untagged Jaccard merge keeps a leading marker, parity failure copies `findings-in-scope.pre-dedup.md`, inline-emitter `Severity`/`Concern` shape survives detection, and (optionally) two tagged near-duplicates merge reviewers without duplicating ballot IDs.
- **Suggested revision**: Address the concern above.



### FINDING_35: **risk-integration** `skills/design/scripts/test-tally-plan-review.sh` — The plan called for unchanged-threshold cases with tagged findings (`YES=1, NO=1` neutral, `YES<NO` rejected, tagged `OOS_*` no special handling). The harness still has no `[SCOPE-REDUCTION]` ballot rows; the only tagged-behavior check lives in the smaller `test-plan-review-scope-anchor.sh` via a direct `classify_result` call. That leaves the tally script path unverified for tagged findings that have passed through dedup/aggregation. **Suggested fix:** Extend `test-tally-plan-review.sh` with tagged FINDING/OOS fixtures and assert `classify_result` / TSV output matches the neutral/rejected baselines.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/test-tally-plan-review.sh` — The plan called for unchanged-threshold cases with tagged findings (`YES=1, NO=1` neutral, `YES<NO` rejected, tagged `OOS_*` no special handling). The harness still has no `[SCOPE-REDUCTION]` ballot rows; the only tagged-behavior check lives in the smaller `test-plan-review-scope-anchor.sh` via a direct `classify_result` call. That leaves the tally script path unverified for tagged findings that have passed through dedup/aggregation. **Suggested fix:** Extend `test-tally-plan-review.sh` with tagged FINDING/OOS fixtures and assert `classify_result` / TSV output matches the neutral/rejected baselines.
- **Suggested revision**: Address the concern above.



### FINDING_4: correctness: (branch vs plan)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-listed harness updates missing: test-dispatch-plan-voters.sh, test-dispatch-plan-review-panel.sh, test-tally-plan-review.sh, test-collect-findings.sh; test-plan-review-loop missing dedup/parity/malformed fixtures Scope-anchor regressions in voter forwarding, panel prompts, tally neutrality, or collect→detector path ship without CI coverage Add the harness cases enumerated in the implementation plan
- **Suggested revision**: Address the concern above.



### FINDING_42: **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:1673-1727` — The plan promised plan-mode regression for partial marker loss, parity-failure rollback, mixed tagged/untagged same-reviewer preservation, inline Severity/Concern emitter shapes, and a code-mode control proving `[SCOPE-REDUCTION]` rules are inactive outside plan mode; the harness only covers the single happy path (withhold → merge → append → renumber). The nested-concern parity false-negative above and LLM duplicate scope-cut paths are therefore unguarded. **Suggested fix:** Add fixtures for (1) two tagged nested concerns that must aggregate successfully, (2) parity failure restoring the pre-aggregation snapshot with `AGGREGATED=false`, (3) LLM untagged duplicate of a withheld tagged concern (expect validation failure or dedup), and (4) identical input run with `--input-mode code` showing no split/append behavior.
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:1673-1727` — The plan promised plan-mode regression for partial marker loss, parity-failure rollback, mixed tagged/untagged same-reviewer preservation, inline Severity/Concern emitter shapes, and a code-mode control proving `[SCOPE-REDUCTION]` rules are inactive outside plan mode; the harness only covers the single happy path (withhold → merge → append → renumber). The nested-concern parity false-negative above and LLM duplicate scope-cut paths are therefore unguarded. **Suggested fix:** Add fixtures for (1) two tagged nested concerns that must aggregate successfully, (2) parity failure restoring the pre-aggregation snapshot with `AGGREGATED=false`, (3) LLM untagged duplicate of a withheld tagged concern (expect validation failure or dedup), and (4) identical input run with `--input-mode code` showing no split/append behavior.
- **Suggested revision**: Address the concern above.



### FINDING_5: correctness: scripts/compute-pr-line-counts.sh:1-99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unrelated PR line-count feature bundled into scope-anchor PR Issue #3482 plan does not include compute-pr-line-counts or final-report line bullets; increases merge risk Split to separate PR or remove from this branch
- **Suggested revision**: Address the concern above.



### FINDING_7: risk-integration: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required dedup parity fallback, malformed anchor abort, approved-outline append, inline-emitter, and aggregation-fallback cases are not implemented; parity WARN path is untested in production. A tagged scope-reduction finding could be dropped during Jaccard dedup or parity failure and the ballot would silently use deduped output; CI would stay green because no fixture forces plan-review-dedup: scope-reduction marker parity failed. Add loop harness fixtures for tagged+untagged merge, forced parity miss, malformed larch:plan strip abort, outline-approved append, and AGGREGATED=false ballot fallback with assertions on WARN text and pre-dedup snapshot restore.
- **Suggested revision**: Address the concern above.



### FINDING_8: risk-integration: scripts/test-dispatch-plan-voters.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] --scope-anchor-file forwarding was added to dispatch-plan-voters.sh but the regression harness does not assert forwarding to render-voter-prompt.sh. A refactor could drop scope-anchor forwarding on retry/context paths while primary-path argv logging still passes; voters would lose issue anchoring without CI failure. Extend stub log assertions for with-flag and without-flag invocations mirroring test-plan-review-loop voter-argv checks.
- **Suggested revision**: Address the concern above.



### FINDING_9: risk-integration: skills/design/scripts/test-tally-plan-review.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required unchanged-threshold cases for tagged [SCOPE-REDUCTION] findings through tally-plan-review.sh were not added. Tally or classification logic could treat tagged scope cuts differently (e.g. auto-accept on tie) and regressions would not be caught; only a direct classify_result unit check exists in test-plan-review-scope-anchor.sh. Add ballot+voter fixtures exercising tagged neutral tie, rejection, exoneration, and tagged OOS no-special-case through tally-plan-review.sh.
- **Suggested revision**: Address the concern above.



