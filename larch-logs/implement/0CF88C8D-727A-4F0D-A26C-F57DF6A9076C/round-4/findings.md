### FINDING_1: code-quality: skills/shared/scripts/oos-serialize.sh:31-62
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Security routing duplicated as inline Python instead of reusing lib-vote-tally.sh::is_security_block. Future security contract changes require editing lib-vote-tally, oos-serialize, python/oos.py, and awk in lockstep; harnesses test each copy independently so drift can ship silently. Source lib-vote-tally.sh in oos-serialize.sh and call is_security_block per block with explicit exit-2 handling; delete the inline Python heredoc.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:1438-1457
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Skipped-OOS path calls is_security_block twice with nested if/else including unreachable sec_rc=0 branch. Harder to audit the 0=security / 1=normalize / 2=abort contract; future edits may reintroduce mis-routing. Single is_security_block call with case on exit code for security append, normalization, or abort.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/lib-vote-tally.sh:56-60
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Plan-scoped SIMPLE fix expanded into broad is_security_block contract changes across vote-tally, SECURITY.md, voting-protocol, oos-serialize, python/oos.py, and awk. Increases change surface and drift risk beyond the header-normalization / emit-tally bug; harder to reason about what #3550 alone required. Narrow to #3550-minimum security changes or extract one shared security-routing module consumed by all four surfaces.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/shared/scripts/oos-serialize.sh:73
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Result= filtering uses whole-block substring heuristics instead of parsing the tally footer line. A rejected OOS block whose Description mentions Result=accepted could be serialized on emit-tally rebuild, reintroducing silent drops or false gate counts. Match only the vote-tally Result= footer line (or parse it explicitly) rather than substring-searching the full block body.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/review/scripts/tally-code-votes.sh:122-123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] NORMALIZE_OOS_HELPER uses SCRIPT_DIR-relative path while OOS_COUNT_HELPER uses PLUGIN_ROOT. Inconsistent helper resolution style in the same initialization block. Resolve both helpers from PLUGIN_ROOT.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: skills/review/scripts/tally-code-votes.sh:547
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] is_security_block failures are swallowed via 2>/dev/null, treating exit 2 as non-security. When python3 is missing, security-tagged accepted OOS can enter the public sink and bypass disposition filing. Propagate exit 2 as a hard failure instead of masking stderr and defaulting to public routing.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/shared/scripts/oos-serialize.sh:31-62
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] oos-serialize.sh now requires python3 for security classification; the prior implementation was pure awk. On a bash-only runner, emit-tally's OOS_ACCEPTED_COUNT==0 serialize/rebuild path fails when python3 is missing, aborting the review round instead of populating the accepted sink. Add an awk-only security fallback when python3 is unavailable, or fail at script entry with an explicit python3 prerequisite and document it in oos-serialize.md.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/review/scripts/tally-code-votes.sh:546-549
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] is_security_block exit 2 (python failure) is swallowed, so security-tagged accepted OOS can be written to the public sink; amplified by expanded security rules in lib-vote-tally.sh. A voted-accepted block with - **focus-area**: security or a [security] heading tag is treated as non-security when python3 is absent, normalized to ### OOS_, counted by the gate, and eligible for public filing. Treat is_security_block exit 2 as a hard tally error, or add a non-python fallback that implements the expanded routing rules.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/shared/scripts/oos-serialize.sh:73
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Result= filtering uses substring match over the entire block body. A hand-edited accepted OOS block whose prose mentions Result=rejected but lacks a Result=accepted vote line is dropped on serialize/rebuild, causing emit-tally rebuild count mismatch and exit 1. Match only the structured vote-tally Result= line (e.g. trailing Result=accepted) instead of any Result= substring in the body.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] correctness: skills/shared/scripts/oos-serialize.sh:89-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Serializer only parses ### FINDING_N: block starters; ### OOS_N: blocks in oos.md are skipped on rebuild. Direct-OOS ballot items desynced from the accepted sink cannot be rebuilt from oos.md; emit-tally fails closed when counts diverge. Pre-existing; extend oos-serialize to open ### OOS_N: blocks or document that rebuild only covers FINDING-tagged oos.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/implement/scripts/oos-non-security-block-count.awk:15
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reader backstop requires [OUT_OF_SCOPE] on FINDING headers while oos-serialize also accepts [OOS]. Surviving legacy ### FINDING_N: … [OOS] headers (no [OUT_OF_SCOPE]) may serialize on the count==0 path but still count as zero in gates. Pre-existing format split; extend counters to accept [OOS] or ensure all producers normalize before gate read.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/issue/scripts/parse-input.sh (no new tests in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required end-to-end filing coverage is missing: no test proves normalized accepted OOS reaches /issue batch parsing or filing. A regression that re-breaks only the filing parser contract (canonical headers present, gate passes) could still ship with OOS filed: 0 in production. Extend test-parse-input.sh or add a harness that feeds normalized ### OOS_<seq>: fixtures through parse-input.sh batch mode (or documented /issue dry-run) and asserts parsed issue records.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/shared/scripts/oos-serialize.sh:33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] serialize path now hard-requires python3; emit-tally no longer ignores serialize failures. On OOS_ACCEPTED_COUNT==0 rounds, missing python3 causes emit-tally/serialize to exit non-zero and abort review emit instead of producing an accepted-OOS sink. Add python3-absent regression cases to test-oos-serialize.sh and/or test-emit-tally.sh, or document and test an explicit fallback if bash-only operation remains supported.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: python/oos.py + skills/implement/scripts/oos-non-security-block-count.awk
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No shared fixture harness enforces awk/Python counter parity despite plan lockstep requirement. Awk and Python counters can diverge on edge cases (trailing vs leading tag, security header forms) while both test suites still pass. Add a shared-fixture parity harness run under make lint comparing awk and python count_non_security on the same markdown files.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/scripts/test-oos-disposition-gate.sh:539-600
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Checkpoint harness lacks legacy FINDING header cases added for the gate primitive. Legacy-header blocks could behave differently in checkpoint wiring (tmpdir discovery, NDJSON paths) than in direct gate tests. Mirror #3550 legacy-header gate cases in the checkpoint section of test-oos-disposition-gate.sh.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: python/test_ship.py:327-426
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Python ship _oos_gate test covers only trailing-tag legacy FINDING headers. Leading-tag legacy headers block PR create via count logic but lack ship-driver regression coverage. Add test_oos_gate_blocks_legacy_leading_tag_without_filed_evidence alongside the existing trailing-tag case.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: skills/review/scripts/tally-code-votes.sh:546-548
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Tally fail-opens when is_security_block errors: stderr suppressed and any non-zero exit leaves security=false, so accepted security OOS can be normalized into the public oos-accepted-review.md sink. With python3/import/read failure (rc 2), a voted ### FINDING_N: [OUT_OF_SCOPE] block carrying sensitive security content is rewritten to ### OOS_1:, counted by the gate, and filed publicly via /issue — whereas pre-#3550 the same block was often silently dropped and never filed. Capture is_security_block exit code explicitly; on rc 2 fail closed (abort or default security=true / hold locally); remove 2>/dev/null; add harness coverage for classifier failure.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/lib-vote-tally.sh:83
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] is_security_block applies explicit_header across the full block, but SECURITY.md, oos-serialize.sh, and gate counters only honor [security]/<security> on the opening heading. A reviewer cites ### FINDING_99: [security] in Concern prose: tally holds locally (no public filing) while serialize/gate docs say body headings are not routing tags — inconsistent public/private routing between producers. Restrict explicit_header matching to lines[0] in is_security_block to match oos-serialize and documented contract, or document and test whole-block scan as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security: skills/implement/scripts/oos-non-security-block-count.awk:21-24
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Gate counter does not exclude blocks whose only security signal is unfenced canonical prose focus-area = security in the body. If producer hold fails, such a block is counted as non-security and the gate pushes public filing even though is_security_block would have held it. Optionally extend awk/python counters to mirror canonical prose detection as defense-in-depth after tally fail-closed fix.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh:60-91
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Four parallel security-routing implementations (lib-vote-tally, oos-serialize, awk counter, python/oos.py) can drift after future edits. Subtle routing mismatch reintroduces silent drops or accidental public filing without cross-harness failure. Consolidate on one shared security-routing module invoked by all paths.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/shared/scripts/oos-serialize.sh:80-110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] oos-serialize.sh now hard-requires python3 for security tagging while emit-tally no longer ignores serialize failures. OOS_ACCEPTED_COUNT==0 runs that call oos-serialize on a host without python3 will abort emit-tally and leave accepted-OOS handling broken on the standalone serialize path. Add python3 availability handling or an awk fallback; fail loudly before mutating the accepted sink.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/tally-code-votes.sh:546-549
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] tally treats is_security_block exit 2 as non-security because stderr is discarded and only exit 0 is treated as security. When python3 is missing or the classifier errors, security-tagged accepted OOS can be normalized and written to the public oos-accepted-review.md sink. Capture is_security_block exit codes; fail closed or hold locally on exit 2, matching review-and-fix.sh.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/review/scripts/tally-code-votes.sh:522-524
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] [OOS] shorthand is not treated as an OOS marker in tally or reader backstop, only in oos-serialize.sh. Accepted ### FINDING_N: [OOS] findings never normalize, never increment OOS_ACCEPTED_COUNT on the production path, and can still be silently dropped at ship time. Extend tally is_oos and awk/Python header matchers to accept [OOS] with the same tag-required semantics as [OUT_OF_SCOPE].
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:1451-1468
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Partial skipped_file content is appended to accumulated-oos.md even when classifier_loop_abort is set. A classifier failure mid-loop can mutate oos-accepted-review.md then exit the round as classifier-failed, leaving inconsistent Step 5 vs ship-gate state. Guard the append on classifier_loop_abort or undo partial mirror writes on abort.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/review/scripts/tally-code-votes.sh:125-130
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] OOS_WRITE_SEQ seeding uses non-security awk count that ignores bare legacy FINDING headers in accumulated-oos.md. Resuming a session with pre-#3550 accumulated content can reuse OOS_1 and produce duplicate or ambiguous blocks for filing parsers. Seed from normalized block count or normalize accumulated-oos.md before continuing the sequence.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: skills/review-and-fix/scripts/review-and-fix.sh:1438-1456
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate is_security_block invocation in the skipped-findings else branch with a dead sec_rc==0 path. No functional breakage today, but obscures the intended 0/1/2 branching and invites future mis-edits. Replace with one classifier call and explicit exit-code branching.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-and-fix.sh:1334-1359
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Degraded-panel retry calls append_round_oos_artifact twice per round. Both review-core passes may append the same round's accepted OOS twice into accumulated-oos.md. Pre-existing; fix outside #3550 unless retry duplication is in scope.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: skills/shared/scripts/oos-serialize.sh:1-110
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Unplanned full rewrite of oos-serialize.sh contradicts plan to leave serialize unchanged on tally-wrote path. A standalone or OOS_ACCEPTED_COUNT==0 path that relied on the old pure-awk serializer now depends on python3, Result= filtering, and duplicated security logic not authorized in the plan. Revert to minimal fallback behavior or amend the plan to authorize serialize as a normalized producer and cover it explicitly in acceptance tests.
- **Suggested revision**: Address the concern above.

