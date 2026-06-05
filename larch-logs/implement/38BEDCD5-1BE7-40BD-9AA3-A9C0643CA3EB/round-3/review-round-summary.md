# Review Round 3

- Mode: `diff`
- 34 accepted, 11 rejected (7 exonerated)

## Accepted Findings

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


### FINDING_17: correctness: skills/design/scripts/plan-review-loop.sh:1315-1328
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dedup refuses to merge two overlapping tagged [SCOPE-REDUCTION] findings Two reviewers emit near-duplicate scope-cut findings; both stay on the ballot and split votes Merge tagged+tagged overlaps like tagged+untagged: keep one leading-marker body and union reviewers
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/design/scripts/plan-review-loop.sh:136-175
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty scope anchor after successful larch:plan strip is not rejected or warned Feature text is only an embedded plan block; reviewers/voters get a blank binding scope and scope anchoring silently fails Fail loud or WARN+abort when stripped exterior plus optional outline is whitespace-only
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/design/scripts/plan-review-loop.sh:1315-1328
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Tagged+tagged Jaccard duplicates are not merged; both scope-reduction findings reach ballot.txt Two reviewers file overlapping [SCOPE-REDUCTION] findings; dedup appends both; voters see duplicate scope cuts and may split YES/NO on the same underlying issue Merge overlapping tagged blocks by combining reviewer attribution into one tagged keeper, or dedupe tagged blocks separately before parity
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: skills/design/scripts/plan-review-loop.sh:1514-1536
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Ballot renumber fallback mixes pre-dedup in-scope with post-dedup OOS Renumber fails after aggregation; ballot pairs stale in-scope snapshot with deduped OOS split Rebuild OOS from the same snapshot generation or re-split from one consistent findings source
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: skills/design/scripts/test-plan-review-scope-anchor.sh:1-55
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Plan-listed dedup/parity/ballot regressions are largely absent from harnesses Marker-loss or parity-fallback regressions can ship without CI coverage Add plan-promised fixtures for tagged dedup merge parity fallback and ballot renumber
- **Suggested revision**: Address the concern above.


### FINDING_27: **risk-integration** `skills/design/scripts/run-step3-review.sh:148-174` — `validate_scope_anchor_handoff` clears `SCOPE_ANCHOR_FILE` on CR/LF, symlink, missing file, or out-of-tmpdir paths with only a `WARN`, then still writes an empty `SCOPE_ANCHOR_FILE` into `.step3-review-result.env`. On `LOOP_STATUS=main-agent-vote-required`, `skills/design/SKILL.md` tells the orchestrator to anchor MainAgent voting from that handoff key; if validation clears it while `plan-review-scope-anchor.txt` still exists on disk, the 0-judge fallback can vote without issue scope and silently undo the feature’s main ratchet fix. **Suggested fix:** On `main-agent-vote-required`, fail closed when handoff validation fails, or deterministically fall back to the canonical staged path `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` when that regular file is readable; do not emit an empty handoff key while a valid staged anchor remains.
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/run-step3-review.sh:148-174` — `validate_scope_anchor_handoff` clears `SCOPE_ANCHOR_FILE` on CR/LF, symlink, missing file, or out-of-tmpdir paths with only a `WARN`, then still writes an empty `SCOPE_ANCHOR_FILE` into `.step3-review-result.env`. On `LOOP_STATUS=main-agent-vote-required`, `skills/design/SKILL.md` tells the orchestrator to anchor MainAgent voting from that handoff key; if validation clears it while `plan-review-scope-anchor.txt` still exists on disk, the 0-judge fallback can vote without issue scope and silently undo the feature’s main ratchet fix. **Suggested fix:** On `main-agent-vote-required`, fail closed when handoff validation fails, or deterministically fall back to the canonical staged path `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` when that regular file is readable; do not emit an empty handoff key while a valid staged anchor remains.
- **Suggested revision**: Address the concern above.


### FINDING_28: **risk-integration** `skills/design/scripts/plan-review-loop.sh:136-175` — Scope-anchor materialization always writes `plan-review-scope-anchor.txt` and proceeds even when `plan-block-strip-body.sh` plus optional outline yield no substantive issue text (whitespace-only / plan-only issue bodies). Downstream panel, voter, and revise paths still receive binding-scope framing, but with an empty anchor, so reviewers and voters cannot actually judge “over-serves the issue.” That recreates vacuum-style review under a false sense of anchoring. **Suggested fix:** After `_materialize_scope_anchor`, require non-whitespace body content (or abort with a loud error) before dispatching scout/panel/voters/revise; optionally allow an explicit operator override, but not silent continuation.
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:136-175` — Scope-anchor materialization always writes `plan-review-scope-anchor.txt` and proceeds even when `plan-block-strip-body.sh` plus optional outline yield no substantive issue text (whitespace-only / plan-only issue bodies). Downstream panel, voter, and revise paths still receive binding-scope framing, but with an empty anchor, so reviewers and voters cannot actually judge “over-serves the issue.” That recreates vacuum-style review under a false sense of anchoring. **Suggested fix:** After `_materialize_scope_anchor`, require non-whitespace body content (or abort with a loud error) before dispatching scout/panel/voters/revise; optionally allow an explicit operator override, but not silent continuation.
- **Suggested revision**: Address the concern above.


