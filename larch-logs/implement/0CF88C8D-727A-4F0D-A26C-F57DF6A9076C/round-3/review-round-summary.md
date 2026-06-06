# Review Round 3

- Mode: `diff`
- 34 accepted, 4 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/review/scripts/tally-code-votes.sh:127-128 and skills/review-and-fix/scripts/review-and-fix.sh:1446-1447
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate ad-hoc OOS block counting for OOS_WRITE_SEQ instead of reusing oos-non-security-block-count.awk as planned. Ad-hoc counter includes bare ### FINDING_N: headers the gate counter ignores, so sequence seeding and disposition counting can diverge on mixed legacy content. Call oos-non-security-block-count.awk (or a shared helper) for seq initialization in both producers.
- **Suggested revision**: Address the concern above.


### FINDING_11: security: skills/review-and-fix/scripts/review-and-fix.sh:203-226
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Skipped-path is_security_block still only matches focus-area = security prose, not the expanded lib-vote-tally routing rules added in this branch. A coder SKIPPED block with - **focus-area**: security (no =) or a [security] heading tag is normalized into accumulated-oos.md / oos-accepted-review.md and can reach public OOS filing even though tally would hold it locally. Reuse scripts/lib-vote-tally.sh is_security_block (or one shared helper) instead of the inline Python copy.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: python/oos.py:36-40
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Python _SECURITY_FOCUS_RE was not updated when oos-non-security-block-count.awk gained backtick-stripped unbolded focus-area matching. Accepted file with - **focus-area**: `security-hardening` yields non_security_oos=0 in bash but count_non_security=1 in ship.py, so python and bash gates disagree. Port the awk security-line rules into python/oos.py and add a parity regression test.
- **Suggested revision**: Address the concern above.


### FINDING_13: correctness: skills/implement/scripts/oos-non-security-block-count.awk:17-21
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Awk counter does not exclude explicit [security] / <security> heading tags that serialize/tally now treat as security routing. A leaked ### OOS_1: `[security]` … block is counted as non-security and pushes the gate toward public filing instead of holdback. Align security exclusion with lib-vote-tally/oos-serialize, or ensure producers never write heading-tagged security into the public sink.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: skills/review/scripts/emit-tally.sh:161-183
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Preserve guard requires oos_sink_count>0 while OOS_ACCEPTED_COUNT includes security-held accepts. Security-only accepted round with missing oos.md makes emit-tally exit 1 despite no public OOS to serialize. Split security vs non-security accepted counts or no-op preserve on security-only rounds.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/review/scripts/test-emit-tally.sh:140-165
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No scope-drift tally→emit integration test for the emit-tally overwrite bug (FINDING_1). Scope-drift bare FINDING blocks can be normalized by tally then wiped or replaced when emit-tally re-serializes from oos.md; chained test only covers tagged [OUT_OF_SCOPE] headers. Add a scope-drift fixture: run tally-code-votes.sh with out-of-scope paths then emit-tally.sh; assert normalized OOS block and awk count survive.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: python/oos.py:36-40
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Python security exclusion lags awk backtick/unbolded focus-area matching after reader hardening. Legacy FINDING header with backtick-wrapped focus-area security value passes Python count_non_security but is excluded by bash awk gate; ship.py and ship-pr.sh disagree. Align python/oos.py security detection with oos-non-security-block-count.awk; add paired python and bash gate tests for backtick focus-area on legacy headers.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: skills/review/scripts/test-emit-tally.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing test for emit-tally fatal exit when OOS_ACCEPTED_COUNT>0, empty sink, and oos.md absent. Documented exit 1 path is untested; a truncate regression could return without failing harnesses. Add harness case asserting non-zero exit and no silent truncate when tally count positive but sink empty and oos.md missing.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/shared/scripts/oos-serialize.sh:57-59
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] oos-serialize.sh inlines the same header sub() normalize-oos-block-header.sh already owns. Future header rewrite tweaks must be edited in two places; serialize and tally paths can diverge silently. Route serialize output through normalize-oos-block-header.sh per accepted block.
- **Suggested revision**: Address the concern above.