### FINDING_29: architecture: scripts/lib-vote-tally.sh:36-75
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Vote-tally security routing expanded beyond plan constraint and file list. Security-tagged OOS detected via focus-area: fields or [security] headings are routed differently than the plan’s unchanged-security-branch assumption. Amend plan for the broader contract or reduce changes to the minimum needed for #3550 header normalization.
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/review/scripts/tally-code-votes.sh:593-609
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] OOS_ACCEPTED_COUNT now excludes security-held accepted OOS. Downstream tooling that still treats OOS_ACCEPTED_COUNT as all accepted OOS may mis-handle security-only review rounds. Document the new meaning everywhere or split public vs security-held counters.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: skills/review/scripts/emit-tally.sh:161-167
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Preserve guard stricter than plan pseudocode (requires sink count match). Tally/env desync exits non-zero instead of blindly preserving per the plan’s if oos_accepted_count > 0 branch. Update plan to match implemented fail-closed/rebuild semantics or simplify to the planned guard.
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: python/oos.py:32-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Python legacy-header regex broader than plan literal (.* vs \\s* before tag). Trailing [OUT_OF_SCOPE] headers count in Python/awk but not under the plan’s immediate-post-colon spec. Unify and document one header-tag placement rule across plan, awk, and Python.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.sh:523
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] [OOS]-only FINDING headers still not classified as OOS in tally. Legacy ballots using [OOS] without [OUT_OF_SCOPE] may still miss producer normalization unless serialize fallback runs. Extend tally OOS detection to [OOS] if that legacy format is still in production use.
- **Suggested revision**: Address the concern above.