### FINDING_29: **risk-integration** `skills/design/scripts/run-step3-review.sh:290-305` — The driver correctly pins plan review to `$DESIGN_TMPDIR/feature-description.txt` (removing the old `IMPLEMENT_TMPDIR` fallback in `plan-review-loop.sh`), but `skills/design/scripts/test-run-step3-review.sh` never regression-tests that binding when `IMPLEMENT_TMPDIR` points at a different tmpdir with its own `feature-description.txt`. The plan called for that fixture; without it, a future revert could reintroduce stale implement-session scope without CI catching it. **Suggested fix:** Add a harness case that sets `IMPLEMENT_TMPDIR` to a decoy tmpdir, runs the launcher, and asserts the loop stub receives `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` (argv log or seam stub), plus a positive `SCOPE_ANCHOR_FILE` emit when the loop stub returns it.
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/run-step3-review.sh:290-305` — The driver correctly pins plan review to `$DESIGN_TMPDIR/feature-description.txt` (removing the old `IMPLEMENT_TMPDIR` fallback in `plan-review-loop.sh`), but `skills/design/scripts/test-run-step3-review.sh` never regression-tests that binding when `IMPLEMENT_TMPDIR` points at a different tmpdir with its own `feature-description.txt`. The plan called for that fixture; without it, a future revert could reintroduce stale implement-session scope without CI catching it. **Suggested fix:** Add a harness case that sets `IMPLEMENT_TMPDIR` to a decoy tmpdir, runs the launcher, and asserts the loop stub receives `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` (argv log or seam stub), plus a positive `SCOPE_ANCHOR_FILE` emit when the loop stub returns it.
- **Suggested revision**: Address the concern above.


### FINDING_30: **risk-integration** `skills/design/SKILL.md:1119` — MainAgent re-tally is instructed to “refresh” `.step3-plan-review-result.env` and `.step3-review-result.env` after re-tally, but `tally-plan-review.sh` does not emit `SCOPE_ANCHOR_FILE`, and there is no merge helper that preserves durable handoff keys during that refresh. The anchor survives only if the orchestrator remembers to copy the prior value prompt-side; a partial rewrite drops scope anchoring after the exact path that needs it most. **Suggested fix:** Before any post–MainAgent re-tally result-env write, read and re-emit the existing `SCOPE_ANCHOR_FILE` (or call a small phase-driver helper that merges allowlisted durable keys), and add an orchestrator-fence / run-step3 test that re-tally refresh retains the staged anchor path.
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **risk-integration** `skills/design/SKILL.md:1119` — MainAgent re-tally is instructed to “refresh” `.step3-plan-review-result.env` and `.step3-review-result.env` after re-tally, but `tally-plan-review.sh` does not emit `SCOPE_ANCHOR_FILE`, and there is no merge helper that preserves durable handoff keys during that refresh. The anchor survives only if the orchestrator remembers to copy the prior value prompt-side; a partial rewrite drops scope anchoring after the exact path that needs it most. **Suggested fix:** Before any post–MainAgent re-tally result-env write, read and re-emit the existing `SCOPE_ANCHOR_FILE` (or call a small phase-driver helper that merges allowlisted durable keys), and add an orchestrator-fence / run-step3 test that re-tally refresh retains the staged anchor path.
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `skills/design/scripts/plan-review-loop.sh:1314-1328` — When two near-duplicate in-scope findings are both detected as scope-reduction tagged (`tagged and kept_tagged[i]`), the Jaccard deduper deliberately refuses to merge and leaves both blocks on the ballot. That preserves markers, but it also splits votes across duplicate `FINDING_*` IDs: panel voters often YES one copy and treat the other as redundant, so each row can land at `YES=1, NO=1` (neutral) instead of accumulating `2+ YES` on a single scope-cut finding. That works against the issue goal that a scope-reduction finding can actually win under unchanged tally thresholds. **Suggested fix:** For the `tagged && kept_tagged[i]` branch, merge reviewer attribution into one kept tagged body when comparison Jaccard exceeds the threshold (same as the tagged-over-untagged path), since both bodies already carry the leading marker and marker loss is not the risk on that branch.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - **correctness** `skills/design/scripts/plan-review-loop.sh:1314-1328` — When two near-duplicate in-scope findings are both detected as scope-reduction tagged (`tagged and kept_tagged[i]`), the Jaccard deduper deliberately refuses to merge and leaves both blocks on the ballot. That preserves markers, but it also splits votes across duplicate `FINDING_*` IDs: panel voters often YES one copy and treat the other as redundant, so each row can land at `YES=1, NO=1` (neutral) instead of accumulating `2+ YES` on a single scope-cut finding. That works against the issue goal that a scope-reduction finding can actually win under unchanged tally thresholds. **Suggested fix:** For the `tagged && kept_tagged[i]` branch, merge reviewer attribution into one kept tagged body when comparison Jaccard exceeds the threshold (same as the tagged-over-untagged path), since both bodies already carry the leading marker and marker loss is not the risk on that branch.
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


### FINDING_40: **correctness** `skills/review/scripts/aggregate-findings.sh:785-794` — Plan-mode tagged-marker parity uses greedy first-fit substring matching (`src_norm in norm_body(b)` / reverse) over `combined_tagged` blocks. When two `[SCOPE-REDUCTION]` findings have nested concern text (e.g. “remove foo” and “remove foo and bar”), the shorter input can match the longer combined block first; the longer input then finds no unused block, parity exits 1, aggregation rolls back to the pre-merge snapshot, and `AGGREGATED=false` even though both tagged blocks were appended verbatim. That is a false-negative parity failure on a realistic multi–scope-cut ballot. **Suggested fix:** Align parity with `plan-review-loop.sh` dedup parity: strip `[SCOPE-REDUCTION]` (and severity) for comparison only, require reviewer overlap where present, use token Jaccard instead of substring containment, and match longest/highest-score candidates first (or sort tagged inputs by descending normalized length before greedy assignment).
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:785-794` — Plan-mode tagged-marker parity uses greedy first-fit substring matching (`src_norm in norm_body(b)` / reverse) over `combined_tagged` blocks. When two `[SCOPE-REDUCTION]` findings have nested concern text (e.g. “remove foo” and “remove foo and bar”), the shorter input can match the longer combined block first; the longer input then finds no unused block, parity exits 1, aggregation rolls back to the pre-merge snapshot, and `AGGREGATED=false` even though both tagged blocks were appended verbatim. That is a false-negative parity failure on a realistic multi–scope-cut ballot. **Suggested fix:** Align parity with `plan-review-loop.sh` dedup parity: strip `[SCOPE-REDUCTION]` (and severity) for comparison only, require reviewer overlap where present, use token Jaccard instead of substring containment, and match longest/highest-score candidates first (or sort tagged inputs by descending normalized length before greedy assignment).
- **Suggested revision**: Address the concern above.