### FINDING_21: security: scripts/lib-vote-tally.sh:68
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Heading-level [security] detection uses substring match anywhere on the h1 line. Accepted [OUT_OF_SCOPE] finding titled e.g. align with [security] policy is mis-routed to private holdback and never filed — silent OOS drop. Require structured tag position/word boundaries for [security]/<security>, or remove heading-tag routing and rely on focus-area fields only.
- **Suggested revision**: Address the concern above.


### FINDING_22: risk-integration: SECURITY.md:24 vs scripts/lib-vote-tally.sh:56-80
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] SECURITY.md not updated for new routing signals introduced in round 2. Reviewers/operators following SECURITY.md may mis-classify findings across public OOS vs private holdback surfaces. Update SECURITY.md in the same PR to document all routing signals and heading-tag semantics.
- **Suggested revision**: Address the concern above.


### FINDING_23: security: skills/implement/scripts/oos-non-security-block-count.awk:11-21
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Producer vs gate asymmetry on [security] heading tags. [security]-headed block in accepted-OOS file is counted non-security; gate pushes public /issue filing for content producers intended to hold locally. Align gate counters with producer heading-tag rules or drop heading tags from producers.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: skills/implement/scripts/oos-non-security-block-count.awk:17-20 vs python/oos.py:36-40
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Awk security-field matcher widened in round 2; Python regex unchanged. Bash and Python ship gates disagree on whether focus-area = security blocks are security-routed. Port awk rules to python/oos.py _SECURITY_FOCUS_RE and add parity tests.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: python/oos.py:36-40 vs skills/implement/scripts/oos-non-security-block-count.awk:17-20
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Awk security exclusion was relaxed (backtick strip; unbold focus-area lines) but Python still requires bold **focus-area**. Accepted sink with `- focus-area: security` (no bold): bash gate excludes the block; ship.py counts it and blocks PR create/merge (or demands filing) while ship-pr.sh passes. Port awk security-line rules into python/oos.py and add parity tests for unbold/backtick-wrapped focus-area values.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: skills/review/scripts/emit-tally.sh:161-170
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Preserve branch keeps a partial sink whenever oos_sink_count>0, even if oos_sink_count < oos_accepted_count. Tally records two non-security accepts but sink file has one block: emit-tally warns and preserves one block; disposition gate only obligates one finding and the second is silently dropped. Preserve only on exact non-security count match; otherwise rebuild from oos.md (same as empty-sink desync path).
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: skills/review/scripts/emit-tally.sh:177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] oos-serialize rebuild errors are swallowed with || true. Desync rebuild after OOS_ACCEPTED_COUNT>0 fails (awk/IO): emit-tally exits 0 with empty sink; gate sees zero blocks and shipping proceeds without filing. Fail closed on serialize failure when oos_accepted_count>0, or assert post-serialize non-security count matches tally env.
- **Suggested revision**: Address the concern above.


### FINDING_28: architecture: skills/review/scripts/emit-tally.sh:82-83,155-173
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT mixes security-held and public accepts; preserve logic uses non-security sink count. Security-only accept with missing oos.md triggers exit 1; mixed rounds always emit mismatch warnings, obscuring real partial-sink failures during ops/debug. Emit/track a non-security-only accepted count for preserve/rebuild decisions.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: skills/review/scripts/tally-code-votes.sh:127; skills/review-and-fix/scripts/review-and-fix.sh:1473
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Seq continuation counts bare FINDING_ headers that the gate ignores. Legacy bare FINDING_ in accumulated-oos.md inflates OOS_WRITE_SEQ so new blocks get high OOS_N ids while fewer blocks are gate-visible/fileable. Seed seq from oos-non-security-block-count.awk or count only canonical OOS_ headers.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: python/oos.py:36-40 vs skills/implement/scripts/oos-non-security-block-count.awk:17-20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Awk counter strips backticks for focus-area security lines; Python _SECURITY_FOCUS_RE does not Accepted block with - **focus-area**: `security-hardening` counts 0 in bash gate but 1 in python ship.py; divergent ship outcomes Port awk security-line normalization into Python and add matching test_oos.py case
- **Suggested revision**: Address the concern above.


