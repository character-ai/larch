## Plan

## Approach

Implement the severity change as one review-pipeline migration, not as separate prompt-only edits.

1. Replace live severity vocabularies with `major|minor|nit`.
   - `JudgeSeverity` becomes only `major`, `minor`, `nit`.
   - Live judge parsing rejects `blocker` and `uncertain`.
   - Reviewer structured-output validators accept `major|minor|nit`, while reviewer prompts tell agents to emit only `major` or `minor`.
   - Keep historical log readers tolerant only where needed for old committed TSVs. Do not let live vote parsing accept retired labels.

2. Make `major` the only high severity.
   - Set `HIGH_SEVERITIES={major}`.
   - Update accepted-finding +2 scoring and neutral rescue to require a strict majority of YES voters with `major`.
   - Route structured continuation (`plan_review_loop.py`) and code-review convergence (`round_runner.py`) through the shared `major` high set instead of hardcoded `blocking`/`important` markers, so accepted-`major` rounds extend, escalate, and converge correctly. Keep legacy high labels only for historical-log compatibility.
   - Remove old `blocker` wording from voter prompts, scoreboards, calibration prose, and docs.

3. Add the source cut and mechanical backstop on both review paths.
   - Update reviewer prompts and generated/pre-rendered agent bodies: emit `major` and `minor` only; never emit `nit`.
   - Change `prune-nit-findings` from "mark as OOS" to "drop before aggregation/vote".
   - Normalize missing or blank severity to `minor` before the filter (at compose time and in the shared drop helper) so only a true `nit` drops; a blank-severity row stays on the ballot as `minor`.
   - Run the drop on BOTH streams: in-scope findings before aggregation AND the separate OOS stream (or composed ballot) before voter dispatch, appending to the audit on each pass.
   - Order matters: mutate the findings file with the drop BEFORE taking the pre-aggregate snapshot, then snapshot, then aggregate, so the pre-aggregate restore path cannot resurrect dropped nits; keep the pre-ballot call as a second hard backstop.
   - Partition drops by the security classifier: write only non-security drops to the public `oos-dropped-before-vote.md`; route security-tagged drops to a local, non-allowlisted sidecar (for example `security-oos-observations.md`).
   - Wire the filter into BOTH the code-review path (`review_core_body.py`) and the design plan-review path (`plan_review_round.py`).
   - If every finding is dropped, take the existing zero-findings branch. Do not dispatch voters for an empty ballot.

4. Gate OOS filing at every sink through one shared predicate.
   - Keep existing OOS voting thresholds: 1/1, 1+/2, 2+/3.
   - Add a derived file gate: OOS is fileable only when the OOS vote result is accepted and a strict majority of YES voters rated it `major`. Expose it as one shared helper (in `voting.py`) reused by every filing sink so plan and code tallies share one rule.
   - Apply the shared predicate at every filing sink and every pool-to-sink hop: code-review tally (`review_tally.py`, including `_append_oos_pool_candidate` / `_promote_aggregate_oos_pool` / `_finalize_emit_oos_filing`), the emit-tally OOS serialize/rebuild path (`python/larch/issue/oos.py`), design OOS aggregate-pool promotion (`design_oos.py`), and design plan-review tally (`plan_review_tally.py`). No sink or pool promotion may key filing on bare `Result=accepted`.
   - Only fileable, non-security OOS enters `oos-accepted-*`, `oos-aggregate-pool.md`, `OOS_ACCEPTED_COUNT`, and GitHub filing.
   - Non-fileable OOS, including accepted-but-`minor`, remains in `oos.md` and classification TSV evidence but is not filed.

5. Hide rejected/logged OOS from final summaries; retain the audit lineage.
   - Stop appending `## Rejected OOS audit` in implement final detail.
   - Keep `round-*/oos.md`, `findings-classification.tsv`, and dropped-nit audit files for analysis tools.
   - Write the dropped-nit audit per round under the committed round subtree (`plan-review/round-N/oos-dropped-before-vote.md` on the design path) so later rounds do not overwrite earlier forensic copies.
   - Allowlist only the public `oos-dropped-before-vote.md` into the committed round-log surface (`run_log_batch.py`); the security sidecar stays local. Final-summary rendering stays suppressed. #6028's dropped-OOS surfacing applies only to non-`nit` dropped-OOS candidates.

