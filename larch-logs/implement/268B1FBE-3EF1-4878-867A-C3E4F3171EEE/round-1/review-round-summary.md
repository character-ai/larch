# Review Round 1

- Mode: `diff`
- Accepted findings: 18
- Rejected findings: 0
- Exonerated findings: 10
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:148` — The parse-rate retry re-dispatches using `tool="$voter_tool"`, but when the original slot fell back to Claude, `dispatch-with-waterfall.sh` rejects initial manifest rows whose tool is `claude`. Scenario: Codex/Cursor is unavailable, Claude fallback returns narrative text, retry writes a `tool:"claude"` manifest, the dispatcher exits before launching, stderr is discarded, and the non-substantive vote remains. **Suggested fix:** Handle Claude fallback retries directly with `launch-claude-review.sh`, or extend `dispatch-with-waterfall.sh` to accept `claude` as an initial slot tool.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:148` — The parse-rate retry re-dispatches using `tool="$voter_tool"`, but when the original slot fell back to Claude, `dispatch-with-waterfall.sh` rejects initial manifest rows whose tool is `claude`. Scenario: Codex/Cursor is unavailable, Claude fallback returns narrative text, retry writes a `tool:"claude"` manifest, the dispatcher exits before launching, stderr is discarded, and the non-substantive vote remains. **Suggested fix:** Handle Claude fallback retries directly with `launch-claude-review.sh`, or extend `dispatch-with-waterfall.sh` to accept `claude` as an initial slot tool.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: scripts/dispatch-plan-voters.sh:135
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Dead guard comparing voter_tool to the literal failed Never true with current waterfall tool names Remove or gate on actual status variable
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


### FINDING_19: correctness: scripts/dispatch-plan-voters.sh:132-136
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] retry_voter compares tool name to literal failed guard is dead / misleading future edit may think failed voters are skipped when they are not remove or compare VOTER_*_STATUS passed explicitly
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:40` — The new plan-voter retry prefix says every line must start with `FINDING_N:`, but `/design` plan-review ballots also contain `OOS_N:` items. In a retry after narrative output, a voter can follow this instruction and omit or mis-ID OOS votes, so `tally-plan-review.sh` records `JUDGE_ERROR` for `OOS_1` and accepted follow-up issues can be skipped. **Suggested fix:** Change the first-pass and retry directives to say “the same ballot ID, `FINDING_N` or `OOS_N`,” and add an OOS retry regression.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:40` — The new plan-voter retry prefix says every line must start with `FINDING_N:`, but `/design` plan-review ballots also contain `OOS_N:` items. In a retry after narrative output, a voter can follow this instruction and omit or mis-ID OOS votes, so `tally-plan-review.sh` records `JUDGE_ERROR` for `OOS_1` and accepted follow-up issues can be skipped. **Suggested fix:** Change the first-pass and retry directives to say “the same ballot ID, `FINDING_N` or `OOS_N`,” and add an OOS retry regression.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/dispatch-plan-voters.sh:4654-4692
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New parse-rate retry helpers with no harness update in diff Retry path regressions slip past CI Add tests in scripts/test-dispatch-plan-voters.sh covering NOT_SUBSTANTIVE→retry→OK
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/review/scripts/dispatch-panel.sh:163-167 vs scripts/render-specialist-prompt.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Example bullet uses '--' while TAGGING_DIFF requires em-dash pattern Models may copy dispatch example and miss exact specialist bullet shape Align example punctuation with TAGGING_DIFF or clarify precedence
- **Suggested revision**: Address the concern above.


### FINDING_23: risk-integration: scripts/dispatch-plan-voters.sh:152-157
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Retry dispatch errors swallowed to /dev/null Failed retry looks like skipped retry; harder ops debugging Emit WARN on retry failure or empty retry output
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/dispatch-plan-voters.sh:check_plan_voter_substantive
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Substantive-vote detector accepts any ALLCAPS_KEY: YES/NO/EXONERATE line Narrative output can include a spurious TOKEN: YES line; retry is skipped while ballot lines remain missing; tally degrades to judge errors Anchor grep to FINDING_/OOS_ ballot ids (or shared vote-line parser)
- **Suggested revision**: Address the concern above.


### FINDING_3: **Important** `risk-integration` `scripts/lint-fix-loop.sh:51` — `compose_prompt` always calls `emit_submodule_prohibition ""`, even though the script builds the real forbidden submodule list at `scripts/lint-fix-loop.sh:246-249`. In a repo with submodule `vendor/foo`, the lint-fixer prompt falsely says no submodules were discovered; if the agent edits `vendor/foo/...`, `post_dispatch_forbidden_revert` later reverts it and the loop fails with `forbidden-path-violation`. **Suggested fix:** Pass the generated `$forbidden_paths_file` into `compose_prompt` and then to `emit_submodule_prohibition`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` `scripts/lint-fix-loop.sh:51` — `compose_prompt` always calls `emit_submodule_prohibition ""`, even though the script builds the real forbidden submodule list at `scripts/lint-fix-loop.sh:246-249`. In a repo with submodule `vendor/foo`, the lint-fixer prompt falsely says no submodules were discovered; if the agent edits `vendor/foo/...`, `post_dispatch_forbidden_revert` later reverts it and the loop fails with `forbidden-path-violation`. **Suggested fix:** Pass the generated `$forbidden_paths_file` into `compose_prompt` and then to `emit_submodule_prohibition`.
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


### FINDING_8: architecture: scripts/lib-submodule-prohibition.sh (file mode)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Sourced library committed executable Unnecessary execute bit on non-entrypoint helper Use non-executable file mode for sourced-only library
- **Suggested revision**: Address the concern above.


### FINDING_9: architecture: scripts/test-prompt-template-invariants.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] harness only greps sources not rendered prompts weaker assurance than plan item 16 stated add minimal runtime render smoke
- **Suggested revision**: Address the concern above.