### FINDING_33: architecture: scripts/lib-vote-tally.sh:413-443, skills/shared/scripts/oos-serialize.sh:1671-1701
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Security classifier and oos-serialize behavior changed though plan forbids vote-tally changes and leaves serialize unchanged on tally path Security holdback differs between tally serialize and documented operator guidance; leakage or over-hold across paths Amend plan explicitly or minimize serialize/security changes to what count=0 fallback strictly needs
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: skills/review/scripts/emit-tally.sh:171-177
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Desync rebuild from oos.md cannot recover scope-drift bare FINDING blocks; no fail-closed when oos.md present Sink cleared after tally wrote scope-drift OOS; rebuild via oos-serialize yields empty sink while OOS_ACCEPTED_COUNT=1 Fail closed on count/sink mismatch or extend oos-serialize for accepted scope-drift blocks in oos.md
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: skills/review-and-fix/scripts/review-and-fix.sh:1471-1474
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] OOS_WRITE_SEQ init uses broader header awk than planned oos-non-security-block-count.awk Legacy accumulated-oos.md with bare FINDING headers could skew OOS sequence numbering Use planned awk counter or count only canonical OOS_ headers
- **Suggested revision**: Address the concern above.


### FINDING_38: **risk-integration** `skills/review-and-fix/scripts/review-and-fix.sh:203-225` — The branch expands security routing in `scripts/lib-vote-tally.sh` and `skills/shared/scripts/oos-serialize.sh` (colon `focus-area`, backtick-wrapped values, `[security]` / `<security>` heading tags), but `review-and-fix.sh` keeps a separate inline `is_security_block` that still matches only unfenced `focus-area\s*=\s*security`. On the coder-`SKIPPED` path (~1460–1490), blocks tally would now hold locally (e.g. `- **focus-area**: security` or a `` `[security]` `` heading) are normalized to `### OOS_<seq>:` and mirrored into `accumulated-oos.md` / `oos-accepted-review.md`, so they enter the public OOS sink and Step 9a.1 filing surface while the production tally path blocks them — a cross-path security-routing split the branch widens rather than closes. **Suggested fix:** Drop the duplicate classifier and `source` `scripts/lib-vote-tally.sh` (or extract shared `is_security_block` into one helper used by tally, serialize, and review-and-fix), and add a skipped-routing harness case where the SKIPPED block uses the new colon/heading security tokens and must land only in `skipped-security-findings.md`.
- **Reviewer**: dyn-oos-flow-output.txt
- **Concern**: - **risk-integration** `skills/review-and-fix/scripts/review-and-fix.sh:203-225` — The branch expands security routing in `scripts/lib-vote-tally.sh` and `skills/shared/scripts/oos-serialize.sh` (colon `focus-area`, backtick-wrapped values, `[security]` / `<security>` heading tags), but `review-and-fix.sh` keeps a separate inline `is_security_block` that still matches only unfenced `focus-area\s*=\s*security`. On the coder-`SKIPPED` path (~1460–1490), blocks tally would now hold locally (e.g. `- **focus-area**: security` or a `` `[security]` `` heading) are normalized to `### OOS_<seq>:` and mirrored into `accumulated-oos.md` / `oos-accepted-review.md`, so they enter the public OOS sink and Step 9a.1 filing surface while the production tally path blocks them — a cross-path security-routing split the branch widens rather than closes. **Suggested fix:** Drop the duplicate classifier and `source` `scripts/lib-vote-tally.sh` (or extract shared `is_security_block` into one helper used by tally, serialize, and review-and-fix), and add a skipped-routing harness case where the SKIPPED block uses the new colon/heading security tokens and must land only in `skipped-security-findings.md`.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/lib-vote-tally.md:383; skills/shared/voting-protocol.md:279-284
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] lib-vote-tally security semantics changed but voting-protocol.md still documents only the legacy token. Operators and downstream skills rely on stale voting-protocol text when authoring security-tagged OOS blocks. Update voting-protocol.md security-tag section to match the new is_security_block contract.
- **Suggested revision**: Address the concern above.


