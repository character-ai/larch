### FINDING_1: code-quality: python/oos.py:32-34 vs skills/implement/scripts/oos-non-security-block-count.awk:10
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Legacy FINDING header detection differs between Python and awk ports. A header like ### FINDING_1: Title [OUT_OF_SCOPE] is counted by bash gate scripts but not by python/oos.py; Python ship soak and bash ship disagree on the same accepted file. Align Python with awk (FINDING prefix plus [OUT_OF_SCOPE] anywhere on line) or share one predicate; add a cross-port regression fixture.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review/scripts/tally-code-votes.sh:123 and skills/review-and-fix/scripts/review-and-fix.sh:155-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Tally resets OOS_WRITE_SEQ per round while append_round_oos_artifact accumulates without cross-round renumbering. Multi-round review accumulates multiple ### OOS_1: blocks in accumulated-oos.md / oos-accepted-review.md, confusing operators and batch filing even though ordinal counting still works. Seed tally seq from accumulated block count on implement path or renumber in append_round_oos_artifact.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/review/scripts/emit-tally.sh:671-685 and skills/shared/scripts/oos-serialize.sh:55-61
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The OOS_ACCEPTED_COUNT==0 path still serializes legacy FINDING headers without normalization. Standalone emit paths can pass reader-hardened gates yet fail /issue filing because parse-input.sh requires ### OOS_N:. Normalize oos-serialize output via the shared helper or document and block filing on that path.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/review/scripts/tally-code-votes.sh:122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NORMALIZE_OOS_HELPER uses SCRIPT_DIR-relative path while PLUGIN_ROOT is already available. Helper resolution is inconsistent with review-and-fix.sh and breaks if script layout changes. Use $PLUGIN_ROOT/skills/shared/scripts/normalize-oos-block-header.sh.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1456-1478
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Skipped-OOS branch invokes is_security_block twice per non-security block. Redundant classifier subprocess calls on every SKIPPED append add noise and maintenance cost. Normalize directly in the else branch without re-invoking is_security_block.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review-and-fix/scripts/review-and-fix.sh:155-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] append_round_oos_artifact blindly concatenates round OOS without a normalization hook. Future round-level producers could reintroduce bare FINDING headers into accumulated sinks. Add normalization at accumulation or enforce invariant that round sink is always canonical.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/design/scripts/file-design-oos.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Design-path OOS producers were not updated per plan scope. /design accepted OOS may still use non-canonical headers into oos-accepted-design.md. Extend normalization to design producers in a follow-up if design-path filing is required.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/scripts/oos-non-security-block-count.awk:10-14 / python/oos.py:32-35 / skills/review/scripts/emit-tally.sh:671-684
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Reader backstop counts legacy FINDING [OUT_OF_SCOPE] headers but OOS_ACCEPTED_COUNT==0 still runs oos-serialize which emits vote-rejected tagged blocks without Result filtering. All OOS proposals rejected (OOS_ACCEPTED_COUNT=0, non-empty oos.md): serialize copies rejected FINDING blocks into oos-accepted-review.md; gate now reports non_security_oos>=1 and blocks ship with no accepted OOS to file — regression vs pre-#3550 silent pass on FINDING headers. Filter oos-serialize to Result=accepted only, teach counter to skip Result=rejected bodies, or skip serialize when only rejected OOS remain.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/scripts/oos-non-security-block-count.awk:10 / python/oos.py:32-34
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] awk uses index() for [OUT_OF_SCOPE] anywhere on FINDING header line; Python requires tag immediately after colon. Header ### FINDING_1: title [OUT_OF_SCOPE] later: awk count=1 Python count=0; bash gate blocks but python ship gate may pass on same artifact. Align awk and Python header matchers on the same colon-adjacent tag rule.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/review/scripts/emit-tally.sh:899-909 / skills/shared/scripts/oos-serialize.sh:55-71
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT=0 serialize fallback still emits ### FINDING_N: headers; parse-input.sh only files ### OOS_N:. Accepted tagged OOS only via serialize path: gate may flag disposition gap but /issue batch parser still cannot file blocks. Normalize serialize output to ### OOS_<seq>: or invoke normalize-oos-block-header.sh in the serialize branch.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:155-162
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] append_round_oos_artifact does not renumber OOS seq across rounds; duplicate ### OOS_1: ids possible in accumulated-oos.md. Multi-round review with OOS each round: duplicate header ids in accumulated file; consumers count by block ordinals so impact is usually low. Pre-existing; renumber on append if global uniqueness becomes required.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/review-and-fix.sh:1354-1356
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Degraded-panel retry appends round OOS before re-running review-core. Degraded first attempt OOS may be duplicated or stale relative to retried tally output. Pre-existing degraded-retry ordering; not introduced by #3550.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: python/oos.py:32-35 + skills/implement/scripts/oos-non-security-block-count.awk:10
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy FINDING header matching differs between awk (index anywhere on line) and Python (tag must follow colon immediately). A header like `### FINDING_1: Title [OUT_OF_SCOPE]` is counted by bash gates but ignored by python/ship._oos_gate, reintroducing silent pass on Python ship. Align matchers; add shared parity fixtures for both canonical and delayed-tag header shapes.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: (plan — acceptance / testing strategy)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No end-to-end test proves normalized accepted OOS reaches `/issue` filing parsers. Counters and disposition gates can pass while Step 9a.1 still cannot file blocks if parser/schema wiring regresses. Add harness: normalized oos-accepted-review.md → parse-input.sh OOS mode → assert parsed/filed OOS item.
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

