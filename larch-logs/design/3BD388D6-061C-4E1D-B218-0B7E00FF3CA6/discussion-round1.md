## Decision 1: voting-tally.env removal
- **Question**: voting-tally.env does not currently exist in the codebase (grep returns 0 hits). What does the scope item 'removal of voting-tally.env' mean?
- **Resolution**: Already done in a sibling piece — drop from this piece's scope entirely. No code change, no comment, no test in #2869.
- **Source**: user

## Decision 2: scripts/lib-voter-coverage.sh purpose
- **Question**: What should the new shared coverage helper consolidate?
- **Resolution**: Voter status counters + KV emit. Extract from dispatch-plan-voters.sh and (if duplicated) tally-plan-review.sh the logic for counting voters by status (launched/skipped/failed/fallback) and emitting the corresponding VOTER_*_STATUS / coverage KVs. Both scripts source it so per-round routing stays consistent.
- **Source**: user

## Decision 3: tally-plan-review.sh always-emit KVs
- **Question**: 'Always-emitted tally KVs' — what changes?
- **Resolution**: Emit TALLY_PLAN_REVIEW_STATUS on every exit path (status only — no new ACCEPTED_COUNT / IMPORTANT_ACCEPTED_COUNT stdout KVs; those belong to piece 5's convergence work). Today TALLY_PLAN_REVIEW_STATUS is emitted only on the two success paths (ok / main-agent-vote-required). After this change, every non-zero exit also emits a tally-error status token so plan-review-loop.sh can always parse status from stdout regardless of failure mode.
- **Source**: user

## Decision 4: Timeout caps location and value
- **Question**: Where do timeout caps apply, with what value, and any override?
- **Resolution**: Per-voter waterfall (dispatch only) — cap the per-voter external-tool timeout passed to dispatch-with-waterfall.sh from inside dispatch-plan-voters.sh. Fixed 1860 seconds (matches existing plan-review / dialectic timeout family per SKILL.md anti-pattern #5). No env override. Tally is local and fast; no cap needed there.
- **Source**: user

## Decision 5: Severity preservation
- **Question**: Where is the severity-preservation gap given the existing 21-field forensic TSV already includes v1/v2/v3 severity columns?
- **Resolution**: Confirm-no-regression invariant. There is no current gap — severity is parsed by parse-judge-vote-and-rating.sh and survives into the forensic TSV. Design's job is to affirm in the .md sidecars that any new helper or KV emission MUST preserve severity (no truncation, no whitespace collapse beyond existing tr ' \t\n' '  ' normalization). No new code path for severity counts at this layer.
- **Source**: user

## Decision 6: Default findings-classification-out path
- **Question**: tally-plan-review.sh hardcodes `$DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv` as the default for --findings-classification-out. How should the design treat that default under per-round routing?
- **Resolution**: Keep the existing round-1 default for backward compatibility (single-round callers that omit the flag still work). Document in tally-plan-review.md that multi-round callers (plan-review-loop.sh today, piece 5's loop variant tomorrow) MUST pass --findings-classification-out explicitly per round. plan-review-loop.sh already does this — no caller change required.
- **Source**: user

## Decision 7: Test scope
- **Question**: What tests accompany this design?
- **Resolution**: Extend existing harnesses only: augment scripts/test-dispatch-plan-voters.sh and skills/design/scripts/test-tally-plan-review.sh to cover (a) the new lib-voter-coverage.sh helper's outputs as observed through dispatch's stdout KVs, (b) always-emit TALLY_PLAN_REVIEW_STATUS on a forced-error path in tally, (c) the fixed 1860s timeout cap surfaced via stub probe in the dispatcher. No new dedicated test file.
- **Source**: user

## Decision 8: Per-round --design-tmpdir routing semantics
- **Question**: What concrete change does "per-round --design-tmpdir routing" require given both scripts already accept --design-tmpdir?
- **Resolution**: Both scripts already use --design-tmpdir as the output root. The actual work in this piece is (a) document in both .md sidecars that callers may pass a per-round subdirectory (e.g., `$DESIGN_TMPDIR/plan-review/round-N`) and outputs will land there, and (b) ensure no helper inside the scripts references `$DESIGN_TMPDIR` directly via a fixed path that bypasses the per-round routing (e.g., the new lib-voter-coverage.sh must read DESIGN_TMPDIR from caller context, not from environment-global location).
- **Source**: codebase