6. Regenerate derived reviewer artifacts.
   - Edit template/source prompts first.
   - Run the repository generator so generated agents and `agents/pre-rendered/*` stay in sync.

## Files to modify/create

### UPDATED: python/larch/review/review_types.py
Change `JudgeSeverity` to `major`, `minor`, and `nit`.

### UPDATED: python/larch/review/voting.py
Update severity constants, high-severity logic, live judge parsing, neutral rescue, accepted-points weighting, and helper tests. Add a shared helper for strict-majority `major` among YES voters (the fileable predicate) so plan and code tallies and every OOS filing sink share one rule.

### UPDATED: python/larch/review/_voting_calibration.py
Update current severity buckets and scoreboard columns. Preserve legacy TSV readability if needed by mapping old `blocker` to `major` and treating old `uncertain` as missing in analysis-only paths.

### UPDATED: python/larch/review/review_tally.py
Apply the OOS file gate in code-review tally. Keep all OOS rows in `oos.md`, but write only fileable accepted OOS (accepted AND strict-majority-`major`) to accepted sinks and aggregate pool. Gate the pool-to-sink hops too — `_append_oos_pool_candidate`, `_promote_aggregate_oos_pool`, and emit-time promotion in `_finalize_emit_oos_filing` — on the shared fileable predicate (or only promote rows already in the gated accepted sink), so accepted-`minor` pool blocks cannot be re-promoted. Update scoreboard/count semantics where they currently assume every accepted OOS is filed.

### UPDATED: python/larch/issue/oos.py
The emit-tally OOS serialize/rebuild path keys on `Result=accepted`, so accepted-but-`minor` OOS can re-enter the accepted sink and be filed; and `_iter_finding_blocks` only splits `### FINDING_` headers, so canonical `### OOS_` blocks in `oos.md` are missed. Split block iteration on both `FINDING_` and `OOS_` headers (matching `_non_security_oos_count`), and apply the shared strict-majority-`major` fileable predicate during serialize/rebuild (or stop rebuilding from full `oos.md` once tally writes the gated sink); align emit-tally rebuild checks with fileable counts only.

### UPDATED: python/larch/review/plan_review_tally.py
Apply the same shared fileable predicate to design plan review. Ensure `oos-accepted-design.md` contains only accepted plus strict-majority-`major` OOS.

### UPDATED: python/larch/design/design_oos.py
Step 5b aggregate-pool promotion still keys on retired body severities (`_AGGREGATE_HIGH_SEVERITIES = {blocking, important}` and a `latent` threshold), so accepted-`major` items can stall and accepted-`minor` items can still be promoted/filed. Repoint aggregate severities to `major|minor|nit`, drop the `latent`-threshold promotion, and gate promotion on the shared fileable predicate: only promote pool rows already marked fileable by tally, filing solely from the gated `oos-accepted-design.md` sink.

### UPDATED: python/larch/review/review_aggregate.py
Change structured severity regexes and `prune-nit-findings` behavior. Drop `nit` blocks from the active findings file and append them to `oos-dropped-before-vote.md` instead of rerouting them to OOS. Recognize the pre-aggregate `[nit]` block shape so nit rows are caught before active findings are written. Extend the shared drop helper with an explicit audit path (round directory) and normalize blank severity to `minor` before dropping; partition security-tagged drops to a local sidecar and write only non-security drops to the public audit.

### UPDATED: agents/orchestrator-aggregator.md
The aggregator prompt still tells the aggregator to merge the old `blocking/important/latent/nit` vocabulary and order. Change the severity schema and merge rule to `major > minor > nit` (no `nit` emission, no `latent`), matching the `review_aggregate.py` validator.

### UPDATED: python/larch/review/review_core_body.py
Run the nit filter before aggregation and keep the pre-ballot backstop on the code-review path. Update diagnostics from "marked as [OUT_OF_SCOPE]" to "dropped before vote".

