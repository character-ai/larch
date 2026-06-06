# Review Round 1

- Mode: `diff`
- 21 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: code-quality: python/oos.py:32-34 vs skills/implement/scripts/oos-non-security-block-count.awk:10
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Legacy FINDING header detection differs between Python and awk ports. A header like ### FINDING_1: Title [OUT_OF_SCOPE] is counted by bash gate scripts but not by python/oos.py; Python ship soak and bash ship disagree on the same accepted file. Align Python with awk (FINDING prefix plus [OUT_OF_SCOPE] anywhere on line) or share one predicate; add a cross-port regression fixture.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: skills/review/scripts/emit-tally.sh:899-909 / skills/shared/scripts/oos-serialize.sh:55-71
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT=0 serialize fallback still emits ### FINDING_N: headers; parse-input.sh only files ### OOS_N:. Accepted tagged OOS only via serialize path: gate may flag disposition gap but /issue batch parser still cannot file blocks. Normalize serialize output to ### OOS_<seq>: or invoke normalize-oos-block-header.sh in the serialize branch.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: python/oos.py:32-35 + skills/implement/scripts/oos-non-security-block-count.awk:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy FINDING header matching differs between awk (index anywhere on line) and Python (tag must follow colon immediately). A header like `### FINDING_1: Title [OUT_OF_SCOPE]` is counted by bash gates but ignored by python/ship._oos_gate, reintroducing silent pass on Python ship. Align matchers; add shared parity fixtures for both canonical and delayed-tag header shapes.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/review/scripts/test-tally-code-votes.sh + skills/review/scripts/test-emit-tally.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No single test chains tally-code-votes.sh output into emit-tally.sh with real review-tally.env. Miswired tally-file or parent copy ordering could restore emit-tally overwrite while isolated harnesses stay green. Add one chained tally→emit-tally case asserting normalized headers and awk count preserved.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1487-1490
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Multi-round skipped OOS sequence continuation is untested. Second-round skipped OOS could reuse `### OOS_1:` and break filing ordinals/dedup. Two-round skipped-routing test with pre-seeded accumulated-oos.md expecting `### OOS_2:` and awk count 2.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: python/test_ship.py
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan cited test_ship*.py for Python gate coverage; no legacy-header _oos_gate test added. Ship-layer regression in accepted-file resolution could slip past oos.py unit tests. One unmocked ship._oos_gate test with legacy-header accepted file and missing disposition.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: scripts/lib-vote-tally.sh:60-68, skills/review/scripts/tally-code-votes.sh:538-600, python/oos.py:32-79, skills/implement/scripts/oos-non-security-block-count.awk:21-33
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Producer is_security_block matches only unfenced focus-area=security (equals) while the gate excludes only dedicated - **focus-area**: security lines; common security reviewer shapes (colon field or header `security` tag) can enter the public accepted-OOS sink. A voted-accepted ### FINDING_N: [OUT_OF_SCOPE] security finding with header `security` focus tag or - **focus-area**: security that is_security_block misses is normalized to ### OOS_<seq>: and the disposition gate now obligates public filing instead of silently dropping it, converting a mis-routed security finding into a forced public GitHub issue. Unify security classification at the producer: extend is_security_block to match gate/materialize-manifest colon field lines (and optionally header security tags); never write security-classified blocks to oos-accepted-review.md; route them to the local security audit sink.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/review/scripts/tally-code-votes.sh:123 and skills/review-and-fix/scripts/review-and-fix.sh:155-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Tally resets OOS_WRITE_SEQ per round while append_round_oos_artifact accumulates without cross-round renumbering. Multi-round review accumulates multiple ### OOS_1: blocks in accumulated-oos.md / oos-accepted-review.md, confusing operators and batch filing even though ordinal counting still works. Seed tally seq from accumulated block count on implement path or renumber in append_round_oos_artifact.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: python/oos.py:32-35
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Python legacy FINDING header regex requires [OUT_OF_SCOPE] immediately after the id; awk matches the tag anywhere on the line. A header like ### FINDING_1: Title text [OUT_OF_SCOPE] is counted by ship-pr.sh but not ship.py, so disposition can pass in one driver and fail in the other. Align Python with awk (e.g. allow tag anywhere on the header line) and add a trailing-tag parity fixture to python/test_oos.py and test-oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.


