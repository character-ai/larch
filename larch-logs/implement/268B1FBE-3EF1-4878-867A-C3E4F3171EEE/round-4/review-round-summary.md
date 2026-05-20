# Review Round 4

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 4
- Exonerated findings: 6
- Neutral findings: 3

## Accepted Findings

### FINDING_10: architecture: scripts/dispatch-plan-voters.sh:133-218
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] external_judges counts any non-empty voter file; substantive retry failure does not affect that count. Narrative-only outputs can still count as healthy external judges while vote parsing fails. After retry, gate external_judges or status on check_plan_voter_substantive or emit explicit degradation when still NOT_SUBSTANTIVE.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/lint-fix-loop.sh / scripts/lib-submodule-prohibition.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] emit_submodule_prohibition is fed forbidden_paths_file containing .gitmodules alongside submodule roots but copy still says “submodule paths”. Coder-facing prose slightly mislabels .gitmodules as a submodule path bullet. Clarify argument contract or filter inputs so listed bullets match the prose.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: scripts/render-specialist-prompt.sh (TAGGING_DIFF)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-specified cross-ref comment uses paraphrased #2417 text instead of literal `# Refs: #2417`. Audit/grep for the agreed marker misses the intended signal. Change the shell comment to `# Refs: #2417` as in the plan.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: skills/shared/voting-protocol.md:59-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] voting-protocol describes a mixed-panel exoneration path (claims 0Y/1N/1E exonerates) that classify_result does not implement. Operator follows voting-protocol for a 0Y/1N/1E tally expecting exonerated labeling; lib-vote-tally.sh returns rejected (also asserted by test-lib-vote-tally.sh), so docs and runtime disagree. Rewrite the tie-break section to match scripts/lib-vote-tally.sh and scripts/lib-vote-tally.md (remove incorrect 0Y/1N/1E exonerates claim).
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: scripts/lint-fix-loop.sh:5079-5085
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] emit_submodule_prohibition receives forbidden_paths_file whose first line is .gitmodules, so the PROHIBITION bullets mislabel that file as a submodule path. Model may over-interpret “do not read” for .gitmodules when the intent is narrower submodule worktree protection. Pass submodule_paths-only list into emit_submodule_prohibition; keep .gitmodules only on the mechanical forbidden-path list.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:58` — The new plan-voter prompt says voters may read the ballot but must not use “any other tools beyond that file read,” which prevents them from verifying ballot claims against the plan or referenced repo files. A false or stale plan-review finding can then be voted on using only reviewer prose, and accepted into the plan without independent validation. **Suggested fix:** keep the anti-narration directive, but allow silent read-only inspection of the plan and referenced files while forbidding status/planning tools and prose output.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:58` — The new plan-voter prompt says voters may read the ballot but must not use “any other tools beyond that file read,” which prevents them from verifying ballot claims against the plan or referenced repo files. A false or stale plan-review finding can then be voted on using only reviewer prose, and accepted into the plan without independent validation. **Suggested fix:** keep the anti-narration directive, but allow silent read-only inspection of the plan and referenced files while forbidding status/planning tools and prose output.
- **Suggested revision**: Address the concern above.


### FINDING_5: **Issue**: The new “After the acceptance threshold…” bullets say `EXONERATE > 0` can yield `exonerated` when `NO == 0` **or** when `EXONERATE >= NO` and `EXONERATE > YES`, and they explicitly claim `0Y/1N/1E` exonerates. The shipped `classify_result` logic only exonerates on `yes > 0 && exonerate > 0 && no == 0` after the acceptance/neutral branches; it does **not** implement the second disjunct, so `0Y/1N/1E` and all-EXON (`0Y/0N/≥1E` with `yes==0`) stay `rejected`, which matches `lib-vote-tally.md` but **not** `voting-protocol.md`.  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Issue**: The new “After the acceptance threshold…” bullets say `EXONERATE > 0` can yield `exonerated` when `NO == 0` **or** when `EXONERATE >= NO` and `EXONERATE > YES`, and they explicitly claim `0Y/1N/1E` exonerates. The shipped `classify_result` logic only exonerates on `yes > 0 && exonerate > 0 && no == 0` after the acceptance/neutral branches; it does **not** implement the second disjunct, so `0Y/1N/1E` and all-EXON (`0Y/0N/≥1E` with `yes==0`) stay `rejected`, which matches `lib-vote-tally.md` but **not** `voting-protocol.md`.
- **Suggested revision**: Address the concern above.