### UPDATED: python/larch/review/plan_review_round.py
The design plan-review path never runs the nit-drop, so the emit-cut does not apply on `/design`. Change `_compose_finding_block` to default blank severity to `minor` (not `nit`) so missing-severity rows stay on the ballot. After collection, mutate the in-scope findings with the drop before the pre-aggregate snapshot (then snapshot, then aggregate), and run the same drop on the separate OOS stream (or composed ballot) before voter dispatch; append per-round drops under `plan-review/round-N/oos-dropped-before-vote.md`. Keep a pre-voter-dispatch backstop mirroring `review_core_body.py`, and take the existing zero-findings branch when only dropped rows remain (do not dispatch voters for an empty ballot).

### UPDATED: python/larch/review/plan_review_gate_b.py
Repoint Gate B structured severities to the unified set. Map `major` to high, `minor` to medium, and `nit` to low.

### UPDATED: python/larch/review/plan_review_loop.py
Structured continuation logic still keys high/high_new off `blocking`/`important`, so accepted-`major` findings may fail to extend or escalate. Import the shared high-severity set (`major` only) and replace the hardcoded `blocking|important` sets in continuation logic.

### UPDATED: python/larch/review/round_runner.py
The code-review convergence helper still looks for `Important`/`Blocking` markers, so rounds with accepted-`major` findings can converge too early. Recognize `major` as high in the convergence helper (rename or generalize it), retaining legacy high labels only for historical compatibility.

### UPDATED: python/larch/research/research_eval.py
Change reviewer structured-output allowed severities to `major|minor|nit`. Enforce the validator backstop for any retired labels.

### UPDATED: python/larch/rendering/rendering.py
Update voter prompt severity grammar and rubric. Update specialist prompt inserts, competition notice, OOS proposal language, and calibration feedback text.

### UPDATED: python/larch/report/review_phase_detail.py
Stop appending `render_rejected_oos_audit_section()` from implement review detail. Leave helper removal or deprecation to the implementer, but no final report should render the section.

### UPDATED: python/larch/report/run_log_batch.py
Allowlist only the public `oos-dropped-before-vote.md` as a committed round artifact (code-review round path and the design plan-review round inclusion path) so the dropped-nit audit trail survives temp cleanup; the local security sidecar is not allowlisted. Final-summary rendering stays suppressed per Approach step 5.

### UPDATED: docs/run-logs.md
Document the new OOS file gate, the revived `oos-dropped-before-vote.md` round-log lineage (now committed per round, not rendered), the security-drop sidecar exclusion, and the final-summary omission of rejected/logged OOS. Note #6028 surfacing applies only to non-`nit` dropped-OOS.

### UPDATED: skills/shared/reviewer-templates.md
Change reviewer severity instructions and JSON/TSV schemas to `major|minor|nit`, with reviewer emission limited to `major|minor`. Remove `blocking`, `important`, `latent`, and `uncertain` where they describe current output.

### UPDATED: skills/shared/review-acceptance-rubric.md
Update severity-floor and neutral-rescue prose to the new labels.

### UPDATED: skills/shared/oos-acceptance-rubric.md
Add the OOS filing gate: threshold acceptance plus strict-majority YES `major`.

### UPDATED: skills/shared/voting-protocol.md
Update vote grammar, neutral rescue, OOS filing semantics, scoring prose, and severity scoreboard examples.

### UPDATED: skills/design/references/plan-review.md
Update plan-review severity grammar, artifact interpretation, and OOS filing semantics.

### UPDATED: agents/code-reviewer.md
Regenerate or update the generated reviewer body from the shared template. The remaining `agents/reviewer-*.md` and `agents/pre-rendered/*` entries below follow the same regenerate-from-template rule.

### UPDATED: agents/reviewer-plan-fidelity.md

### UPDATED: agents/reviewer-code-robustness.md

### UPDATED: agents/reviewer-security-structure-tests.md

### UPDATED: agents/reviewer-correctness.md

### UPDATED: agents/reviewer-edge-cases.md

### UPDATED: agents/reviewer-security.md

### UPDATED: agents/reviewer-structure.md

### UPDATED: agents/reviewer-testing.md

### UPDATED: agents/pre-rendered/reviewer-code-robustness-body.txt

### UPDATED: agents/pre-rendered/reviewer-correctness-body.txt