### FINDING_23: architecture: skills/review/scripts/tally-code-votes.sh:123,590-601; skills/review-and-fix/scripts/review-and-fix.sh:155-162
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Per-round OOS_WRITE_SEQ resets to 0 while append_round_oos_artifact concatenates rounds without renumbering. Multi-round Step 5 with one accepted OOS per round accumulates duplicate ### OOS_1: blocks, confusing /issue parsing and dedup even though the gate counts blocks. Continue seq from accumulated-oos.md block count before tally writes, or renumber accumulated content after each append_round_oos_artifact.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: skills/review/scripts/emit-tally.sh:155-161
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Preserve branch trusts OOS_ACCEPTED_COUNT alone and skips serialize/truncate without validating markdown sink content. Security-only accepted OOS or env/file desync yields OOS_ACCEPTED_COUNT>0 with an empty oos-accepted-review.md; gate sees zero blocks and passes, silently dropping items. Preserve only when awk non-security count on the sink is >0 (or matches expected non-security tally); otherwise fall through and warn.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: skills/review/scripts/emit-tally.sh:162-165; skills/shared/scripts/oos-serialize.sh:55-63
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT==0 fallback still serializes legacy ### FINDING_N: headers without normalization; reader ignores [OOS]-only tags. Standalone / 0-judge paths that rely on serialize emit [OOS]-tagged FINDING blocks that counters skip and parse-input.sh cannot file. Normalize in oos-serialize.sh or extend reader backstop to [OOS]-tagged FINDING headers; add serialize-path regression coverage.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1444-1447
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Skipped-path seq init uses awk that ignores bare ### FINDING_N: in accumulated-oos.md. Resume after a pre-fix run leaves bare FINDING blocks uncounted; new normalized blocks reuse OOS_1 while legacy blocks stay gate-invisible. Initialize seq from producer-aware counting or normalize existing accumulated content before appending.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/review/scripts/emit-tally.sh:671-685 and skills/shared/scripts/oos-serialize.sh:55-61
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The OOS_ACCEPTED_COUNT==0 path still serializes legacy FINDING headers without normalization. Standalone emit paths can pass reader-hardened gates yet fail /issue filing because parse-input.sh requires ### OOS_N:. Normalize oos-serialize output via the shared helper or document and block filing on that path.
- **Suggested revision**: Address the concern above.


### FINDING_31: **risk-integration** `skills/review/scripts/emit-tally.sh:155-161` — The new preserve branch keys only on `OOS_ACCEPTED_COUNT > 0` and never checks that `$OOS_ACCEPTED_FILE` actually contains the expected non-security blocks (e.g., via `oos-non-security-block-count.awk`). That counter is incremented for security-held accepted OOS as well (`skills/review/scripts/tally-code-votes.sh:585-601`), so `OOS_ACCEPTED_COUNT` can be > 0 while the public sink is legitimately empty. More importantly, any future desync where the tally env says > 0 but the accepted file is empty or short (partial write, stale env, or `copy_to_parent` propagating an empty round file) will skip both `oos-serialize.sh` and the truncate branch, leaving an empty sink; the disposition gate then counts zero blocks and passes, reproducing the silent-drop failure mode #3550 was meant to close. **Suggested fix:** Gate the preserve branch on `awk -f …/oos-non-security-block-count.awk "$OOS_ACCEPTED_FILE" > 0` (or a dedicated non-security tally counter), not raw `OOS_ACCEPTED_COUNT`; when the env count and awk block count disagree, log a warning and fall back to the serialize path when `oos.md` exists, otherwise fail closed.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/emit-tally.sh:155-161` — The new preserve branch keys only on `OOS_ACCEPTED_COUNT > 0` and never checks that `$OOS_ACCEPTED_FILE` actually contains the expected non-security blocks (e.g., via `oos-non-security-block-count.awk`). That counter is incremented for security-held accepted OOS as well (`skills/review/scripts/tally-code-votes.sh:585-601`), so `OOS_ACCEPTED_COUNT` can be > 0 while the public sink is legitimately empty. More importantly, any future desync where the tally env says > 0 but the accepted file is empty or short (partial write, stale env, or `copy_to_parent` propagating an empty round file) will skip both `oos-serialize.sh` and the truncate branch, leaving an empty sink; the disposition gate then counts zero blocks and passes, reproducing the silent-drop failure mode #3550 was meant to close. **Suggested fix:** Gate the preserve branch on `awk -f …/oos-non-security-block-count.awk "$OOS_ACCEPTED_FILE" > 0` (or a dedicated non-security tally counter), not raw `OOS_ACCEPTED_COUNT`; when the env count and awk block count disagree, log a warning and fall back to the serialize path when `oos.md` exists, otherwise fail closed.
- **Suggested revision**: Address the concern above.


