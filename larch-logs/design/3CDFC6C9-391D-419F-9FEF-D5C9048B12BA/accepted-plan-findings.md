### FINDING_1: Add `scripts/larch-log-batches.sh` registration (and md + harness)
- **Concern**: Plan registers `review-findings-classification` only in `skills/review/scripts/log-phase.sh`, but `log-phase.sh` ultimately calls `scripts/larch-log.sh write`, which validates batch slugs through `LARCH_LOG_BATCHES` in `scripts/larch-log-batches.sh` (resolution via `larch_log_batch_info` / `lib-larch-log.sh:66-72`). Without an entry there, every `log-phase.sh --batch review-findings-classification` call fails closed with `unknown batch`. Also impacts `/implement` publishing through `larch-log.sh write-round`.
- **Proposed resolution**: Extend Files-to-modify to include `scripts/larch-log-batches.sh` (add row with extension `.tsv`, mode `replace`, sanitizer `none`), `scripts/larch-log-batches.md` (catalog prose), and `scripts/test-larch-logs-batches.sh` (expected slug list + widen `.tsv` extension allowlist if required). Raised by ~14 of 16 reviewers (universal).


### FINDING_10: `FINDINGS_CLASSIFICATION_TSV_FILE` emit must not inherit `YIELD_TSV_FILE`'s manifest gate
- **Concern**: Plan says emit `FINDINGS_CLASSIFICATION_TSV_FILE=<path>` "alongside the existing `YIELD_TSV_FILE` emit." But `tally-code-votes.sh:632-633` emits `YIELD_TSV_FILE` only when `MANIFEST_FILE` is set AND the yield file exists. Voting runs without a manifest in many configurations; classification telemetry would be dropped.
- **Proposed resolution**: Emit `FINDINGS_CLASSIFICATION_TSV_FILE` whenever the classification file is written, independent of `MANIFEST_FILE`. Document in plan with explicit `[[ -f "$CLASSIFICATION_TSV" ]] && emit_kv ...` pattern. Raised by ~3 reviewers.


### FINDING_11: Standalone `/review --diff` multi-round overwrites single TSV file
- **Concern**: Plan defines `$REVIEW_TMPDIR/findings-classification.tsv` (single basename) and one flat batch slug, but `/review --diff` wrapper supports up to 5 rounds (`round_cap=5` in `skills/review/SKILL.md:44`); each `review-core.sh` round writes the same `$REVIEW_TMPDIR` location. Round 2 overwrites round 1; Step 4 batches only the final round.
- **Proposed resolution**: Either use round-scoped filenames (e.g., `findings-classification-round-N.tsv`) and round-suffixed batch slugs (`review-findings-classification-round-N`), or stage round artifacts inside a per-round subdir under `$REVIEW_TMPDIR/round-N/` and have Step 4 publish each one. Add a multi-round standalone fixture. Raised by ~3 reviewers.


### FINDING_12: `reviewer_slots` and `voting_result` TSV column semantics underspecified
- **Concern**: Plan names `reviewer_slots` and `voting_result` columns without defining code-review semantics. These names overlap with JSONL vocabulary (`reviewer_slots` is a normalized array there; `outcome` uses `out_of_scope` for OOS rows). In `tally-code-votes.sh`, `reviewer_for_block` returns free-form attribution prose and `classify_result` emits `accepted|rejected|exonerated|neutral`. Consumers can't join the TSV with JSONL artifacts safely.
- **Proposed resolution**: Pin `reviewer_slots` = originating ballot reviewer attribution string (specify delimiter — likely "+" — and whitespace rules); `voting_result` = `classify_result` enum {`accepted|rejected|exonerated|neutral`} for BOTH `FINDING` and `OOS` rows (do not switch to `out_of_scope` for OOS rows). Mirror the rule in `docs/run-logs.md`. Raised by ~2 reviewers (dynamic schema archetype) — but load-bearing for downstream consumers.


