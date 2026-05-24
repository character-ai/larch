## Plan

## Scope

Add per-finding 4-axis forensic ratings (correctness / severity / quality / uncertain) to the 3-judge code-review voting panel used by both `/implement` Step 5 review rounds and standalone `/review --diff` rounds. Each round emits a `findings-classification.tsv` file covering every ballot entry (accepted / rejected / neutral / exonerated; both `FINDING_N:` and `OOS_N:`). Vote tallying behavior is unchanged.

**Blocked on**: #2671 (L2). L6 implementation does not start until `scripts/parse-judge-vote-and-rating.sh` lands AND its sibling `scripts/parse-judge-vote-and-rating.md` pins the contract enumerated under "Parser contract dependency" below.

## Parser contract dependency (L2 prerequisite)

L6 reuses L2's `scripts/parse-judge-vote-and-rating.sh`. Before L6 implementation starts, L2's sibling `scripts/parse-judge-vote-and-rating.md` MUST pin all of the following (this design is unimplementable otherwise — addresses FINDING_15 and FINDING_16):

- **Invocation**: positional `<voter_file> <ballot_id>`. No flags required.
- **Stdout schema**: line-oriented KV lines via `lib-quiet.sh` `emit_kv`:
  - `PARSED_VOTE=<YES|NO|EXONERATE|>` (empty when no recognized vote token; consumer treats empty as JUDGE_ERROR).
  - `PARSED_CORRECTNESS=<true|partially-true|false-positive|uncertain|>` (empty when missing or unrecognized).
  - `PARSED_SEVERITY=<blocker|major|minor|nit|uncertain|>` (same emptiness rule).
  - `PARSED_QUALITY=<excellent|good|adequate|weak|no-fix|uncertain|>` (same emptiness rule).
  - `PARSED_UNCERTAIN=<true|false>` (defaults to `true` when any of the 4 axes was missing or unrecognized).
- **Exit codes**: **0** whenever the vote token is recognized OR when no `FINDING_N`/`OOS_N` line for the given id is present in the voter file (consumer treats absence as JUDGE_ERROR). **Non-zero** only on hard failures (unreadable file, malformed input pipeline). This is required so `tally-code-votes.sh` (which runs under `set -euo pipefail`) does not abort on soft rating gaps.
- **Position-agnostic axis tokens**: the parser accepts `CORRECTNESS=`/`SEVERITY=`/`QUALITY=`/`UNCERTAIN=` tokens in any order on the vote line. The vote token (`YES|NO|EXONERATE`) MUST remain immediately after `<ID>:` because `scripts/lib-vote-tally.sh:12-29` anchors on that position.

If L2 ships an incompatible API, the L6 call site adapts; the contract above is the recommended target.

## Files to modify

### 1. `scripts/dispatch-code-voters.sh` (+ sibling `.md`)

Extend `make_voter_prompt_file()` and `VOTER_PARSE_RATE_RETRY_PREFIX` to instruct each judge to emit the 4-axis ratings on the same line as the vote. The new line shape covers BOTH ballot id forms:

```
FINDING_N: <YES|NO|EXONERATE> CORRECTNESS=<true|partially-true|false-positive|uncertain> SEVERITY=<blocker|major|minor|nit|uncertain> QUALITY=<excellent|good|adequate|weak|no-fix|uncertain> UNCERTAIN=<true|false> -- rationale
OOS_N: <YES|NO|EXONERATE> CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<true|false> -- rationale
```

Show explicit parallel examples for both prefixes (FINDING_6). Rewrite the "silent ignore" rule from "Lines that do not start with FINDING_N: …" to "Lines that do not start with `FINDING_N:` or `OOS_N:` (matching the ballot's heading id) followed by `YES|NO|EXONERATE` are silently ignored." Update `VOTER_PARSE_RATE_RETRY_PREFIX` with the same dual-prefix instruction and a one-line reminder that 4-axis ratings are also expected.

Also extend `check_voter_parse_rate` ID enumeration (FINDING_5): change `ids_count` (currently `grep -cE '^### (FINDING_[0-9]+):'`) and the per-id awk/grep loop to `^### (FINDING_[0-9]+|OOS_[0-9]+):`. Update diagnostic message text to "ballot items" rather than "findings". Mirror `split_ballot_to_blocks` in `scripts/lib-vote-tally.sh:104-106`.

### 2. `skills/review/scripts/tally-code-votes.sh` (+ sibling `.md`)

Inside the existing per-block ballot loop:

