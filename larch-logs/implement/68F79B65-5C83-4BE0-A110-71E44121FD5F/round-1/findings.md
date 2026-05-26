### FINDING_1: code-quality: skills/design/scripts/tally-plan-review.sh:129-183
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --voter uses position_for_voter heuristics instead of argv dispatch order. Generic paths with non-canonical --voter order can place Codex in v2 and Claude in v1 regardless of argv sequence; analytics assuming dispatch order mis-attribute ratings. When SEEN_VOTER=true assign by monotonic dispatch index; keep position_for_voter for --voter-files fallback only.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/design/scripts/tally-plan-review.sh:274-327
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] voting_result uses vote_for_id while vN_vote uses PARSED_VOTE from a second parser. If parsers disagree on a malformed line TSV shows voting_result accepted/rejected from one vote set and vN_vote cells from another. Use vote_for_id for vN_vote cells; restrict rating parser to axes; add parity harness loop.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/tally-plan-review.sh:280-413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicated per-finding vote-count loop in TSV writer and markdown tally. Future tally threshold or JERR rule change updated in one path only leaves TSV and voting-tally.md inconsistent. Extract shared tally_block_votes helper used by both paths.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/plan-review-loop.sh:97-99
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] write_empty_review_artifacts duplicates 21-column header literal. Adding a column updates tally header but empty-round short-circuit can emit stale header-only TSV. Invoke tally on empty ballot or share emit_findings_classification_header.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan acceptance item to document test-findings-classification is missing. Contributors rely on Makefile grep to discover the new CI harness. Add test-findings-classification to docs/linting.md harness list.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: skills/design/scripts/tally-plan-review.sh:274-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] parse_rating_for spawns subprocess and kv_value awk per cell. 30-finding 3-judge round runs 90+ parser invocations plus hundreds of awk splits. Batch-parse each voter file once per tally invocation.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] No systematic vote_for_id vs PARSED_VOTE parity coverage. Subtle awk vs lib-vote-tally regex drift ships until downstream analytics show inconsistent rows. Add cross-parser assertion over all fixture lines.
- **Suggested revision**: Address the concern above.

### FINDING_8: security: scripts/test-design-log-publish.sh:1384-1411
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Partial plan-review publish negative tests only. Regression removing find -type l or under-root guard might not fail CI until production publish. Add missing symlink-root intermediate-dir and path-escape cases from plan.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/scripts/tally-plan-review.sh:129-168
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] --voter slot assignment uses basename/tool heuristics instead of argv ordinal canonical positions. When slot 1 is skipped and the sole voter is --voter Claude:custom-path (no codex-vote-output basename), ratings land in v1 instead of v2, misaligning analytics with dispatch slot identity. Assign --voter args to v1/v2/v3 by canonical emission order from the loop, or embed explicit slot numbers in argv; restrict heuristics to legacy --voter-files.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: docs/run-logs.md:19-21
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan-required prose for findings-classification.tsv schema and semantics is missing. Operators reading run-logs only see a path in the tree, not 21-column meaning, vN_tool semantics, or degraded-round empty cells. Add a subsection documenting schema, canonical positions, and cross-reference to tally-plan-review.md.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: docs/linting.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Makefile adds test-findings-classification but linting docs were not updated per acceptance. Contributors may not discover the new harness when debugging CI shard 9 failures. List test-findings-classification beside other design plan-review harness entries.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/parse-judge-vote-and-rating.sh:38-72
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Without -- delimiter, prose tokens matching axis=value patterns are parsed as real ratings. A judge writing "reviewer mentioned QUALITY=weak" without -- can populate vN_quality=weak in the committed TSV. Tighten parsing or require -- before rationale; update harness to match.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: skills/design/scripts/tally-plan-review.sh:314-319
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Parser uses raw ballot_id; vote_for_id uppercases the id prefix. Voter file with finding_1: lowercase id yields JUDGE_ERROR in voting_result path but empty vN_vote from parser on the same line. Normalize id in parse-judge-vote-and-rating.sh like vote_for_id; add parity harness rows.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: skills/design/scripts/plan-review-loop.sh:97-99
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Zero-findings header is duplicated inline, not sourced from tally helper. Future schema column changes in tally could leave empty-round design logs with an outdated header line. Call tally for header-only output or share emit_findings_classification_header.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/test-design-log-publish.sh:1384-1411
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Symlinked intermediate plan-review directory not covered by harness. Explicit find -type l sweep for symlinked round-N dirs is unverified; regression could reintroduce silent publish skips. Add symlinked-directory fixture asserting PUBLISH_OK=false.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/tally-plan-review.sh:274-277
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] parse_rating_for captures parser via stdout while emit_kv uses FD 3 under larch_quiet_init /design tally without LARCH_QUIET_DISABLE leaves vN rating columns empty in findings-classification.tsv while vote columns still populate via vote_for_id stdout Wrap parser invocation with LARCH_QUIET_DISABLE=1 or FD-3 capture; add harness without quiet disable
- **Suggested revision**: Address the concern above.

