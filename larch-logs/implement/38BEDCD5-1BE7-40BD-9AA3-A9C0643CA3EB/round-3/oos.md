### FINDING_16: security: scripts/scout-dynamic-archetypes.sh:541-572
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Scout prompt_body validation does not cover new plan_review_scope_anchor or feature delimiter tags introduced by scope anchoring. Malicious issue text can steer scout JSON to emit unescaped delimiter-shaped prompt_body that passes jq validation; dispatch-plan-review-panel.sh cats it into the trusted dynamic-reviewer preamble before the hardened scope-anchor block. Extend scout unsafe-tag checks for plan_review_scope_anchor and feature tags; escape or wrap prompt_body in write_dynamic_prompt.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **architecture** `skills/design/scripts/assess-plan-round.sh:89-90` — Step 3.6 assessor still prefers `${IMPLEMENT_TMPDIR}/feature-description.txt` over the design feature file. That is outside this branch’s plan-review loop wiring, but it is the same stale-session class of bug this issue fixes for Step 3; the sibling assessor-on-SIMPLE work should align it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_32: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-scope-anchor-flow-output.txt
- **Concern**: - **correctness** `scripts/plan-block-strip-body.sh:70` — Strip helper can emit `MALFORMED=end-before-start`, which is not part of the shared `plan-block-read.sh` malformed vocabulary documented for scope-anchor fail-closed behavior. Low impact today because materialization treats any non-zero strip rc as fatal, but the token sets are slightly divergent. Overall, the main happy path is wired well: `plan-review-loop.sh` stages the anchor once, threads it to scout (`plan-review-scope-anchor.scout.txt`), panel (`--feature-file`), voters (`--scope-anchor-file`), and revise; `dispatch-plan-voters.sh` fails hard on unreadable anchors; and `test-plan-review-loop.sh` has solid brainstorm-vs-binding separation coverage. The remaining risks are mostly fail-open handoffs on the MainAgent / validation edges rather than missing argv forwarding on the primary path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_36: [OUT_OF_SCOPE] `scripts/check-scope-reduction-marker.sh:33-55` — Leading-only detection, single severity-prefix strip, fenced/inline false negatives, and OOS heading exclusion match the plan and are covered by `test-check-scope-reduction-marker.sh` and `test-lib-vote-tally.sh`.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - `scripts/check-scope-reduction-marker.sh:33-55` — Leading-only detection, single severity-prefix strip, fenced/inline false negatives, and OOS heading exclusion match the plan and are covered by `test-check-scope-reduction-marker.sh` and `test-lib-vote-tally.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] `skills/review/scripts/aggregate-findings.sh:155-188` — Plan-mode split withholds tagged blocks from the LLM prompt and `test-aggregate-findings.sh` covers tagged preservation + renumber; `insufficient-input` correctly leaves the original `findings-in-scope.md` untouched when fewer than two untagged blocks remain (so tagged-only ballots are not dropped).
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - `skills/review/scripts/aggregate-findings.sh:155-188` — Plan-mode split withholds tagged blocks from the LLM prompt and `test-aggregate-findings.sh` covers tagged preservation + renumber; `insufficient-input` correctly leaves the original `findings-in-scope.md` untouched when fewer than two untagged blocks remain (so tagged-only ballots are not dropped).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] `scripts/lib-vote-tally.sh:76-80` — `is_scope_reduction_block` is not invoked from `tally-plan-review.sh`; that matches the plan’s “no protected tally override / unchanged thresholds” decision. Tally behavior for tagged findings is the same as for untagged findings.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - `scripts/lib-vote-tally.sh:76-80` — `is_scope_reduction_block` is not invoked from `tally-plan-review.sh`; that matches the plan’s “no protected tally override / unchanged thresholds” decision. Tally behavior for tagged findings is the same as for untagged findings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_39: [OUT_OF_SCOPE] `skills/design/scripts/test-plan-review-scope-anchor.sh:51-53` — The OOS block uses a no-op `if is_scope_reduction_block; then : fi` instead of asserting exit 1; `test-check-scope-reduction-marker.sh` already enforces OOS exclusion, so this is weak documentation-only coverage rather than a production defect.
- **Reviewer**: dyn-scope-marker-output.txt
- **Concern**: - `skills/design/scripts/test-plan-review-scope-anchor.sh:51-53` — The OOS block uses a no-op `if is_scope_reduction_block; then : fi` instead of asserting exit 1; `test-check-scope-reduction-marker.sh` already enforces OOS exclusion, so this is weak documentation-only coverage rather than a production defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_44: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-collect-findings.sh` — The plan called for a collect → `check-scope-reduction-marker.sh` regression (`TSV what: [SCOPE-REDUCTION] …` → Concern `[important] [SCOPE-REDUCTION] …`); no such case appears in the branch. Collect folding is on the critical path before aggregation; absence of this test is a coverage gap, not a verified production defect in the collect script itself.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-aggregation-parity-output.txt
- **Concern**: - **architecture** `skills/review/scripts/aggregate-findings.md:55-57` — Docs state combined output is validated for “tagged-marker preservation and sequentially renumbered” outcomes; they overstate reviewer-coverage validation on the combined stream (see in-scope finding above). Documentation drift only; behavior is defined by the script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_49: [OUT_OF_SCOPE] Voter and static reviewer paths are materially improved: shared `emit_untrusted_file_block` pattern, untrusted-evidence framing, delimiter-breakout tests in `scripts/test-render-voter-prompt.sh` and `skills/design/scripts/test-plan-review-prompt.sh`, and `--scope-anchor-file` gated to `--verification-context plan` (`skills/shared/scripts/render-voter-prompt.sh:87-90`).
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - Voter and static reviewer paths are materially improved: shared `emit_untrusted_file_block` pattern, untrusted-evidence framing, delimiter-breakout tests in `scripts/test-render-voter-prompt.sh` and `skills/design/scripts/test-plan-review-prompt.sh`, and `--scope-anchor-file` gated to `--verification-context plan` (`skills/shared/scripts/render-voter-prompt.sh:87-90`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_50: [OUT_OF_SCOPE] Scout reads a pre-escaped `plan-review-scope-anchor.scout.txt` via file path (`skills/design/scripts/plan-review-loop.sh:164-169,899`) rather than inlining raw issue text into the scout launcher prompt — a sensible defense for the description-file path.
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - Scout reads a pre-escaped `plan-review-scope-anchor.scout.txt` via file path (`skills/design/scripts/plan-review-loop.sh:164-169,899`) rather than inlining raw issue text into the scout launcher prompt — a sensible defense for the description-file path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_51: [OUT_OF_SCOPE] `SCOPE_ANCHOR_FILE` handoff hardening (symlink rejection, `DESIGN_TMPDIR` confinement, CR/LF path rejection) in `skills/design/scripts/run-step3-review.sh:148-174` and `skills/design/scripts/lib-phase-driver.sh:101-109` is sound for result-env injection.
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - `SCOPE_ANCHOR_FILE` handoff hardening (symlink rejection, `DESIGN_TMPDIR` confinement, CR/LF path rejection) in `skills/design/scripts/run-step3-review.sh:148-174` and `skills/design/scripts/lib-phase-driver.sh:101-109` is sound for result-env injection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_52: [OUT_OF_SCOPE] `redact_untrusted_stream` / `emit_untrusted_file_block` are duplicated across three renderers; that predates this branch but increases the risk that a future security fix lands in one path only (maintainability, not an active defect here).
- **Reviewer**: dyn-prompt-boundary-output.txt
- **Concern**: - `redact_untrusted_stream` / `emit_untrusted_file_block` are duplicated across three renderers; that predates this branch but increases the risk that a future security fix lands in one path only (maintainability, not an active defect here).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_55: [OUT_OF_SCOPE] New helpers (`plan-block-strip-body.sh`, `compute-pr-line-counts.sh`, `render-voter-prompt.sh` scope-anchor path) use Bash 3.2–safe constructs: `mktemp`, `[[ =~ ]]`, `sed -E`, BSD `grep -c … || …` fallbacks, quoted arrays (`"${_render_args[@]}"`), and `set +e` around `gh`/helper calls where needed. No `mapfile`/`readarray`/`declare -A`/`${var,,}`/`wait -n` were introduced in the production diff.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - New helpers (`plan-block-strip-body.sh`, `compute-pr-line-counts.sh`, `render-voter-prompt.sh` scope-anchor path) use Bash 3.2–safe constructs: `mktemp`, `[[ =~ ]]`, `sed -E`, BSD `grep -c … || …` fallbacks, quoted arrays (`"${_render_args[@]}"`), and `set +e` around `gh`/helper calls where needed. No `mapfile`/`readarray`/`declare -A`/`${var,,}`/`wait -n` were introduced in the production diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_56: [OUT_OF_SCOPE] `check-scope-reduction-marker.sh` is Python-only (duplicated stdin/`--file` blocks); that matches existing plan-review Python usage but deepens the runtime Python dependency—consistent with repo norms, not a new Bash 3.2 regression.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - `check-scope-reduction-marker.sh` is Python-only (duplicated stdin/`--file` blocks); that matches existing plan-review Python usage but deepens the runtime Python dependency—consistent with repo norms, not a new Bash 3.2 regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_57: [OUT_OF_SCOPE] `count_finding_blocks` + `[[ "$AGGREGATE_INPUT_COUNT" -lt 2 ]]` in `aggregate-findings.sh` can emit “integer expression expected” if the helper ever returns an empty string (pre-existing fragility, amplified by the new plan-mode branch); in normal operation BSD `grep -c` still prints `0` before exiting 1.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - `count_finding_blocks` + `[[ "$AGGREGATE_INPUT_COUNT" -lt 2 ]]` in `aggregate-findings.sh` can emit “integer expression expected” if the helper ever returns an empty string (pre-existing fragility, amplified by the new plan-mode branch); in normal operation BSD `grep -c` still prints `0` before exiting 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_59: **risk-integration** `scripts/test-render-run-summary-callsites.sh:8-17` — The callsite harness pins `--claude-input-tokens` / `--cost-unavailable` and `--emergency-requested` for every `render-run-summary.sh` invocation in `write-final-report.sh`, but it does not pin the new `--code-added` / `--code-deleted` / `--logs-added` / `--logs-deleted` forwarding added in `write-final-report.sh:480-493`. A future edit could drop `line_args` from `run_body_render` without failing `make test-render-run-summary-callsites`. **Suggested fix:** Extend the callsite test to assert that when `LINES_DATA_OK=true` wiring exists, each renderer invocation either passes all four line-count flags or omits them consistently (mirror the existing per-invocation flag-count guard).
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - **risk-integration** `scripts/test-render-run-summary-callsites.sh:8-17` — The callsite harness pins `--claude-input-tokens` / `--cost-unavailable` and `--emergency-requested` for every `render-run-summary.sh` invocation in `write-final-report.sh`, but it does not pin the new `--code-added` / `--code-deleted` / `--logs-added` / `--logs-deleted` forwarding added in `write-final-report.sh:480-493`. A future edit could drop `line_args` from `run_body_render` without failing `make test-render-run-summary-callsites`. **Suggested fix:** Extend the callsite test to assert that when `LINES_DATA_OK=true` wiring exists, each renderer invocation either passes all four line-count flags or omits them consistently (mirror the existing per-invocation flag-count guard).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_63: [OUT_OF_SCOPE] The branch bundles two largely independent features: scope-anchor plan review (`bd196ee5a`) and PR line-count reporting (`88fb73af4` / #3506). The reporting-metrics surface is not part of the attached #3506 scope-anchor design plan; reviewers should treat it as a separate behavioral change with its own acceptance criteria.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - The branch bundles two largely independent features: scope-anchor plan review (`bd196ee5a`) and PR line-count reporting (`88fb73af4` / #3506). The reporting-metrics surface is not part of the attached #3506 scope-anchor design plan; reviewers should treat it as a separate behavioral change with its own acceptance criteria.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_64: [OUT_OF_SCOPE] `scripts/render-run-summary.sh:216-222` and `skills/implement/scripts/write-final-report.sh:127-147` now agree on all-or-nothing integer validation for the four line-count flags; `scripts/test-render-run-summary.sh:257-280` covers partial-flag `N/A` rendering. The earlier partial-flag malformed-bullet concern appears resolved on this branch.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - `scripts/render-run-summary.sh:216-222` and `skills/implement/scripts/write-final-report.sh:127-147` now agree on all-or-nothing integer validation for the four line-count flags; `scripts/test-render-run-summary.sh:257-280` covers partial-flag `N/A` rendering. The earlier partial-flag malformed-bullet concern appears resolved on this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_65: [OUT_OF_SCOPE] `skills/design/scripts/render-final-summary.sh:376-397` correctly omits line-count flags and relies on `--skill design` suppression, so `/design` summaries remain byte-compatible with the prior contract (`scripts/test-render-run-summary.sh:391`).
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - `skills/design/scripts/render-final-summary.sh:376-397` correctly omits line-count flags and relies on `--skill design` suppression, so `/design` summaries remain byte-compatible with the prior contract (`scripts/test-render-run-summary.sh:391`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_66: [OUT_OF_SCOPE] Makefile / agent-lint registration for `test-compute-pr-line-counts` (shard 4) and the offline harnesses for `compute-pr-line-counts`, `render-run-summary`, and `write-final-report` are present and internally consistent; no missing target was found for the new helper.
- **Reviewer**: dyn-reporting-metrics-output.txt
- **Concern**: - Makefile / agent-lint registration for `test-compute-pr-line-counts` (shard 4) and the offline harnesses for `compute-pr-line-counts`, `render-run-summary`, and `write-final-report` are present and internally consistent; no missing target was found for the new helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