- For each effective voter file, invoke L2's `scripts/parse-judge-vote-and-rating.sh "$voter_file" "$ballot_id"`; capture stdout via `_parsed_out=$("$PARSER" "$voter_file" "$ballot_id" 2>/dev/null) || true` (the `|| true` belt-and-braces in case L2 ever ships a stricter parser; the redirect prevents stderr noise under `set -e`). Extract `PARSED_VOTE`/`PARSED_CORRECTNESS`/`PARSED_SEVERITY`/`PARSED_QUALITY`/`PARSED_UNCERTAIN` from the KV output.
- **Lenient policy uniformly** (resolved per Round 1 Decision 2 + FINDING_9): when any axis token is missing or carries a value outside the documented enum, the consumer records that axis as the empty string AND sets `UNCERTAIN=true` for the TSV row. Drop the prior "raw verbatim" alternative — there is one rule.
- **Single parse per (voter_file, id)** (FINDING_14): the captured `PARSED_VOTE` feeds BOTH `classify_result` inputs (replacing the prior `vote_for_id "$id" "$voter_file"` call at line 312) AND the TSV `vN_vote` column. This eliminates the two-parser disagreement risk. Add a harness assertion that `parse-judge-vote-and-rating.sh` and `vote_for_id` agree on every fixture line (regression guard against future divergence).

**TSV write — factored helper** (FINDING_2 + FINDING_17): factor a shared function `write_classification_tsv_row` that takes `(ballot_id, reviewer_slots, voting_result, per_voter_records...)` and appends one row. Call it from both the normal per-block voting path AND from a new pre-`EFFECTIVE_VOTERS==0`-exit path (between `split_ballot_to_blocks` and the early return at lines 252-280). The early-exit path emits one TSV row per ballot id with all voter columns empty. For the empty-ballot edge case (zero `block_files`), still write the schema header row only. Always `emit_kv FINDINGS_CLASSIFICATION_TSV_FILE` whenever the file is written, independent of `MANIFEST_FILE` presence (FINDING_10). Explicit guard pattern:
```bash
[[ -f "$CLASSIFICATION_TSV" ]] && emit_kv FINDINGS_CLASSIFICATION_TSV_FILE "$CLASSIFICATION_TSV"
```

**TSV path** (FINDING_11 — multi-round):
- `/implement` review: `$REVIEW_TMPDIR/findings-classification.tsv` (per-round tmpdir already differs by round — `$IMPLEMENT_TMPDIR/round-<N>/` is passed as `--review-tmpdir` per `review-and-fix.sh:966-1005`).
- Standalone `/review --diff`: per-round filenames `$REVIEW_TMPDIR/findings-classification-round-${ROUND_NUM}.tsv` (round number flows through `--round-num`, already a tally argument). The standalone wrapper publishes each round's file separately via Step 4.

**TSV schema** (FINDING_12 — explicit semantics):
```
finding_id\treviewer_slots\tvoting_result\tv1_vote\tv1_correctness\tv1_severity\tv1_quality\tv1_uncertain\tv2_vote\tv2_correctness\tv2_severity\tv2_quality\tv2_uncertain\tv3_vote\tv3_correctness\tv3_severity\tv3_quality\tv3_uncertain
```