### FINDING_41: **correctness** `skills/review/scripts/aggregate-findings.sh:692-809` — The plan contract calls for marker/reviewer validation on the **combined** post-append stream. Implementation validates only `AGGREGATE_SOURCE_FILE` (untagged subset) against the LLM candidate before append; after tagged blocks are concatenated and renumbered, no second `validate_py` (or equivalent reviewer-coverage) pass runs on the combined output. If the LLM recreates a scope-cut concern in the untagged merge **without** a leading marker, parity can still pass (only appended blocks are `combined_tagged`), and the ballot can carry duplicate scope-reduction content—one untagged, one tagged—undermining the scope-anchor goal. **Suggested fix:** After append and before `AGGREGATED=true`, run reviewer-coverage validation on the full combined stream (or reject untagged merged blocks whose normalized concern is a superset/substring match of any withheld tagged block after comparison-only marker stripping).
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:692-809` — The plan contract calls for marker/reviewer validation on the **combined** post-append stream. Implementation validates only `AGGREGATE_SOURCE_FILE` (untagged subset) against the LLM candidate before append; after tagged blocks are concatenated and renumbered, no second `validate_py` (or equivalent reviewer-coverage) pass runs on the combined output. If the LLM recreates a scope-cut concern in the untagged merge **without** a leading marker, parity can still pass (only appended blocks are `combined_tagged`), and the ballot can carry duplicate scope-reduction content—one untagged, one tagged—undermining the scope-anchor goal. **Suggested fix:** After append and before `AGGREGATED=true`, run reviewer-coverage validation on the full combined stream (or reject untagged merged blocks whose normalized concern is a superset/substring match of any withheld tagged block after comparison-only marker stripping).
- **Suggested revision**: Address the concern above.


### FINDING_42: **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:1673-1727` — The plan promised plan-mode regression for partial marker loss, parity-failure rollback, mixed tagged/untagged same-reviewer preservation, inline Severity/Concern emitter shapes, and a code-mode control proving `[SCOPE-REDUCTION]` rules are inactive outside plan mode; the harness only covers the single happy path (withhold → merge → append → renumber). The nested-concern parity false-negative above and LLM duplicate scope-cut paths are therefore unguarded. **Suggested fix:** Add fixtures for (1) two tagged nested concerns that must aggregate successfully, (2) parity failure restoring the pre-aggregation snapshot with `AGGREGATED=false`, (3) LLM untagged duplicate of a withheld tagged concern (expect validation failure or dedup), and (4) identical input run with `--input-mode code` showing no split/append behavior.
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:1673-1727` — The plan promised plan-mode regression for partial marker loss, parity-failure rollback, mixed tagged/untagged same-reviewer preservation, inline Severity/Concern emitter shapes, and a code-mode control proving `[SCOPE-REDUCTION]` rules are inactive outside plan mode; the harness only covers the single happy path (withhold → merge → append → renumber). The nested-concern parity false-negative above and LLM duplicate scope-cut paths are therefore unguarded. **Suggested fix:** Add fixtures for (1) two tagged nested concerns that must aggregate successfully, (2) parity failure restoring the pre-aggregation snapshot with `AGGREGATED=false`, (3) LLM untagged duplicate of a withheld tagged concern (expect validation failure or dedup), and (4) identical input run with `--input-mode code` showing no split/append behavior.
- **Suggested revision**: Address the concern above.


### FINDING_43: **correctness** `skills/review/scripts/aggregate-findings.sh:774-777` — Parity `norm_body()` strips a leading severity bracket from the block body but not `[SCOPE-REDUCTION]`, while `plan-review-loop.sh` dedup parity strips both for comparison-only tokenization (`plan-review-loop.sh:1419-1421`). That inconsistency can make aggregation parity stricter or looser than upstream dedup parity for the same findings, producing divergent fallback behavior across pipeline stages. **Suggested fix:** Reuse one shared normalization helper (or mirror the dedup parity `prob()` logic) in both places so comparison-only stripping is identical.
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:774-777` — Parity `norm_body()` strips a leading severity bracket from the block body but not `[SCOPE-REDUCTION]`, while `plan-review-loop.sh` dedup parity strips both for comparison-only tokenization (`plan-review-loop.sh:1419-1421`). That inconsistency can make aggregation parity stricter or looser than upstream dedup parity for the same findings, producing divergent fallback behavior across pipeline stages. **Suggested fix:** Reuse one shared normalization helper (or mirror the dedup parity `prob()` logic) in both places so comparison-only stripping is identical.
- **Suggested revision**: Address the concern above.