### UPDATED: agents/pre-rendered/reviewer-edge-cases-body.txt

### UPDATED: agents/pre-rendered/reviewer-plan-fidelity-body.txt

### UPDATED: agents/pre-rendered/reviewer-security-body.txt

### UPDATED: agents/pre-rendered/reviewer-security-structure-tests-body.txt

### UPDATED: agents/pre-rendered/reviewer-structure-body.txt

### UPDATED: agents/pre-rendered/reviewer-testing-body.txt

### UPDATED: python/tests/review/test_voting.py
Update severity enum, live parsing, high-severity scoring, neutral rescue, and calibration expectations. Cover the shared strict-majority-`major` fileable helper.

### UPDATED: python/tests/review/test_review_tally.py
Add OOS file-gate coverage for accepted-major, accepted-minor, neutral-major, and rejected cases, including accepted-`minor` pool content that must not be promoted into the filing sink.

### UPDATED: python/tests/issue/test_oos.py
Cover the emit-tally serialize/rebuild path with `OOS_`-headed `oos.md` input: accepted-`minor` OOS must not re-enter the accepted sink; only strict-majority-`major` accepted OOS serializes.

### UPDATED: python/tests/review/test_plan_review.py
Add design plan-review coverage: OOS file gate, the pre-aggregate/pre-ballot nit-drop with per-round `oos-dropped-before-vote.md` audit, the drop applied to the OOS stream, a missing-severity row staying on the ballot as `minor`, and the all-dropped zero-ballot branch.

### UPDATED: python/tests/design/test_design_oos.py
Cover accepted-`minor` aggregate-pool blocks staying out of `oos-accepted-design.md`, and accepted-`major` pool blocks promoting under the unified severities.

### UPDATED: python/tests/review/test_review_pipeline.py
Replace old "OOS stays on ballot" assumptions only for `nit`. Add dropped-nit audit and zero-ballot coverage.

### UPDATED: python/tests/review/test_review_aggregate.py
Cover `prune-nit-findings` dropping, audit writing, security-drop partitioning, no-nit no-op, all-nit output, and the aggregator prompt's `major > minor > nit` merge expectations.

### UPDATED: python/tests/review/test_review_and_fix.py
Update the convergence-helper regression test so accepted-`major` findings are recognized as high (round not marked converged too early).

### UPDATED: python/tests/report/test_run_logs.py
Flip the retired-artifact expectation so the public `oos-dropped-before-vote.md` is committed as a round artifact while the security sidecar stays excluded.

### UPDATED: python/tests/report/test_review_phase_detail.py
Update tests so implement detail no longer includes `## Rejected OOS audit`.

### UPDATED: python/tests/rendering/test_rendering.py
Update rendered voter/specialist prompt expectations and calibration text.

### UPDATED: skills/design/scripts/test-findings-classification.sh
Update severity fixture literals and parser expectations.

### UPDATED: skills/design/scripts/test-step3-review-cap.sh
Update severity fixture literals that assert current prompt or Gate B behavior.

### MAY_UPDATE: skills/fluff-analysis/scripts/fluff-analysis.py
Only update if tests or manual inspection show current analysis collapses new `major|minor|nit` back into old `important|latent|nit` buckets in user-facing output.

### MAY_UPDATE: skills/fluff-analysis/scripts/test-fluff-analysis.sh
Update only if `fluff-analysis.py` output buckets change.

### MAY_UPDATE: skills/voter-calibration/scripts/voter-calibration.md
Update only if voter severity scoreboard columns or high-rate prose change.

### MAY_UPDATE: skills/voter-calibration/scripts/test-voter-calibration.sh
Update only if calibration rendering changes.

## Edge cases

