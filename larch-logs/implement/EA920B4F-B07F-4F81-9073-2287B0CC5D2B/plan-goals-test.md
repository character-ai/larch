## Goal
Add success-path impure-attestation strip coverage and fix misleading padded-attestation stanza title in test-aggregate-findings.sh

## Implementation Plan
## Plan

# Plan: OOS test improvements — success-path impure-strip coverage + misleading-title rename

## Goal

Address issue #2822 (filed from PR #2820 code review). Two test-quality improvements to `skills/review/scripts/test-aggregate-findings.sh`:

1. **Add success-path coverage** for the impure-attestation strip predicate at `skills/review/scripts/aggregate-findings.sh:675` (`stripped.startswith(EMPTY_MERGE_ATTESTATION)`). The existing `zero_findings_impure_attest` stanza only covers the rejection path; the persistence-strip predicate only runs when `AGGREGATED=true`, so a regression in that predicate would silently leak the impure-suffix variant into `findings.md` while current tests still pass.

2. **Rename the misleading padded-attestation echo and stub kind** so the test header reflects what is actually asserted (rejection, not acceptance).

Plus a path-triggered repo-hygiene item surfaced by plan review (FINDING_1 / FINDING_7):

3. **Add the missing sibling `test-aggregate-findings.md`** under `skills/review/scripts/`. Per `.claude/rules/script-md-siblings.md`, every `.sh` under `skills/**/scripts/` must have a sibling `.md` stub; the harness currently has none. Item #3 is bundled here because it sits in the same path-triggered rule surface that this PR's harness edits already trigger.

No SUT (`skills/review/scripts/aggregate-findings.sh`) changes.

## Files to modify/create

### NEW: `skills/review/scripts/test-aggregate-findings.md`

Minimal sibling stub conforming to `.claude/rules/script-md-siblings.md` "harness gets a sibling `.md` stub that points to the primary `.md`" pattern (primary = `skills/review/scripts/aggregate-findings.md`). Content roughly:

```markdown
# test-aggregate-findings.sh

Regression harness for `skills/review/scripts/aggregate-findings.sh`. See the primary contract in `skills/review/scripts/aggregate-findings.md`.

## Makefile target

`make test-aggregate-findings` — runs `bash skills/review/scripts/test-aggregate-findings.sh` (shard `test-harnesses-8`; see `Makefile:648-649` and `Makefile:56`).

## Coverage

Exercises the aggregator's empty-merge attestation contract across rejection and success paths, including:

- Pure-token zero-findings acceptance / rejection cases (`zero_findings_padded_attest_rejected`, `zero_findings_impure_attest`, etc.).
- Merge-success-path persistence-strip coverage via the `merge_plus_impure_attest` stub kind (asserts the `startswith` predicate at `aggregate-findings.sh:675` strips adjacent-suffix attestation lines before the merged ballot is persisted).
- Validator pre-strip behavior via `drop_impure_empty_merge_attestation_lines` (`aggregate-findings.sh:506`).

## Edit-in-sync rule

When changing the aggregator's empty-merge contract (`EMPTY_MERGE_ATTESTATION` token, validator strip ordering, persistence-strip predicate, or attestation-line shapes), update this harness and its sibling `.md`/`aggregate-findings.md` in the same PR.
```

This is approximately 18-20 lines of plain prose, satisfies the rule, and adds no behavior. Cross-reference the primary `.md` per the rule's "Primary owns the full contract" pattern.

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

Three changes in this single file.

**Change A — New stub kind `merge_plus_impure_attest`** (in the `write_stub_dispatch` heredoc, immediately after the existing `merge_plus_spurious_attest` case at line 233-244):

```bash
            merge_plus_impure_attest)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTEDjunk-suffix

EOF
                ;;
```

**Fixture-boundary tightness (FINDING_4)**: the attestation line is `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTEDjunk-suffix` (adjacent, no whitespace) rather than `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED junk-suffix` (whitespace-separated). The SUT predicate `stripped.startswith(EMPTY_MERGE_ATTESTATION)` at `skills/review/scripts/aggregate-findings.sh:675` is character-level; an adjacent suffix is the strictest boundary the contract must strip. If a future regression narrowed the predicate to only-whitespace-separated suffixes, the adjacent-form test would fail — while a whitespace-separated test would not. Using adjacent-suffix exercises the actual contract boundary the OOS body describes.

