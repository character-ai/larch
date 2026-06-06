### FINDING_10: [OUT_OF_SCOPE] correctness: skills/shared/scripts/oos-serialize.sh:89-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Serializer only parses ### FINDING_N: block starters; ### OOS_N: blocks in oos.md are skipped on rebuild. Direct-OOS ballot items desynced from the accepted sink cannot be rebuilt from oos.md; emit-tally fails closed when counts diverge. Pre-existing; extend oos-serialize to open ### OOS_N: blocks or document that rebuild only covers FINDING-tagged oos.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/implement/scripts/oos-non-security-block-count.awk:15
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reader backstop requires [OUT_OF_SCOPE] on FINDING headers while oos-serialize also accepts [OOS]. Surviving legacy ### FINDING_N: … [OOS] headers (no [OUT_OF_SCOPE]) may serialize on the count==0 path but still count as zero in gates. Pre-existing format split; extend counters to accept [OOS] or ensure all producers normalize before gate read.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_16: risk-integration: python/test_ship.py:327-426
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Python ship _oos_gate test covers only trailing-tag legacy FINDING headers. Leading-tag legacy headers block PR create via count logic but lack ship-driver regression coverage. Add test_oos_gate_blocks_legacy_leading_tag_without_filed_evidence alongside the existing trailing-tag case.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] security: skills/implement/scripts/oos-non-security-block-count.awk:21-24
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Gate counter does not exclude blocks whose only security signal is unfenced canonical prose focus-area = security in the body. If producer hold fails, such a block is counted as non-security and the gate pushes public filing even though is_security_block would have held it. Optionally extend awk/python counters to mirror canonical prose detection as defense-in-depth after tally fail-closed fix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:60-91
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Four parallel security-routing implementations (lib-vote-tally, oos-serialize, awk counter, python/oos.py) can drift after future edits. Subtle routing mismatch reintroduces silent drops or accidental public filing without cross-harness failure. Consolidate on one shared security-routing module invoked by all paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-and-fix.sh:1334-1359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Degraded-panel retry calls append_round_oos_artifact twice per round. Both review-core passes may append the same round's accepted OOS twice into accumulated-oos.md. Pre-existing; fix outside #3550 unless retry duplication is in scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_33: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.sh:523
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] [OOS]-only FINDING headers still not classified as OOS in tally. Legacy ballots using [OOS] without [OUT_OF_SCOPE] may still miss producer normalization unless serialize fallback runs. Extend tally OOS detection to [OOS] if that legacy format is still in production use.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: **risk-integration** `scripts/lib-vote-tally.sh:74-83` + `skills/shared/scripts/oos-serialize.sh:41-53` — `is_security_block` now runs `explicit_header.search(text_no_fence)` with `re.MULTILINE` over the whole block, so a body line like `### FINDING_N: [security] …` (a cited heading in Concern/Suggested revision) can mark the block security-held in `tally-code-votes.sh` (`OOS_ACCEPTED_COUNT` stays 0; nothing is written to the tally accepted sink). The same block is still copied into `oos.md`, and when `emit-tally.sh` takes the `OOS_ACCEPTED_COUNT == 0` serialize fallback it calls `oos-serialize.sh`, whose `is_security_tagged_block` only applies `explicit_header` to line 1. A block whose opening line is a benign `### FINDING_1: [OUT_OF_SCOPE] …` but cites a security heading in the body can therefore be re-published into `oos-accepted-review.md`, bypassing tally’s hold and potentially reaching `/issue` public filing. This diverges from `SECURITY.md` (“later `### … [security] …` headings inside prose are not routing tags”) and creates inconsistent producer/consumer security routing on the tally → emit-tally → serialize chain. **Suggested fix:** Restrict `explicit_header` in `is_security_block` to the block-opening line only (match `oos-serialize.sh` / `SECURITY.md`), or teach `is_security_tagged_block` the same body-level rule if body citations must route — but do not let tally hold on body citations while serialize publishes on the `OOS_ACCEPTED_COUNT == 0` path.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `scripts/lib-vote-tally.sh:74-83` + `skills/shared/scripts/oos-serialize.sh:41-53` — `is_security_block` now runs `explicit_header.search(text_no_fence)` with `re.MULTILINE` over the whole block, so a body line like `### FINDING_N: [security] …` (a cited heading in Concern/Suggested revision) can mark the block security-held in `tally-code-votes.sh` (`OOS_ACCEPTED_COUNT` stays 0; nothing is written to the tally accepted sink). The same block is still copied into `oos.md`, and when `emit-tally.sh` takes the `OOS_ACCEPTED_COUNT == 0` serialize fallback it calls `oos-serialize.sh`, whose `is_security_tagged_block` only applies `explicit_header` to line 1. A block whose opening line is a benign `### FINDING_1: [OUT_OF_SCOPE] …` but cites a security heading in the body can therefore be re-published into `oos-accepted-review.md`, bypassing tally’s hold and potentially reaching `/issue` public filing. This diverges from `SECURITY.md` (“later `### … [security] …` headings inside prose are not routing tags”) and creates inconsistent producer/consumer security routing on the tally → emit-tally → serialize chain. **Suggested fix:** Restrict `explicit_header` in `is_security_block` to the block-opening line only (match `oos-serialize.sh` / `SECURITY.md`), or teach `is_security_tagged_block` the same body-level rule if body citations must route — but do not let tally hold on body citations while serialize publishes on the `OOS_ACCEPTED_COUNT == 0` path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/review-core.sh:931-932` + `skills/review-and-fix/scripts/review-and-fix.sh:158-166` — On a review round with zero accepted OOS, `copy_to_parent` can overwrite `$IMPLEMENT_TMPDIR/oos-accepted-review.md` with an empty round file while `append_round_oos_artifact` no-ops; `accumulated-oos.md` may still hold prior-round OOS. `oos-disposition-checkpoint.sh` counts only the mirror paths (`oos-accepted-review.md`, not `accumulated-oos.md`), so the gate can all-clear on an empty mirror even when accumulated markdown still has blocks. Pre-existing; not introduced by this branch, though it remains a cross-artifact consistency gap alongside the mirror-based gate.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/tally-code-votes.sh:547` — `is_security_block "$block" 2>/dev/null` still swallows classifier failures (including `return 2` when `python3` is missing from the shared library); pre-existing, but now more consequential because security detection logic is duplicated across `lib-vote-tally.sh` and `oos-serialize.sh` without a single shared probe helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-and-fix.sh:1438-1447` — The skipped-OOS branch calls `is_security_block` twice for every non-security block (once in the `if`, again in the `else` for exit-code routing); harmless but avoidable overhead introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_40: **correctness** `scripts/lib-vote-tally.sh:74-83` — `is_security_block` applies `explicit_header` with `re.MULTILINE` to the entire `text_no_fence`, so any body line shaped like `### … [security] …` is treated as a security route. That conflicts with `scripts/lib-vote-tally.md:44` (“later body headings that merely cite `[security]` do not route the block”), with `skills/shared/scripts/oos-serialize.sh:50-53` (only `lines[0]` is checked), and with `python/oos.py:77-85` / `skills/implement/scripts/oos-non-security-block-count.awk:15-24` (security heading tags apply only on block-opening lines). `skills/shared/scripts/test-oos-serialize.sh:27-38` expects `### FINDING_8: [OUT_OF_SCOPE] Cited security heading` plus body `### Example [security] policy` to stay public (4 accepted, not held), but the tally production path (`tally-code-votes.sh` → `is_security_block`) would hold it as security and skip the public accepted-OOS sink—another silent drop of voted-in non-security OOS. **Suggested fix:** Match `oos-serialize.sh`: test `explicit_header` only against the first non-empty line of `text_no_fence` (or drop the full-text `explicit_header.search` and keep header-tag detection block-local). Add a `scripts/test-lib-vote-tally.sh` case mirroring `test-oos-serialize.sh` FINDING_8 so tally and serialize stay aligned.
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `scripts/lib-vote-tally.sh:74-83` — `is_security_block` applies `explicit_header` with `re.MULTILINE` to the entire `text_no_fence`, so any body line shaped like `### … [security] …` is treated as a security route. That conflicts with `scripts/lib-vote-tally.md:44` (“later body headings that merely cite `[security]` do not route the block”), with `skills/shared/scripts/oos-serialize.sh:50-53` (only `lines[0]` is checked), and with `python/oos.py:77-85` / `skills/implement/scripts/oos-non-security-block-count.awk:15-24` (security heading tags apply only on block-opening lines). `skills/shared/scripts/test-oos-serialize.sh:27-38` expects `### FINDING_8: [OUT_OF_SCOPE] Cited security heading` plus body `### Example [security] policy` to stay public (4 accepted, not held), but the tally production path (`tally-code-votes.sh` → `is_security_block`) would hold it as security and skip the public accepted-OOS sink—another silent drop of voted-in non-security OOS. **Suggested fix:** Match `oos-serialize.sh`: test `explicit_header` only against the first non-empty line of `text_no_fence` (or drop the full-text `explicit_header.search` and keep header-tag detection block-local). Add a `scripts/test-lib-vote-tally.sh` case mirroring `test-oos-serialize.sh` FINDING_8 so tally and serialize stay aligned.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/oos-non-security-block-count.awk:15`, `python/oos.py:32-34`, `skills/review/scripts/tally-code-votes.sh:523` — Legacy FINDING block-start counting/backstop keys on `[OUT_OF_SCOPE]` only; `skills/shared/scripts/oos-serialize.sh:95-96` also treats `[OOS]` as OOS-tagged. Unnormalized `### FINDING_N: [OOS]` sinks could still read as zero blocks at the gate; producer normalization is the intended fix, but reader parity for `[OOS]`-only FINDING headers was not extended.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `skills/shared/scripts/oos-serialize.sh:89-98` — Serialization still splits only on `^### FINDING_[0-9]+:`; ballot blocks headed `### OOS_N:` are not split on the `OOS_ACCEPTED_COUNT==0` serialize fallback path (pre-existing; unchanged by this branch).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_46: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `skills/review/scripts/tally-code-votes.sh:590-592` — Accepted security OOS blocks are still appended to round-local `oos.md` before the holdback branch runs. `SECURITY.md` says security findings are never written to the `oos.md` visibility export; that doc/code mismatch predates this branch and was not introduced by the #3550 changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_47: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `scripts/lib-vote-tally.sh:56-90` vs `skills/implement/scripts/oos-non-security-block-count.awk:14-28` — The write-time classifier routes on unfenced canonical `focus-area\s*=\s*security` anywhere in the block, while the gate counter intentionally ignores that prose pattern to avoid miscounting mixed files. That asymmetry is longstanding; this branch amplifies its impact only when fail-open writers place such blocks in dedicated accepted-OOS sinks (see first in-scope finding).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_49: **correctness** `skills/implement/scripts/test-oos-disposition-gate.sh:165-275` — Legacy `### FINDING_N: [OUT_OF_SCOPE]` gate cases cover unresolved disposition (exit 1) and filed-URL pass (exit 0), but there is no bash integration case that a security-routed legacy header (`### FINDING_1: [OUT_OF_SCOPE]` plus `- **focus-area**: security`) is excluded from the non-security obligation set and passes without URLs. `python/test_oos.py` has `test_count_non_security_excludes_security_tagged_legacy_header`, yet the bash gate harness only exercises security exclusion on `### OOS_` fixtures, so awk security handling on legacy `FINDING_` headers can drift from Python without failing CI’s bash shard. **Suggested fix:** Add a gate (and optionally checkpoint) fixture with a legacy tagged `FINDING_` security block and assert exit 0 with empty filed-urls, plus a direct `oos-non-security-block-count.awk` assertion that the count is 0.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-oos-disposition-gate.sh:165-275` — Legacy `### FINDING_N: [OUT_OF_SCOPE]` gate cases cover unresolved disposition (exit 1) and filed-URL pass (exit 0), but there is no bash integration case that a security-routed legacy header (`### FINDING_1: [OUT_OF_SCOPE]` plus `- **focus-area**: security`) is excluded from the non-security obligation set and passes without URLs. `python/test_oos.py` has `test_count_non_security_excludes_security_tagged_legacy_header`, yet the bash gate harness only exercises security exclusion on `### OOS_` fixtures, so awk security handling on legacy `FINDING_` headers can drift from Python without failing CI’s bash shard. **Suggested fix:** Add a gate (and optionally checkpoint) fixture with a legacy tagged `FINDING_` security block and assert exit 0 with empty filed-urls, plus a direct `oos-non-security-block-count.awk` assertion that the count is 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_51: [OUT_OF_SCOPE] The plan’s end-to-end “`/issue` actually files legacy-header OOS” assertion is still not covered; harnesses stop at gate/disposition and normalized sinks (`skills/issue/scripts/test-parse-input.sh` remains `### OOS_N:`-only by design).
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - The plan’s end-to-end “`/issue` actually files legacy-header OOS” assertion is still not covered; harnesses stop at gate/disposition and normalized sinks (`skills/issue/scripts/test-parse-input.sh` remains `### OOS_N:`-only by design).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_52: [OUT_OF_SCOPE] `test-review-core.sh` continues to stub tally/emit (called out in the plan), so production review-core integration of the tally→emit preserve chain is not exercised there; this branch instead adds `test-tally-code-votes.sh`, `test-emit-tally.sh`, and chained cases for that chain.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - `test-review-core.sh` continues to stub tally/emit (called out in the plan), so production review-core integration of the tally→emit preserve chain is not exercised there; this branch instead adds `test-tally-code-votes.sh`, `test-emit-tally.sh`, and chained cases for that chain.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_53: [OUT_OF_SCOPE] No dedicated `test-oos-non-security-block-count.awk` harness exists; bare `### FINDING_N:` → count 0 is asserted only in `python/test_oos.py`, not as a standalone bash unit test (bash coverage is indirect via gate tests on tagged legacy headers).
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - No dedicated `test-oos-non-security-block-count.awk` harness exists; bare `### FINDING_N:` → count 0 is asserted only in `python/test_oos.py`, not as a standalone bash unit test (bash coverage is indirect via gate tests on tagged legacy headers).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:547
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] is_security_block failures are swallowed via 2>/dev/null, treating exit 2 as non-security. When python3 is missing, security-tagged accepted OOS can enter the public sink and bypass disposition filing. Propagate exit 2 as a hard failure instead of masking stderr and defaulting to public routing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