Column semantics (documented in `tally-code-votes.md` and `docs/run-logs.md`):
- `finding_id`: ballot id verbatim (`FINDING_N` or `OOS_N`).
- `reviewer_slots`: pipe-delimited (`|`) attribution string from `reviewer_for_block`. Whitespace stripped at delimiter boundaries.
- `voting_result`: `classify_result` enum — `accepted | rejected | exonerated | neutral`. **Use the same enum values for both FINDING_N and OOS_N rows** (do not switch to JSONL's `out_of_scope`).
- `vN_*` columns: ordered per `EFFECTIVE_VOTER_FILES` iteration order, same inner loop as `vote_for_id` (FINDING_3 correction). Per FINDING_4 (exonerated 1-2-0 → simpler fix preferred): `vN` columns track effective-voter order, NOT slot identity. When a slot fails, the next successful voter shifts left into the lower `vN` column. Fixture B's column-qualified assertions (FINDING_19) target the post-compaction position.
- `vN_vote`: `YES | NO | EXONERATE | JUDGE_ERROR | ""` (empty if voter file present but no recognized line for this id).
- `vN_correctness`/`vN_severity`/`vN_quality`: enum values from the parser contract, or `""` when missing/unrecognized.
- `vN_uncertain`: `true | false`.

**Field sanitization** (FINDING_8): TSV cells are restricted to enum tokens only (no rationale, no free-form text). The `voting_result` and `vN_*` columns are pre-validated against the documented enums before write; values outside the enum are coerced to `""` and `vN_uncertain=true` (matches the lenient policy). This eliminates the tab/newline/CR injection risk entirely.

### 3. `skills/review/scripts/review-core.sh` (+ sibling `.md`)

Re-emit `FINDINGS_CLASSIFICATION_TSV_FILE` upstream when present (mirrors the existing `YIELD_TSV_FILE` pass-through at lines 631-633) — apply in BOTH the normal-completion path AND the zero-findings branch at lines 434-490 (FINDING_17). Document the new emitted-KV in `skills/review/scripts/review-core.md` alongside `YIELD_TSV_FILE`.

The equality chain `tally-code-votes.sh --review-tmpdir` = `review-core.sh --output-dir` = `review-and-fix.sh round_dir` (for `/implement`) is preserved — no new directory plumbing.

### 4. `scripts/larch-log-batches.sh` (+ sibling `.md`) and `scripts/test-larch-logs-batches.sh` — FINDING_1 (CRITICAL)

Add `review-findings-classification-round-N` rows to `LARCH_LOG_BATCHES`. Since the table uses explicit slug rows and standalone `/review` has `round_cap=5`, enumerate the 5 round slugs: `review-findings-classification-round-1` through `review-findings-classification-round-5`. Extension `.tsv`, mode `replace`, sanitizer `none`. (Per-round flat slugs match the multi-round structure resolved in FINDING_11.)

Update `scripts/larch-log-batches.md` (catalog prose section) to list the new slugs and `scripts/test-larch-logs-batches.sh`:
- Expand expected slug list.
- Widen the extension allowlist to include `.tsv` if not already permitted.
- Add a test case asserting each registered round slug resolves correctly.

### 5. `scripts/larch-log.sh`

Extend the explicit-name allowlist in `round_artifact_included` (around line 89) to include `findings-classification.tsv`. This lets `larch-log.sh write-round` publish the TSV to `larch-logs/implement/<RUN_ID>/round-<N>/findings-classification.tsv` without weakening the generic `*.tsv` exclusion.

### 6. `skills/review/scripts/log-phase.sh` (+ sibling `.md`)

Register the new round-suffixed batch slugs in the case statement at line 37, matching the 5 entries added in item 4. Update `skills/review/scripts/log-phase.md` to extend the documented batch list beyond the current six (FINDING_20 OOS cleanup; effectively in scope here).

### 7. `skills/review/SKILL.md` Steps 0, 3, 4 — FINDING_7

- **Step 0**: add `FINDINGS_CLASSIFICATION_TSV_FILE` to the heavy-worker return-KV bind list (around line 27) so subagent runs propagate the path to the parent.
- **Step 3**: add `FINDINGS_CLASSIFICATION_TSV_FILE` to the wrapper's `review-core.sh` stdout parse list (around line 44) so inline runs bind the path.
- **Step 4**: extend the `log-phase.sh` invocation list (around line 59) to include the appropriate `review-findings-classification-round-${ROUND_NUM}` slug for the current round, using `--payload-file "$FINDINGS_CLASSIFICATION_TSV_FILE"` when the KV is non-empty. One call per round.

### 8. `skills/review/references/heavy-worker.md` — FINDING_7

Add `FINDINGS_CLASSIFICATION_TSV_FILE` everywhere `YIELD_TSV_FILE` is currently listed:
- Step 3 KV preserve line (around line 36).
- Return-footer example (around lines 85-94).
- Parent-binding instructions text.

### 9. `skills/shared/voting-protocol.md` — FINDING_13

Update the `/review` vote-line section (around lines 32-33, 110-111) to authorize `OOS_N:` vote lines for code review (matching the ballot-splitter behavior in `scripts/lib-vote-tally.sh:104-106`). Add `OOS_N:` to the shared examples alongside `FINDING_N:`. This realigns the canonical normative doc with the ballot reality and unblocks the prompt change.

### 10. NEW: `skills/review/scripts/test-findings-classification.sh` (+ sibling `.md`)

Integration harness covering both consumer paths. Fixtures:

- **Fixture A**: synthetic `/implement` Step 5 round 1 with a 2-voter `EFFECTIVE_VOTER_FILES` (voter 3 failed) + `OOS_N` entries. Assert: TSV emitted with rows for every ballot id; columns track post-compaction order (the surviving voters land in `v1_*` and `v2_*`; `v3_*` columns hold empty values per the schema's fixed 3-slot width); `larch-log.sh write-round` publishes `findings-classification.tsv` under `round-1/`.
- **Fixture B**: synthetic standalone `/review --diff` round 1 with 3 judges, lenient missing-rating handling (the voter at index 2 of `EFFECTIVE_VOTER_FILES` — Codex — omits `CORRECTNESS=`). Assert column-qualified: `v2_correctness=""` AND `v2_uncertain=true` (FINDING_19); `voting_result` column equals the no-ratings baseline outcome; vote tally is unaffected.
- **Fixture C**: 0-judge panel (`EFFECTIVE_VOTERS==0`). Assert: TSV emitted via the new pre-exit helper (FINDING_2); one row per ballot id with all voter columns empty; `FINDINGS_CLASSIFICATION_TSV_FILE` KV emitted; tally `main-agent-vote-required` flow proceeds unchanged.
- **Fixture D**: empty-ballot (zero `block_files`). Assert: TSV schema header row emitted; no data rows; `FINDINGS_CLASSIFICATION_TSV_FILE` KV emitted (FINDING_17 — zero-findings path coverage).
- **Fixture E**: standalone `/review --diff` multi-round (round_num=1 then round_num=2). Assert: both `findings-classification-round-1.tsv` AND `findings-classification-round-2.tsv` exist in `$REVIEW_TMPDIR`; both registered slugs publish under `larch-logs/review/<RUN_ID>/` (FINDING_11).
- **Fixture F** (parity regression guard, FINDING_14): all 3 judges emit well-formed votes with axes; assert `parse-judge-vote-and-rating.sh` and `vote_for_id` agree on every line.

Register in `Makefile` under one of the existing `test-harnesses-N` shards.

### 11. UPDATED existing harnesses

- `scripts/test-dispatch-code-voters.sh --section happy` (FINDING_18 — single file with `--section` modes, not split files) — assert new ratings instructions appear in rendered prompt; both `FINDING_N:` and `OOS_N:` examples present; ignore-rule text updated.
- `scripts/test-dispatch-code-voters.sh --section edge-and-r3-claude` — assert retry prefix carries the ratings reminder; OOS-only ballot triggers parse-rate retry (FINDING_5 regression guard).
- `skills/review/scripts/test-tally-code-votes.sh` — assert `FINDINGS_CLASSIFICATION_TSV_FILE` emission + schema; inject ratings into voter outputs in an existing fixture.
- `scripts/test-larch-log-write-round.sh` — assert `findings-classification.tsv` included in published `round-<N>/`.
- `skills/review/scripts/test-log-phase.sh` — assert each new round-suffixed slug is registered and writes payload.
- `scripts/test-larch-logs-batches.sh` (FINDING_1) — assert all 5 new slugs in expected list; `.tsv` extension allowed.

### 12. `docs/run-logs.md`

Document `findings-classification.tsv` in the `round-<N>/` section (under `/implement` review) and add a parallel mention for standalone `/review` per-round flat batches `review-findings-classification-round-N`. Include column semantics from §2 above so downstream consumers don't need to read `tally-code-votes.md` to understand the schema.

### 13. `Makefile`

Register `test-findings-classification` target wired into a `test-harnesses-N` shard.

## Approach

- **Prompt-side change** is contained to `dispatch-code-voters.sh` + `.md`. No new dispatch wrapper.
- **TSV write** lives in `tally-code-votes.sh` via a factored helper called from both the per-block voting path AND the `EFFECTIVE_VOTERS==0` early-exit path (FINDING_2). The empty-ballot edge case writes the header row only (FINDING_17). The new helper also unifies the emit-KV pattern.
- **Single parse per (voter, id)** via L2's `parse-judge-vote-and-rating.sh` feeds both `classify_result` and TSV columns (FINDING_14). Vote tally thresholds remain unchanged (driven by the same `PARSED_VOTE` values that `vote_for_id` would have produced).
- **L2 contract** is pinned in this plan (FINDING_15 / FINDING_16) so L6 implementation is unblocked the moment L2 lands.
- **`/implement` publishing** rides existing `larch-log.sh write-round --source-dir "$REVIEW_TMPDIR"`. Allowlist update in `larch-log.sh`; canonical table update in `larch-log-batches.sh`.
- **`/review` per-round publishing** uses 5 round-suffixed slugs (FINDING_11). Each round's TSV is a separate flat batch under `larch-logs/review/<RUN_ID>/`.
- **Heavy-worker / subagent** path carries `FINDINGS_CLASSIFICATION_TSV_FILE` end-to-end (FINDING_7).
- **Shared voting-protocol.md** updated to authorize `OOS_N:` vote lines (FINDING_13) — single normative source aligns with ballot reality.
- **TSV cells are enum-only** (FINDING_8) — eliminates injection risk by construction.

## Edge cases

- **Missing voter (degraded panel)** — `EFFECTIVE_VOTER_FILES` shrinks; `vN` columns track compact order (FINDING_4 exonerated path: simpler than slot-positional plumbing). Fixture A covers the 2-voter shape; Fixture C covers 0 voters.
- **JUDGE_ERROR for one or more voters** — `vN_vote=JUDGE_ERROR`, axis columns empty (parser sees no recognized rating tokens). Existing threshold behavior unchanged.
- **`OOS_N:` ballot entries** — same row schema; `voting_result` uses the same enum as FINDING_N rows.
- **Empty ballot (zero findings)** — header row only; `FINDINGS_CLASSIFICATION_TSV_FILE` still emitted (Fixture D, FINDING_17).
- **Voter file present but contains no recognized vote line for a given finding** — `vN_vote=""`, all axes empty (distinct from `JUDGE_ERROR`).
- **Rating tokens emitted in unexpected order** — parser is token-position-agnostic for axes; vote token remains positional immediately after `<ID>:` (`vote_for_id` invariant from `lib-vote-tally.sh:12-29`).
- **Judge emits a rating value outside the documented enum** — lenient policy uniformly: consumer treats the axis as missing, records `""` and sets `UNCERTAIN=true`. (FINDING_9 resolved — single rule.)
- **Judge emits embedded tabs/newlines in tokens** — TSV cells are enum-only, so anything not matching the documented enum gets coerced to `""` (FINDING_8).

## Failure modes

1. **L2 parser API divergence from this plan's contract** (FINDING_15) — most likely when L2's design re-asks the same questions and picks differently. Earliest signal: L6 Fixture F fails because `parse-judge-vote-and-rating.sh` doesn't accept positional argv or emits different KV keys. Mitigation: L6 implementation Step 1 reads L2's shipped `parse-judge-vote-and-rating.md` first; adapts the single call site; if KV keys differ, update only the `PARSED_*` extraction names.
2. **L2 parser exits non-zero for soft gaps** (FINDING_16) — `set -euo pipefail` in `tally-code-votes.sh` aborts. Earliest signal: harness Fixture B aborts mid-tally with no TSV emission. Mitigation: capture parser stdout via `_out=$("$PARSER" ... 2>/dev/null) || true` and parse stdout regardless; emit a `WARN=` breadcrumb when rc != 0 so the regression is visible without aborting.
3. **TSV column desync between vote tally and TSV** (FINDING_14 regression) — if a future refactor reintroduces `vote_for_id` for the tally inputs while the TSV stays on the new parser, the two could diverge silently. Earliest signal: Fixture F (parity guard) fails. Mitigation: Fixture F is the regression guard; document the single-parse invariant in `tally-code-votes.md`.

## Testing strategy

- New `test-findings-classification.sh` integration harness with six fixtures (A-F above) covering both consumer paths, the multi-round /review case, the empty-ballot edge, and the parity guard.
- Updated existing harnesses (`test-dispatch-code-voters.sh --section happy` + `--section edge-and-r3-claude`, `test-tally-code-votes.sh`, `test-larch-log-write-round.sh`, `test-log-phase.sh`, `test-larch-logs-batches.sh`).
- `make lint-bash32` after shell edits. `bash scripts/relevant-checks.sh` after any change touching `scripts/` or `skills/review/`.
- Manual smoke at implementation time: run `/review --diff` against a small real diff in `larch4` (2-3 rounds expected) and verify all per-round TSVs land under `larch-logs/review/<RUN_ID>/`. Same for an `/implement` round via `/implement --merge` on a tiny issue — verify TSV appears under `larch-logs/implement/<RUN_ID>/round-<N>/`.

diff_lines: 480


## Acceptance

- All existing unit / harness tests pass.
- `make lint-bash32` clean.
- `bash scripts/relevant-checks.sh` clean after every edit touching `scripts/` or `skills/review/`.
- New `skills/review/scripts/test-findings-classification.sh` integration harness passes (6 fixtures: A-F).
- Updated harnesses pass: `test-dispatch-code-voters.sh --section happy` + `--section edge-and-r3-claude`, `test-tally-code-votes.sh`, `test-larch-log-write-round.sh`, `test-log-phase.sh`, `test-larch-logs-batches.sh`.
- Manual smoke: one `/review --diff` run produces `findings-classification-round-N.tsv` artifacts under `larch-logs/review/<RUN_ID>/`; one `/implement` round publishes `findings-classification.tsv` under `larch-logs/implement/<RUN_ID>/round-<N>/`.
- Blocking: do not start L6 implementation until #2671 (L2) lands and `scripts/parse-judge-vote-and-rating.md` pins the contract enumerated in this plan.

diff_lines: 480