### FINDING_13: voting-protocol.md says `/review` votes always use `FINDING_N:`, plan introduces `OOS_N:` votes
- **Concern**: `skills/shared/voting-protocol.md:32-33,110-111` (normative shared contract) says `/review` always uses `FINDING_N:` vote lines for all items including `[OUT_OF_SCOPE]`. The plan introduces `OOS_N:` vote lines (matching `split_ballot_to_blocks` headings in `lib-vote-tally.sh:104-106`). This is a real conflict between the shared protocol doc and the ballot-splitter behavior; the prompt change cannot land without resolving which is canonical.
- **Proposed resolution**: Either (a) keep the voter contract on `FINDING_N:`-only for code-review (the ballot still has `### OOS_N:` headings but voters cast votes using the parent `FINDING_N` index) — minimal change but requires reconciling with how `vote_for_id` keys by block id; or (b) update `voting-protocol.md` to authorize `OOS_N:` votes for code review. Recommend (b): align the shared protocol with the ballot-splitter reality, add `OOS_N:` to the shared examples, and accept the prompt change. Raised by 1 reviewer (Cursor-Requirements) — singular but load-bearing.


### FINDING_14: Two-parser disagreement risk (vote_for_id vs parse-judge-vote-and-rating.sh)
- **Concern**: After the change, `classify_result` still consumes `vote_for_id` for vote outcomes, while the new TSV writer uses `scripts/parse-judge-vote-and-rating.sh` for vote + axes. On malformed vote lines, the two parsers could yield different `vN_vote` results from the actual `voting_result` (Tally column 3). The TSV becomes internally contradictory.
- **Proposed resolution**: Parse each `(voter_file, ballot_id)` once via `parse-judge-vote-and-rating.sh` and feed both `classify_result` inputs and the TSV columns from that single parse. Alternative: keep `vote_for_id` as authoritative and use the new parser only for the 4 axis tokens; add a harness assertion that the two parsers agree on every fixture line. Raised by ~3 reviewers.


### FINDING_15: Parser API contract underspecified
- **Concern**: Plan references `scripts/parse-judge-vote-and-rating.sh` with "voter file + ballot id" but doesn't pin argv order (flags vs positional), stdout format (KV lines? JSON? `lib-quiet.sh` FD 3?), exit-code semantics (success / partial-parse / total-failure), or field names. L2 could ship an API incompatible with the L6 call site; "adapt during implementation" is too vague for a blocked-on dependency.
- **Proposed resolution**: Block on L2 finalizing `scripts/parse-judge-vote-and-rating.md` with explicit argv contract (recommend positional `<voter_file> <ballot_id>`), stdout KV schema (`PARSED_VOTE=`, `PARSED_CORRECTNESS=`, etc.), exit-code rules (0 when vote token is recognized regardless of axis quality, non-zero only on hard parser failures). Add the contract excerpt to the L6 plan or cross-reference it. Raised by ~2 reviewers (dynamic L2-bridge archetype).


### FINDING_16: `set -euo pipefail` aborts tally on parser non-zero exit
- **Concern**: `tally-code-votes.sh:6` runs under `set -euo pipefail`. If L2's `parse-judge-vote-and-rating.sh` ever exits non-zero — even for "soft" rating gaps that should fall through to the lenient policy — the entire tally aborts before the consumer-side fill can run. Lenient policy is unreachable.
- **Proposed resolution**: Co-design with L2: parser MUST exit 0 whenever the vote token is recognized (rating gaps are soft fields, mapped to UNCERTAIN=true by consumer). Hard failures (no recognized vote, IO error) are non-zero. Document explicitly in `parse-judge-vote-and-rating.md`. Alternatively, the consumer captures via `_out=$("$PARSER" ... 2>/dev/null) || true` and parses stdout regardless. Raised by ~1 reviewer (Cursor-L2-bridge).