### FINDING_40: **risk-integration** `skills/review/scripts/emit-tally.sh:161-170` — The preserve branch requires both `OOS_ACCEPTED_COUNT > 0` and `oos_sink_count > 0`; on `oos_sink_count != oos_accepted_count` it logs a warning and still preserves the sink. If the sink is under-filled (partial tally write, security/counter skew, or mixed legacy content), accepted blocks implied by `OOS_ACCEPTED_COUNT` are dropped while emit-tally completes successfully; `review-core.sh` then `copy_to_parent`s that sink (`skills/review/scripts/review-core.sh:932`) and `append_round_oos_artifact` propagates it into `accumulated-oos.md` / `oos-accepted-review.md`, baking the loss into the Step 9a.1 inputs. **Suggested fix:** Fail closed (non-zero exit) when `oos_sink_count != oos_accepted_count` after tally, or re-derive the accepted sink from authoritative tally output (`OOS_ACCEPTED_OUT` / parent mirror) instead of preserving an under-counted round file.
- **Reviewer**: dyn-oos-flow-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/emit-tally.sh:161-170` — The preserve branch requires both `OOS_ACCEPTED_COUNT > 0` and `oos_sink_count > 0`; on `oos_sink_count != oos_accepted_count` it logs a warning and still preserves the sink. If the sink is under-filled (partial tally write, security/counter skew, or mixed legacy content), accepted blocks implied by `OOS_ACCEPTED_COUNT` are dropped while emit-tally completes successfully; `review-core.sh` then `copy_to_parent`s that sink (`skills/review/scripts/review-core.sh:932`) and `append_round_oos_artifact` propagates it into `accumulated-oos.md` / `oos-accepted-review.md`, baking the loss into the Step 9a.1 inputs. **Suggested fix:** Fail closed (non-zero exit) when `oos_sink_count != oos_accepted_count` after tally, or re-derive the accepted sink from authoritative tally output (`OOS_ACCEPTED_OUT` / parent mirror) instead of preserving an under-counted round file.
- **Suggested revision**: Address the concern above.


### FINDING_44: **correctness** `skills/review/scripts/tally-code-votes.sh:127` / `skills/review-and-fix/scripts/review-and-fix.sh:1446` — `OOS_WRITE_SEQ` is seeded by counting every line matching `^###[[:space:]]+(OOS_|FINDING_[0-9]+:)`, but `normalize-oos-block-header.sh` deliberately leaves body lines that look like `### FINDING_N:` untouched (`NR==1` guard; tested in `skills/shared/scripts/test-normalize-oos-block-header.sh:37-43`). Any cited heading inside an accumulated block is therefore counted as an extra block, inflating the sequence before the next normalize append. That does not break the gate (consumers count ordinals), but it can skip `OOS_<n>` ids and, in multi-round runs, assign a higher seq than `oos-non-security-block-count.awk` would imply—diverging from the plan’s stated init contract (`oos-non-security-block-count.awk` on `$oos_markdown`). **Suggested fix:** Seed `OOS_WRITE_SEQ` from `oos-non-security-block-count.awk` (canonical blocks only), and add a separate pass that counts legacy bare `^### FINDING_[0-9]+:` headers still present in the sink for migration continuity.
- **Reviewer**: dyn-shell-parsers-output.txt
- **Concern**: - **correctness** `skills/review/scripts/tally-code-votes.sh:127` / `skills/review-and-fix/scripts/review-and-fix.sh:1446` — `OOS_WRITE_SEQ` is seeded by counting every line matching `^###[[:space:]]+(OOS_|FINDING_[0-9]+:)`, but `normalize-oos-block-header.sh` deliberately leaves body lines that look like `### FINDING_N:` untouched (`NR==1` guard; tested in `skills/shared/scripts/test-normalize-oos-block-header.sh:37-43`). Any cited heading inside an accumulated block is therefore counted as an extra block, inflating the sequence before the next normalize append. That does not break the gate (consumers count ordinals), but it can skip `OOS_<n>` ids and, in multi-round runs, assign a higher seq than `oos-non-security-block-count.awk` would imply—diverging from the plan’s stated init contract (`oos-non-security-block-count.awk` on `$oos_markdown`). **Suggested fix:** Seed `OOS_WRITE_SEQ` from `oos-non-security-block-count.awk` (canonical blocks only), and add a separate pass that counts legacy bare `^### FINDING_[0-9]+:` headers still present in the sink for migration continuity.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/implement/scripts/oos-non-security-block-count.awk:17-20; python/oos.py:36-39
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Awk security exclusion was hardened; Python _SECURITY_FOCUS_RE was not. Python ship gate counts security blocks with backtick-wrapped focus-area values that bash awk excludes, causing bash/Python disposition disagreement. Align Python security-line matching with awk (strip backticks; support unbolded focus-area and := separators).
- **Suggested revision**: Address the concern above.