### FINDING_18: risk-integration: python/test_oos.py:206-218
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Python lacks legacy-header disposition_ok pass case with filed URL that bash gate harness has. Asymmetric coverage if filed-URL counting diverges for legacy blocks in Python only. Add test_disposition_passes_for_legacy_header_with_filed_url mirroring bash harness.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/lib-vote-tally.sh:60-68, skills/review/scripts/tally-code-votes.sh:538-600, python/oos.py:32-79, skills/implement/scripts/oos-non-security-block-count.awk:21-33
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Producer is_security_block matches only unfenced focus-area=security (equals) while the gate excludes only dedicated - **focus-area**: security lines; common security reviewer shapes (colon field or header `security` tag) can enter the public accepted-OOS sink. A voted-accepted ### FINDING_N: [OUT_OF_SCOPE] security finding with header `security` focus tag or - **focus-area**: security that is_security_block misses is normalized to ### OOS_<seq>: and the disposition gate now obligates public filing instead of silently dropping it, converting a mis-routed security finding into a forced public GitHub issue. Unify security classification at the producer: extend is_security_block to match gate/materialize-manifest colon field lines (and optionally header security tags); never write security-classified blocks to oos-accepted-review.md; route them to the local security audit sink.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/review/scripts/emit-tally.sh:671-685
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] emit-tally preserve skips oos-serialize.sh whenever OOS_ACCEPTED_COUNT>0, so scope-drift bare FINDING blocks bypass serialize's secondary security tag scan. Scope-drift OOS about sensitive out-of-plan paths without a detectable security marker is normalized and preserved for public filing without the serialize fallback filter. Apply shared security classification immediately before normalize-oos-block-header.sh in tally and review-and-fix, matching oos-serialize semantics.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security: skills/shared/scripts/normalize-oos-block-header.sh:27-33
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Normalization preserves full reviewer body text into public OOS sinks; redaction remains a downstream responsibility. Mis-redacted reviewer prose could still expose secrets in filed issues, same as before this branch. Ensure /issue pipeline redaction remains mandatory; no change required in this helper.
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

### FINDING_27: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-and-fix.sh:155-162; skills/review/scripts/review-core.sh:931-932
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append_round_oos_artifact skips when round_oos is empty, so a later OOS-free round can leave oos-accepted-review.md empty while accumulated-oos.md still has prior rounds. Round 2+ with no accepted OOS wipes the public mirror via copy_to_parent but never re-mirrors accumulated content. Re-mirror accumulated-oos.md whenever copy_to_parent runs, even when the current round_oos is empty.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/emit-tally.sh:165
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] oos-serialize.sh errors are silenced with || true on the count==0 path. serialize failure with a populated oos.md produces an empty accepted sink with no surfaced error. Surface serialize failures or fail closed when oos.md is non-empty but output is empty.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **architecture** `skills/shared/scripts/oos-serialize.sh` — The plan deliberately leaves the `OOS_ACCEPTED_COUNT == 0` serialize fallback unchanged. `oos-serialize.sh` still emits `### FINDING_N:` headers, so standalone paths that rely on serialize alone can still pass the reader backstop (legacy tagged headers) yet fail `/issue` filing (`parse-input.sh` keys on `### OOS_N:`). The plan scoped acceptance to the production review-core and coder-skipped paths; this serialize-only gap is pre-existing and explicitly out of scope.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **risk-integration** `skills/review/scripts/test-tally-code-votes.sh:491-500` — The scope-drift normalization case asserts stdout `OOS_ACCEPTED_COUNT` but not `review-tally.env`. The plan only requires that guard “in at least one OOS/scope-drift case,” and the tagged-OOS fixture at lines 84 satisfies it. Adding the same `review-tally.env` assertion to the drift case would better pin FINDING_1 (emit-tally reading env, not stdout), but that is optional hardening, not a plan miss.
- **Suggested revision**: Address the concern above.