### FINDING_46: **security** `skills/design/SKILL.md:1119` — MainAgent 0-judge scope anchoring is enforced only by orchestrator prose: the skill tells the agent to manually redact and HTML-escape `$SCOPE_ANCHOR_FILE` into `<plan_review_scope_anchor encoding="literal-redacted">`, but unlike voters (`skills/shared/scripts/render-voter-prompt.sh:14-26,92-100`) and reviewers (`skills/design/scripts/render-plan-review-prompt.sh:107-118,132-146`) there is no script helper or harness proving delimiter breakout resistance on that path. A compliant-but-careless orchestrator can inline raw GitHub issue bytes (e.g. `</plan_review_scope_anchor>` plus instruction text) into the voting context. **Suggested fix:** Extract `redact_untrusted_stream` / `emit_untrusted_file_block` into a shared helper (e.g. `scripts/lib-untrusted-prompt.sh`) and add a small `render-main-agent-scope-anchor.sh` (or reuse the voter renderer with a `--mode main-agent` flag) that the SKILL invokes via Bash before adjudication; add a delimiter-breakout harness mirroring `scripts/test-render-voter-prompt.sh:124-139`.
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - **security** `skills/design/SKILL.md:1119` — MainAgent 0-judge scope anchoring is enforced only by orchestrator prose: the skill tells the agent to manually redact and HTML-escape `$SCOPE_ANCHOR_FILE` into `<plan_review_scope_anchor encoding="literal-redacted">`, but unlike voters (`skills/shared/scripts/render-voter-prompt.sh:14-26,92-100`) and reviewers (`skills/design/scripts/render-plan-review-prompt.sh:107-118,132-146`) there is no script helper or harness proving delimiter breakout resistance on that path. A compliant-but-careless orchestrator can inline raw GitHub issue bytes (e.g. `</plan_review_scope_anchor>` plus instruction text) into the voting context. **Suggested fix:** Extract `redact_untrusted_stream` / `emit_untrusted_file_block` into a shared helper (e.g. `scripts/lib-untrusted-prompt.sh`) and add a small `render-main-agent-scope-anchor.sh` (or reuse the voter renderer with a `--mode main-agent` flag) that the SKILL invokes via Bash before adjudication; add a delimiter-breakout harness mirroring `scripts/test-render-voter-prompt.sh:124-139`.
- **Suggested revision**: Address the concern above.