### FINDING_17: security: scripts/design-log-publish.sh:279-335
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plan-review publish allowlist rejects symlinks but not hardlinks at allowlisted paths. A session writer hardlinks plan-review/round-1/findings-classification.tsv to another readable local file; publish stages that content into public larch-logs after redaction. Reject hardlinked allowlist paths (stat link count / inode checks) or only stage TSV files created by tally in-session.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: skills/design/scripts/tally-plan-review.sh:252-326
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] finding_reviewers propagates untrusted ballot attribution into committed design logs. Aggregator text with paths or token-shaped strings lands in larch-logs; gitleaks does not scan larch-logs, so redact-secrets completeness is the only gate. Document untrusted column; consider redacting finding_reviewers or post-processing the TSV before publish.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: scripts/parse-judge-vote-and-rating.sh:36-37
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ballot_id is embedded in an awk regex without escaping. A non-conforming caller could pass metacharacters and mis-parse or stress awk matching. Use literal-prefix matching or escape id before regex construction.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:337-378
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] render-cache lacks the symlink sweep added for plan-review. Symlinked intermediate dirs under render-cache may still hide files from enumeration without failing publish. Mirror plan-review find -type l sweep for render-cache.
- **Suggested revision**: Address the concern above.

### FINDING_21: architecture: skills/design/scripts/tally-plan-review.sh:129-168
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --voter placement uses basename heuristics before argv order Direct tally with generic paths or reversed --voter order can put Cursor in v3 and Claude in v1 while analytics expect v1/v2 by dispatch order Use dispatch-index assignment when SEEN_VOTER; reserve basename inference for --voter-files only
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/design/scripts/tally-plan-review.sh:274-327
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] vN_vote from parser is never cross-checked against vote_for_id used for voting_result Divergent parse could yield voting_result=accepted while v2_vote is empty on the same row Add harness asserting PARSED_VOTE matches vote_for_id for every fixture line
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/design/scripts/plan-review-loop.sh:656-666
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tally failure does not refresh or clear findings-classification.tsv After tally-error a stale per-round TSV may publish under a new run id On tally-error remove round TSV or write header-only stub like write_empty_review_artifacts
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/parse-judge-vote-and-rating.sh:43-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Without -- delimiter axis-like rationale text is parsed as real axes Judge writes UNCERTAIN=false ... mentioned QUALITY=weak and vN_quality becomes weak Keep prompt discipline; optionally tighten parser or parse-rate warnings
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-design-log-publish.sh:356-383
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] plan-review publish security cases are only partly tested Symlinked plan-review root or intermediate directory could regress without CI failure Add harness cases for empty dir success symlink root fail round-0 fail and path escape guard
- **Suggested revision**: Address the concern above.

### FINDING_26: code-quality: skills/design/scripts/tally-plan-review.md:69
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness shard documentation is stale Contributors may run wrong make shard target Update doc to test-harnesses-9
- **Suggested revision**: Address the concern above.