### FINDING_34: **risk-integration** `scripts/lib-vote-tally.sh:74-83` + `skills/shared/scripts/oos-serialize.sh:41-53` — `is_security_block` now runs `explicit_header.search(text_no_fence)` with `re.MULTILINE` over the whole block, so a body line like `### FINDING_N: [security] …` (a cited heading in Concern/Suggested revision) can mark the block security-held in `tally-code-votes.sh` (`OOS_ACCEPTED_COUNT` stays 0; nothing is written to the tally accepted sink). The same block is still copied into `oos.md`, and when `emit-tally.sh` takes the `OOS_ACCEPTED_COUNT == 0` serialize fallback it calls `oos-serialize.sh`, whose `is_security_tagged_block` only applies `explicit_header` to line 1. A block whose opening line is a benign `### FINDING_1: [OUT_OF_SCOPE] …` but cites a security heading in the body can therefore be re-published into `oos-accepted-review.md`, bypassing tally’s hold and potentially reaching `/issue` public filing. This diverges from `SECURITY.md` (“later `### … [security] …` headings inside prose are not routing tags”) and creates inconsistent producer/consumer security routing on the tally → emit-tally → serialize chain. **Suggested fix:** Restrict `explicit_header` in `is_security_block` to the block-opening line only (match `oos-serialize.sh` / `SECURITY.md`), or teach `is_security_tagged_block` the same body-level rule if body citations must route — but do not let tally hold on body citations while serialize publishes on the `OOS_ACCEPTED_COUNT == 0` path.
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `scripts/lib-vote-tally.sh:74-83` + `skills/shared/scripts/oos-serialize.sh:41-53` — `is_security_block` now runs `explicit_header.search(text_no_fence)` with `re.MULTILINE` over the whole block, so a body line like `### FINDING_N: [security] …` (a cited heading in Concern/Suggested revision) can mark the block security-held in `tally-code-votes.sh` (`OOS_ACCEPTED_COUNT` stays 0; nothing is written to the tally accepted sink). The same block is still copied into `oos.md`, and when `emit-tally.sh` takes the `OOS_ACCEPTED_COUNT == 0` serialize fallback it calls `oos-serialize.sh`, whose `is_security_tagged_block` only applies `explicit_header` to line 1. A block whose opening line is a benign `### FINDING_1: [OUT_OF_SCOPE] …` but cites a security heading in the body can therefore be re-published into `oos-accepted-review.md`, bypassing tally’s hold and potentially reaching `/issue` public filing. This diverges from `SECURITY.md` (“later `### … [security] …` headings inside prose are not routing tags”) and creates inconsistent producer/consumer security routing on the tally → emit-tally → serialize chain. **Suggested fix:** Restrict `explicit_header` in `is_security_block` to the block-opening line only (match `oos-serialize.sh` / `SECURITY.md`), or teach `is_security_tagged_block` the same body-level rule if body citations must route — but do not let tally hold on body citations while serialize publishes on the `OOS_ACCEPTED_COUNT == 0` path.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-oos-pipeline-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/review-core.sh:931-932` + `skills/review-and-fix/scripts/review-and-fix.sh:158-166` — On a review round with zero accepted OOS, `copy_to_parent` can overwrite `$IMPLEMENT_TMPDIR/oos-accepted-review.md` with an empty round file while `append_round_oos_artifact` no-ops; `accumulated-oos.md` may still hold prior-round OOS. `oos-disposition-checkpoint.sh` counts only the mirror paths (`oos-accepted-review.md`, not `accumulated-oos.md`), so the gate can all-clear on an empty mirror even when accumulated markdown still has blocks. Pre-existing; not introduced by this branch, though it remains a cross-artifact consistency gap alongside the mirror-based gate.
- **Suggested revision**: Address the concern above.

### FINDING_36: **code-quality** `skills/shared/scripts/oos-serialize.sh:31-62` — The round-3 rewrite replaced a pure-awk `is_security_tagged` implementation with a `python3` heredoc inside `is_security_tagged_block`, but unlike `scripts/lib-vote-tally.sh`'s `is_security_block` (lines 62–63) there is no `command -v python3` / import probe and no structured failure mode when Python is missing or broken. Under `set -euo pipefail`, that makes the serialize fallback path hard-fail instead of degrading predictably, and `emit-tally.sh` now propagates serialize failures (`skills/review/scripts/emit-tally.sh:174`, `|| true` removed in round 3). That is a portability regression relative to the prior awk-only script and the repo's Bash 3.2 / minimal-dependency authoring constraints. **Suggested fix:** Mirror the `lib-vote-tally.sh` availability probe (`command -v python3` + import smoke test, return a distinct non-zero code with a clear stderr message), document `python3` as a hard prerequisite if intentional, and add a harness case that asserts the script fails closed (not silently mis-classifies) when `python3` is unavailable.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/shared/scripts/oos-serialize.sh:31-62` — The round-3 rewrite replaced a pure-awk `is_security_tagged` implementation with a `python3` heredoc inside `is_security_tagged_block`, but unlike `scripts/lib-vote-tally.sh`'s `is_security_block` (lines 62–63) there is no `command -v python3` / import probe and no structured failure mode when Python is missing or broken. Under `set -euo pipefail`, that makes the serialize fallback path hard-fail instead of degrading predictably, and `emit-tally.sh` now propagates serialize failures (`skills/review/scripts/emit-tally.sh:174`, `|| true` removed in round 3). That is a portability regression relative to the prior awk-only script and the repo's Bash 3.2 / minimal-dependency authoring constraints. **Suggested fix:** Mirror the `lib-vote-tally.sh` availability probe (`command -v python3` + import smoke test, return a distinct non-zero code with a clear stderr message), document `python3` as a hard prerequisite if intentional, and add a harness case that asserts the script fails closed (not silently mis-classifies) when `python3` is unavailable.
- **Suggested revision**: Address the concern above.