### FINDING_31: **risk-integration** `skills/review/scripts/emit-tally.sh:155-161` — The new preserve branch keys only on `OOS_ACCEPTED_COUNT > 0` and never checks that `$OOS_ACCEPTED_FILE` actually contains the expected non-security blocks (e.g., via `oos-non-security-block-count.awk`). That counter is incremented for security-held accepted OOS as well (`skills/review/scripts/tally-code-votes.sh:585-601`), so `OOS_ACCEPTED_COUNT` can be > 0 while the public sink is legitimately empty. More importantly, any future desync where the tally env says > 0 but the accepted file is empty or short (partial write, stale env, or `copy_to_parent` propagating an empty round file) will skip both `oos-serialize.sh` and the truncate branch, leaving an empty sink; the disposition gate then counts zero blocks and passes, reproducing the silent-drop failure mode #3550 was meant to close. **Suggested fix:** Gate the preserve branch on `awk -f …/oos-non-security-block-count.awk "$OOS_ACCEPTED_FILE" > 0` (or a dedicated non-security tally counter), not raw `OOS_ACCEPTED_COUNT`; when the env count and awk block count disagree, log a warning and fall back to the serialize path when `oos.md` exists, otherwise fail closed.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/emit-tally.sh:155-161` — The new preserve branch keys only on `OOS_ACCEPTED_COUNT > 0` and never checks that `$OOS_ACCEPTED_FILE` actually contains the expected non-security blocks (e.g., via `oos-non-security-block-count.awk`). That counter is incremented for security-held accepted OOS as well (`skills/review/scripts/tally-code-votes.sh:585-601`), so `OOS_ACCEPTED_COUNT` can be > 0 while the public sink is legitimately empty. More importantly, any future desync where the tally env says > 0 but the accepted file is empty or short (partial write, stale env, or `copy_to_parent` propagating an empty round file) will skip both `oos-serialize.sh` and the truncate branch, leaving an empty sink; the disposition gate then counts zero blocks and passes, reproducing the silent-drop failure mode #3550 was meant to close. **Suggested fix:** Gate the preserve branch on `awk -f …/oos-non-security-block-count.awk "$OOS_ACCEPTED_FILE" > 0` (or a dedicated non-security tally counter), not raw `OOS_ACCEPTED_COUNT`; when the env count and awk block count disagree, log a warning and fall back to the serialize path when `oos.md` exists, otherwise fail closed.
- **Suggested revision**: Address the concern above.