### FINDING_27: code-quality: docs/linting.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Acceptance-listed lint doc update missing Operators may not discover test-findings-classification target Add Makefile target to docs/linting.md
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/lib-voter-parse-rate.sh:87+
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate does not require forensic axes Judges omit axes pass retry and produce all-uncertain TSV rows Extend check_voter_parse_rate when axis coverage is mandatory
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] code-quality: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Render voter prompt regression only partially covers new contract Prompt drift on Output ONLY vote lines or finding-only delimiter prose may slip Add remaining plan-listed grep assertions
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/scripts/tally-plan-review.sh:129-168
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] --voter uses position_for_voter basename/tool heuristics instead of argv dispatch order. --voter Cursor:slot1 --voter Claude:slot2 can land Claude in v1 and Cursor in v3, contradicting plan positional v1/v2/v3 semantics and case 11 intent. When SEEN_VOTER is true assign slot index by argv order only; reserve position_for_voter for legacy --voter-files.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: docs/linting.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan-required lint doc entry for test-findings-classification is missing. make lint docs omit the new harness; contributors may not run or register the target. Add a Makefile harness table row for make test-findings-classification (shard 9).
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: skills/design/scripts/test-tally-plan-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan mandates 13 new tally harness cases; script unchanged. Acceptance-listed tally regressions (mutex stderr exact text out flag MainAgent 21-field sanitization) are not exercised on test-tally-plan-review.sh. Implement the 13 cases in test-tally-plan-review.sh or revise acceptance to a single harness with explicit mapping.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: scripts/test-render-voter-prompt.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Only partial plan assertions added for 4-axis voter prompt. Missing greps for Output ONLY vote lines sentinel isolation lowercase enums and finding-only delimiter prose allow renderer regressions. Add the five assertion groups from the plan to case_finding_only and case_finding_oos.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/test-design-log-publish.sh:1384-1411
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Publish allowlist harness incomplete vs plan failure-mode list. Empty plan-review success symlinked root intermediate symlink dir round-0 and path escape are unstaged regressions. Add harness cases (a)(d)(e)(g)(h) from the plan publish checklist.
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: skills/design/scripts/test-plan-review-loop.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Loop harness lacks middle-slot failure and full zero-exit TSV coverage. VOTER_2_STATUS=failed compaction and panel-failed header-only TSV paths are unverified; tally --voter argv not inspected. Stub failed slot 2 assert v2 empty v3 filled assert TSV on panel-failed optionally log tally argv.
- **Suggested revision**: Address the concern above.

### FINDING_36: architecture: skills/design/scripts/plan-review-loop.sh:87-99
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] write_empty_review_artifacts inlines TSV header instead of tally invocation. Header string could drift from tally emit_findings_classification_header without a failing test. Call tally with empty ballot and --findings-classification-out or share one header helper.
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: scripts/parse-judge-vote-and-rating.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] No quiet-mode PARSED_* capture test. LARCH_QUIET_DISABLE-only harness misses FD3 emit_kv breakage under larch_quiet_init. Add one quiet-mode capture case like test-tally-plan-review emit_kv pattern.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] correctness: skills/design/scripts/tally-plan-review.sh:2064-2066
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Argv validation exits use code 2 not plan exit 1. Callers checking exact exit 1 would mis-handle errors. Align exit codes with plan or document exit 2 in tally-plan-review.md.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] architecture: scripts/test-render-voter-prompt.md:1442
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness doc shard reference may be stale relative to Makefile. Readers may look at wrong test-harnesses-N shard list. Keep test-render doc aligned with Makefile shard assignment.
- **Suggested revision**: Address the concern above.