### FINDING_52: **security** `skills/shared/scripts/oos-serialize.sh:50,77` — `is_security_tagged()` applies the same unrestricted `^###…[security]…` match on every unfenced line in the block, so the serialize path shares the cited-heading false positive above: rebuild/preserve flows that re-derive from `oos.md` can still suppress public OOS when the only “security” signal is a quoted `### … [security] …` heading in the body. **Suggested fix:** Mirror the producer fix: only evaluate `[security]` / `<security>` header tags on the block-start heading line (the `^### FINDING_[0-9]+:` opener), not on arbitrary later `###` lines inside Concern/Suggested-revision prose.
- **Reviewer**: dyn-security-routing-output.txt
- **Concern**: - **security** `skills/shared/scripts/oos-serialize.sh:50,77` — `is_security_tagged()` applies the same unrestricted `^###…[security]…` match on every unfenced line in the block, so the serialize path shares the cited-heading false positive above: rebuild/preserve flows that re-derive from `oos.md` can still suppress public OOS when the only “security” signal is a quoted `### … [security] …` heading in the body. **Suggested fix:** Mirror the producer fix: only evaluate `[security]` / `<security>` header tags on the block-start heading line (the `^### FINDING_[0-9]+:` opener), not on arbitrary later `###` lines inside Concern/Suggested-revision prose.
- **Suggested revision**: Address the concern above.