### FINDING_32: **risk-integration** `skills/review/scripts/emit-tally.sh:162-165` — The `OOS_ACCEPTED_COUNT == 0` fallback still routes through `oos-serialize.sh`, which copies legacy `### FINDING_N:` headers verbatim into `oos-accepted-review.md` (`skills/shared/scripts/oos-serialize.sh:55-62`). This branch is unchanged by the producer normalization work in `tally-code-votes.sh` / `review-and-fix.sh`, so any caller that reaches emit with a zero count while accepted tagged OOS live only in `oos.md` (standalone emit, env desync, or a future tally bypass) will again produce headers that `skills/issue/scripts/parse-input.sh:377` cannot file even though the reader backstop may now count them for the gate. **Suggested fix:** Run `normalize-oos-block-header.sh` over `oos-serialize.sh` output (or inside serialize itself) so the count=0 fallback emits canonical `### OOS_<seq>:` blocks, keeping the gate, filing parser, and counters aligned on every path.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/emit-tally.sh:162-165` — The `OOS_ACCEPTED_COUNT == 0` fallback still routes through `oos-serialize.sh`, which copies legacy `### FINDING_N:` headers verbatim into `oos-accepted-review.md` (`skills/shared/scripts/oos-serialize.sh:55-62`). This branch is unchanged by the producer normalization work in `tally-code-votes.sh` / `review-and-fix.sh`, so any caller that reaches emit with a zero count while accepted tagged OOS live only in `oos.md` (standalone emit, env desync, or a future tally bypass) will again produce headers that `skills/issue/scripts/parse-input.sh:377` cannot file even though the reader backstop may now count them for the gate. **Suggested fix:** Run `normalize-oos-block-header.sh` over `oos-serialize.sh` output (or inside serialize itself) so the count=0 fallback emits canonical `### OOS_<seq>:` blocks, keeping the gate, filing parser, and counters aligned on every path.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/tally-code-votes.sh:116` + `skills/review/scripts/review-core.sh:932` + `skills/review-and-fix/scripts/review-and-fix.sh:155-162` — Pre-existing multi-round gap: each round’s tally truncates the parent `$IMPLEMENT_TMPDIR/oos-accepted-review.md` when `--session-env-path` is set; if a later round accepts zero OOS, `emit-tally` truncates and `copy_to_parent` pushes an empty file, and `append_round_oos_artifact` skips re-mirroring because `round_oos` is empty—even though `accumulated-oos.md` still holds prior rounds. Step 9a.1 / the disposition gate read `oos-accepted-review.md`, not `accumulated-oos.md`, so cross-round OOS can still vanish from the filing surface. This branch does not add a final accumulated→mirror sync.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **architecture** `skills/review/scripts/test-review-core.sh` — As noted in the plan, review-core harness stubs `emit-tally.sh`, so the production tally → emit-tally → `copy_to_parent` chain lacks an integration regression test; coverage is isolated to `test-tally-code-votes.sh` and `test-emit-tally.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_35: **correctness** `python/oos.py:32-35` / `skills/implement/scripts/oos-non-security-block-count.awk:10` — The branch extends both counters for legacy `FINDING` headers, but they are not equivalent: awk treats any line matching `^### FINDING_[0-9]+:` with `[OUT_OF_SCOPE]` anywhere on the line as a block start, while Python’s `_OOS_HEADER_RE` only matches when `[OUT_OF_SCOPE]` immediately follows the id (`FINDING_\d+:\s*\[OUT_OF_SCOPE\]`). A header like `### FINDING_1: Latent issue [OUT_OF_SCOPE]` is counted by the bash gate (`oos-disposition-gate.sh`) but returns `0` from `python/oos.count_non_security`, so `ship.py` can still treat disposition as satisfied while the bash path blocks — the exact parity failure mode the plan’s “edit both in lockstep” rule is meant to prevent. **Suggested fix:** Align Python with awk (e.g. match `^###\s+FINDING_\d+:` and require `[OUT_OF_SCOPE]` anywhere on that line, or share one test fixture with both counters and make the regexes identical), and add a regression case for a non-immediate tag placement.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **correctness** `python/oos.py:32-35` / `skills/implement/scripts/oos-non-security-block-count.awk:10` — The branch extends both counters for legacy `FINDING` headers, but they are not equivalent: awk treats any line matching `^### FINDING_[0-9]+:` with `[OUT_OF_SCOPE]` anywhere on the line as a block start, while Python’s `_OOS_HEADER_RE` only matches when `[OUT_OF_SCOPE]` immediately follows the id (`FINDING_\d+:\s*\[OUT_OF_SCOPE\]`). A header like `### FINDING_1: Latent issue [OUT_OF_SCOPE]` is counted by the bash gate (`oos-disposition-gate.sh`) but returns `0` from `python/oos.count_non_security`, so `ship.py` can still treat disposition as satisfied while the bash path blocks — the exact parity failure mode the plan’s “edit both in lockstep” rule is meant to prevent. **Suggested fix:** Align Python with awk (e.g. match `^###\s+FINDING_\d+:` and require `[OUT_OF_SCOPE]` anywhere on that line, or share one test fixture with both counters and make the regexes identical), and add a regression case for a non-immediate tag placement.
- **Suggested revision**: Address the concern above.