### FINDING_47: **security** `skills/design/scripts/revise-plan-with-waterfall.sh:143-156` — `compose_prompt` hardens the scope anchor (`<feature encoding="literal-redacted">` with `redact-secrets.sh` + `&lt;`/`&gt;` escaping) but still copies `$PLAN_FILE` and `$FINDINGS_FILE` raw inside `<plan>` / `<findings>` tags without redaction or markup escaping. Reviewer-produced findings are untrusted; a finding body containing `</findings>` and instruction-like prose lands in the trusted orchestrator-composed region immediately before the scope-anchor preamble, weakening the new boundary. **Suggested fix:** Route plan and findings through the same `redact_untrusted_stream` pipeline (or matching `encoding="literal-redacted"` wrappers) used for the feature block, and extend `scripts/test-revise-plan-with-waterfall.sh` with a `</findings>` breakout fixture.
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - **security** `skills/design/scripts/revise-plan-with-waterfall.sh:143-156` — `compose_prompt` hardens the scope anchor (`<feature encoding="literal-redacted">` with `redact-secrets.sh` + `&lt;`/`&gt;` escaping) but still copies `$PLAN_FILE` and `$FINDINGS_FILE` raw inside `<plan>` / `<findings>` tags without redaction or markup escaping. Reviewer-produced findings are untrusted; a finding body containing `</findings>` and instruction-like prose lands in the trusted orchestrator-composed region immediately before the scope-anchor preamble, weakening the new boundary. **Suggested fix:** Route plan and findings through the same `redact_untrusted_stream` pipeline (or matching `encoding="literal-redacted"` wrappers) used for the feature block, and extend `scripts/test-revise-plan-with-waterfall.sh` with a `</findings>` breakout fixture.
- **Suggested revision**: Address the concern above.