### FINDING_40: **architecture** `skills/design/scripts/tally-plan-review.sh:129-168` — The branch adds `position_for_voter()` / `assign_voter()`, but `--voter` placement is **not** pure dispatch order as the plan and `tally-plan-review.md` imply. `position_for_voter()` checks basename globs first (`*claude-vote-output*` → v1, `*codex-vote-output*` → v2, `*cursor-vote-output*` → v3), then tool-based canonical slots, then the first free index. The `for spec in "${VOTER_SPECS[@]}"` loop never passes argv index into `assign_voter`, so argument order is advisory. Today that mostly works because `dispatch-plan-voters.sh` keeps fixed paths (`claude-vote-output.txt`, `codex-vote-output.txt`, `cursor-vote-output.txt`) and `plan-review-loop.sh:623-625` emits slots 1→3, but any caller with non-canonical basenames or reordered `--voter` args can mis-place voters (e.g. second `--voter Cursor:…` with a `*codex-vote-output*` basename lands in v2, not v3). **Suggested fix:** For `SEEN_VOTER=true`, assign strictly by argv sequence (`next_pos=1` … `3` per spec, skip only on validation failure) and use `<SLOT>` only for `vN_tool`; keep basename heuristics only on the deprecated `--voter-files` path. Document the split in `tally-plan-review.md`.
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/tally-plan-review.sh:129-168` — The branch adds `position_for_voter()` / `assign_voter()`, but `--voter` placement is **not** pure dispatch order as the plan and `tally-plan-review.md` imply. `position_for_voter()` checks basename globs first (`*claude-vote-output*` → v1, `*codex-vote-output*` → v2, `*cursor-vote-output*` → v3), then tool-based canonical slots, then the first free index. The `for spec in "${VOTER_SPECS[@]}"` loop never passes argv index into `assign_voter`, so argument order is advisory. Today that mostly works because `dispatch-plan-voters.sh` keeps fixed paths (`claude-vote-output.txt`, `codex-vote-output.txt`, `cursor-vote-output.txt`) and `plan-review-loop.sh:623-625` emits slots 1→3, but any caller with non-canonical basenames or reordered `--voter` args can mis-place voters (e.g. second `--voter Cursor:…` with a `*codex-vote-output*` basename lands in v2, not v3). **Suggested fix:** For `SEEN_VOTER=true`, assign strictly by argv sequence (`next_pos=1` … `3` per spec, skip only on validation failure) and use `<SLOT>` only for `vN_tool`; keep basename heuristics only on the deprecated `--voter-files` path. Document the split in `tally-plan-review.md`.
- **Suggested revision**: Address the concern above.

### FINDING_41: **architecture** `skills/design/scripts/tally-plan-review.sh:154-167` — When two `--voter` entries resolve to the same position (e.g. two paths matching `*claude-vote-output*`), `assign_voter` **silently overwrites** `SLOT_FILE[pos]` / `SLOT_TOOL[pos]` with no error. Forensic TSV and vote tallies then reflect only the last file while both paths stay in `VOTER_FILES[@]` for readability checks—a latent data-loss path for misconfigured harnesses or future multi-Claude panels. **Suggested fix:** Detect `SLOT_FILE[pos]` already set before assignment; exit non-zero with a clear diagnostic (`error: duplicate voter position N`) or require an explicit overwrite flag.
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/tally-plan-review.sh:154-167` — When two `--voter` entries resolve to the same position (e.g. two paths matching `*claude-vote-output*`), `assign_voter` **silently overwrites** `SLOT_FILE[pos]` / `SLOT_TOOL[pos]` with no error. Forensic TSV and vote tallies then reflect only the last file while both paths stay in `VOTER_FILES[@]` for readability checks—a latent data-loss path for misconfigured harnesses or future multi-Claude panels. **Suggested fix:** Detect `SLOT_FILE[pos]` already set before assignment; exit non-zero with a clear diagnostic (`error: duplicate voter position N`) or require an explicit overwrite flag.
- **Suggested revision**: Address the concern above.