### FINDING_36: **correctness** `skills/implement/scripts/oos-non-security-block-count.awk:10-14` — The new legacy `FINDING` block-start rule keys only on line-anchored headers and does not distinguish producer-written block boundaries from reviewer prose. A normalized block whose body contains a line-start citation such as `### FINDING_2: [OUT_OF_SCOPE] …` will be counted as an extra non-security block, inflating `non_security_oos` and causing a disposition-gap gate failure even after the accepted item is filed. **Suggested fix:** Restrict the legacy `FINDING` backstop to first-line-only semantics (mirror the producer’s `NR==1` guard), or only apply the legacy match when the file still lacks any `### OOS_` headers (pre-normalization artifacts).
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/oos-non-security-block-count.awk:10-14` — The new legacy `FINDING` block-start rule keys only on line-anchored headers and does not distinguish producer-written block boundaries from reviewer prose. A normalized block whose body contains a line-start citation such as `### FINDING_2: [OUT_OF_SCOPE] …` will be counted as an extra non-security block, inflating `non_security_oos` and causing a disposition-gap gate failure even after the accepted item is filed. **Suggested fix:** Restrict the legacy `FINDING` backstop to first-line-only semantics (mirror the producer’s `NR==1` guard), or only apply the legacy match when the file still lacks any `### OOS_` headers (pre-normalization artifacts).
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `skills/review-and-fix/scripts/review-and-fix.sh:1446` — `OOS_WRITE_SEQ` initialization swallows `awk` failures via `2>/dev/null || printf '0'`; this predates the #3550 seq-continuation logic but is now load-bearing for monotonic ids across rounds.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - `skills/review-and-fix/scripts/review-and-fix.sh:1446` — `OOS_WRITE_SEQ` initialization swallows `awk` failures via `2>/dev/null || printf '0'`; this predates the #3550 seq-continuation logic but is now load-bearing for monotonic ids across rounds.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] `skills/shared/scripts/oos-serialize.sh` — The `OOS_ACCEPTED_COUNT==0` serialize fallback still emits raw `### FINDING_N:` headers; the branch relies on producer normalization and reader backstop rather than normalizing here. That is acceptable for the main review-core path but remains a latent gap on serialize-only paths.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - `skills/shared/scripts/oos-serialize.sh` — The `OOS_ACCEPTED_COUNT==0` serialize fallback still emits raw `### FINDING_N:` headers; the branch relies on producer normalization and reader backstop rather than normalizing here. That is acceptable for the main review-core path but remains a latent gap on serialize-only paths.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] `skills/review-and-fix/scripts/review-and-fix.sh:155-162` (`append_round_oos_artifact`) — Each round’s tally renumbers accepted OOS from `OOS_1`, so `accumulated-oos.md` can accumulate duplicate `### OOS_1:` ids across rounds; pre-existing behavior, and consumers count blocks ordinally rather than by id.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - `skills/review-and-fix/scripts/review-and-fix.sh:155-162` (`append_round_oos_artifact`) — Each round’s tally renumbers accepted OOS from `OOS_1`, so `accumulated-oos.md` can accumulate duplicate `### OOS_1:` ids across rounds; pre-existing behavior, and consumers count blocks ordinally rather than by id.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `python/oos.py:32-35` vs `skills/implement/scripts/oos-non-security-block-count.awk:10` — The legacy-header rules are not semantically equivalent. Awk starts a block on any `### FINDING_<n>:` line where `index($0, "[OUT_OF_SCOPE]")` is true anywhere on that line; Python requires the tag immediately after the id (`FINDING_\d+:\s*\[OUT_OF_SCOPE\]`). For a header like `### FINDING_1: Some title [OUT_OF_SCOPE]`, awk returns `1` but Python returns `0` (the file-level `_OOS_HEADER_RE.search()` guard at `python/oos.py:91-92` also skips the file). That breaks the stated awk port contract and can make `ship-pr.sh` (awk at `scripts/ship-pr.sh:745`) and `python/ship.py` (`disposition_ok` via `python/oos.py:191`) disagree on the same accepted-OOS artifact: bash may block shipping while Python trivially passes, reintroducing a silent-drop path on the Python soak/cutover (#3462). Tests only use the canonical `### FINDING_N: [OUT_OF_SCOPE] …` shape (`python/test_oos.py:190`, `skills/implement/scripts/test-oos-disposition-gate.sh:230`), so CI will not catch this drift. **Suggested fix:** Make Python mirror awk explicitly—e.g. treat a line as a legacy block start when it matches `^###\s+FINDING_\d+:` and contains the literal `[OUT_OF_SCOPE]` anywhere on that line (same for the file guard)—or narrow awk to the Python rule if that stricter shape is the only supported legacy format; add a paired fixture with the tag after title text and assert identical counts from both counters.
- **Reviewer**: dyn-counter-parity-output.txt
- **Concern**: - **correctness** `python/oos.py:32-35` vs `skills/implement/scripts/oos-non-security-block-count.awk:10` — The legacy-header rules are not semantically equivalent. Awk starts a block on any `### FINDING_<n>:` line where `index($0, "[OUT_OF_SCOPE]")` is true anywhere on that line; Python requires the tag immediately after the id (`FINDING_\d+:\s*\[OUT_OF_SCOPE\]`). For a header like `### FINDING_1: Some title [OUT_OF_SCOPE]`, awk returns `1` but Python returns `0` (the file-level `_OOS_HEADER_RE.search()` guard at `python/oos.py:91-92` also skips the file). That breaks the stated awk port contract and can make `ship-pr.sh` (awk at `scripts/ship-pr.sh:745`) and `python/ship.py` (`disposition_ok` via `python/oos.py:191`) disagree on the same accepted-OOS artifact: bash may block shipping while Python trivially passes, reintroducing a silent-drop path on the Python soak/cutover (#3462). Tests only use the canonical `### FINDING_N: [OUT_OF_SCOPE] …` shape (`python/test_oos.py:190`, `skills/implement/scripts/test-oos-disposition-gate.sh:230`), so CI will not catch this drift. **Suggested fix:** Make Python mirror awk explicitly—e.g. treat a line as a legacy block start when it matches `^###\s+FINDING_\d+:` and contains the literal `[OUT_OF_SCOPE]` anywhere on that line (same for the file guard)—or narrow awk to the Python rule if that stricter shape is the only supported legacy format; add a paired fixture with the tag after title text and assert identical counts from both counters.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-counter-parity-output.txt
- **Concern**: - **correctness** (pre-existing, not introduced by this branch) Both counters ignore `### FINDING_N:` blocks tagged only with `[OOS]` (no `[OUT_OF_SCOPE]`), while `skills/shared/scripts/oos-serialize.sh:61,69` still serializes them when `OOS_ACCEPTED_COUNT == 0`. Awk and Python agree on that miss, but accepted OOS using only `[OOS]` can still be dropped by both gates on the serialize fallback path; fixing it would be outside the #3550 scope unless you broaden tag recognition consistently in tally, serialize, and both counters.
- **Suggested revision**: Address the concern above.

### FINDING_42: **code-quality** `skills/review/scripts/test-emit-tally.sh:74-96` — The new preserve cases exercise `emit-tally.sh` in isolation with hand-seeded `### OOS_1:` content and a synthetic `OOS_ACCEPTED_COUNT=1` tally env; they never run `tally-code-votes.sh` first and never seed the production failure shape (scope-drift bare `### FINDING_N:` or legacy tagged headers that tally normalizes). The original #3550 bug was specifically the tally→emit overwrite chain on the review-core path, so a regression that breaks tally output or `review-tally.env` handoff while leaving the preserve branch intact could still pass these tests. **Suggested fix:** Add a chained case (new harness section or tail of `test-emit-tally.sh`) that runs `tally-code-votes.sh` with a scope-drift or `[OUT_OF_SCOPE]` fixture, then invokes real `emit-tally.sh` with the emitted `review-tally.env`, and asserts `oos-accepted-review.md` still has exactly one canonical `### OOS_` block and `awk` count `== 1`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-emit-tally.sh:74-96` — The new preserve cases exercise `emit-tally.sh` in isolation with hand-seeded `### OOS_1:` content and a synthetic `OOS_ACCEPTED_COUNT=1` tally env; they never run `tally-code-votes.sh` first and never seed the production failure shape (scope-drift bare `### FINDING_N:` or legacy tagged headers that tally normalizes). The original #3550 bug was specifically the tally→emit overwrite chain on the review-core path, so a regression that breaks tally output or `review-tally.env` handoff while leaving the preserve branch intact could still pass these tests. **Suggested fix:** Add a chained case (new harness section or tail of `test-emit-tally.sh`) that runs `tally-code-votes.sh` with a scope-drift or `[OUT_OF_SCOPE]` fixture, then invokes real `emit-tally.sh` with the emitted `review-tally.env`, and asserts `oos-accepted-review.md` still has exactly one canonical `### OOS_` block and `awk` count `== 1`.
- **Suggested revision**: Address the concern above.

### FINDING_43: **code-quality** `skills/review/scripts/test-tally-code-votes.sh:382-390` — The plan called for dual-sink coverage (standalone alias + implement mirror), but the only dual-sink assertion is in standalone case1 (`:82-83`). The `--session-env-path` case checks classification TSV naming only and does not assert that `$(dirname session.env)/oos-accepted-review.md` receives normalized accepted OOS, has no bare `### FINDING_` header, or has `awk` count `== 1` without duplicating the round-tmpdir sink. That leaves the `/implement` parent-mirror path unguarded. **Suggested fix:** Extend the session-bound case (or add `case_session_oos_mirror`) with an accepted OOS ballot, `--session-env-path`, and assertions on both `$TMP/round-N/oos-accepted-review.md` and `$TMP/oos-accepted-review.md` (parent) for canonical headers, `awk` count `== 1`, and byte-identical normalized content between sinks.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-tally-code-votes.sh:382-390` — The plan called for dual-sink coverage (standalone alias + implement mirror), but the only dual-sink assertion is in standalone case1 (`:82-83`). The `--session-env-path` case checks classification TSV naming only and does not assert that `$(dirname session.env)/oos-accepted-review.md` receives normalized accepted OOS, has no bare `### FINDING_` header, or has `awk` count `== 1` without duplicating the round-tmpdir sink. That leaves the `/implement` parent-mirror path unguarded. **Suggested fix:** Extend the session-bound case (or add `case_session_oos_mirror`) with an accepted OOS ballot, `--session-env-path`, and assertions on both `$TMP/round-N/oos-accepted-review.md` and `$TMP/oos-accepted-review.md` (parent) for canonical headers, `awk` count `== 1`, and byte-identical normalized content between sinks.
- **Suggested revision**: Address the concern above.

### FINDING_44: **code-quality** `skills/review/scripts/test-tally-code-votes.sh:473-500` — The new `case6a_norm` scope-drift case checks stdout `OOS_ACCEPTED_COUNT` and normalized headers but, unlike case1 (`:84`), does not assert `OOS_ACCEPTED_COUNT` was appended to `$TMP/review-tally.env`. The plan explicitly required that guard because emit-tally reads `--tally-file` (the env file), not stdout KV; dropping the env append while keeping `emit_kv` would reproduce the overwrite/truncate bug on the production path while unit tally tests still pass. **Suggested fix:** Add `got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env"); assert_eq ... "1"` to `case6a_norm` (and optionally to case6a as a zero-count control).
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-tally-code-votes.sh:473-500` — The new `case6a_norm` scope-drift case checks stdout `OOS_ACCEPTED_COUNT` and normalized headers but, unlike case1 (`:84`), does not assert `OOS_ACCEPTED_COUNT` was appended to `$TMP/review-tally.env`. The plan explicitly required that guard because emit-tally reads `--tally-file` (the env file), not stdout KV; dropping the env append while keeping `emit_kv` would reproduce the overwrite/truncate bug on the production path while unit tally tests still pass. **Suggested fix:** Add `got=$(awk -F= '$1=="OOS_ACCEPTED_COUNT"{print $2}' "$TMP/review-tally.env"); assert_eq ... "1"` to `case6a_norm` (and optionally to case6a as a zero-count control).
- **Suggested revision**: Address the concern above.

### FINDING_45: **code-quality** `python/test_ship.py:313-324` — New legacy-header coverage lives only in `python/test_oos.py`; `test_ship.py` still exercises `_oos_gate` / `run_ship` with canonical `### OOS_1` fixtures or mocks `disposition_ok`, so the Python ship driver (#3462) is not regression-tested for the silent-drop scenario where `oos-accepted-review.md` contains only `### FINDING_N: [OUT_OF_SCOPE]` blocks. Reader-only fixes could satisfy `test_oos.py` while ship wiring or accepted-file discovery regresses. **Suggested fix:** Add `test_oos_gate_legacy_finding_header_blocks_pr_create` (and/or an unmocked `_oos_gate` case) that writes only legacy tagged headers under `oos-accepted-review.md`, omits ndjson/filed URLs, and asserts `Outcome.NEEDS_USER_INPUT` with `non_security_count >= 1` via the real `oos.count_non_security` path.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `python/test_ship.py:313-324` — New legacy-header coverage lives only in `python/test_oos.py`; `test_ship.py` still exercises `_oos_gate` / `run_ship` with canonical `### OOS_1` fixtures or mocks `disposition_ok`, so the Python ship driver (#3462) is not regression-tested for the silent-drop scenario where `oos-accepted-review.md` contains only `### FINDING_N: [OUT_OF_SCOPE]` blocks. Reader-only fixes could satisfy `test_oos.py` while ship wiring or accepted-file discovery regresses. **Suggested fix:** Add `test_oos_gate_legacy_finding_header_blocks_pr_create` (and/or an unmocked `_oos_gate` case) that writes only legacy tagged headers under `oos-accepted-review.md`, omits ndjson/filed URLs, and asserts `Outcome.NEEDS_USER_INPUT` with `non_security_count >= 1` via the real `oos.count_non_security` path.
- **Suggested revision**: Address the concern above.

### FINDING_46: **code-quality** `skills/implement/scripts/test-oos-disposition-gate.sh:521-582` — Legacy-header cases were added for the gate (`:228-257`) but the checkpoint harness section still uses only `### OOS_1:` fixtures for proceed/gap/logging paths. Step 8+ runs `oos-disposition-checkpoint.sh`, which wraps the gate with extra ndjson discovery and Tool Failures logging; a checkpoint-specific regression (e.g., legacy header + gap → exit 1 + execution-issues entry) is not pinned. **Suggested fix:** Mirror the gate’s legacy `### FINDING_1: [OUT_OF_SCOPE]` gap/pass cases in the checkpoint block so the Step 8+ orchestration surface is covered end-to-end.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/test-oos-disposition-gate.sh:521-582` — Legacy-header cases were added for the gate (`:228-257`) but the checkpoint harness section still uses only `### OOS_1:` fixtures for proceed/gap/logging paths. Step 8+ runs `oos-disposition-checkpoint.sh`, which wraps the gate with extra ndjson discovery and Tool Failures logging; a checkpoint-specific regression (e.g., legacy header + gap → exit 1 + execution-issues entry) is not pinned. **Suggested fix:** Mirror the gate’s legacy `### FINDING_1: [OUT_OF_SCOPE]` gap/pass cases in the checkpoint block so the Step 8+ orchestration surface is covered end-to-end.
- **Suggested revision**: Address the concern above.

### FINDING_47: **code-quality** `skills/review-and-fix/scripts/test-review-and-fix.sh:1515-1521` — Skipped-routing assertions verify single-round normalization and `awk` count `== 1`, but the implementation continues `OOS_WRITE_SEQ` from the existing `accumulated-oos.md` block count across rounds (`review-and-fix.sh:1487-1490`). There is no multi-round skipped test proving round-2 append renumbers to `### OOS_2:` (not `OOS_1` again) and keeps `awk` count aligned with accumulated blocks. **Suggested fix:** Add a two-round skipped-routing case with a pre-seeded `accumulated-oos.md` containing one `### OOS_1:` block, then assert the new skipped block becomes `### OOS_2:` and total `awk` count `== 2`.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/test-review-and-fix.sh:1515-1521` — Skipped-routing assertions verify single-round normalization and `awk` count `== 1`, but the implementation continues `OOS_WRITE_SEQ` from the existing `accumulated-oos.md` block count across rounds (`review-and-fix.sh:1487-1490`). There is no multi-round skipped test proving round-2 append renumbers to `### OOS_2:` (not `OOS_1` again) and keeps `awk` count aligned with accumulated blocks. **Suggested fix:** Add a two-round skipped-routing case with a pre-seeded `accumulated-oos.md` containing one `### OOS_1:` block, then assert the new skipped block becomes `### OOS_2:` and total `awk` count `== 2`.
- **Suggested revision**: Address the concern above.

### FINDING_48: **code-quality** `skills/review/scripts/test-emit-tally.sh:98-109` — The `OOS_ACCEPTED_COUNT=0` serialize fallback case only greps for body text (`serialize me`) and does not assert header shape or document why preserve matters for scope drift. `oos-serialize.sh` ignores bare `### FINDING_N:` blocks without `[OUT_OF_SCOPE]`/`[OOS]`, so a negative case showing serialize drops scope-drift while `OOS_ACCEPTED_COUNT>0` preserve retains it would directly fail on the pre-fix bug and strengthen the regression story. **Suggested fix:** Add a case with `OOS_ACCEPTED_COUNT=0` and `oos.md` containing an accepted scope-drift bare `### FINDING_1:` block; assert `oos-accepted-review.md` is empty or lacks that block, contrasted with a chained tally+preserve case where the same drift block survives.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/test-emit-tally.sh:98-109` — The `OOS_ACCEPTED_COUNT=0` serialize fallback case only greps for body text (`serialize me`) and does not assert header shape or document why preserve matters for scope drift. `oos-serialize.sh` ignores bare `### FINDING_N:` blocks without `[OUT_OF_SCOPE]`/`[OOS]`, so a negative case showing serialize drops scope-drift while `OOS_ACCEPTED_COUNT>0` preserve retains it would directly fail on the pre-fix bug and strengthen the regression story. **Suggested fix:** Add a case with `OOS_ACCEPTED_COUNT=0` and `oos.md` containing an accepted scope-drift bare `### FINDING_1:` block; assert `oos-accepted-review.md` is empty or lacks that block, contrasted with a chained tally+preserve case where the same drift block survives.
- **Suggested revision**: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] `skills/review/scripts/test-review-core.sh:312-339` still stubs `emit-tally.sh` to overwrite `oos-accepted-review.md` with placeholder `# oos` content; the plan documents this limitation, so production tally→emit behavior cannot be validated through `test-review-core.sh` without stub changes.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - `skills/review/scripts/test-review-core.sh:312-339` still stubs `emit-tally.sh` to overwrite `oos-accepted-review.md` with placeholder `# oos` content; the plan documents this limitation, so production tally→emit behavior cannot be validated through `test-review-core.sh` without stub changes.
- **Suggested revision**: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] `skills/issue/scripts/test-parse-input.sh` has no `### FINDING_N: [OUT_OF_SCOPE]` batch-mode cases; that is consistent with the plan’s producer-normalization approach (filing still requires `### OOS_N:`), but the `OOS_ACCEPTED_COUNT=0` serialize fallback in `emit-tally.sh` can still emit legacy `FINDING_` headers via `oos-serialize.sh`, relying on reader backstop rather than `/issue` parser coverage.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - `skills/issue/scripts/test-parse-input.sh` has no `### FINDING_N: [OUT_OF_SCOPE]` batch-mode cases; that is consistent with the plan’s producer-normalization approach (filing still requires `### OOS_N:`), but the `OOS_ACCEPTED_COUNT=0` serialize fallback in `emit-tally.sh` can still emit legacy `FINDING_` headers via `oos-serialize.sh`, relying on reader backstop rather than `/issue` parser coverage.
- **Suggested revision**: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] Makefile wiring looks correct: `test-normalize-oos-block-header` is registered (`Makefile:895-896`) and included in `test-harnesses-9` (`Makefile:53`); related harnesses (`test-emit-tally`, `test-tally-code-votes`, `test-oos-disposition-gate`, `test-review-and-fix`) remain on their existing shards.
- **Reviewer**: dyn-harness-coverage-output.txt
- **Concern**: - Makefile wiring looks correct: `test-normalize-oos-block-header` is registered (`Makefile:895-896`) and included in `test-harnesses-9` (`Makefile:53`); related harnesses (`test-emit-tally`, `test-tally-code-votes`, `test-oos-disposition-gate`, `test-review-and-fix`) remain on their existing shards.
- **Suggested revision**: Address the concern above.