- A structured row with blank or missing severity composes as `minor` and stays on the ballot; only an explicit `nit` is dropped.
- A reviewer emits `nit`: the row is dropped before the aggregator and before voting, on both the code-review and design plan-review paths.
- Aggregator emits or preserves `nit`: the pre-ballot backstop drops it.
- A security-tagged `nit` drop is routed to the local security sidecar, never the public `oos-dropped-before-vote.md` (which is committed).
- Later review rounds keep their own `plan-review/round-N/oos-dropped-before-vote.md`; earlier forensic copies are not overwritten.
- All findings are dropped: return the existing zero-findings path and do not launch voters (both paths).
- OOS accepted by threshold but YES severities are all `minor`: log it, but do not file it. Every filing sink and pool hop applies the same predicate, so no path refiles it.
- One-judge OOS accepted with `major`: file it, because 1/1 is a strict majority.
- Two-judge OOS accepted with one YES `major`: file it, because one YES voter exists and 1/1 YES voters is a strict majority.
- Three-judge OOS accepted with YES severities `major, minor`: do not file, because `major` is not a strict majority of YES voters.
- Security OOS remains excluded from public filing regardless of severity.
- Historical run logs may contain old labels. Analysis tools should not crash on them.

## Failure modes

- Prompt/code drift can make reviewers emit retired labels that the parser drops. Regenerate and run prompt invariant tests.
- Treating accepted-but-minor OOS as filed can regress the token-saving goal. Keep every accepted sink and every pool-to-sink hop tied to the one shared fileable predicate; no path may key on bare `Result=accepted`.
- Applying the nit-drop on only one review path or only the in-scope stream silently leaves OOS uncut. Wire the filter into both `review_core_body.py` and `plan_review_round.py`, and run it on the OOS stream too.
- Snapshotting before the nit-drop lets the pre-aggregate restore resurrect dropped nits. Drop first, then snapshot.
- Writing security-tagged drops into the public audit leaks them into committed logs. Partition by the security classifier before writing, and allowlist only the public file.
- Dropping `nit` without a committed per-round audit can regress the required lineage. Write `plan-review/round-N/oos-dropped-before-vote.md` and allowlist it in `run_log_batch.py`.
- Updating live severity parsing without updating calibration, continuation, and convergence readers can break old run-log analysis or mis-converge rounds. Repoint `plan_review_loop.py` and `round_runner.py` to the shared `major` high set.
- Removing the final report section must not delete source artifacts. Keep `round-*/oos.md` and classification TSV intact.

## Testing strategy

Run focused tests first:

- `python -m pytest python/tests/review/test_voting.py`
- `python -m pytest python/tests/review/test_review_tally.py`
- `python -m pytest python/tests/issue/test_oos.py`
- `python -m pytest python/tests/review/test_plan_review.py`
- `python -m pytest python/tests/design/test_design_oos.py`
- `python -m pytest python/tests/review/test_review_pipeline.py`
- `python -m pytest python/tests/review/test_review_aggregate.py`
- `python -m pytest python/tests/review/test_review_and_fix.py`
- `python -m pytest python/tests/report/test_run_logs.py`
- `python -m pytest python/tests/report/test_review_phase_detail.py`
- `python -m pytest python/tests/rendering/test_rendering.py`

Run affected harnesses:

- `bash skills/design/scripts/test-findings-classification.sh`
- `bash skills/design/scripts/test-step3-review-cap.sh`
- `python3 python/cli.py generate check`

Then run relevant checks for the changed files:

- `python3 python/cli.py checks run-relevant`

## Acceptance

Run focused tests first:

- `python -m pytest python/tests/review/test_voting.py`
- `python -m pytest python/tests/review/test_review_tally.py`
- `python -m pytest python/tests/issue/test_oos.py`
- `python -m pytest python/tests/review/test_plan_review.py`
- `python -m pytest python/tests/design/test_design_oos.py`
- `python -m pytest python/tests/review/test_review_pipeline.py`
- `python -m pytest python/tests/review/test_review_aggregate.py`
- `python -m pytest python/tests/review/test_review_and_fix.py`
- `python -m pytest python/tests/report/test_run_logs.py`
- `python -m pytest python/tests/report/test_review_phase_detail.py`
- `python -m pytest python/tests/rendering/test_rendering.py`

Run affected harnesses:

- `bash skills/design/scripts/test-findings-classification.sh`
- `bash skills/design/scripts/test-step3-review-cap.sh`
- `python3 python/cli.py generate check`

Then run relevant checks for the changed files:

- `python3 python/cli.py checks run-relevant`

review_status: complete
rounds_completed: 2
difficulty: HARD
mechanical_churn: true
diff_lines: 2000