### FINDING_48: **security** `scripts/scout-dynamic-archetypes.sh:539-572` — Scout manifest validation still keys off legacy delimiter names (`<implementation_plan`, `<feature_description`, `</reviewer_`, `</scout_notes>`). This branch introduces `<reviewer_feature_description encoding="literal-redacted">` (reviewers) and `<plan_review_scope_anchor encoding="literal-redacted">` (voters). A jailbroken or manipulated scout can emit an opening `<reviewer_feature_description encoding="literal-redacted">` in `prompt_body` (not matched by `has_unsafe_plan_delimiter`) or a closing `</plan_review_scope_anchor>` (not matched by `contains("</reviewer_")`). `dispatch-plan-review-panel.sh:82-88` embeds `prompt_body` verbatim before the real escaped scope anchor in `append_shared_prompt_tail`, so fake tags can sit adjacent to authentic hardened blocks. **Suggested fix:** Extend `has_unsafe_plan_delimiter` / `has_unsafe_wrapper_tag` to reject opening/closing tags for `reviewer_feature_description`, `plan_review_scope_anchor`, and `feature encoding="literal-redacted"`; add a scout harness with malicious `prompt_body` fixtures.
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - **security** `scripts/scout-dynamic-archetypes.sh:539-572` — Scout manifest validation still keys off legacy delimiter names (`<implementation_plan`, `<feature_description`, `</reviewer_`, `</scout_notes>`). This branch introduces `<reviewer_feature_description encoding="literal-redacted">` (reviewers) and `<plan_review_scope_anchor encoding="literal-redacted">` (voters). A jailbroken or manipulated scout can emit an opening `<reviewer_feature_description encoding="literal-redacted">` in `prompt_body` (not matched by `has_unsafe_plan_delimiter`) or a closing `</plan_review_scope_anchor>` (not matched by `contains("</reviewer_")`). `dispatch-plan-review-panel.sh:82-88` embeds `prompt_body` verbatim before the real escaped scope anchor in `append_shared_prompt_tail`, so fake tags can sit adjacent to authentic hardened blocks. **Suggested fix:** Extend `has_unsafe_plan_delimiter` / `has_unsafe_wrapper_tag` to reject opening/closing tags for `reviewer_feature_description`, `plan_review_scope_anchor`, and `feature encoding="literal-redacted"`; add a scout harness with malicious `prompt_body` fixtures.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: scripts/compute-pr-line-counts.sh:1-99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Unrelated PR line-count feature bundled into scope-anchor PR Issue #3482 plan does not include compute-pr-line-counts or final-report line bullets; increases merge risk Split to separate PR or remove from this branch
- **Suggested revision**: Address the concern above.


