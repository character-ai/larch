## Plan

# Plan — Clean up `_attempt_attestation_repair` (issue #2787)

## Approach

Delete the empty-merge attestation **synthesis** path (Option 2 in the OOS body). The synthesis was a recovery mechanism that appended `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` to vendor output when the model omitted it on the empty-merge path. After the recent validator change (issue #2782), the validator unconditionally rejects empty-merge output when input had findings (`AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input`) — so the synthesis fires, emits a misleading `ATTESTATION_SYNTHESIZED=true` breadcrumb, and the validator then rejects anyway. The zero-input branch (`INPUT_COUNT < 2`) is short-circuited at the top of the script before the aggregator pipeline runs, so the synthesis never had a real customer.

The cleanup removes three coupled surfaces:

1. The Python `_attempt_attestation_repair` function, its CLI entry `repair_attestation_main`, and the `--repair-attestation` argv dispatch — all inside the embedded heredoc in `aggregate-findings.sh`.
2. The bash pipeline step in `_agg_pipeline_for_candidate` that invoked the validator with `--repair-attestation` and routed its stderr through a breadcrumb-grep into `aggregator-repair.stderr`. The pipeline collapses to: validator runs on the dispatch candidate directly; on success, the strip step also runs on the dispatch candidate.
3. The downstream `FAILURE_LOG` branch that consumed `aggregate-repair-failed.stderr` (only ever written by the deleted pipeline step) — becomes unreachable.

Validator-side behavior is unchanged: the `main()` validator still drops impure attestation lines (in memory), still emits `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` on narrative drift, and still rejects empty-merge from nonempty input with `empty_merge_from_nonempty_input`. The two helper predicates `has_nonconforming_finding_heading_markers` and `has_preamble_finding_signal` stay because the validator's `main()` calls them.

**Preserve the impure-attestation strip invariant**. The OLD `_attempt_attestation_repair` unconditionally called `drop_impure_empty_merge_attestation_lines` at function entry and wrote the cleaned text to `$cand_repaired_tmp`, so the downstream strip step (and the move to `$agg_dest`) operated on already-cleaned bytes. With that path deleted, the inline strip Python heredoc must also filter impure-token variants (lines whose trimmed text begins with the attestation token but is not exactly it). Otherwise a model that emits valid FINDING blocks alongside an impure attestation line would leak the variant into `findings.md` — the harness has a stanza dedicated to guarding against that leak.

**Drop the success-path self-move**. `$cand` is the dispatch's `ALL_OUTPUT_FILES[0]`, which equals the slot's `output:` path, which equals `$out_path` (== `$agg_dest`). With the repaired temp file gone, `mv -f "$cand" "$agg_dest"` is a self-move — harmless under GNU coreutils but rejected by BSD `mv`. Drop the move entirely; `$cand` already lives at `$agg_dest`.

Tests for synthesis behavior become dead — the breadcrumb file `aggregator-repair.stderr` is no longer written, so assertions that grep it for `ATTESTATION_SYNTHESIZED=true` / `AGGREGATOR_SYNTHESIS_SUPPRESSED=` no longer apply. The substantive `AGGREGATED=false` / `REASON=validation-failed` / `findings.md unchanged` assertions in the surrounding stanzas stay — they exercise the validator's `empty_merge_from_nonempty_input` rejection.

The doc bullets describing the synthesis path collapse to a single sentence noting that empty-merge from nonempty input is rejected (no automatic recovery).

## Files to modify/create

### UPDATED: `skills/review/scripts/aggregate-findings.sh`

- Delete the Python `_attempt_attestation_repair` function body in full.
- Delete the Python `repair_attestation_main` function (the `--repair-attestation` CLI worker).
- Delete the dispatch guard `if len(sys.argv) >= 4 and sys.argv[1] == "--repair-attestation": raise SystemExit(repair_attestation_main())` at the embedded script's `__main__` block.
- Inside `_agg_pipeline_for_candidate`:
  - Remove the local variables `repair_err_tmp` and `cand_repaired_tmp`. The latter becomes unused after the rename below; the former is only set by the deleted repair invocation.
  - Remove the `rm -f "$REVIEW_TMPDIR/aggregator-repair.stderr" "$REVIEW_TMPDIR/aggregate-repair-failed.stderr"` line at the top of the function (both files are no longer written).
  - Remove the `python3 "$validate_py" --repair-attestation ...` invocation block in full, including the failure branch that writes `aggregate-repair-failed.stderr`.
  - Remove the breadcrumb-filter block that copied `ATTESTATION_SYNTHESIZED=` / `AGGREGATOR_SYNTHESIS_SUPPRESSED=` lines from `$repair_err_tmp` into `$REVIEW_TMPDIR/aggregator-repair.stderr` (and the corresponding `rm -f` cleanup of the same path).
  - Update the subsequent validator invocation (`python3 "$validate_py" "$FINDINGS_FILE" "$cand_repaired_tmp"`) to read `$cand` instead of `$cand_repaired_tmp`. Drop the validator-failure branch's `rm -f "$cand_repaired_tmp"` since no temp was created.
  - Update the inline strip Python heredoc to read `$cand` instead of `$cand_repaired_tmp`. Extend the strip predicate so it also skips impure attestation lines (lines whose `.strip()` starts with the attestation token but is not exactly it). The simplest form is to assign both the exact token and a startswith-but-not-equal helper, then drop matching lines.
  - On the success path, drop the line `mv -f "$cand_repaired_tmp" "$agg_dest"` entirely (do NOT rewrite it as `mv -f "$cand" "$agg_dest"`). `$cand` is already at `$agg_dest`; only `mv -f "$merged_tmp" "$FINDINGS_FILE"` remains.
  - Drop the strip-step failure branch's `rm -f "$cand_repaired_tmp" "$merged_tmp"` reduction so it removes only `$merged_tmp`. Apply the same change to the staged-merge-output-empty branch.
- Remove the `MERGE_PIPELINE_RC=2` sub-branch in the outer driver loop (the per-phase loop in the script's main body) that probes for `$REVIEW_TMPDIR/aggregate-repair-failed.stderr` and remaps `FAILURE_LOG` to it. The fallback to `$REVIEW_TMPDIR/aggregator-validate.stderr` (and the further fallbacks for `aggregator-strip.stderr` / `aggregator-empty-merge.stderr`) still applies on the unchanged path.

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

- In the stanza titled `zero output without model attestation: script synthesizes token (#2563)`: drop the `grep -Eq '^ATTESTATION_SYNTHESIZED=true ...'` assertion; retitle to indicate the post-cleanup invariant (`zero output without model attestation: validator rejects empty-merge`). Keep the existing `AGGREGATED=false` / `REASON=validation-failed` / `findings.md unchanged` assertions and the execution-issues isolation subtest (which verifies that the rejection is logged to `execution-issues.md`).
- In the stanza titled `zero_findings_nonconforming_heading`: drop the `rm -f .../aggregator-repair.stderr` housekeeping, the existence check for `aggregator-repair.stderr`, and the synthesis/suppression breadcrumb assertions. Keep the substantive `AGGREGATED=false` / `REASON=validation-failed` assertions — the validator still rejects with `empty_merge_from_nonempty_input` on this input. Retitle to drop the synthesis-suppression framing.
- In the stanza titled `zero_findings_nospace_pseudo_heading`: same treatment as the nonconforming-heading stanza.
- In the stanza titled `zero_findings_prose_finding_ids`: drop the `rm -f .../aggregator-repair.stderr`, the suppression-breadcrumb negative assertion, and the synthesis-breadcrumb positive assertion. Keep the substantive `AGGREGATED=false` / `REASON=validation-failed` / `findings.md unchanged` assertions (the validator's `preamble_finding_substring` path still fires on this input).
- In the stanza titled `empty_merge_existing_token_passthrough`: remove the stanza in full. Its only distinguishing assertion was "no synthesis breadcrumb when model already emitted attestation"; with synthesis deleted, this is vacuously true. The validator-rejection assertion it carries is already covered by the `zero output FINDING blocks fails closed when input had findings (#2536)` stanza.
- The `zero_findings_impure_attest` stanza already asserts `cmp -s` on the input ballot (findings.md unchanged) and that `junk-suffix` does not appear in findings.md. With the strip step's impure-line filter extended, this assertion continues to hold — no changes required to that stanza beyond what's covered above.

### UPDATED: `skills/review/scripts/aggregate-findings.md`

- Keep the parent `Empty-merge attestation (runtime contract)` bullet describing the `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token and the strip-on-validation behavior — both still apply.
- Keep the impure-attestation drop bullet (`drop_impure_empty_merge_attestation_lines` is still invoked inside the validator's `main()`, and the inline strip step now also filters impure variants).
- Replace the two long bullets describing pseudo-FINDING-heading synthesis suppression and the deterministic attestation synthesis recovery path with a single short bullet noting that when input has findings and aggregator output has zero findings, validation always fails (`empty_merge_from_nonempty_input` or `preamble_finding_substring` for narrative drift); there is no automatic synthesis recovery (rationale: post-issue #2782 the validator rejects regardless of attestation presence).

## Edge cases

- **Model omits attestation on empty-merge** (previously triggered synthesis): now goes directly to validator, which rejects with the non-token "zero merged FINDING blocks while input had findings; output must include ..." diagnostic (because `has_attest_line=False` and no preamble drift). This is `MERGE_PIPELINE_RC=2`, single-shot validation-failed (matches the doc's "Other validation failures keep the legacy single-shot behavior"). For the case where the model DID emit attestation, the validator's `empty_merge_from_nonempty_input` branch still emits the token and the narrow-trigger retry still fires on the per-phase outer loop.
- **Model emits `###FINDING_1:` typo on empty-merge** (previously triggered synthesis-suppressed breadcrumb): now goes directly to validator, which falls through preamble check (suppressed by `has_nonconforming_finding_heading_markers`) and rejects with the non-token "zero merged FINDING blocks ..." diagnostic. Same end state (findings.md unchanged).
- **Model emits preamble narrative referencing `FINDING_N` ids on empty-merge** (previously triggered `preamble_finding_substring` suppression): the validator's `main()` emits `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` on this input. End state unchanged. The narrow-trigger retry across outer phases (waterfall over Cursor → Codex → Claude) keys off this same stderr token and still advances correctly.
- **Model correctly emits attestation token on empty-merge**: validator drops impure-token variants via `drop_impure_empty_merge_attestation_lines` (in memory), then rejects with `empty_merge_from_nonempty_input` (per the post-#2782 invariant — attestation alone is no longer sufficient). The narrow-trigger retry still fires for this case. End state unchanged.
- **Model emits valid FINDING blocks alongside impure attestation variants** (rare): the validator's in-memory drop catches them and validation passes for block validation. The inline strip step's extended predicate filters the impure variants from the file output, so `findings.md` stays clean. Matches the OLD behavior where `_attempt_attestation_repair`'s entry call to `drop_impure_empty_merge_attestation_lines` cleaned the file before strip.
- **Input has fewer than two FINDING blocks**: short-circuited at the early `if [[ "$INPUT_COUNT" -lt 2 ]]; then ... exit 0; fi` guard. Unchanged.

## Failure modes

This is a localized cleanup removing dead-code paths and adding a one-line predicate extension to the strip step. No new failure modes are introduced. The `MERGE_PIPELINE_RC=1` outer-waterfall retry (validator-detected preamble drift OR `empty_merge_from_nonempty_input`) and the `MERGE_PIPELINE_RC=2` validator JSON error path continue to function — both still trigger from the surviving validator invocation in `_agg_pipeline_for_candidate`.

## Testing strategy

- `make test-aggregate-findings` (covers `skills/review/scripts/test-aggregate-findings.sh`) — the harness retains its empty-merge validator-rejection coverage via the `zero output FINDING blocks fails closed when input had findings (#2536)` stanza and the trimmed synthesis-era stanzas. The `zero_findings_impure_attest` stanza continues to assert that `junk-suffix` does not appear in `findings.md` — this passes via the strip step's extended predicate even though `_attempt_attestation_repair` is gone. New stanzas are not needed.
- `make lint` / pre-commit hooks — bash 3.2 compat, shellcheck on the trimmed script, and markdownlint on the trimmed doc.
- Manual verification before commit: grep the live tree for `_attempt_attestation_repair`, `repair_attestation_main`, `--repair-attestation`, `aggregate-repair-failed.stderr`, and `aggregator-repair.stderr` — should return zero hits outside `larch-logs/` after the patch.

## Acceptance

- `make test-aggregate-findings` passes; the `zero output FINDING blocks fails closed when input had findings (#2536)` stanza still exercises the validator's empty-merge rejection.
- `make lint` passes (bash 3.2 compat, shellcheck on the trimmed script, markdownlint on the trimmed doc).
- `grep -rn '_attempt_attestation_repair\|repair_attestation_main\|--repair-attestation\|aggregate-repair-failed.stderr\|aggregator-repair.stderr' scripts/ skills/ docs/ .claude/` returns zero hits.
- The `zero_findings_impure_attest` stanza continues to assert that `junk-suffix` does not appear in `findings.md` (extended strip predicate covers it).

diff_lines: 230
