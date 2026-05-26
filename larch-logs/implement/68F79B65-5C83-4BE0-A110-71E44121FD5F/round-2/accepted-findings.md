### FINDING_1: code-quality: skills/design/scripts/tally-plan-review.sh:176-199
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --voter fills v1/v2/v3 by argv order so skipping a failed middle slot compacts later judges into v2. When VOTER_2_STATUS=failed the loop emits only Claude and Cursor --voter args; Cursor ratings land in v2_* instead of v3_* breaking canonical analytics. Map by canonical slot index pass empty placeholders or document/test compaction explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/parse-judge-vote-and-rating.sh:4
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No test runs parser under larch_quiet_init / FD 3 emit_kv path. Awk/emit_kv regression ships while test-findings-classification only validates stdout with LARCH_QUIET_DISABLE=1. Add quiet-mode capture case mirroring test-tally-plan-review emit_kv pattern.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-render-voter-prompt.sh:39-55
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] finding-oos render case lacks axis-token and sentinel checks required by plan. Code-review voter prompts (same renderer) could lose axis examples on finding-oos grammar without failing CI. Duplicate finding-only assertions in case_finding_oos; grep Verify silently / Do NOT modify without CORRECTNESS=.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: skills/design/scripts/test-plan-review-loop.sh:3109-3142
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test for VOTER_2_STATUS=failed forwarding or per-slot KV argv shape. Loop could regress to VOTER_PATHS_FILE compaction without CI failure until a live design run. Stub failed slot 2 and assert tally --voter list or TSV column placement per chosen contract.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/design/scripts/test-findings-classification.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing default classification path and reverse-order MainAgent mutex sub-case. Default mkdir -p round-1 path and argv-order diagnostics are unverified edge cases. Add two minimal tally invocations to the harness.
- **Suggested revision**: Address the concern above.


### FINDING_17: security: scripts/design-log-publish.sh:295-332
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Plan-review publish validates symlinks once, then reads files in a separate loop without re-checking link type. A race could replace an allowed TSV with a symlink to a sensitive file between the find -type l sweep and design_publish_stage_file read. Re-assert ! -L on each path immediately before staging, or use open semantics that do not follow symlinks.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/design/scripts/tally-plan-review.sh:176-199, skills/design/scripts/plan-review-loop.sh:620-629
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --voter dispatch-order compaction mis-maps survivors when a middle canonical slot is skipped. Codex slot 2 fails; loop emits --voter Claude:path1 and --voter Cursor:path3 only; tally fills v2 with Cursor and leaves v3 empty, mis-labeling forensic columns vs canonical v2=Codex/v3=Cursor semantics. Pass explicit canonical slot index (1/2/3) from plan-review-loop into tally assign_voter; stop using next_pos for production argv; add harness for VOTER_2_STATUS=failed.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/design/scripts/plan-review-loop.sh:87-103
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] The 21-column findings-classification header is copy-pasted in loop and tally; write_empty_review_artifacts ignores its local helper. Schema renames require editing multiple literals; zero-findings path can diverge from tally header. Invoke tally for header-only output or share one emit_findings_classification_header implementation.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/scripts/test-tally-plan-review.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan required 13 new forensic/argv cases in test-tally-plan-review.sh; branch only updates the sibling .md and leaves the .sh unchanged vs main. Default round-1 TSV path and mkdir -p behavior are undocumented in any running harness; a regression removing the default --findings-classification-out write would not fail test-findings-classification or test-tally-plan-review. Add the planned cases to test-tally-plan-review.sh or formally map each planned case to an existing test-findings-classification assertion and update acceptance criteria.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/design/scripts/test-findings-classification.sh:139-154
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan harness case 4 requires tally TSV cells (empty vN_quality, vN_uncertain=true) for a partial rating line; only direct parser output is asserted. kv_value or quiet subprocess capture could break TSV emission while parser unit checks still pass. assert_cell on FINDING_2 (or dedicated fixture) after a full tally invocation.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/design/scripts/test-findings-classification.sh:6
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Plan testing strategy requires parser checks under quiet mode and LARCH_QUIET_DISABLE=1; harness only disables quiet. Quiet-mode emit_kv routing bugs might not surface until production /design tally. Add a case that invokes the parser the same way tally does without LARCH_QUIET_DISABLE.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/test-render-voter-prompt.sh:47-63
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan required four axis tokens and output-only sentinel checks for both id-grammars; finding-oos case omits them. Renderer regressions on plan-review prompts could drop axis enums while finding-only tests still pass. Mirror case_finding_only axis and sentinel greps in case_finding_oos.
- **Suggested revision**: Address the concern above.


### FINDING_3: code-quality: skills/design/scripts/test-findings-classification.sh:167-177
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No harness covers middle-slot failure with --voter; legacy --voter-files still hole-preserves columns. Production regressions on Codex-failed rounds would not be caught while legacy path behavior differs. Add loop+tally fixture asserting v2 empty and v3 populated when slot 2 is skipped.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/tally-plan-review.sh:176-199
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Middle-slot failed judges are compacted into v2 when later --voter args are passed because assign_voter uses next_pos not canonical slot index. Codex slot 2 fails; loop passes Claude then Cursor; TSV shows v2_tool=Cursor and empty v3, mis-attributing Cursor forensic ratings to the Codex column. Pass canonical slot number on each --voter from plan-review-loop or use assign_voter keyed by slot 1..3 instead of next_pos.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: skills/design/scripts/tally-plan-review.sh:176-199
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Middle failed slot is skipped in loop argv; tally fills v1 then v2 by dispatch order, not v1 empty v2 v3. When Codex slot fails and Claude+Cursor succeed, analytics see Cursor in v2_tool instead of v3_tool, breaking per-round canonical columns promised in acceptance. Align design: map --voter to fixed slots 1-3 (pass explicit slot index) or emit placeholder args; update test-findings-classification case 10 and docs.
- **Suggested revision**: Address the concern above.