### FINDING_32: **risk-integration** `skills/review/scripts/emit-tally.sh:162-165` — The `OOS_ACCEPTED_COUNT == 0` fallback still routes through `oos-serialize.sh`, which copies legacy `### FINDING_N:` headers verbatim into `oos-accepted-review.md` (`skills/shared/scripts/oos-serialize.sh:55-62`). This branch is unchanged by the producer normalization work in `tally-code-votes.sh` / `review-and-fix.sh`, so any caller that reaches emit with a zero count while accepted tagged OOS live only in `oos.md` (standalone emit, env desync, or a future tally bypass) will again produce headers that `skills/issue/scripts/parse-input.sh:377` cannot file even though the reader backstop may now count them for the gate. **Suggested fix:** Run `normalize-oos-block-header.sh` over `oos-serialize.sh` output (or inside serialize itself) so the count=0 fallback emits canonical `### OOS_<seq>:` blocks, keeping the gate, filing parser, and counters aligned on every path.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/emit-tally.sh:162-165` — The `OOS_ACCEPTED_COUNT == 0` fallback still routes through `oos-serialize.sh`, which copies legacy `### FINDING_N:` headers verbatim into `oos-accepted-review.md` (`skills/shared/scripts/oos-serialize.sh:55-62`). This branch is unchanged by the producer normalization work in `tally-code-votes.sh` / `review-and-fix.sh`, so any caller that reaches emit with a zero count while accepted tagged OOS live only in `oos.md` (standalone emit, env desync, or a future tally bypass) will again produce headers that `skills/issue/scripts/parse-input.sh:377` cannot file even though the reader backstop may now count them for the gate. **Suggested fix:** Run `normalize-oos-block-header.sh` over `oos-serialize.sh` output (or inside serialize itself) so the count=0 fallback emits canonical `### OOS_<seq>:` blocks, keeping the gate, filing parser, and counters aligned on every path.
- **Suggested revision**: Address the concern above.


### FINDING_43: **code-quality** `skills/review/scripts/test-tally-code-votes.sh:382-390` — The plan called for dual-sink coverage (standalone alias + implement mirror), but the only dual-sink assertion is in standalone case1 (`:82-83`). The `--session-env-path` case checks classification TSV naming only and does not assert that `$(dirname session.env)/oos-accepted-review.md` receives normalized accepted OOS, has no bare `### FINDING_` header, or has `awk` count `== 1` without duplicating the round-tmpdir sink. That leaves the `/implement` parent-mirror path unguarded. **Suggested fix:** Extend the session-bound case (or add `case_session_oos_mirror`) with an accepted OOS ballot, `--session-env-path`, and assertions on both `$TMP/round-N/oos-accepted-review.md` and `$TMP/oos-accepted-review.md` (parent) for canonical headers, `awk` count `== 1`, and byte-identical normalized content between sinks.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-tally-code-votes.sh:382-390` — The plan called for dual-sink coverage (standalone alias + implement mirror), but the only dual-sink assertion is in standalone case1 (`:82-83`). The `--session-env-path` case checks classification TSV naming only and does not assert that `$(dirname session.env)/oos-accepted-review.md` receives normalized accepted OOS, has no bare `### FINDING_` header, or has `awk` count `== 1` without duplicating the round-tmpdir sink. That leaves the `/implement` parent-mirror path unguarded. **Suggested fix:** Extend the session-bound case (or add `case_session_oos_mirror`) with an accepted OOS ballot, `--session-env-path`, and assertions on both `$TMP/round-N/oos-accepted-review.md` and `$TMP/oos-accepted-review.md` (parent) for canonical headers, `awk` count `== 1`, and byte-identical normalized content between sinks.
- **Suggested revision**: Address the concern above.


