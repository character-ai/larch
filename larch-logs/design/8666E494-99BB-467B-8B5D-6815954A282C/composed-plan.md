# Implementation Plan — Issue #2782

Reject aggregator outputs that produce zero merged FINDING blocks when the input had one or more FINDING blocks, regardless of whether the empty-merge attestation token is present. This catches the Cursor CreatePlan turn-end failure mode reported in issue #2782 AND any silent-empty variants, by tightening the inlined validator inside `skills/review/scripts/aggregate-findings.sh`.

## Approach

The bug report cites a non-existent `scripts/aggregator-validate.py`. The actual validator is a heredoc-generated Python program inlined into `skills/review/scripts/aggregate-findings.sh` and materialized at runtime as `$REVIEW_TMPDIR/aggregate-validate.py` (lines 173-687). Its `main()` function currently has an escape hatch: when output has zero merged FINDING blocks AND an empty-merge attestation line is present, `main()` returns `0` (success), even if the input had N>0 FINDING blocks. That escape hatch is what allowed the bug case to slip through with a 244-byte preamble-plus-attestation output from 57 input findings.

The fix replaces the escape-hatch `return 0` with an explicit rejection. Other branches of `main()` are unchanged. The companion `_attempt_attestation_repair` function is left as-is (it still synthesizes attestation when missing, but the synthesized output is now rejected by `main()` for the input-was-nonempty case — semantic dead code but harmless).

On rejection, the existing pipeline in `aggregate-findings.sh` already takes the desired graceful-degradation path: `mv -f "$merged_tmp" "$FINDINGS_FILE"` at line 753 only fires on validator success, so `findings-in-scope.md` remains the pre-aggregator Python-deduped raw findings. Wrapper stdout reports `AGGREGATED=false REASON=validation-failed`. `plan-review-loop.sh` then builds `ballot.txt` from the raw deduped findings, which voters can score correctly. No changes to `plan-review-loop.sh` are required (Layer 2 from the bug report is redundant).

**Outer waterfall progression**. The new validation-failed reason token `empty_merge_from_nonempty_input` must also progress the outer Cursor → Codex → Claude aggregation waterfall, matching the existing behavior for `preamble_finding_substring` at `aggregate-findings.sh` line 717. This directly addresses the bug report's observation that Codex succeeded on the same input where Cursor failed: with progression, Cursor's bogus empty-merge advances to Codex (and then Claude) rather than terminating immediately at `REASON=validation-failed`. Worst case (all three externals produce empty merges from non-empty input) is bounded by the existing `validation-exhausted` terminal path — `findings-in-scope.md` remains the raw deduped findings via the same graceful degradation, and operators see one consolidated execution-issues entry. The wrapper edit extends the existing grep clause to match either token rather than only `preamble_finding_substring`.

The aggregator agent prompt at `agents/orchestrator-aggregator.md` is out of scope — the validator is the deterministic backstop; prompt-side wording changes are a separate concern.

## Files to modify/create

### UPDATED: `skills/review/scripts/aggregate-findings.sh`

In the inlined Python `main()` function (heredoc block lines 173-687), replace the escape-hatch `return 0` at the bottom of the `if not blocks:` branch with a new rejection:

```python
if not blocks:
    # input_slot_set non-empty (checked above) => structured input findings exist.
    if (
        has_preamble_finding_signal(outtext)
        and not has_nonconforming_finding_heading_markers(outtext)
    ):
        print(
            "AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring",
            file=sys.stderr,
        )
        return 1
    if not has_attest_line:
        print(
            "zero merged FINDING blocks while input had findings; "
            "output must include a line whose trimmed text equals %r "
            "(machine-readable attestation; leading/trailing whitespace ignored)"
            % (EMPTY_MERGE_ATTESTATION,),
            file=sys.stderr,
        )
        return 1
    input_finding_count = len(input_blocks(intext))
    print(
        "AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input "
        "input had %d FINDING blocks; merged output has zero "
        "(attestation present is not sufficient when inputs were nonempty)"
        % (input_finding_count,),
        file=sys.stderr,
    )
    return 1
```