The data otherwise mirrors `merge_plus_spurious_attest`: identical merged `FINDING_1` block. Per the SUT validator at `skills/review/scripts/aggregate-findings.sh:506`, impure lines are pre-stripped via `drop_impure_empty_merge_attestation_lines(outtext)` before the "merged-blocks + pure-attest" check at line 536 — so the validator sees a clean merged output and returns success. The persistence-strip heredoc at lines 665-678 then drops the impure line via the `startswith()` predicate when persisting to `findings.md`.

**Change B — New test stanza `merge_plus_impure_attest`** (immediately after the existing `merge_plus_spurious_attest` test block ending at line 722, before `=== input reviewer parenthetical suffixes normalize on successful merge ===` at line 724):

```bash
echo "=== merged FINDING blocks plus impure adjacent attestation suffix: success path strips suffix line ==="
cp "$TMP/in3.md" "$TMP/in3-impure-success.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_plus_impure_attest \
"$AGG" \
    --findings-file "$TMP/in3-impure-success.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-impure-success.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-impure-success.env" || fail "merge+impure-attest AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-impure-success.env" || fail "merge+impure-attest REASON"
grep -Fq 'MERGED_COUNT=1' "$TMP/out-impure-success.env" || fail "merge+impure-attest MERGED_COUNT"
grep -Fq 'junk-suffix' "$TMP/in3-impure-success.md" && fail "impure attestation suffix must not survive persisted findings.md on success path"
grep -Fq 'LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED' "$TMP/in3-impure-success.md" && fail "attestation token (any form) must not survive persisted findings.md on success path"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-impure-success.md" | tr -d '[:space:]')" == "1" ]] || fail "expected one FINDING block after merge+impure-attest"
```

This stanza directly targets the `startswith()` predicate at `skills/review/scripts/aggregate-findings.sh:675` (the only code path that drops impure-suffix lines on the success branch). Note that the second negative grep (`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`) is a substring grep, so it catches BOTH the exact token AND the adjacent-suffix form — providing one assertion covering both the `==` predicate (line 673) and the `startswith` predicate (line 675).

The assertions are minimal and orthogonal: success-path booleans (`AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=1`) confirm the validator accepted the output; two negative greps prove neither variant of the attestation token survives in the persisted ballot; the final block-count assertion confirms the merge actually ran (rather than silently passing through the input).

**Change C — Rename misleading padded-attestation echo title and stub kind**.

Three edit sites for the stub-kind rename `zero_findings_padded_attest` → `zero_findings_padded_attest_rejected`. **Two of the three edit sites contain the literal kind-name token**; the third is the human-readable echo title that does not contain the kind-name token. This distinction is load-bearing for the post-rename verification recipe (see Failure modes Risk 3 below):