### FINDING_37: **code-quality** `skills/review/scripts/tally-code-votes.sh:598-600` — Accepted OOS blocks are captured via command substitution (`normalized=$(...)`) before append, but Bash strips all trailing newlines from `$(...)` output. That can mutate multiline block content (e.g., drop a terminal blank line) before it reaches `oos-accepted-review.md`, while the parallel path in `skills/review-and-fix/scripts/review-and-fix.sh:1446-1447` correctly streams helper stdout with `>>` and preserves bytes. The inconsistency is a real quoting/content-handling defect on a path explicitly constrained to portable shell. **Suggested fix:** Stop using command substitution for multiline normalized blocks; redirect `normalize-oos-block-header.sh` stdout directly to the sink (or through a temp file reused for the conditional mirror write), matching the `review-and-fix.sh` pattern.
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/tally-code-votes.sh:598-600` — Accepted OOS blocks are captured via command substitution (`normalized=$(...)`) before append, but Bash strips all trailing newlines from `$(...)` output. That can mutate multiline block content (e.g., drop a terminal blank line) before it reaches `oos-accepted-review.md`, while the parallel path in `skills/review-and-fix/scripts/review-and-fix.sh:1446-1447` correctly streams helper stdout with `>>` and preserves bytes. The inconsistency is a real quoting/content-handling defect on a path explicitly constrained to portable shell. **Suggested fix:** Stop using command substitution for multiline normalized blocks; redirect `normalize-oos-block-header.sh` stdout directly to the sink (or through a temp file reused for the conditional mirror write), matching the `review-and-fix.sh` pattern.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/review/scripts/tally-code-votes.sh:547` — `is_security_block "$block" 2>/dev/null` still swallows classifier failures (including `return 2` when `python3` is missing from the shared library); pre-existing, but now more consequential because security detection logic is duplicated across `lib-vote-tally.sh` and `oos-serialize.sh` without a single shared probe helper.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-shell-portability-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-and-fix.sh:1438-1447` — The skipped-OOS branch calls `is_security_block` twice for every non-security block (once in the `if`, again in the `else` for exit-code routing); harmless but avoidable overhead introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `scripts/lib-vote-tally.sh:74-83` — `is_security_block` applies `explicit_header` with `re.MULTILINE` to the entire `text_no_fence`, so any body line shaped like `### … [security] …` is treated as a security route. That conflicts with `scripts/lib-vote-tally.md:44` (“later body headings that merely cite `[security]` do not route the block”), with `skills/shared/scripts/oos-serialize.sh:50-53` (only `lines[0]` is checked), and with `python/oos.py:77-85` / `skills/implement/scripts/oos-non-security-block-count.awk:15-24` (security heading tags apply only on block-opening lines). `skills/shared/scripts/test-oos-serialize.sh:27-38` expects `### FINDING_8: [OUT_OF_SCOPE] Cited security heading` plus body `### Example [security] policy` to stay public (4 accepted, not held), but the tally production path (`tally-code-votes.sh` → `is_security_block`) would hold it as security and skip the public accepted-OOS sink—another silent drop of voted-in non-security OOS. **Suggested fix:** Match `oos-serialize.sh`: test `explicit_header` only against the first non-empty line of `text_no_fence` (or drop the full-text `explicit_header.search` and keep header-tag detection block-local). Add a `scripts/test-lib-vote-tally.sh` case mirroring `test-oos-serialize.sh` FINDING_8 so tally and serialize stay aligned.
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `scripts/lib-vote-tally.sh:74-83` — `is_security_block` applies `explicit_header` with `re.MULTILINE` to the entire `text_no_fence`, so any body line shaped like `### … [security] …` is treated as a security route. That conflicts with `scripts/lib-vote-tally.md:44` (“later body headings that merely cite `[security]` do not route the block”), with `skills/shared/scripts/oos-serialize.sh:50-53` (only `lines[0]` is checked), and with `python/oos.py:77-85` / `skills/implement/scripts/oos-non-security-block-count.awk:15-24` (security heading tags apply only on block-opening lines). `skills/shared/scripts/test-oos-serialize.sh:27-38` expects `### FINDING_8: [OUT_OF_SCOPE] Cited security heading` plus body `### Example [security] policy` to stay public (4 accepted, not held), but the tally production path (`tally-code-votes.sh` → `is_security_block`) would hold it as security and skip the public accepted-OOS sink—another silent drop of voted-in non-security OOS. **Suggested fix:** Match `oos-serialize.sh`: test `explicit_header` only against the first non-empty line of `text_no_fence` (or drop the full-text `explicit_header.search` and keep header-tag detection block-local). Add a `scripts/test-lib-vote-tally.sh` case mirroring `test-oos-serialize.sh` FINDING_8 so tally and serialize stay aligned.
- **Suggested revision**: Address the concern above.