### FINDING_42: **architecture** `skills/design/scripts/test-findings-classification.sh:158-168,194-203` — Harness cases labeled “missing judge” and “waterfall fallback” do not prove dispatch-order semantics. Case 2 passes `--voter Claude:…phase2` then `--voter Cursor:…phase3` and expects `v2_tool` empty and `v3_tool` Cursor; that outcome requires basename routing (`*cursor-vote-output*` → 3), not “second argv → v2”. Case 18 passes `--voter Claude:…/codex-vote-output.txt` as the second arg; `v2_tool=Claude` holds because `*codex-vote-output*` forces v2 even if argv order were ignored. The tests therefore lock in filename heuristics, not the plan’s dispatch-order contract, and would not catch a regression to pure argv-order placement. **Suggested fix:** Add fixtures with neutral basenames (e.g. `slot1.txt`, `slot2.txt`) asserting v1/v2/v3 follow argv order only; keep separate basename tests for legacy `--voter-files`.
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/test-findings-classification.sh:158-168,194-203` — Harness cases labeled “missing judge” and “waterfall fallback” do not prove dispatch-order semantics. Case 2 passes `--voter Claude:…phase2` then `--voter Cursor:…phase3` and expects `v2_tool` empty and `v3_tool` Cursor; that outcome requires basename routing (`*cursor-vote-output*` → 3), not “second argv → v2”. Case 18 passes `--voter Claude:…/codex-vote-output.txt` as the second arg; `v2_tool=Claude` holds because `*codex-vote-output*` forces v2 even if argv order were ignored. The tests therefore lock in filename heuristics, not the plan’s dispatch-order contract, and would not catch a regression to pure argv-order placement. **Suggested fix:** Add fixtures with neutral basenames (e.g. `slot1.txt`, `slot2.txt`) asserting v1/v2/v3 follow argv order only; keep separate basename tests for legacy `--voter-files`.
- **Suggested revision**: Address the concern above.

### FINDING_43: **architecture** `skills/design/scripts/tally-plan-review.md:53-56` — The sibling contract states `vN_tool` comes from `--voter` but does not document `position_for_voter()` basename/tool heuristics, while the embedded plan (and acceptance) claim v1/v2/v3 “fill by dispatch order” and designate this file as the schema authority for #2675. Downstream code-review forensics may assume argv-order columns when the implementation is path-pattern-driven. **Suggested fix:** Either implement argv-order placement and document it, or document the three-tier resolver explicitly (basename → tool canonical → first free slot) and which paths each tier applies to.
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/tally-plan-review.md:53-56` — The sibling contract states `vN_tool` comes from `--voter` but does not document `position_for_voter()` basename/tool heuristics, while the embedded plan (and acceptance) claim v1/v2/v3 “fill by dispatch order” and designate this file as the schema authority for #2675. Downstream code-review forensics may assume argv-order columns when the implementation is path-pattern-driven. **Suggested fix:** Either implement argv-order placement and document it, or document the three-tier resolver explicitly (basename → tool canonical → first free slot) and which paths each tier applies to.
- **Suggested revision**: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **correctness** `skills/design/scripts/test-tally-plan-review.sh` — The implementation plan lists 13 new `--voter` / TSV cases for this harness; the branch diff does not extend `test-tally-plan-review.sh` (still only `--voter-files`). Regression for the new argv surface relies on `test-findings-classification.sh`, which (per above) does not fully exercise dispatch order.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **architecture** `skills/design/scripts/plan-review-loop.sh:87-99` — Zero-findings exits inline-print the 21-column header instead of calling `tally-plan-review.sh` with an empty ballot (plan’s preferred single source of truth). Low risk while the header string is duplicated in `emit_findings_classification_header`, but it is a second definition to drift.
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-voter-slot-position-output.txt
- **Concern**: - **correctness** `docs/run-logs.md` — Layout tree lists `findings-classification.tsv` but the branch does not add the planned paragraph on 21-column schema, dispatch-order vs `vN_tool`, or empty-cell semantics (acceptance item still open).
- **Suggested revision**: Address the concern above.