The new branch fires when `not blocks` AND `has_attest_line` AND `input_slot_set` (which always implies input had >=1 FINDING block, per the input_blocks/reviewer_line_slots derivation). The message format follows the existing `AGGREGATOR_VALIDATION_FAILED=<reason>` convention used by the preamble check so downstream operators can grep for it. No other branches in `main()` change. The `_attempt_attestation_repair` function and the `--repair-attestation` CLI subcommand are unchanged.

**Outer-waterfall grep clause update**. At `aggregate-findings.sh` line 717 in `merge_attempt()`, extend the existing single-token grep:

```bash
if grep -q '^AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring' "$REVIEW_TMPDIR/aggregator-validate.stderr" 2>/dev/null; then
```

to also match the new reason token (an extended regex alternation, anchored to the start of the line):

```bash
if grep -Eq '^AGGREGATOR_VALIDATION_FAILED=(preamble_finding_substring|empty_merge_from_nonempty_input)$' "$REVIEW_TMPDIR/aggregator-validate.stderr" 2>/dev/null; then
```

The `^...$` anchors avoid accidental substring matches if future reason tokens share a prefix. The `MERGE_PIPELINE_RC=1` set inside the `then` branch is unchanged — same outer-phase progression signal.

### UPDATED: `SECURITY.md`

Rewrite the two sentences in the aggregator paragraph (around line 68) that document the old "attestation as guardrail when input had findings" behavior. Replace:

> "When the model returns zero structured `### FINDING_` blocks while the input ballot still had findings, validation additionally requires a full-line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token in the raw vendor output (a guardrail, not a proof against a hostile model); that line is stripped before the rewritten ballot is persisted so downstream voting surfaces do not display it."

with:

> "When the model returns zero structured `### FINDING_` blocks while the input ballot still had findings, validation fails closed with `AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input` regardless of whether the empty-merge attestation token is present — the attestation token is no longer accepted as a guardrail in this case. The outer Cursor → Codex → Claude aggregation waterfall progresses on this rejection (same behavior as `preamble_finding_substring`) so a single external's empty-merge slip does not terminate the run; only `validation-exhausted` after all three phases fail terminally leaves `findings.md` unchanged."

Also update the closing sentence of the same paragraph (about "blocks + attestation fails closed") to mention that the broader "input had findings ⇒ output must have ≥1 block" rule also fails closed, by appending one short clause: "; likewise the new `empty_merge_from_nonempty_input` rule fails closed even when only the attestation line is present and no merged blocks exist." No other changes to `SECURITY.md`.

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

Update existing tests that asserted "zero merged FINDING blocks from non-empty input is a successful aggregation". These tests encoded the prior permissive behavior and must now assert `AGGREGATED=false REASON=validation-failed` and that `findings.md` is left unchanged (still contains the original input blocks). Add one new test that explicitly pins the bug-case behavior.

Affected existing test sections (one update each — flip the expected status from success-with-empty-merge to validation-failed-leaves-input-unchanged):

- `=== AGGREGATE_STUB_MERGE_KIND=zero_findings ===` (around line 528)
- `=== zero output without model attestation: script synthesizes token (#2563) ===` (around line 545)
- `=== zero_findings_impure_attest: drop near-token line then synthesize ===` (around line 583)
- `=== zero_findings_prose_finding_ids: FINDING_ids prose does not suppress synthesis ===` (around line 636)
- `=== empty_merge_existing_token_passthrough: model token present, no synthesis stderr ===` (around line 654)
- `=== zero output accepts whitespace-padded empty-merge attestation (#2536) ===` (around line 677)
- `=== empty_merge_negative_finding_prose: ### FINDING_ids must not trip preamble signal ===` (around line 1140)

For each, change:

```bash
grep -Fq 'AGGREGATED=true' "$TMP/out-<name>.env" || fail "..."
grep -Fq 'REASON=ok' "$TMP/out-<name>.env" || fail "..."
```

to:

```bash
grep -Fq 'AGGREGATED=false' "$TMP/out-<name>.env" || fail "..."
grep -Fq 'REASON=validation-failed' "$TMP/out-<name>.env" || fail "..."
```