### FINDING_41: **correctness** `python/oos.py:36-39`, `skills/implement/scripts/oos-non-security-block-count.awk:24`, `scripts/lib-vote-tally.sh:79-81` — Security `focus-area` detection diverges: producers/serializers use `field_value` with `^[ \t-]*focus-area…` (dash optional), while the gate counters require a list-marker dash (`^\s*-\s*focus-area` in Python; `^[[:space:]]*-[[:space:]]*focus-area` in awk). A block such as `### OOS_1: …` followed by a line-start `focus-area: security` (no leading `-`) is held as security by `is_security_block` / `oos-serialize.sh`, but if that shape lands in an accepted-OOS sink (manual artifact, partial rebuild, or future writer), `count_non_security` still counts it as non-security and the disposition gate can push public filing. **Suggested fix:** Port the producer `field_value` pattern into `_SECURITY_FOCUS_RE` and `oos-non-security-block-count.awk` (optional leading `-`/whitespace, `:` or `=`, same `security…` suffix rule), and add paired tests in `python/test_oos.py` and `skills/implement/scripts/test-oos-disposition-gate.sh`.
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `python/oos.py:36-39`, `skills/implement/scripts/oos-non-security-block-count.awk:24`, `scripts/lib-vote-tally.sh:79-81` — Security `focus-area` detection diverges: producers/serializers use `field_value` with `^[ \t-]*focus-area…` (dash optional), while the gate counters require a list-marker dash (`^\s*-\s*focus-area` in Python; `^[[:space:]]*-[[:space:]]*focus-area` in awk). A block such as `### OOS_1: …` followed by a line-start `focus-area: security` (no leading `-`) is held as security by `is_security_block` / `oos-serialize.sh`, but if that shape lands in an accepted-OOS sink (manual artifact, partial rebuild, or future writer), `count_non_security` still counts it as non-security and the disposition gate can push public filing. **Suggested fix:** Port the producer `field_value` pattern into `_SECURITY_FOCUS_RE` and `oos-non-security-block-count.awk` (optional leading `-`/whitespace, `:` or `=`, same `security…` suffix rule), and add paired tests in `python/test_oos.py` and `skills/implement/scripts/test-oos-disposition-gate.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/oos-non-security-block-count.awk:15`, `python/oos.py:32-34`, `skills/review/scripts/tally-code-votes.sh:523` — Legacy FINDING block-start counting/backstop keys on `[OUT_OF_SCOPE]` only; `skills/shared/scripts/oos-serialize.sh:95-96` also treats `[OOS]` as OOS-tagged. Unnormalized `### FINDING_N: [OOS]` sinks could still read as zero blocks at the gate; producer normalization is the intended fix, but reader parity for `[OOS]`-only FINDING headers was not extended.
- **Suggested revision**: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-parser-parity-output.txt
- **Concern**: - **correctness** `skills/shared/scripts/oos-serialize.sh:89-98` — Serialization still splits only on `^### FINDING_[0-9]+:`; ballot blocks headed `### OOS_N:` are not split on the `OOS_ACCEPTED_COUNT==0` serialize fallback path (pre-existing; unchanged by this branch).
- **Suggested revision**: Address the concern above.

