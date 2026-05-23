## Decision 1: Fix direction
- **Question**: Adopt Option 1 (re-prompt), Option 2 (fail-loud), or Option 3 (carry-through) from the issue body?
- **Resolution**: Hybrid — extend the existing dispatch-with-waterfall.sh waterfall (Cursor → Codex → Claude) so that semantic validation failure (not just launch failure) triggers progression to the next phase. After all 3 phases fail validation, stall with a distinct STALL_REASON. No carry-through, no inline main-agent aggregation.
- **Source**: user

## Decision 2: What counts as a 'semantic validation failure' that triggers waterfall progression
- **Question**: Should retry fire on any aggregate-validate.py non-zero exit, or only on a stricter subset?
- **Resolution**: Any aggregate-validate.py non-zero exit. The validator gets a new check: when output has zero `### FINDING_` blocks AND output text contains the substring `### FINDING_` (raw bytes anywhere), reject as `validation-failed`. Existing zero_findings_no_attest (#2563) path continues to succeed via deterministic synthesis (no regression).
- **Source**: user

## Decision 3: Where the per-phase retry loop lives
- **Question**: Should the retry loop live inside aggregate-findings.sh or as a new --post-launch-validator hook in dispatch-with-waterfall.sh?
- **Resolution**: Inside aggregate-findings.sh. The script builds a single-tool slot manifest per phase, calls dispatch-with-waterfall.sh once per phase with that manifest, validates after each, stops on first success. dispatch-with-waterfall.sh is unchanged.
- **Source**: user

## Decision 4: Terminal stall reason
- **Question**: What STALL_REASON token surfaces in /implement Step 5 when all 3 phases fail validation?
- **Resolution**: `aggregator-validation-exhausted`. The wrapper in review-implement-step5-loop.sh routes the new IRF status token to this STALL_REASON. /implement SKILL.md Step 5 stall-reason table gets a new row.
- **Source**: user

## Decision 5: Regression test fixture style
- **Question**: Synthetic minimal reproducer, byte-faithful #2638 replica, or both?
- **Resolution**: Synthetic minimal reproducer only. New AGGREGATE_STUB_MERGE_KIND values in test-aggregate-findings.sh emit short preambles like "We have FINDING_N blocks" followed by zero structural blocks. Tests assert (a) substring detection rejects degenerate output, (b) waterfall progresses through all 3 phases on consecutive validation failures, (c) STALL_REASON=aggregator-validation-exhausted emerges from review-and-fix wrapper after exhaustion.
- **Source**: user

## Decision 6: Observability for phase progression
- **Question**: How should phase progression be surfaced when the validation-retry waterfall fires?
- **Resolution**: Add `PHASES_ATTEMPTED=<comma-list>` (e.g. `PHASES_ATTEMPTED=cursor,codex,claude`) to aggregate-findings.sh stdout. Existing per-phase output files (`aggregator-output.txt.phase1` / `.phase2` / `.phase3`) continue to land in REVIEW_TMPDIR for investigation; the new KV is a one-glance summary.
- **Source**: user

## Hard constraints (in-scope, must not break)
- Existing test cases at test-aggregate-findings.sh (lines 459 `zero_findings_no_attest`, 497 `zero_findings_impure_attest`, 513 `zero_findings_nonconforming_heading`, 532 `zero_findings_nospace_pseudo_heading`, 550 `zero_findings_prose_finding_ids`, 568 `empty_merge_existing_token_passthrough`, etc.) must continue to pass.
- `LARCH_AGGREGATOR_DISABLED=1` must continue to no-op (pass-through, `REASON=disabled`).
- Existing stdout contract: `AGGREGATED`, `INPUT_COUNT`, `MERGED_COUNT`, `REASON`, optional `FAILURE_LOG` continue to be emitted exactly as before. `PHASES_ATTEMPTED` is additive.
- collect-findings.sh / collect-agent-results.sh contract: unchanged (reviewer-output validation surface is not modified).
- /implement SKILL.md Step 5 stall-reason table receives ONE new row for `aggregator-validation-exhausted`; the wrapper's `*)` fallthrough remains intact for unknown post_round_status values.

## Non-goals (out-of-scope)
- No re-prompt-with-stricter-instructions retry (Option 1 in the issue body) — phase progression just swaps the model, not the prompt.
- No carry-through of raw input findings (Option 3 in the issue body) — stall is preferred on full waterfall exhaustion.
- No main-agent inline aggregation fallback (no new `main-agent-aggregation-required` IRF status).
- No change to reviewer-output validation in collect-findings.sh.
- No refactor of dispatch-with-waterfall.sh — it stays unchanged.
- No new escape-hatch env var (e.g. `LARCH_AGGREGATOR_NO_WATERFALL_RETRY`) — YAGNI.

6 decisions resolved.