- **C.1 — case label in `write_stub_dispatch` (line 225)**: `zero_findings_padded_attest)` → `zero_findings_padded_attest_rejected)`. Data content (lines 226-231) is unchanged.
- **C.2 — echo title (line 691)**: change `echo "=== zero output accepts whitespace-padded empty-merge attestation (#2536) ==="` to `echo "=== zero output rejects whitespace-padded empty-merge attestation for nonempty input (#2536) ==="`. The `(#2536)` PR/issue cross-reference is retained. The kind-name token is NOT in this echo line.
- **C.3 — `AGGREGATE_STUB_MERGE_KIND=` invocation (line 696)**: `AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest \` → `AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest_rejected \`. Existing assertions at lines 704-706 (already verifying rejection) are unchanged.

The rename suffix `_rejected` makes the stub kind name reflect the asserted outcome, eliminating the prior dissonance where the kind name was descriptive of input shape only.

## Approach

The change rests on three observations from reading `skills/review/scripts/aggregate-findings.sh`:

1. **Validator strips impure lines before the "blocks + attest" rule** (`skills/review/scripts/aggregate-findings.sh:506` calls `drop_impure_empty_merge_attestation_lines(outtext)`; the rule at line 536 only fires on pure-token lines). This means merged blocks + impure-suffix line → validation succeeds → `AGGREGATED=true`. This is exactly the success-path entry the OOS body identifies.

2. **Persistence-strip heredoc uses two predicates** at lines 668-676: exact-match `stripped == EMPTY_MERGE_ATTESTATION` (line 673) AND `stripped.startswith(EMPTY_MERGE_ATTESTATION)` (line 675). The `startswith` predicate is precisely what drops adjacent and whitespace-separated suffix forms like `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTEDjunk-suffix`. Existing tests do not exercise this code path because every other `_impure_attest`-shaped scenario routes through validation failure (the rejection path).

3. **Symmetric pairing of `merge_plus_*` stub kinds**: `merge_plus_spurious_attest` (existing) covers blocks + pure token → rejected. `merge_plus_impure_attest` (new) covers blocks + impure adjacent-suffix line → accepted-then-stripped. Operators reading the harness see both halves of the contract.

The misleading-title fix is a low-risk cosmetic rename that improves readability for future test maintainers. Renaming the stub-kind name in lockstep (per Round 1 decision) keeps the dispatch-stub vocabulary self-consistent.

## Edge cases

- **`MERGED_COUNT` assertion**: success-path tests in this harness consistently assert `MERGED_COUNT=1` for single-block merge cases (e.g., line 442, 755, 800). The new stub returns one merged block, so `MERGED_COUNT=1` is the correct expected value.
- **`LARCH_AGGREGATE_MAX_OUTER_PHASES`**: success-path `merge_plus_*` tests in this harness do NOT set `LARCH_AGGREGATE_MAX_OUTER_PHASES` (see line 708-722 for `merge_plus_spurious_attest`). Follow that pattern; do not introduce a phase override for the new test.
- **Findings file vs. input file**: the harness creates a working copy (`cp "$TMP/in3.md" "$TMP/in3-impure-success.md"`) and passes the COPY to `--findings-file`. The aggregator REPLACES the working copy in-place on success. Greps for `junk-suffix` and `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must target the working copy (the replaced file), not the original `in3.md`.
- **Block ordering**: the new stanza is inserted between `merge_plus_spurious_attest` (line 708-722) and `input reviewer parenthetical suffixes` (line 724) so the contrast pair is immediately readable.
- **Sibling `.md` file**: the new `skills/review/scripts/test-aggregate-findings.md` is a stub that satisfies the path-triggered rule without duplicating the aggregator contract; the primary `.md` for the aggregator is `skills/review/scripts/aggregate-findings.md`.

## Failure modes