### FINDING_44: **security** `skills/review/scripts/tally-code-votes.sh:546-608`, `skills/review/scripts/emit-tally.sh:155-167`, `skills/implement/scripts/oos-non-security-block-count.awk:14-28`, `python/oos.py:36-88` — The branch adds canonical-header normalization on the public accepted-OOS write path and a new emit-tally preserve branch, but `tally-code-votes.sh` still classifies security with a fail-open call (`is_security_block "$block" 2>/dev/null`), while `review-and-fix.sh` was updated to fail closed on classifier errors. When `python3`/classifier failure makes `is_security_block` return non-zero, a block whose only security marker is unfenced prose such as `focus-area = security` in **Concern**/**Description** is normalized into `oos-accepted-review.md` and increments `OOS_ACCEPTED_COUNT`. The gate counter does not treat that prose token as security (only dedicated line-start `focus-area:`/`=` fields and opening `[security]` heading tags), so `oos_sink_count` matches `oos_accepted_count` and emit-tally preserves the file without running `oos-serialize.sh`'s security filter. The disposition gate then counts the block as public non-security and can drive `/issue` filing of sensitive review content. **Suggested fix:** Make `tally-code-votes.sh` use the same fail-closed `sec_rc` handling as `review-and-fix.sh` (treat exit `2` as round failure, never normalize/write on classifier error), and either extend `oos-non-security-block-count.awk` / `python/oos.py` to exclude unfenced canonical `focus-area\s*=\s*security` prose in dedicated OOS sinks as defense-in-depth, or abort emit-tally preserve when classifier health cannot be verified.
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `skills/review/scripts/tally-code-votes.sh:546-608`, `skills/review/scripts/emit-tally.sh:155-167`, `skills/implement/scripts/oos-non-security-block-count.awk:14-28`, `python/oos.py:36-88` — The branch adds canonical-header normalization on the public accepted-OOS write path and a new emit-tally preserve branch, but `tally-code-votes.sh` still classifies security with a fail-open call (`is_security_block "$block" 2>/dev/null`), while `review-and-fix.sh` was updated to fail closed on classifier errors. When `python3`/classifier failure makes `is_security_block` return non-zero, a block whose only security marker is unfenced prose such as `focus-area = security` in **Concern**/**Description** is normalized into `oos-accepted-review.md` and increments `OOS_ACCEPTED_COUNT`. The gate counter does not treat that prose token as security (only dedicated line-start `focus-area:`/`=` fields and opening `[security]` heading tags), so `oos_sink_count` matches `oos_accepted_count` and emit-tally preserves the file without running `oos-serialize.sh`'s security filter. The disposition gate then counts the block as public non-security and can drive `/issue` filing of sensitive review content. **Suggested fix:** Make `tally-code-votes.sh` use the same fail-closed `sec_rc` handling as `review-and-fix.sh` (treat exit `2` as round failure, never normalize/write on classifier error), and either extend `oos-non-security-block-count.awk` / `python/oos.py` to exclude unfenced canonical `focus-area\s*=\s*security` prose in dedicated OOS sinks as defense-in-depth, or abort emit-tally preserve when classifier health cannot be verified.
- **Suggested revision**: Address the concern above.

### FINDING_45: **security** `skills/shared/scripts/oos-serialize.sh:31-77`, `skills/review/scripts/emit-tally.sh:168-183` — On the emit-tally mismatch rebuild path (`OOS_ACCEPTED_COUNT > 0` but sink count differs), accepted OOS is regenerated from `oos.md` via `oos-serialize.sh`, whose `is_security_tagged_block()` helper treats any Python failure as “not security” and proceeds to normalize/write the block. That is the opposite of the fail-closed posture now documented for `review-and-fix.sh` in `SECURITY.md` and can reintroduce security-tagged blocks from `oos.md` into `oos-accepted-review.md` when `python3` is unavailable or the helper errors. The branch increases reliance on this rebuild path whenever tally sink counts diverge. **Suggested fix:** Mirror the skipped-path contract: on classifier exit `2` or launch failure, fail the emit-tally rebuild (exit non-zero) instead of serializing; optionally share one fail-closed wrapper around `is_security_block` for tally, review-and-fix, and oos-serialize.
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `skills/shared/scripts/oos-serialize.sh:31-77`, `skills/review/scripts/emit-tally.sh:168-183` — On the emit-tally mismatch rebuild path (`OOS_ACCEPTED_COUNT > 0` but sink count differs), accepted OOS is regenerated from `oos.md` via `oos-serialize.sh`, whose `is_security_tagged_block()` helper treats any Python failure as “not security” and proceeds to normalize/write the block. That is the opposite of the fail-closed posture now documented for `review-and-fix.sh` in `SECURITY.md` and can reintroduce security-tagged blocks from `oos.md` into `oos-accepted-review.md` when `python3` is unavailable or the helper errors. The branch increases reliance on this rebuild path whenever tally sink counts diverge. **Suggested fix:** Mirror the skipped-path contract: on classifier exit `2` or launch failure, fail the emit-tally rebuild (exit non-zero) instead of serializing; optionally share one fail-closed wrapper around `is_security_block` for tally, review-and-fix, and oos-serialize.
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `skills/review/scripts/tally-code-votes.sh:590-592` — Accepted security OOS blocks are still appended to round-local `oos.md` before the holdback branch runs. `SECURITY.md` says security findings are never written to the `oos.md` visibility export; that doc/code mismatch predates this branch and was not introduced by the #3550 changes.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-holdback-routing-output.txt
- **Concern**: - **security** `scripts/lib-vote-tally.sh:56-90` vs `skills/implement/scripts/oos-non-security-block-count.awk:14-28` — The write-time classifier routes on unfenced canonical `focus-area\s*=\s*security` anywhere in the block, while the gate counter intentionally ignores that prose pattern to avoid miscounting mixed files. That asymmetry is longstanding; this branch amplifies its impact only when fail-open writers place such blocks in dedicated accepted-OOS sinks (see first in-scope finding).
- **Suggested revision**: Address the concern above.

### FINDING_48: **correctness** `skills/review/scripts/test-emit-tally.sh:182-207` — The chained tagged-OOS tally→emit case only checks that `oos-accepted-review.md` ends up with a canonical `### OOS_1:` block, but when `oos.md` is present a broken `OOS_ACCEPTED_COUNT>0` preserve branch still passes because `oos-serialize.sh` re-derives and normalizes the same tagged legacy block. That means this case cannot catch the original #3550 failure mode (tally wrote the sink, then emit overwrote it) on the tagged-OOS path when `oos.md` exists; only `preserve1` (mismatched `oos.md` content) and `chained-drift` (bare scope-drift not recoverable from `oos.md`) actually exercise preserve. **Suggested fix:** Make the chained tagged case mirror `preserve1`: pre-seed tally-normalized sink content with a tally-only marker, give `oos.md` conflicting serialize output, and `cmp` after emit so a serialize fallback changes the file; or assert `review-tally.env` carries `OOS_ACCEPTED_COUNT=1` and add a sibling case with `oos.md` absent after tally (scope-drift-style) so missing env count cannot be masked by serialize.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-emit-tally.sh:182-207` — The chained tagged-OOS tally→emit case only checks that `oos-accepted-review.md` ends up with a canonical `### OOS_1:` block, but when `oos.md` is present a broken `OOS_ACCEPTED_COUNT>0` preserve branch still passes because `oos-serialize.sh` re-derives and normalizes the same tagged legacy block. That means this case cannot catch the original #3550 failure mode (tally wrote the sink, then emit overwrote it) on the tagged-OOS path when `oos.md` exists; only `preserve1` (mismatched `oos.md` content) and `chained-drift` (bare scope-drift not recoverable from `oos.md`) actually exercise preserve. **Suggested fix:** Make the chained tagged case mirror `preserve1`: pre-seed tally-normalized sink content with a tally-only marker, give `oos.md` conflicting serialize output, and `cmp` after emit so a serialize fallback changes the file; or assert `review-tally.env` carries `OOS_ACCEPTED_COUNT=1` and add a sibling case with `oos.md` absent after tally (scope-drift-style) so missing env count cannot be masked by serialize.
- **Suggested revision**: Address the concern above.

### FINDING_49: **correctness** `skills/implement/scripts/test-oos-disposition-gate.sh:165-275` — Legacy `### FINDING_N: [OUT_OF_SCOPE]` gate cases cover unresolved disposition (exit 1) and filed-URL pass (exit 0), but there is no bash integration case that a security-routed legacy header (`### FINDING_1: [OUT_OF_SCOPE]` plus `- **focus-area**: security`) is excluded from the non-security obligation set and passes without URLs. `python/test_oos.py` has `test_count_non_security_excludes_security_tagged_legacy_header`, yet the bash gate harness only exercises security exclusion on `### OOS_` fixtures, so awk security handling on legacy `FINDING_` headers can drift from Python without failing CI’s bash shard. **Suggested fix:** Add a gate (and optionally checkpoint) fixture with a legacy tagged `FINDING_` security block and assert exit 0 with empty filed-urls, plus a direct `oos-non-security-block-count.awk` assertion that the count is 0.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-oos-disposition-gate.sh:165-275` — Legacy `### FINDING_N: [OUT_OF_SCOPE]` gate cases cover unresolved disposition (exit 1) and filed-URL pass (exit 0), but there is no bash integration case that a security-routed legacy header (`### FINDING_1: [OUT_OF_SCOPE]` plus `- **focus-area**: security`) is excluded from the non-security obligation set and passes without URLs. `python/test_oos.py` has `test_count_non_security_excludes_security_tagged_legacy_header`, yet the bash gate harness only exercises security exclusion on `### OOS_` fixtures, so awk security handling on legacy `FINDING_` headers can drift from Python without failing CI’s bash shard. **Suggested fix:** Add a gate (and optionally checkpoint) fixture with a legacy tagged `FINDING_` security block and assert exit 0 with empty filed-urls, plus a direct `oos-non-security-block-count.awk` assertion that the count is 0.
- **Suggested revision**: Address the concern above.

### FINDING_50: **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:1522-1557` — Skipped-routing coverage validates normalized headers and awk count on `oos-accepted-review.md` / `accumulated-oos.md`, but never inspects `accumulated-oos.jsonl`, even though `review-and-fix.sh` writes jsonl via `--rawfile body "$skipped_file"` and the plan requires jsonl and markdown to share the same normalized aggregate. A regression that normalizes markdown but leaves bare `### FINDING_` in jsonl would pass this harness while breaking downstream consumers that read jsonl. **Suggested fix:** After skipped-routing round 1, `jq -r '.body' accumulated-oos.jsonl` (or per-line parse) and assert canonical `^### OOS_` headers and absence of `^### FINDING_` in the non-security entry.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/test-review-and-fix.sh:1522-1557` — Skipped-routing coverage validates normalized headers and awk count on `oos-accepted-review.md` / `accumulated-oos.md`, but never inspects `accumulated-oos.jsonl`, even though `review-and-fix.sh` writes jsonl via `--rawfile body "$skipped_file"` and the plan requires jsonl and markdown to share the same normalized aggregate. A regression that normalizes markdown but leaves bare `### FINDING_` in jsonl would pass this harness while breaking downstream consumers that read jsonl. **Suggested fix:** After skipped-routing round 1, `jq -r '.body' accumulated-oos.jsonl` (or per-line parse) and assert canonical `^### OOS_` headers and absence of `^### FINDING_` in the non-security entry.
- **Suggested revision**: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] The plan’s end-to-end “`/issue` actually files legacy-header OOS” assertion is still not covered; harnesses stop at gate/disposition and normalized sinks (`skills/issue/scripts/test-parse-input.sh` remains `### OOS_N:`-only by design).
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - The plan’s end-to-end “`/issue` actually files legacy-header OOS” assertion is still not covered; harnesses stop at gate/disposition and normalized sinks (`skills/issue/scripts/test-parse-input.sh` remains `### OOS_N:`-only by design).
- **Suggested revision**: Address the concern above.

### FINDING_52: [OUT_OF_SCOPE] `test-review-core.sh` continues to stub tally/emit (called out in the plan), so production review-core integration of the tally→emit preserve chain is not exercised there; this branch instead adds `test-tally-code-votes.sh`, `test-emit-tally.sh`, and chained cases for that chain.
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - `test-review-core.sh` continues to stub tally/emit (called out in the plan), so production review-core integration of the tally→emit preserve chain is not exercised there; this branch instead adds `test-tally-code-votes.sh`, `test-emit-tally.sh`, and chained cases for that chain.
- **Suggested revision**: Address the concern above.

### FINDING_53: [OUT_OF_SCOPE] No dedicated `test-oos-non-security-block-count.awk` harness exists; bare `### FINDING_N:` → count 0 is asserted only in `python/test_oos.py`, not as a standalone bash unit test (bash coverage is indirect via gate tests on tagged legacy headers).
- **Reviewer**: dyn-regression-harness-output.txt
- **Concern**: - No dedicated `test-oos-non-security-block-count.awk` harness exists; bare `### FINDING_N:` → count 0 is asserted only in `python/test_oos.py`, not as a standalone bash unit test (bash coverage is indirect via gate tests on tagged legacy headers).
- **Suggested revision**: Address the concern above.