Also retain the existing `cmp -s "$TMP/in3.md" "$TMP/in3-<name>.md"` assertion (already present in most of these), inverted where needed: the original `findings.md` must remain unchanged because the validator rejected the merge. Drop assertions about `MERGED_COUNT=0` or post-merge `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` absence that no longer make sense because the merge was rejected (the `MERGED_COUNT` line is not emitted on `AGGREGATED=false`). Preserve the `ATTESTATION_SYNTHESIZED=true` breadcrumb assertions where present — the repair function still fires before the validator runs, so the breadcrumb still appears on stderr; the wrapper's overall outcome is now `validation-failed` but the repair-stage breadcrumb is unaffected.

Add a new positive test at the end of the empty-merge cluster (after the existing `empty_merge_existing_token_passthrough` block, around line 695):

```bash
echo "=== zero_findings_input_nonempty rejected: input had findings, output empty + attestation => validation-failed (#2782) ==="
cp "$TMP/in3.md" "$TMP/in3-zfn.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings \
"$AGG" \
    --findings-file "$TMP/in3-zfn.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zfn.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zfn.env" || fail "#2782: aggregation must fail when input had findings and output is empty"
grep -Fq 'REASON=validation-failed' "$TMP/out-zfn.env" || fail "#2782: REASON must be validation-failed"
grep -Fq 'AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input' "$TMP/aggregator-validate.stderr" \
    || fail "#2782: validator must emit empty_merge_from_nonempty_input reason"
cmp -s "$TMP/in3.md" "$TMP/in3-zfn.md" || fail "#2782: findings.md must remain unchanged on validator rejection"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-zfn.md" | tr -d '[:space:]')" == "3" ]] \
    || fail "#2782: original 3 FINDING blocks must survive"
```

This new test is the regression pin for the exact bug report scenario.

Add a second new test that exercises the outer-waterfall progression on the new token. Drop it next to existing waterfall progression coverage (search for the `PHASES_ATTEMPTED` token in the file for the right neighborhood):

```bash
echo "=== zero_findings_input_nonempty progresses outer waterfall: Cursor empty-merge then Codex success (#2782) ==="
cp "$TMP/in3.md" "$TMP/in3-zfn-wf.md"
# Stub: first outer phase (Cursor) returns zero_findings; second outer phase (Codex) returns merge success.
write_stub_dispatch_waterfall_2782   # helper to set AGGREGATE_STUB_MERGE_KIND per phase
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
"$AGG" \
    --findings-file "$TMP/in3-zfn-wf.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zfn-wf.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-zfn-wf.env" || fail "#2782 waterfall: must succeed on phase 2"
grep -Fq 'REASON=ok' "$TMP/out-zfn-wf.env" || fail "#2782 waterfall: REASON ok after retry"
grep -Eq '^PHASES_ATTEMPTED=cursor,codex' "$TMP/out-zfn-wf.env" || fail "#2782 waterfall: must record cursor then codex"
```

If the existing test harness does not already have a per-phase stub helper (`write_stub_dispatch_waterfall_*`), inline a minimal one above this test that selects `AGGREGATE_STUB_MERGE_KIND` based on a `STUB_PHASE_COUNTER` env var (the existing preamble-progression test under `larch-logs/design/76D114D7-AB72-451E-8D0F-50E326074749/composed-plan.md` shows the established pattern; reuse it). Keep the helper local to this test if the file does not already factor it.

## Edge cases

- **Input has 0 FINDING blocks**: `main()` hits the earlier `if not input_slot_set: ... return 1` and returns before reaching the new branch. The new check only fires when the input contained at least one FINDING block. Existing zero-input behavior unchanged.
- **Output has N>0 FINDING blocks + attestation**: the existing rule at the top of `main()` (`if blocks and has_attest_line: return 1`, line 588) already rejects this. Unchanged.
- **Output has N>0 FINDING blocks, no attestation**: the existing happy path through block-level validation. Unchanged.
- **Output has 0 FINDING blocks, no attestation**: the existing `if not has_attest_line: return 1` branch still fires first. New branch never reaches it. Unchanged.
- **Output has 0 FINDING blocks + impure attestation line** (e.g., `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED junk-suffix`): caught by the existing impure-attestation rejection at the very top of `main()` (line 562). Unchanged.
- **Whitespace-padded attestation**: `drop_impure_empty_merge_attestation_lines` normalizes leading/trailing whitespace before the `has_attest_line` check, so the new branch behaves the same whether the attestation token had surrounding whitespace.