### FINDING_47: **correctness** `scripts/parse-judge-vote-and-rating.sh:47-52`, `skills/design/scripts/tally-plan-review.sh:294-319` — Vote extraction in the awk program uses the first whitespace-delimited token (`sub(/[[:space:]].*$/, "", token)`), while `vote_for_id` in `scripts/lib-vote-tally.sh:20-25` accepts `YES|NO|EXONERATE` when immediately followed by `-` or whitespace. A line like `FINDING_1: YES-CORRECTNESS=true SEVERITY=major` yields `PARSED_VOTE=` (empty) and skips the glued `CORRECTNESS=` token, but `vote_for_id` returns `YES`. Tally uses `vote_for_id` for `voting_result` (lines 294–307) and `PARSED_VOTE` for `vN_vote` (lines 314–315), so the TSV can show an empty vote while the row’s `voting_result` reflects a YES—breaking the plan’s parity requirement and corrupting forensic analytics. **Suggested fix:** Parse the vote with the same anchored regex as `vote_for_id` (`^(YES|NO|EXONERATE)([[:space:]-]|$)` on the post-prefix segment, case-insensitive, emit upper-case), or set `vN_vote` from `vote_for_id` and keep the parser for axes only.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **correctness** `scripts/parse-judge-vote-and-rating.sh:47-52`, `skills/design/scripts/tally-plan-review.sh:294-319` — Vote extraction in the awk program uses the first whitespace-delimited token (`sub(/[[:space:]].*$/, "", token)`), while `vote_for_id` in `scripts/lib-vote-tally.sh:20-25` accepts `YES|NO|EXONERATE` when immediately followed by `-` or whitespace. A line like `FINDING_1: YES-CORRECTNESS=true SEVERITY=major` yields `PARSED_VOTE=` (empty) and skips the glued `CORRECTNESS=` token, but `vote_for_id` returns `YES`. Tally uses `vote_for_id` for `voting_result` (lines 294–307) and `PARSED_VOTE` for `vN_vote` (lines 314–315), so the TSV can show an empty vote while the row’s `voting_result` reflects a YES—breaking the plan’s parity requirement and corrupting forensic analytics. **Suggested fix:** Parse the vote with the same anchored regex as `vote_for_id` (`^(YES|NO|EXONERATE)([[:space:]-]|$)` on the post-prefix segment, case-insensitive, emit upper-case), or set `vN_vote` from `vote_for_id` and keep the parser for axes only.
- **Suggested revision**: Address the concern above.

### FINDING_48: **correctness** `scripts/parse-judge-vote-and-rating.sh:36-38`, `scripts/lib-vote-tally.sh:18-20` — The awk prefix match is case-sensitive on `$0` (`$0 ~ "^" id ":[[:space:]]*"`), but `vote_for_id` matches on `toupper(line)` with `toupper(id)`. A voter line `finding_1: yes CORRECTNESS=true ...` produces empty `PARSED_*` fields while `vote_for_id` still returns `YES`, again splitting `vN_vote` from the vote counts that drive `voting_result`. **Suggested fix:** Match lines case-insensitively (e.g. `toupper($0) ~ "^" toupper(id) ":[[:space:]]*"`) before parsing, mirroring `vote_for_id`.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **correctness** `scripts/parse-judge-vote-and-rating.sh:36-38`, `scripts/lib-vote-tally.sh:18-20` — The awk prefix match is case-sensitive on `$0` (`$0 ~ "^" id ":[[:space:]]*"`), but `vote_for_id` matches on `toupper(line)` with `toupper(id)`. A voter line `finding_1: yes CORRECTNESS=true ...` produces empty `PARSED_*` fields while `vote_for_id` still returns `YES`, again splitting `vN_vote` from the vote counts that drive `voting_result`. **Suggested fix:** Match lines case-insensitively (e.g. `toupper($0) ~ "^" toupper(id) ":[[:space:]]*"`) before parsing, mirroring `vote_for_id`.
- **Suggested revision**: Address the concern above.

### FINDING_49: **correctness** `scripts/parse-judge-vote-and-rating.sh:43-46` — Rationale scoping uses `index(scoped, " -- ")` (ASCII space–dash–dash–space only). With a tab before `--` (`...\t-- reviewer mentioned QUALITY=weak`), the delimiter is not found; a live check then sets `PARSED_QUALITY=weak` from rationale text instead of the intended pre-delimiter value `good`. Prompts specify ` -- `, but minor formatting drift is plausible in LLM output. **Suggested fix:** Treat `[[:space:]]--[[:space:]]` (any whitespace around `--`) as the delimiter, or normalize tabs to spaces before `index`, and add a harness case for tab-before-`--`.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **correctness** `scripts/parse-judge-vote-and-rating.sh:43-46` — Rationale scoping uses `index(scoped, " -- ")` (ASCII space–dash–dash–space only). With a tab before `--` (`...\t-- reviewer mentioned QUALITY=weak`), the delimiter is not found; a live check then sets `PARSED_QUALITY=weak` from rationale text instead of the intended pre-delimiter value `good`. Prompts specify ` -- `, but minor formatting drift is plausible in LLM output. **Suggested fix:** Treat `[[:space:]]--[[:space:]]` (any whitespace around `--`) as the delimiter, or normalize tabs to spaces before `index`, and add a harness case for tab-before-`--`.
- **Suggested revision**: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] Scout checklist items **parts[1] axis loop**, **`reset_fields` / last-line-wins**, and **`FINDING_1` vs `FINDING_10` prefix collision** behave as intended; no defect found (verified including `FINDING_10` non-match).
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - Scout checklist items **parts[1] axis loop**, **`reset_fields` / last-line-wins**, and **`FINDING_1` vs `FINDING_10` prefix collision** behave as intended; no defect found (verified including `FINDING_10` non-match).
- **Suggested revision**: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] **Double space before `--`** (e.g. `UNCERTAIN=false  -- reason`) still truncates at the delimiter and keeps `PARSED_QUALITY=good`; not a regression.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - **Double space before `--`** (e.g. `UNCERTAIN=false  -- reason`) still truncates at the delimiter and keeps `PARSED_QUALITY=good`; not a regression.
- **Suggested revision**: Address the concern above.