### FINDING_17: Zero-findings (empty ballot) branch pass-through missing
- **Concern**: `review-core.sh:434-490` zero-findings branch only re-emits `VOTING_TALLY_FILE`; it doesn't reach the `YIELD_TSV_FILE`-style pass-through at lines 631-633. The plan's "empty ballot → header-only TSV" edge case has no path to `log-phase.sh` from this branch even if `tally-code-votes.sh` somehow writes the header.
- **Proposed resolution**: Extend `review-core.sh` zero-findings branch to also call `kv_get`+`emit_kv` for `FINDINGS_CLASSIFICATION_TSV_FILE`. Document in `review-core.md`. Add a zero-findings header-only fixture. Raised by ~3 reviewers.


### FINDING_18: Plan references nonexistent `test-dispatch-code-voters-happy.sh` / `-edge-and-r3-claude.sh` files
- **Concern**: Plan Files-to-modify item 8 names `scripts/test-dispatch-code-voters-happy.sh` and `scripts/test-dispatch-code-voters-edge-and-r3-claude.sh` as separate files. The repo has a single `scripts/test-dispatch-code-voters.sh` with `--section happy` / `--section edge-and-r3-claude` runtime modes (Makefile targets `test-dispatch-code-voters-happy` invoke `test-dispatch-code-voters.sh --section happy`).
- **Proposed resolution**: Replace the two filenames in plan item 8 with `scripts/test-dispatch-code-voters.sh --section happy` and `scripts/test-dispatch-code-voters.sh --section edge-and-r3-claude` (plus sibling `.md`). Raised by 1 reviewer (Codex-L2-bridge).


### FINDING_19: Fixture B assertions not column-qualified
- **Concern**: Plan Fixture B description says "assert that voter's row has `correctness=""` and `uncertain=true`" but doesn't bind to which slot column (`v1_correctness`? `v2_correctness`?). Harness author may assert the wrong slot.
- **Proposed resolution**: Specify Fixture B assertions against `vN_correctness` and `vN_uncertain` for a known slot ordering (e.g., "voter 2 — Codex — omits `CORRECTNESS=` → assert `v2_correctness=""` and `v2_uncertain=true`, and `voting_result` column equals the no-ratings baseline outcome"). Raised by 1 reviewer (Cursor-L2-bridge).

---


### FINDING_2: Fixture C / 0-judge panel contradicts `EFFECTIVE_VOTERS==0` early-exit
- **Concern**: Plan places the TSV writer inside the per-block voting loop in `tally-code-votes.sh`, but the `EFFECTIVE_VOTERS==0` branch at `tally-code-votes.sh:252-280` exits before that loop runs. Fixture C asserts per-ballot rows under a 0-judge panel; that fixture cannot pass as written. Same gap applies to the zero-findings (empty ballot) edge case at plan line 64-65.
- **Proposed resolution**: Either (a) factor a shared helper that iterates `block_files` once and writes the classification header + per-id rows with empty voter columns before the 0-voter exit, then `emit_kv FINDINGS_CLASSIFICATION_TSV_FILE` in that branch; or (b) redefine Fixture C as a non-empty panel where every voter file returns `JUDGE_ERROR` for every block. Either choice must also cover the zero-findings empty-ballot case with a header-only TSV. Raised by ~12 of 16 reviewers.


### FINDING_3: Plan says "`EFFECTIVE_VOTERS` order" but that symbol is an integer count
- **Concern**: Plan Files-to-modify item 2 says column ordering follows "`EFFECTIVE_VOTERS` ordering used elsewhere", but in `tally-code-votes.sh:249-250,321,631` `EFFECTIVE_VOTERS` is the numeric quorum count; ordered iteration uses the `EFFECTIVE_VOTER_FILES` array (lines 240-247, 311). Implementers may key off the wrong structure and desync `vN_*` columns from `vote_for_id` inputs.
- **Proposed resolution**: Update plan wording to "EFFECTIVE_VOTER_FILES iteration order (same inner loop variable as `vote_for_id`)". Raised by ~8 reviewers.