### FINDING_53: **security** `python/oos.py:148-152` vs `skills/implement/scripts/oos-non-security-block-count.awk:17-20` — This branch hardens the awk gate counter to strip backticks/asterisks before matching `- focus-area: security…`, and `oos-serialize.sh`/`is_security_block` do the same, but `_SECURITY_FOCUS_RE` in Python is unchanged and still requires a literal `- **focus-area**: security` with no backtick wrapping. A block that reaches the accepted sink as `- **focus-area**: \`security\`` (or backtick-wrapped label/value) is excluded by bash routing/awk counting yet counted as non-security by `python/oos.py`, which can force disposition/`/issue` filing on the Python ship path (#3462) and publish security-routed content. **Suggested fix:** Port the awk normalization into `_count_non_security_markdown` (strip `` ` ``/`*` on candidate lines before applying the focus-area regex, and accept `:`/`=` forms without requiring bold markers), and add a `python/test_oos.py` case for backtick-wrapped `focus-area` values matching `skills/shared/scripts/test-oos-serialize.sh` FINDING_7.
- **Reviewer**: dyn-security-routing-output.txt
- **Concern**: - **security** `python/oos.py:148-152` vs `skills/implement/scripts/oos-non-security-block-count.awk:17-20` — This branch hardens the awk gate counter to strip backticks/asterisks before matching `- focus-area: security…`, and `oos-serialize.sh`/`is_security_block` do the same, but `_SECURITY_FOCUS_RE` in Python is unchanged and still requires a literal `- **focus-area**: security` with no backtick wrapping. A block that reaches the accepted sink as `- **focus-area**: \`security\`` (or backtick-wrapped label/value) is excluded by bash routing/awk counting yet counted as non-security by `python/oos.py`, which can force disposition/`/issue` filing on the Python ship path (#3462) and publish security-routed content. **Suggested fix:** Port the awk normalization into `_count_non_security_markdown` (strip `` ` ``/`*` on candidate lines before applying the focus-area regex, and accept `:`/`=` forms without requiring bold markers), and add a `python/test_oos.py` case for backtick-wrapped `focus-area` values matching `skills/shared/scripts/test-oos-serialize.sh` FINDING_7.
- **Suggested revision**: Address the concern above.


### FINDING_54: **risk-integration** `skills/review/scripts/tally-code-votes.sh:608` + `skills/review/scripts/emit-tally.sh:993-1006` — `OOS_ACCEPTED_COUNT` is still incremented for security-held accepted OOS (the increment sits outside the `security=true` branch), while `emit-tally.sh` now keys preserve/rebuild decisions on that counter versus `oos_sink_count`. When every accepted OOS is security-routed (`oos_accepted_count > 0`, `oos_sink_count == 0`), emit-tally falls through to the `oos-serialize.sh` rebuild path instead of preserving an empty sink; today `oos-serialize` re-filters security correctly, but the inflated counter masks “security-only” rounds behind a misleading non-zero tally signal and couples two independent classifiers in a way that will publish if serialize ever diverges from `is_security_block`. **Suggested fix:** Increment `OOS_ACCEPTED_COUNT` only in the non-security write branch (matching the documented “excluding security-tagged” contract), and treat `oos_sink_count == 0` with no rebuild when the accepted set is security-only.
- **Reviewer**: dyn-security-routing-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/tally-code-votes.sh:608` + `skills/review/scripts/emit-tally.sh:993-1006` — `OOS_ACCEPTED_COUNT` is still incremented for security-held accepted OOS (the increment sits outside the `security=true` branch), while `emit-tally.sh` now keys preserve/rebuild decisions on that counter versus `oos_sink_count`. When every accepted OOS is security-routed (`oos_accepted_count > 0`, `oos_sink_count == 0`), emit-tally falls through to the `oos-serialize.sh` rebuild path instead of preserving an empty sink; today `oos-serialize` re-filters security correctly, but the inflated counter masks “security-only” rounds behind a misleading non-zero tally signal and couples two independent classifiers in a way that will publish if serialize ever diverges from `is_security_block`. **Suggested fix:** Increment `OOS_ACCEPTED_COUNT` only in the non-security write branch (matching the documented “excluding security-tagged” contract), and treat `oos_sink_count == 0` with no rebuild when the accepted set is security-only.
- **Suggested revision**: Address the concern above.


### FINDING_58: **architecture** `skills/shared/scripts/oos-serialize.sh:54-62` — Header normalization is implemented inline (`sub(/^###[[:space:]]+[A-Za-z]+_[0-9]+:/, …)` inside `flush()`) instead of calling the new shared `normalize-oos-block-header.sh`, even though `normalize-oos-block-header.md` positions that helper as the single canonical rewrite and only lists `tally-code-votes.sh` and `review-and-fix.sh` as callers. The fallback `OOS_ACCEPTED_COUNT==0` path and the `emit-tally.sh` desync-rebuild path (`emit-tally.sh:171-177`) both depend on `oos-serialize.sh`, so a future tweak to the shared helper (regex, `NR==1` guard, seq rules) can drift from the serializer without any harness failing on parity. **Suggested fix:** Route `oos-serialize.sh` through `normalize-oos-block-header.sh --seq N` per emitted block (or extract one shared awk snippet both scripts source), and extend `normalize-oos-block-header.md` / `test-oos-serialize.sh` to pin serializer output against the helper contract.
- **Reviewer**: dyn-harness-contracts-output.txt
- **Concern**: - **architecture** `skills/shared/scripts/oos-serialize.sh:54-62` — Header normalization is implemented inline (`sub(/^###[[:space:]]+[A-Za-z]+_[0-9]+:/, …)` inside `flush()`) instead of calling the new shared `normalize-oos-block-header.sh`, even though `normalize-oos-block-header.md` positions that helper as the single canonical rewrite and only lists `tally-code-votes.sh` and `review-and-fix.sh` as callers. The fallback `OOS_ACCEPTED_COUNT==0` path and the `emit-tally.sh` desync-rebuild path (`emit-tally.sh:171-177`) both depend on `oos-serialize.sh`, so a future tweak to the shared helper (regex, `NR==1` guard, seq rules) can drift from the serializer without any harness failing on parity. **Suggested fix:** Route `oos-serialize.sh` through `normalize-oos-block-header.sh --seq N` per emitted block (or extract one shared awk snippet both scripts source), and extend `normalize-oos-block-header.md` / `test-oos-serialize.sh` to pin serializer output against the helper contract.
- **Suggested revision**: Address the concern above.


### FINDING_59: **architecture** `skills/review-and-fix/scripts/review-and-fix.md:108` vs `skills/review-and-fix/scripts/review-and-fix.sh:1444-1447` — The contract says skipped-OOS sequencing continues from the existing `accumulated-oos.md` **non-security block count**, but the implementation uses a bespoke `awk '/^###[[:space:]]+(OOS_|FINDING_[0-9]+:)/'` header-line counter instead of `oos-non-security-block-count.awk` (as the plan specified). That counter treats any line-1 `### FINDING_N:` as a block (including bare scope-drift shapes and any legacy pre-#3550 content) and does not apply the security `focus-area` exclusion the gate uses, so resumed or malformed accumulated files can yield `OOS_<seq>` ids that disagree with disposition/gate ordinals. **Suggested fix:** Initialize `OOS_WRITE_SEQ` with `awk -f skills/implement/scripts/oos-non-security-block-count.awk "$oos_markdown"` (0 when empty), align `tally-code-votes.sh:125-128` the same way, and add a `test-review-and-fix.sh` fixture with a security block in accumulated to assert seq/gate parity.
- **Reviewer**: dyn-harness-contracts-output.txt
- **Concern**: - **architecture** `skills/review-and-fix/scripts/review-and-fix.md:108` vs `skills/review-and-fix/scripts/review-and-fix.sh:1444-1447` — The contract says skipped-OOS sequencing continues from the existing `accumulated-oos.md` **non-security block count**, but the implementation uses a bespoke `awk '/^###[[:space:]]+(OOS_|FINDING_[0-9]+:)/'` header-line counter instead of `oos-non-security-block-count.awk` (as the plan specified). That counter treats any line-1 `### FINDING_N:` as a block (including bare scope-drift shapes and any legacy pre-#3550 content) and does not apply the security `focus-area` exclusion the gate uses, so resumed or malformed accumulated files can yield `OOS_<seq>` ids that disagree with disposition/gate ordinals. **Suggested fix:** Initialize `OOS_WRITE_SEQ` with `awk -f skills/implement/scripts/oos-non-security-block-count.awk "$oos_markdown"` (0 when empty), align `tally-code-votes.sh:125-128` the same way, and add a `test-review-and-fix.sh` fixture with a security block in accumulated to assert seq/gate parity.
- **Suggested revision**: Address the concern above.


### FINDING_60: **architecture** `skills/review/scripts/test-emit-tally.sh` (missing case) — Harnesses cover preserve/truncate/serialize fallbacks and a tagged-OOS `tally-code-votes.sh`→`emit-tally.sh` chain, but not the security-holdback branch documented in `emit-tally.md:7` (`OOS_ACCEPTED_COUNT > 0`, zero non-security sink, rebuild from `oos.md`). `test-tally-code-votes.sh:439-461` stops at tally for security-only accepted OOS; nothing asserts that `emit-tally.sh` rebuilds to an empty public sink without exiting 1 or that `oos-serialize.sh` holdback still matches `OOS_ACCEPTED_COUNT`. **Suggested fix:** Add a `test-emit-tally.sh` case that feeds `review-tally.env` from the security fixture (`OOS_ACCEPTED_COUNT=1`, empty `oos-accepted-review.md`, security block in `oos.md`), expects `emit-tally` exit 0, empty accepted sink, and optionally greps the rebuild warning on stderr.
- **Reviewer**: dyn-harness-contracts-output.txt
- **Concern**: - **architecture** `skills/review/scripts/test-emit-tally.sh` (missing case) — Harnesses cover preserve/truncate/serialize fallbacks and a tagged-OOS `tally-code-votes.sh`→`emit-tally.sh` chain, but not the security-holdback branch documented in `emit-tally.md:7` (`OOS_ACCEPTED_COUNT > 0`, zero non-security sink, rebuild from `oos.md`). `test-tally-code-votes.sh:439-461` stops at tally for security-only accepted OOS; nothing asserts that `emit-tally.sh` rebuilds to an empty public sink without exiting 1 or that `oos-serialize.sh` holdback still matches `OOS_ACCEPTED_COUNT`. **Suggested fix:** Add a `test-emit-tally.sh` case that feeds `review-tally.env` from the security fixture (`OOS_ACCEPTED_COUNT=1`, empty `oos-accepted-review.md`, security block in `oos.md`), expects `emit-tally` exit 0, empty accepted sink, and optionally greps the rebuild warning on stderr.
- **Suggested revision**: Address the concern above.


### FINDING_8: code-quality: skills/review/scripts/emit-tally.sh:161-170
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Preserve branch requires both OOS_ACCEPTED_COUNT>0 and oos_sink_count>0; mismatch only warns while preserving an under-filled sink. Tally env says 2 accepted OOS but sink has 1 block; emit-tally preserves the partial sink and ship may under-file. Rebuild from oos.md when sink_count < oos_accepted_count and oos.md exists; document mismatch policy.
- **Suggested revision**: Address the concern above.