### FINDING_52: [OUT_OF_SCOPE] `scripts/parse-judge-vote-and-rating.md:34` states the ` -- ` delimiter is the same one `vote_for_id` uses, but `vote_for_id` does not implement `--` scoping—documentation-only inaccuracy.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - `scripts/parse-judge-vote-and-rating.md:34` states the ` -- ` delimiter is the same one `vote_for_id` uses, but `vote_for_id` does not implement `--` scoping—documentation-only inaccuracy.
- **Suggested revision**: Address the concern above.

### FINDING_53: [OUT_OF_SCOPE] Harness case `FINDING_7` (line without `--`, prose `QUALITY=weak`) intentionally parses rationale tokens; that is contract-by-design, not an awk bug.
- **Reviewer**: dyn-awk-parser-correctness-output.txt
- **Concern**: - Harness case `FINDING_7` (line without `--`, prose `QUALITY=weak`) intentionally parses rationale tokens; that is contract-by-design, not an awk bug.
- **Suggested revision**: Address the concern above.

### FINDING_54: **correctness** `scripts/parse-judge-vote-and-rating.sh:36-38` — The new parser matches ballot IDs case-sensitively (`prefix="^" id ":[[:space:]]*"` on raw `$0`), while `vote_for_id` in `scripts/lib-vote-tally.sh:18-20` folds both the line and id with `toupper()` before matching. In `write_findings_classification` (`skills/design/scripts/tally-plan-review.sh:2289-2310`), `voting_result` is derived from `vote_for_id` counts but `vN_vote` / rating columns come from the parser. A voter line like `finding_1: YES CORRECTNESS=true ...` can be counted as YES for the tally outcome while the forensic columns for that slot stay empty, breaking the plan’s “parser agrees with vote_for_id” invariant. **Suggested fix:** Make the parser’s ID prefix match case-insensitive the same way `vote_for_id` does (e.g., match against `toupper($0)` with `toupper(id)` in the prefix), and add a harness case with a lowercased id line asserting `PARSED_VOTE` and axis fields match `vote_for_id` on the same fixture.
- **Reviewer**: dyn-quiet-mode-kv-capture-output.txt
- **Concern**: - **correctness** `scripts/parse-judge-vote-and-rating.sh:36-38` — The new parser matches ballot IDs case-sensitively (`prefix="^" id ":[[:space:]]*"` on raw `$0`), while `vote_for_id` in `scripts/lib-vote-tally.sh:18-20` folds both the line and id with `toupper()` before matching. In `write_findings_classification` (`skills/design/scripts/tally-plan-review.sh:2289-2310`), `voting_result` is derived from `vote_for_id` counts but `vN_vote` / rating columns come from the parser. A voter line like `finding_1: YES CORRECTNESS=true ...` can be counted as YES for the tally outcome while the forensic columns for that slot stay empty, breaking the plan’s “parser agrees with vote_for_id” invariant. **Suggested fix:** Make the parser’s ID prefix match case-insensitive the same way `vote_for_id` does (e.g., match against `toupper($0)` with `toupper(id)` in the prefix), and add a harness case with a lowercased id line asserting `PARSED_VOTE` and axis fields match `vote_for_id` on the same fixture.
- **Suggested revision**: Address the concern above.