### FINDING_5: `OOS_N` missing from `check_voter_parse_rate`
- **Concern**: `dispatch-code-voters.sh:142-163` `check_voter_parse_rate` counts only `### FINDING_[0-9]+:` headings via `ids_count` and the per-id grep loop. With the plan extending ballots to also cover `OOS_N:`, OOS-only or mixed-OOS ballots can pass parse-rate even when judges emit prose for every OOS line; the retry path never fires and OOS rows become avoidable JUDGE_ERROR.
- **Proposed resolution**: Extend the grep/awk patterns to `^### (FINDING_[0-9]+|OOS_[0-9]+):` everywhere parse-rate enumerates ballot ids; update diagnostic message text to "ballot items" (not "findings"); add an OOS-only / mixed-OOS retry fixture to `scripts/test-dispatch-code-voters.sh --section edge-and-r3-claude`. Raised by ~9 reviewers.


### FINDING_6: Voter prompt examples and silent-ignore rule are `FINDING_N`-only
- **Concern**: `make_voter_prompt_file()` at `scripts/dispatch-code-voters.sh:64-69` shows examples only for `FINDING_N:` lines and instructs: "Lines that do not start with FINDING_N: followed by YES, NO, or EXONERATE are silently ignored." When the plan extends to `OOS_N:` votes, the ignore rule and examples drift from the actual `split_ballot_to_blocks` headings that already accept `OOS_N`.
- **Proposed resolution**: Add explicit parallel `OOS_N:` example lines with the same rating-token shape, and rewrite the "silent ignore" instruction to name both `FINDING_N` and `OOS_N` (or "the ballot's exact id prefix"). Update `VOTER_PARSE_RATE_RETRY_PREFIX` in parallel. Raised by ~6 reviewers.


### FINDING_7: Heavy-worker / subagent KV propagation omitted
- **Concern**: `skills/review/SKILL.md` Step 0 (line 27) and Step 3 (line 44) parse only scout KVs + `YIELD_TSV_FILE`. `skills/review/references/heavy-worker.md` (lines 36-37, 85-94) preserves and returns the same narrow set. A `/review --diff --subagent` worker can produce `findings-classification.tsv` in `$REVIEW_TMPDIR`, but the parent never binds `FINDINGS_CLASSIFICATION_TSV_FILE` and Step 4 has no payload path for `log-phase.sh`.
- **Proposed resolution**: Add `FINDINGS_CLASSIFICATION_TSV_FILE` to: SKILL.md Step 0/3 parse list, SKILL.md Step 4 `log-phase.sh --payload-file` wiring, `heavy-worker.md` preserve line + footer example. Mirror the existing `YIELD_TSV_FILE` pattern. Raised by ~11 reviewers.


### FINDING_8: TSV field sanitization missing for judge tokens
- **Concern**: Raw judge tokens copied "verbatim" into TSV cells could contain literal tabs or newlines (especially in `rationale` portions if those land in the TSV, or if a misbehaving judge emits multi-line tokens). This breaks column alignment / injects synthetic rows, and the audit consumer corrupts silently.
- **Proposed resolution**: Define field escaping in `tally-code-votes.sh` before writing cells — either strip/replace `\t`/`\n`/`\r` with spaces, or restrict TSV cell values to enum tokens only (rationale never in TSV). Document the rule in `tally-code-votes.md` and the TSV schema. Raised by ~6 reviewers (some tagged security, others nit).


### FINDING_9: Lenient policy internal contradiction (UNCERTAIN=true vs verbatim raw)
- **Concern**: Plan line 17 says "missing or unparseable rating tokens become `UNCERTAIN=true` with empty values for the other axes". Lines 67-68 (Edge cases) say "Judge emits a rating value outside the documented enum — lenient policy: consumer records the raw token verbatim (no normalization)". These contradict for the "out-of-enum value" case. Fixture B can't be written until policy is settled.
- **Proposed resolution**: Pick one rule and align prompt, parser call-site handling, TSV tests, and docs. Recommended: out-of-enum value → consumer treats as unrecognized → empty axes + `UNCERTAIN=true` (consistent with line 17, simpler downstream). Drop line 68's verbatim-recording sentence. Raised by ~7 reviewers.


