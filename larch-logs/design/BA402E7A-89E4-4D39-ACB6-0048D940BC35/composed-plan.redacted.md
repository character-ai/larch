## Plan

### Approach
SIMPLE-tier minimum-change plan. Add two new regression tests to `skills/review/scripts/test-aggregate-findings.sh` covering coverage gaps left by issue #2939's attestation-only empty-merge contract. No changes to production code in `skills/review/scripts/aggregate-findings.sh`. The two new tests mirror the structure of the existing `zero_findings_nospace_pseudo_heading` and `zero_findings_round_trip_pure_attestation_success` blocks so future readers can pattern-match them as siblings.

### Files to modify/create

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

Add one new fixture branch inside the existing `case "${AGGREGATE_STUB_MERGE_KIND:-merge}"` block (which currently spans roughly lines 81–363), and two new top-level assertion blocks adjacent to the existing related tests.

1. **New fixture (gap 1)** — add a new `case` arm `zero_findings_nospace_pseudo_heading_with_attestation)` between the existing `zero_findings_nospace_pseudo_heading)` arm (ends ~line 221) and the existing `zero_findings_prose_finding_ids)` arm (starts ~line 222). Body:
   ```
   zero_findings_nospace_pseudo_heading_with_attestation)
       cat > "$out" <<'EOF'
   Aggregator narrative: tight ###FINDING_ typo combined with attestation must fail validation.

   ###FINDING_1: not a strict heading (no space after ###)

   LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

   EOF
       ;;
   ```

2. **New assertion block (gap 1)** — insert immediately after the existing `=== zero_findings_nospace_pseudo_heading: validation-failed ===` block (currently ends at the `nospace-pseudo REASON` assertion around line 920) and before the `=== zero_findings_prose_finding_ids: validation-failed ===` block (around line 922). Mirror the existing `zero_findings_nonconforming_with_attestation` test pattern (lines ~870–885) but use the new fixture name. Body:
   ```
   echo "=== zero_findings_nospace_pseudo_heading_with_attestation: validation-exhausted (#3003) ==="
   cp "$TMP/in3.md" "$TMP/in3-nospace-pseudo-attest.md"
   write_stub_dispatch
   AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
   AGGREGATE_STUB_MODE=ok \
   AGGREGATE_STUB_MERGE_KIND=zero_findings_nospace_pseudo_heading_with_attestation \
   "$AGG" \
       --findings-file "$TMP/in3-nospace-pseudo-attest.md" \
       --review-tmpdir "$TMP" \
       --codex-present true \
       --cursor-present true \
       --mode diff >"$TMP/out-nospace-pseudo-attest.env"
   grep -Fq 'AGGREGATED=false' "$TMP/out-nospace-pseudo-attest.env" || fail "nospace-pseudo+attest AGGREGATED"
   grep -Fq 'REASON=validation-exhausted' "$TMP/out-nospace-pseudo-attest.env" || fail "nospace-pseudo+attest REASON"
   grep -Fq 'AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation' "$TMP/aggregator-validate.stderr" || fail "expected nonconforming_heading_with_attestation token for nospace pseudo-heading"
   cmp -s "$TMP/in3.md" "$TMP/in3-nospace-pseudo-attest.md" || fail "findings unchanged on nospace-pseudo+attest validator rejection"
   ```

3. **New input fixture inline + assertion block (gap 2)** — insert immediately after the existing `=== validation accepts merge when reviewer has both OOS and in-scope input findings (#2491) ===` block (the existing `oos_shared_slot_merge` test around lines 737–756) and before the next `=== ... ===` block. The fixture is defined inline because, like other one-off OOS fixtures, it does not belong in the stub `case` block (which controls aggregator output, not input). Body:
   ```
   echo "=== all-OOS input + attestation-only output accepted: oos_only_slots enforcement does not fire (#3003) ==="
   cat > "$TMP/in-all-oos.md" <<'EOF'
   ### FINDING_1: [OUT_OF_SCOPE] **code-quality** [`x`]
   - **Reviewer**: cursor-a-output.txt
   - **Concern**: oos x
   - **Suggested revision**: n/a

   ### FINDING_2: [OUT_OF_SCOPE] **correctness** [`y`]
   - **Reviewer**: cursor-b-output.txt
   - **Concern**: oos y
   - **Suggested revision**: n/a

   ### FINDING_3: [OUT_OF_SCOPE] **architecture** [`z`]
   - **Reviewer**: cursor-c-output.txt
   - **Concern**: oos z
   - **Suggested revision**: n/a

   EOF
   cp "$TMP/in-all-oos.md" "$TMP/in-all-oos-work.md"
   write_stub_dispatch
   AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
   AGGREGATE_STUB_MODE=ok \
   AGGREGATE_STUB_MERGE_KIND=zero_findings_pure_attest \
   "$AGG" \
       --findings-file "$TMP/in-all-oos-work.md" \
       --review-tmpdir "$TMP" \
       --codex-present true \
       --cursor-present true \
       --mode diff >"$TMP/out-all-oos.env"
   grep -Fq 'AGGREGATED=true' "$TMP/out-all-oos.env" || fail "all-OOS+attest AGGREGATED"
   grep -Fq 'REASON=ok' "$TMP/out-all-oos.env" || fail "all-OOS+attest REASON"
   grep -Fq 'MERGED_COUNT=0' "$TMP/out-all-oos.env" || fail "all-OOS+attest MERGED_COUNT"
   grep -Fq 'AGGREGATOR_VALIDATION_FAILED=' "$TMP/aggregator-validate.stderr" 2>/dev/null && fail "all-OOS+attest success must not emit validation failure token"
   assert_whitespace_only "$TMP/in-all-oos-work.md" "all-OOS+attest findings.md must be whitespace-only after attested empty merge"
   ```