### FINDING_53: **code-quality** `skills/design/scripts/plan-review-loop.sh:136-174` — `_materialize_scope_anchor` creates two `mktemp` files (`stripped_tmp`, `anchor_tmp`) and only removes them on the strip-failure path or at normal completion; if `redact-secrets.sh` or the following `sed -E` pipeline fails under `set -euo pipefail`, the function aborts without an ERR/`trap` cleanup, leaving orphaned `.plan-review-scope-anchor.*` files in `$DESIGN_TMPDIR`. **Suggested fix:** Add a function-local `trap` that `rm -f`s both temps on any exit, or wrap the redact/sed block in explicit failure handling that deletes temps before re-raising.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/plan-review-loop.sh:136-174` — `_materialize_scope_anchor` creates two `mktemp` files (`stripped_tmp`, `anchor_tmp`) and only removes them on the strip-failure path or at normal completion; if `redact-secrets.sh` or the following `sed -E` pipeline fails under `set -euo pipefail`, the function aborts without an ERR/`trap` cleanup, leaving orphaned `.plan-review-scope-anchor.*` files in `$DESIGN_TMPDIR`. **Suggested fix:** Add a function-local `trap` that `rm -f`s both temps on any exit, or wrap the redact/sed block in explicit failure handling that deletes temps before re-raising.
- **Suggested revision**: Address the concern above.


### FINDING_61: **risk-integration** `scripts/compute-pr-line-counts.md:370-376` — The documented KV table lists only `LINES_STATUS=skipped` with `REASON=no-pr`, but the implementation also emits `REASON=invalid-pr-number` and `REASON=invalid-repo` (`scripts/compute-pr-line-counts.sh:38-48`). Downstream operators and harness authors reading the contract doc will mis-classify those paths. **Suggested fix:** Extend the KV table (and the “Failures are non-fatal” prose) to enumerate all `skipped` / `unavailable` reason tokens the helper actually emits.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - **risk-integration** `scripts/compute-pr-line-counts.md:370-376` — The documented KV table lists only `LINES_STATUS=skipped` with `REASON=no-pr`, but the implementation also emits `REASON=invalid-pr-number` and `REASON=invalid-repo` (`scripts/compute-pr-line-counts.sh:38-48`). Downstream operators and harness authors reading the contract doc will mis-classify those paths. **Suggested fix:** Extend the KV table (and the “Failures are non-fatal” prose) to enumerate all `skipped` / `unavailable` reason tokens the helper actually emits.
- **Suggested revision**: Address the concern above.


### FINDING_62: **risk-integration** `skills/implement/scripts/write-final-report.sh:115-126` — Every `write-final-report.sh` invocation with a non-zero `PR_NUMBER` and `REPO_UNAVAILABLE!=true` now performs a live `gh api` call (including `--comment-only` post-PR refreshes from `ship-pr.sh`), even though line counts are advisory and failures are swallowed. That adds network latency and an extra GitHub API dependency to a path that previously only rendered local artifacts. **Suggested fix:** Either document this as an accepted trade-off in `write-final-report.md`, or gate the `compute-pr-line-counts.sh` call behind a cheap local sentinel (e.g. skip when `PR_NUMBER` is placeholder/0, or cache counts in `ship-pr-state.sh` after first successful fetch) so comment-only refreshes do not re-hit the API.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - **risk-integration** `skills/implement/scripts/write-final-report.sh:115-126` — Every `write-final-report.sh` invocation with a non-zero `PR_NUMBER` and `REPO_UNAVAILABLE!=true` now performs a live `gh api` call (including `--comment-only` post-PR refreshes from `ship-pr.sh`), even though line counts are advisory and failures are swallowed. That adds network latency and an extra GitHub API dependency to a path that previously only rendered local artifacts. **Suggested fix:** Either document this as an accepted trade-off in `write-final-report.md`, or gate the `compute-pr-line-counts.sh` call behind a cheap local sentinel (e.g. skip when `PR_NUMBER` is placeholder/0, or cache counts in `ship-pr-state.sh` after first successful fetch) so comment-only refreshes do not re-hit the API.
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