### FINDING_44: **code-quality** `skills/review/scripts/test-tally-code-votes.sh:473-500` — The new `case6a_norm` scope-drift case checks stdout `OOS_ACCEPTED_COUNT` and normalized headers but, unlike case1 (`:84`), does not assert `OOS_ACCEPTED_COUNT` was appended to `$TMP/review-tally.env`. The plan explicitly required that guard because emit-tally reads `--tally-file` (the env file), not stdout KV; dropping the env append while keeping `emit_kv` would reproduce the overwrite/truncate bug on the production path while unit tally tests still pass. **Suggested fix:** Add `got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env"); assert_eq ... "1"` to `case6a_norm` (and optionally to case6a as a zero-count control).
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-tally-code-votes.sh:473-500` — The new `case6a_norm` scope-drift case checks stdout `OOS_ACCEPTED_COUNT` and normalized headers but, unlike case1 (`:84`), does not assert `OOS_ACCEPTED_COUNT` was appended to `$TMP/review-tally.env`. The plan explicitly required that guard because emit-tally reads `--tally-file` (the env file), not stdout KV; dropping the env append while keeping `emit_kv` would reproduce the overwrite/truncate bug on the production path while unit tally tests still pass. **Suggested fix:** Add `got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env"); assert_eq ... "1"` to `case6a_norm` (and optionally to case6a as a zero-count control).
- **Suggested revision**: Address the concern above.


### FINDING_47: **code-quality** `skills/review-and-fix/scripts/test-review-and-fix.sh:1515-1521` — Skipped-routing assertions verify single-round normalization and `awk` count `== 1`, but the implementation continues `OOS_WRITE_SEQ` from the existing `accumulated-oos.md` block count across rounds (`review-and-fix.sh:1487-1490`). There is no multi-round skipped test proving round-2 append renumbers to `### OOS_2:` (not `OOS_1` again) and keeps `awk` count aligned with accumulated blocks. **Suggested fix:** Add a two-round skipped-routing case with a pre-seeded `accumulated-oos.md` containing one `### OOS_1:` block, then assert the new skipped block becomes `### OOS_2:` and total `awk` count `== 2`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/test-review-and-fix.sh:1515-1521` — Skipped-routing assertions verify single-round normalization and `awk` count `== 1`, but the implementation continues `OOS_WRITE_SEQ` from the existing `accumulated-oos.md` block count across rounds (`review-and-fix.sh:1487-1490`). There is no multi-round skipped test proving round-2 append renumbers to `### OOS_2:` (not `OOS_1` again) and keeps `awk` count aligned with accumulated blocks. **Suggested fix:** Add a two-round skipped-routing case with a pre-seeded `accumulated-oos.md` containing one `### OOS_1:` block, then assert the new skipped block becomes `### OOS_2:` and total `awk` count `== 2`.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/scripts/oos-non-security-block-count.awk:10-14 / python/oos.py:32-35 / skills/review/scripts/emit-tally.sh:671-684
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Reader backstop counts legacy FINDING [OUT_OF_SCOPE] headers but OOS_ACCEPTED_COUNT==0 still runs oos-serialize which emits vote-rejected tagged blocks without Result filtering. All OOS proposals rejected (OOS_ACCEPTED_COUNT=0, non-empty oos.md): serialize copies rejected FINDING blocks into oos-accepted-review.md; gate now reports non_security_oos>=1 and blocks ship with no accepted OOS to file — regression vs pre-#3550 silent pass on FINDING headers. Filter oos-serialize to Result=accepted only, teach counter to skip Result=rejected bodies, or skip serialize when only rejected OOS remain.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/implement/scripts/oos-non-security-block-count.awk:10 / python/oos.py:32-34
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] awk uses index() for [OUT_OF_SCOPE] anywhere on FINDING header line; Python requires tag immediately after colon. Header ### FINDING_1: title [OUT_OF_SCOPE] later: awk count=1 Python count=0; bash gate blocks but python ship gate may pass on same artifact. Align awk and Python header matchers on the same colon-adjacent tag rule.
- **Suggested revision**: Address the concern above.