## Failure modes

1. **Behavior change rejecting previously-passing aggregator outputs**. Any pre-existing legitimate "noise-only" inputs that the aggregator deduped to zero merged blocks will now also be rejected. Early warning signal: `AGGREGATED=false REASON=validation-failed` rate in run logs after deploy; check `larch-logs/design/*/aggregator-validate.stderr` for the new `empty_merge_from_nonempty_input` reason token. Mitigation: this is the intended behavior per the design decision (decision 3 in `discussion-round1.md`). If false positives appear, the wrapper's existing graceful degradation already preserves correctness — operators see raw deduped findings in the ballot instead.

2. **Test churn surface**. The seven existing test sections that pinned the old permissive behavior must all be updated atomically with the validator change, or `bash skills/review/scripts/test-aggregate-findings.sh` fails on the next CI run. Early warning signal: pre-commit hook or `make lint` will catch test failures locally. Mitigation: include all test updates in the same commit as the validator change; do not split.

3. **Repair function becomes semantic dead code for input-nonempty case**. The `_attempt_attestation_repair` function still synthesizes attestation lines and emits `ATTESTATION_SYNTHESIZED=true` breadcrumbs, but `main()` then rejects the resulting output. Early warning signal: `ATTESTATION_SYNTHESIZED=true` followed by `AGGREGATED=false REASON=validation-failed` in the same run log. Mitigation: leave as-is per the minimal-surface-change decision (decision 1). A future cleanup commit may simplify the repair function, but it's out of scope for this issue.

## Testing strategy

- Update the seven existing test sections in `skills/review/scripts/test-aggregate-findings.sh` listed above to expect `AGGREGATED=false REASON=validation-failed`.
- Add the new `zero_findings_input_nonempty rejected` test pinning the single-phase rejection (bug-case regression).
- Add the new `zero_findings_input_nonempty progresses outer waterfall` test pinning Cursor → Codex recovery.
- Run `bash skills/review/scripts/test-aggregate-findings.sh` locally; all tests must pass.
- Run `bash scripts/relevant-checks.sh` after edits (per AGENTS.md).
- No new test fixture in `skills/design/scripts/test-plan-review-loop.sh` (per decision 4 in `discussion-round1.md`).
- Manual smoke (post-merge, optional): on a future `/design --simple` run, observe that `aggregator-validate.stderr` contains `empty_merge_from_nonempty_input` when an aggregator phase degrades, that `PHASES_ATTEMPTED` records the progression, and that `voting-tally.md` is populated from either a successful later-phase merge or (in the all-phases-degrade case) the raw deduped findings via `REASON=validation-exhausted`.


## Acceptance

- `aggregate-findings.sh` inlined Python validator (`$REVIEW_TMPDIR/aggregate-validate.py` at runtime) rejects with `AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input` when input had ≥1 FINDING block AND output has 0 FINDING blocks, regardless of whether the empty-merge attestation token is present.
- `aggregate-findings.sh` outer waterfall progresses (sets `MERGE_PIPELINE_RC=1`) on the new reason token as well as on `preamble_finding_substring` — Cursor → Codex → Claude retries on empty-merge slips.
- On terminal rejection (`REASON=validation-failed` or `validation-exhausted` after all phases), the wrappers leave `findings-in-scope.md` unchanged so plan-review-loop.sh ballots from the pre-aggregator deduped findings.
- `SECURITY.md` aggregator paragraph updated to describe the new invariant; old "attestation as guardrail" wording removed.
- The 7 existing tests in `skills/review/scripts/test-aggregate-findings.sh` that asserted "zero merged FINDING blocks from non-empty input = AGGREGATED=true REASON=ok" are flipped to assert `AGGREGATED=false REASON=validation-failed` and that the original `findings.md` is unchanged.
- New regression test `zero_findings_input_nonempty rejected` (#2782) pins the bug-case behavior.
- New regression test `zero_findings_input_nonempty progresses outer waterfall` (#2782) pins Cursor → Codex recovery via `PHASES_ATTEMPTED=cursor,codex`.
- `bash skills/review/scripts/test-aggregate-findings.sh` passes after the change.
- `bash scripts/relevant-checks.sh` passes after the change.

diff_lines: 135