The two issue-tag comments (`(#3003)`) keep grep traceability consistent with the existing `(#2939)` / `(#2491)` / `(#2563)` markers in the file.

### Edge cases
- The nospace pseudo-heading regex (`_PSEUDO_FINDING_HEADING = r"^###\s*FINDING_[0-9]"` in `aggregate-findings.sh`) matches both `### FINDING_1:` and `###FINDING_1:` (the `\s*` matches zero spaces), so the existing validator at the `has_nonconforming_finding_heading_markers(outtext) and has_attest_line` branch already covers the nospace case — the new test simply asserts that path fires for the nospace variant. This is an existing-behavior assertion, not new behavior.
- For gap 2, every input slot is OOS, so `oos_only_slots = {a, b, c}` is non-empty, but the enforcement loop at `aggregate-findings.sh:602-610` only iterates `blocks`, which is empty in the attestation-only branch. The test locks in the resulting `REASON=ok` outcome so a future refactor that moves the `oos_only_slots` check outside the loop (or that changes the empty-merge attestation acceptance path) will fail visibly.
- The new gap-1 fixture purposefully uses the same `### FINDING_1` numeric form as the existing nonconforming-with-attestation fixture (so `has_preamble_finding_signal` would otherwise also trigger), but the explicit `has_nonconforming_finding_heading_markers` check at validator line 555 short-circuits before the preamble-signal branch, preserving the exhaustive-validation `REASON=validation-exhausted` outcome.
- `assert_whitespace_only` (already defined in the file) tolerates a fully empty file, a newline-only file, or whitespace-only content — the actual post-attest content depends on the aggregator strip path but is always whitespace-only after a successful attestation acceptance.

### Failure modes
1. **Wrong `REASON=` value asserted for gap 1** — if the test asserts `REASON=validation-failed` instead of `REASON=validation-exhausted`, it would still appear to pass when added but fail to detect the actual code-path. Mitigation: model gap 1 on the existing `zero_findings_nonconforming_with_attestation` block (line 882-885), which uses the `validation-exhausted` token.
2. **Fixture name collision with existing case arm** — Bash `case` silently uses the first matching arm. Mitigation: pick the explicit name `zero_findings_nospace_pseudo_heading_with_attestation` (longer than the existing arms) and place it sequentially next to the related arms; verify with `grep -c 'zero_findings_nospace_pseudo_heading_with_attestation)' test-aggregate-findings.sh` returning exactly `1` after the edit.
3. **Test ordering side-effects from `$TMP/aggregator-validate.stderr` accumulating across tests** — the existing tests already grep `aggregator-validate.stderr` and assume the helper rewrites it. Mitigation: the existing test at line 884 already asserts the same token grep without explicit reset, so our gap-1 test will inherit the same proven pattern; no new mechanism needed.

### Testing strategy
- Run `bash skills/review/scripts/test-aggregate-findings.sh` after the edits. The harness is self-contained: it does not require external services, and the two new tests run in the same process under the existing `write_stub_dispatch` infrastructure.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) as the final repo-required validation step after the harness edits land. AGENTS.md mandates this gate after any change; the design must not be considered implemented until that command exits 0.
- `make lint` runs the test as part of the relevant-checks pre-commit hook in this repo.


## Acceptance

The design is implemented when:

- A new `case` arm `zero_findings_nospace_pseudo_heading_with_attestation)` exists in `skills/review/scripts/test-aggregate-findings.sh` and its body contains both `###FINDING_1: not a strict heading (no space after ###)` (no whitespace between `###` and `FINDING_1`) and a line whose trimmed text is exactly `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`.
- A new `=== zero_findings_nospace_pseudo_heading_with_attestation: validation-exhausted (#3003) ===` assertion block exists in the same file, asserts `AGGREGATED=false`, asserts `REASON=validation-exhausted`, asserts `AGGREGATOR_VALIDATION_FAILED=nonconforming_heading_with_attestation` in `aggregator-validate.stderr`, and asserts the input findings file is byte-identical to the baseline (`cmp -s`).
- A new `=== all-OOS input + attestation-only output accepted: oos_only_slots enforcement does not fire (#3003) ===` assertion block exists in the same file, defines an inline input fixture with three `### FINDING_N: [OUT_OF_SCOPE] ...` blocks (one each for slots a, b, c), invokes the aggregator with `AGGREGATE_STUB_MERGE_KIND=zero_findings_pure_attest`, and asserts `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=0`, that no `AGGREGATOR_VALIDATION_FAILED=` token is present in `aggregator-validate.stderr`, and that the input file becomes whitespace-only via `assert_whitespace_only`.
- `bash skills/review/scripts/test-aggregate-findings.sh` exits 0 with the new tests included.
- `bash scripts/relevant-checks.sh` (or `make lint`) exits 0 with the new tests included.
- `skills/review/scripts/aggregate-findings.sh` is unchanged.

diff_lines: 56