- **Risk 1: regression in `drop_impure_empty_merge_attestation_lines` causes validation to fail** instead of succeed on merged-blocks + impure-suffix input. Earliest warning: `merge+impure-attest AGGREGATED` assertion in the new stanza fails with `AGGREGATED=false`. Mitigation: the test asserts both the success boolean AND the absence of attestation residue, so a validator regression and a strip regression both surface as test failures with distinct messages.
- **Risk 2: the `startswith` predicate at `skills/review/scripts/aggregate-findings.sh:675` is removed or weakened** (e.g., changed to only-exact match, or to only-whitespace-separated forms). Earliest warning: `impure attestation suffix must not survive persisted findings.md on success path` fails because `junk-suffix` (adjacent form) leaks through. Mitigation: the negative grep is the direct contract assertion — same line, no ambiguity. The adjacent-suffix fixture (vs. whitespace-separated) is what makes this regression catchable.
- **Risk 3: the rename of `zero_findings_padded_attest` misses one of the three edit sites**. The verification recipe must account for the fact that `zero_findings_padded_attest` is a PREFIX of `zero_findings_padded_attest_rejected`, so a plain substring grep cannot return zero hits after a correct rename. Use boundary-aware patterns:
   - `grep -nE 'zero_findings_padded_attest\)' skills/review/scripts/test-aggregate-findings.sh` should return ZERO hits (the old case-label form with `)`).
   - `grep -nE 'AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest[^_a-z]' skills/review/scripts/test-aggregate-findings.sh` should return ZERO hits (the old env-var invocation form, where `[^_a-z]` rules out the new name's `_rejected` continuation).
   - `grep -nE 'zero_findings_padded_attest_rejected' skills/review/scripts/test-aggregate-findings.sh` should return EXACTLY TWO hits (case label at line 225 + `AGGREGATE_STUB_MERGE_KIND=` invocation at line 696). The echo at line 691 is prose-only and does NOT contain the kind-name token.
   - `grep -n 'rejects whitespace-padded' skills/review/scripts/test-aggregate-findings.sh` should return ONE hit (the renamed echo at line 691).

   On stub-kind miss, the actual harness stderr is `stub: bad AGGREGATE_STUB_MERGE_KIND` (see `skills/review/scripts/test-aggregate-findings.sh:350-352`). Mitigation: run all four boundary-aware greps as a final post-rename sanity check before commit.

## Testing strategy

- **Primary verification**: `make test-aggregate-findings` (Makefile target at line 648-649; shard `test-harnesses-8`) must pass with the new stanza added and the rename applied.
- **Repo-wide hygiene**: `bash scripts/relevant-checks.sh` (per AGENTS.md "After any change") runs lint, agent-lint, etc. The change is test-only and Bash 3.2-portable (no associative arrays, namerefs, mapfile, parameter case conversion — uses `cat <<'EOF'`, plain `grep`, `cp`, `||`-guarded asserts).
- **Sibling-doc lint**: the new `skills/review/scripts/test-aggregate-findings.md` satisfies the path-triggered `.claude/rules/script-md-siblings.md` rule; any sibling-existence lint should now pass on this surface.
- **Negative test ablation (manual sanity, not committed)**: temporarily comment out line 675 (the `startswith` predicate) in `skills/review/scripts/aggregate-findings.sh` and re-run `make test-aggregate-findings`; the new stanza MUST fail with `impure attestation suffix must not survive persisted findings.md on success path`. Adjacent suffix is what makes this ablation observable. Restore the predicate after ablation.

## Diff size estimate

- New sibling .md file: ~20 lines (added)
- Change A (new stub kind): ~10 lines (added)
- Change B (new test stanza): ~17 lines (added)
- Change C.1 (case label rename): 1 line touched
- Change C.2 (echo title rename): 1 line touched
- Change C.3 (invocation env rename): 1 line touched

Total: ~50 LOC (~30 LOC in the harness shell + ~20 LOC in the new sibling .md). The shell-only portion still matches the OOS budget; the sibling .md is a path-triggered repo-hygiene addition surfaced by plan review (FINDING_1 / FINDING_7).

## Acceptance

- `make test-aggregate-findings` passes (shard `test-harnesses-8`).
- `bash scripts/relevant-checks.sh` passes (lint + agent-lint + sibling-doc lint + Bash 3.2 portability).
- The new `skills/review/scripts/test-aggregate-findings.md` sibling stub exists and matches the `.claude/rules/script-md-siblings.md` "harness stub points to primary `.md`" pattern.
- The new `merge_plus_impure_attest` test stanza in `test-aggregate-findings.sh` exists and exercises the success path: `AGGREGATED=true`, `REASON=ok`, `MERGED_COUNT=1`, and neither `junk-suffix` nor the `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` token survives in the persisted `findings.md`.
- The renamed stub kind `zero_findings_padded_attest_rejected` appears exactly twice (`grep -nE "zero_findings_padded_attest_rejected" skills/review/scripts/test-aggregate-findings.sh` returns 2 hits: case label + `AGGREGATE_STUB_MERGE_KIND=` invocation).
- The old kind name has zero remaining boundary-aware matches (`grep -nE "zero_findings_padded_attest\)" skills/review/scripts/test-aggregate-findings.sh` and `grep -nE "AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest[^_a-z]" skills/review/scripts/test-aggregate-findings.sh` both return zero).
- The echo at line 691 contains "rejects" not "accepts" (`grep -n "rejects whitespace-padded" skills/review/scripts/test-aggregate-findings.sh` returns one hit).
- Manual ablation (not committed): commenting out the `startswith()` predicate at `skills/review/scripts/aggregate-findings.sh:675` causes the new stanza to fail; restoring it passes.

diff_lines: 50

## Test plan
(no test plan section in plan-file)
