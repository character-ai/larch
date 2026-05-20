### FINDING_1: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:148` — The parse-rate retry re-dispatches using `tool="$voter_tool"`, but when the original slot fell back to Claude, `dispatch-with-waterfall.sh` rejects initial manifest rows whose tool is `claude`. Scenario: Codex/Cursor is unavailable, Claude fallback returns narrative text, retry writes a `tool:"claude"` manifest, the dispatcher exits before launching, stderr is discarded, and the non-substantive vote remains. **Suggested fix:** Handle Claude fallback retries directly with `launch-claude-review.sh`, or extend `dispatch-with-waterfall.sh` to accept `claude` as an initial slot tool.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:148` — The parse-rate retry re-dispatches using `tool="$voter_tool"`, but when the original slot fell back to Claude, `dispatch-with-waterfall.sh` rejects initial manifest rows whose tool is `claude`. Scenario: Codex/Cursor is unavailable, Claude fallback returns narrative text, retry writes a `tool:"claude"` manifest, the dispatcher exits before launching, stderr is discarded, and the non-substantive vote remains. **Suggested fix:** Handle Claude fallback retries directly with `launch-claude-review.sh`, or extend `dispatch-with-waterfall.sh` to accept `claude` as an initial slot tool.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:40` — The new plan-voter retry prefix says every line must start with `FINDING_N:`, but `/design` plan-review ballots also contain `OOS_N:` items. In a retry after narrative output, a voter can follow this instruction and omit or mis-ID OOS votes, so `tally-plan-review.sh` records `JUDGE_ERROR` for `OOS_1` and accepted follow-up issues can be skipped. **Suggested fix:** Change the first-pass and retry directives to say “the same ballot ID, `FINDING_N` or `OOS_N`,” and add an OOS retry regression.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:40` — The new plan-voter retry prefix says every line must start with `FINDING_N:`, but `/design` plan-review ballots also contain `OOS_N:` items. In a retry after narrative output, a voter can follow this instruction and omit or mis-ID OOS votes, so `tally-plan-review.sh` records `JUDGE_ERROR` for `OOS_1` and accepted follow-up issues can be skipped. **Suggested fix:** Change the first-pass and retry directives to say “the same ballot ID, `FINDING_N` or `OOS_N`,” and add an OOS retry regression.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `risk-integration` `scripts/lint-fix-loop.sh:51` — `compose_prompt` always calls `emit_submodule_prohibition ""`, even though the script builds the real forbidden submodule list at `scripts/lint-fix-loop.sh:246-249`. In a repo with submodule `vendor/foo`, the lint-fixer prompt falsely says no submodules were discovered; if the agent edits `vendor/foo/...`, `post_dispatch_forbidden_revert` later reverts it and the loop fails with `forbidden-path-violation`. **Suggested fix:** Pass the generated `$forbidden_paths_file` into `compose_prompt` and then to `emit_submodule_prohibition`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` `scripts/lint-fix-loop.sh:51` — `compose_prompt` always calls `emit_submodule_prohibition ""`, even though the script builds the real forbidden submodule list at `scripts/lint-fix-loop.sh:246-249`. In a repo with submodule `vendor/foo`, the lint-fixer prompt falsely says no submodules were discovered; if the agent edits `vendor/foo/...`, `post_dispatch_forbidden_revert` later reverts it and the loop fails with `forbidden-path-violation`. **Suggested fix:** Pass the generated `$forbidden_paths_file` into `compose_prompt` and then to `emit_submodule_prohibition`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: larch-logs/** noise in diff
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] large implement run logs in branch diff human review cost only no code change required per policy
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: git history
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Feature branch stacks unrelated version bumps Noise for reviewers scanning commit list Prefer separate branch/PR for bumps unless policy requires stacking
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-prompt-template-invariants.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Fragile grep for removed printf pattern Refactor noise may fail harness without real regression Optional: assert absence via a more stable marker
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:compose_coder_prompt
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Duplicate .git/.gitmodules prohibition after shared emitter Redundant prompt text only; no new execution surface Optionally dedupe to single PROHIBITION block for clarity
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/lib-submodule-prohibition.sh (file mode)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Sourced library committed executable Unnecessary execute bit on non-entrypoint helper Use non-executable file mode for sourced-only library
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/test-prompt-template-invariants.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] harness only greps sources not rendered prompts weaker assurance than plan item 16 stated add minimal runtime render smoke
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/dispatch-plan-voters.sh:135
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dead guard comparing voter_tool to the literal failed Never true with current waterfall tool names Remove or gate on actual status variable
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/dispatch-plan-voters.sh:40
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Retry prefix says lines must start with FINDING_N: literally Minor model confusion vs real ballot ids Reword to reference ballot ids generically
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/lib-submodule-prohibition.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New sourced lib chmod +x Slight mismatch with sourced-only contract Use 100644 file mode
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-prompt-template-invariants.sh:1-130
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness only substring-greps sources; does not render composed prompts per plan #16 False confidence if markers exist but runtime prompt path omits them or diverges via interpolation Add fixture-driven runs that invoke each composer and assert on emitted prompt text
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/design/scripts/test-classify-issue.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ratifier case 2 comment mismatches fixture doc-only wording vs generic feature text rewrite comment to match actual inputs
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/design/scripts/test-classify-issue.sh:5558-5590
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] “Doc-only misclassified” regression story does not match non-doc fixture Misleading contract when test fails or when validating ratifier behavior Replace fixture with true doc-only→SIMPLE deterministic case; align comments and classify-issue.md
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/review/scripts/dispatch-panel.sh:167
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] acceptable-example bullet uses ASCII -- vs specialist em dash inconsistent examples may increase format drift align separator with render-specialist-prompt TAGGING_DIFF
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/review/scripts/dispatch-panel.sh:5840-5844 vs scripts/render-specialist-prompt.sh:5006-5008
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent delimiter between minimum-shape example and specialist bullet pin Subtle format drift for reviewers Unify `--` vs `—` (or document both) across examples
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: skills/review/scripts/dispatch-panel.sh:synthesize_dynamic_slots
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Acceptable-example bullet uses -- instead of specialist em dash Mild format inconsistency vs render-specialist-prompt pinning Match the pinned bullet separator in the example
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/dispatch-plan-voters.sh:132-136
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] retry_voter compares tool name to literal failed guard is dead / misleading future edit may think failed voters are skipped when they are not remove or compare VOTER_*_STATUS passed explicitly
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/dispatch-plan-voters.sh:4654-4692
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New parse-rate retry helpers with no harness update in diff Retry path regressions slip past CI Add tests in scripts/test-dispatch-plan-voters.sh covering NOT_SUBSTANTIVE→retry→OK
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/lib-vote-tally.sh:115-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] classify_result exoneration rules expanded beyond prior yes-gated behavior classify_result 0 0 3 3 returns exonerated where older logic returned rejected; downstream tally semantics change Document in CHANGELOG/issue or split PR if unintended; add release note for operators
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/review/scripts/dispatch-panel.sh:163-167 vs scripts/render-specialist-prompt.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Example bullet uses '--' while TAGGING_DIFF requires em-dash pattern Models may copy dispatch example and miss exact specialist bullet shape Align example punctuation with TAGGING_DIFF or clarify precedence
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/dispatch-plan-voters.sh:152-157
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry dispatch errors swallowed to /dev/null Failed retry looks like skipped retry; harder ops debugging Emit WARN on retry failure or empty retry output
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/dispatch-plan-voters.sh:73-82
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] substantive vote grep may false-positive on echoed YES/NO lines rare narrative file containing a matching line skips parse-retry tighten matcher or reuse ballot parser
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/dispatch-plan-voters.sh:check_plan_voter_substantive
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Substantive-vote detector accepts any ALLCAPS_KEY: YES/NO/EXONERATE line Narrative output can include a spurious TOKEN: YES line; retry is skipped while ballot lines remain missing; tally degrades to judge errors Anchor grep to FINDING_/OOS_ ballot ids (or shared vote-line parser)
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/lib-vote-tally.sh:132-136
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] classify_result exoneration broadened without YES requirement Multi-judge outcomes like 0Y/0N/3E or 0Y/1N/1E now exonerate; changes finding disposition independent of prompt edits Split or explicitly document and review as voting-policy change; verify tally callers
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/lib-vote-tally.sh:132-136;scripts/test-lib-vote-tally.sh:175-273
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Vote exoneration semantics broadened beyond prompt-audit plan scope Downstream tallies may differ from pre-branch behavior for some vote mixes Explicit PR/changelog intent or split to dedicated semantics PR
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/lib-vote-tally.sh:4821-4846
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Bundled tally/exoneration semantic change outside the 16-item prompt-audit plan PR labeled as prompt-only may ship vote-behavior changes without reviewers expecting them Split/relabel PR or expand plan/changelog to explicitly require tally change
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: scripts/lib-vote-tally.sh:classify_result
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Broader exoneration branches vs prior gate More vote mixes classify as exonerated; downstream semantics may treat concerns as softened differently Confirm product intent; align tally consumers with documented two-arm exoneration rule
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: scripts/test-dispatch-plan-voters.sh:1-57
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No coverage for new parse-rate retry and substantive vote-line detection New retry logic can regress silently Extend stub harness to simulate NOT_SUBSTANTIVE then successful retry
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/test-lib-submodule-prohibition.sh:31-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] grep patterns start with hyphen without operand terminator BSD grep on macOS treats '- vendor/foo' as invalid flags; make lint fails locally while Linux CI may pass Use grep -Fq -- '- vendor/foo' (and for external/bar) or assert without a leading hyphen token
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: scripts/test-prompt-template-invariants.sh:1-130
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Harness only substring-scans sources, not rendered prompts per plan #16 Refactors can break prompt assembly while strings remain in file Add fixture-driven smoke that exercises real compose/render paths
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: skills/design/scripts/test-classify-issue.sh:95-120
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Ratifier case2 narrative does not match fixture; no deterministic baseline assertion Test may pass without enforcing the documented misclassification scenario Assert SKIP_CURSOR SIMPLE (or use true doc-only mis-tagged fixture) before cursor path
- **Suggested revision**: Address the concern above.

