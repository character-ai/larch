## Decision 1: Fix location
- **Question**: Bug report cites `scripts/aggregator-validate.py` but no such standalone file exists. Where should the fix live?
- **Resolution**: Extend the inlined validator (heredoc Python in `skills/review/scripts/aggregate-findings.sh` lines 173-687, materialized to `$REVIEW_TMPDIR/aggregate-validate.py`). No refactor to a standalone file.
- **Source**: user

## Decision 2: Layer 2 fallback in plan-review-loop.sh
- **Question**: Do we need explicit Layer 2 fallback / WARN emit in `skills/design/scripts/plan-review-loop.sh`?
- **Resolution**: Skip. `aggregate-findings.sh` already leaves `findings-in-scope.md` unchanged on validator failure (mv at line 753 only fires on success); the ballot naturally uses the pre-aggregator deduped raw findings via `AGGREGATED=false REASON=...`. No Layer 2 work.
- **Source**: user

## Decision 3: Reject criteria
- **Question**: When input had N>0 FINDING blocks, what output shape should the new rule reject?
- **Resolution**: Reject when output has 0 FINDING blocks, regardless of whether the empty-merge attestation token is present. Simpler invariant; catches both the empty-merge-attestation slip AND silent-empty variants.
- **Source**: user

## Decision 4: Regression-test location
- **Question**: Where should the new regression fixture live?
- **Resolution**: `skills/review/scripts/test-aggregate-findings.sh` (existing harness for the inlined validator). No new integration test in `test-plan-review-loop.sh`.
- **Source**: user

## Decision 5: Out-of-scope items
- **Question**: What is explicitly out of scope for this fix?
- **Resolution**:
  - Out of scope: refactor of the heredoc validator to standalone `scripts/aggregator-validate.py`.
  - Out of scope: changes to `plan-review-loop.sh` (no Layer 2).
  - Out of scope: any fix for the duplicate OOS_1 bug (issue #2764) — independent.
  - Out of scope: changes to the aggregator prompt (`agents/orchestrator-aggregator.md`) — the LLM-prompt-side fix is a separate concern; the validator is the deterministic backstop.
  - Out of scope: changes to `_attempt_attestation_repair` (it only synthesizes missing attestations, which is orthogonal).
- **Source**: codebase + user

## Decision 6: Hard constraints
- **Question**: What must this fix preserve?
- **Resolution**:
  - Existing legitimate empty merge case (input had 0 FINDING blocks → output has 0 FINDING blocks + attestation token) must still validate successfully. The new rule only fires when input had N≥1 FINDING blocks.
  - Existing rule "empty-merge attestation must not appear when merged FINDING blocks exist" (line 588) is unchanged.
  - Existing `_attempt_attestation_repair` behavior unchanged.
  - Existing `--repair-attestation` CLI subcommand contract unchanged.
- **Source**: codebase

5 decisions resolved (1 short-circuit decision was the Round 1 short-circuit itself).
