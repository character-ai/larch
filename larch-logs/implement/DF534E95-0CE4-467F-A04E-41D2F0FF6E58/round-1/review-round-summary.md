# Review Round 1

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 2
- Exonerated findings: 2
- Neutral findings: 2

## Accepted Findings

### FINDING_1: **Important** `correctness` `scripts/dispatch-code-voters.sh:56` — The new “Do not invoke any tools” directive conflicts with the voter prompt’s file-based workflow: the prompt only gives voters a ballot path at `scripts/dispatch-code-voters.sh:54`, and asks them to verify diff/plan context at `scripts/dispatch-code-voters.sh:55`. For Codex/Cursor voter launches, the generic prompt path is passed as plain prompt text, so a voter that obeys “Do not invoke any tools” cannot read the ballot or inspect context files before voting. Concrete scenario: a ballot with multiple `FINDING_N` entries is dispatched to Cursor; Cursor follows the no-tools instruction, never reads the ballot path, and either emits no valid `FINDING_N: VOTE` lines or guesses, triggering parse retry/degraded judging or incorrect votes. Fix by making the voter prompt self-contained for no-tool execution, at minimum embedding the ballot text and any diff/plan context needed for verification, or narrow the directive so file/context reads remain allowed while narrative/status/planning tool use is forbidden.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/dispatch-code-voters.sh:56` — The new “Do not invoke any tools” directive conflicts with the voter prompt’s file-based workflow: the prompt only gives voters a ballot path at `scripts/dispatch-code-voters.sh:54`, and asks them to verify diff/plan context at `scripts/dispatch-code-voters.sh:55`. For Codex/Cursor voter launches, the generic prompt path is passed as plain prompt text, so a voter that obeys “Do not invoke any tools” cannot read the ballot or inspect context files before voting. Concrete scenario: a ballot with multiple `FINDING_N` entries is dispatched to Cursor; Cursor follows the no-tools instruction, never reads the ballot path, and either emits no valid `FINDING_N: VOTE` lines or guesses, triggering parse retry/degraded judging or incorrect votes. Fix by making the voter prompt self-contained for no-tool execution, at minimum embedding the ballot text and any diff/plan context needed for verification, or narrow the directive so file/context reads remain allowed while narrative/status/planning tool use is forbidden.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: CHANGELOG.md:14-18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] CHANGELOG 29.8.30 documents #2398 only; no entry for the harmonized voter first-pass prompt. Consumers of CHANGELOG may not discover the new voter instructions without reading git commits or issue threads. Add a concise Changed bullet for the voter prompt harmonization (or cross-reference #2396 phase 2) where release notes fit repo convention.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/dispatch-code-voters.sh:55-56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Verify guidance conflicts with no-tools directive Models may skip needed file-backed verification or stall on conflicting instructions if ballot or diff/plan are path references rather than inlined context yet tools are disallowed Clarify that verification uses only attached or inlined context without extra tool calls or align launcher to always inline bounded context
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: scripts/test-dispatch-code-voters.sh:179-181
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Regression tests only assert anti-narrative strings on claude-vote-prompt.txt. If make_voter_prompt_file later diverges per voter label, codex or cursor prompts could lose directives while tests still pass. Mirror the three grep checks (or cmp) against codex-vote-prompt.txt and cursor-vote-prompt.txt in the same happy-path block.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: CHANGELOG.md:14-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] 29.8.30 changelog omits voter prompt contract change Shipped 29.8.30 behavior for judge prompts changes without a changelog signal; upgrades miss operational and debugging context Add a Changed bullet describing voter anti-narrative directives with correct issue reference
- **Suggested revision**: Address the concern above.


