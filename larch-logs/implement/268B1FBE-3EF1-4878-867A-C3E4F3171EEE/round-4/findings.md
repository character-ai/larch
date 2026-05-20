### FINDING_1: **Concrete scenario**: A maintainer “fixes” tally code or tests to match the protocol doc, or an operator trusts the doc when triaging a borderline ballot, and acceptance/exoneration semantics for `/review` or `/design` voting drift without a deliberate product decision.  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Concrete scenario**: A maintainer “fixes” tally code or tests to match the protocol doc, or an operator trusts the doc when triaging a borderline ballot, and acceptance/exoneration semantics for `/review` or `/design` voting drift without a deliberate product decision.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Focus area**: risk-integration  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Focus area**: risk-integration
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:58` — The new plan-voter prompt says voters may read the ballot but must not use “any other tools beyond that file read,” which prevents them from verifying ballot claims against the plan or referenced repo files. A false or stale plan-review finding can then be voted on using only reviewer prose, and accepted into the plan without independent validation. **Suggested fix:** keep the anti-narration directive, but allow silent read-only inspection of the plan and referenced files while forbidding status/planning tools and prose output.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `risk-integration` `scripts/dispatch-plan-voters.sh:58` — The new plan-voter prompt says voters may read the ballot but must not use “any other tools beyond that file read,” which prevents them from verifying ballot claims against the plan or referenced repo files. A false or stale plan-review finding can then be voted on using only reviewer prose, and accepted into the plan without independent validation. **Suggested fix:** keep the anti-narration directive, but allow silent read-only inspection of the plan and referenced files while forbidding status/planning tools and prose output.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Important** `risk-integration` `scripts/render-specialist-prompt.sh:323` / `skills/review/scripts/collect-findings.sh:392` — The new reviewer grammar requires OOS bullets to use plain backtick file refs, but the collector only preserves file refs in markdown-link form like ``[`path`]``. A compliant OOS bullet such as `- **risk-integration** \`scripts/foo.sh:12\` — ...` is normalized to `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream issue serialization and conflict detection. **Suggested fix:** update the collector to extract the first plain backtick file token too, and add a regression using the exact rendered prompt grammar.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/render-specialist-prompt.sh:323` / `skills/review/scripts/collect-findings.sh:392` — The new reviewer grammar requires OOS bullets to use plain backtick file refs, but the collector only preserves file refs in markdown-link form like ``[`path`]``. A compliant OOS bullet such as `- **risk-integration** \`scripts/foo.sh:12\` — ...` is normalized to `[OUT_OF_SCOPE] risk-integration`, dropping the path needed by downstream issue serialization and conflict detection. **Suggested fix:** update the collector to extract the first plain backtick file token too, and add a regression using the exact rendered prompt grammar.
- **Suggested revision**: Address the concern above.

### FINDING_5: **Issue**: The new “After the acceptance threshold…” bullets say `EXONERATE > 0` can yield `exonerated` when `NO == 0` **or** when `EXONERATE >= NO` and `EXONERATE > YES`, and they explicitly claim `0Y/1N/1E` exonerates. The shipped `classify_result` logic only exonerates on `yes > 0 && exonerate > 0 && no == 0` after the acceptance/neutral branches; it does **not** implement the second disjunct, so `0Y/1N/1E` and all-EXON (`0Y/0N/≥1E` with `yes==0`) stay `rejected`, which matches `lib-vote-tally.md` but **not** `voting-protocol.md`.  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Issue**: The new “After the acceptance threshold…” bullets say `EXONERATE > 0` can yield `exonerated` when `NO == 0` **or** when `EXONERATE >= NO` and `EXONERATE > YES`, and they explicitly claim `0Y/1N/1E` exonerates. The shipped `classify_result` logic only exonerates on `yes > 0 && exonerate > 0 && no == 0` after the acceptance/neutral branches; it does **not** implement the second disjunct, so `0Y/1N/1E` and all-EXON (`0Y/0N/≥1E` with `yes==0`) stay `rejected`, which matches `lib-vote-tally.md` but **not** `voting-protocol.md`.
- **Suggested revision**: Address the concern above.

### FINDING_6: **Location**: [`skills/shared/voting-protocol.md:59-65`](skills/shared/voting-protocol.md) vs [`scripts/lib-vote-tally.sh:115-138`](scripts/lib-vote-tally.sh) and [`scripts/lib-vote-tally.md:30-32`](scripts/lib-vote-tally.md)  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Location**: [`skills/shared/voting-protocol.md:59-65`](skills/shared/voting-protocol.md) vs [`scripts/lib-vote-tally.sh:115-138`](scripts/lib-vote-tally.sh) and [`scripts/lib-vote-tally.md:30-32`](scripts/lib-vote-tally.md)
- **Suggested revision**: Address the concern above.

### FINDING_7: **Severity**: Important  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Severity**: Important
- **Suggested revision**: Address the concern above.

### FINDING_8: **Suggested fix**: Rewrite the new `voting-protocol.md` paragraph so it matches `scripts/lib-vote-tally.sh::classify_result` (and the `lib-vote-tally.md` summary), or change `classify_result` **and** `scripts/test-lib-vote-tally.sh` together if the protocol text reflects newly intended policy.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Suggested fix**: Rewrite the new `voting-protocol.md` paragraph so it matches `scripts/lib-vote-tally.sh::classify_result` (and the `lib-vote-tally.md` summary), or change `classify_result` **and** `scripts/test-lib-vote-tally.sh` together if the protocol text reflects newly intended policy.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: implementation_plan.md:Files to modify
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] The enumerated file list omits several files changed for #2417 OOS/TAGGING integration Reviewers using only the plan table may miss compose-review-findings, collect-findings, lib-vote-tally, and related tests/docs when tracing requirements Amend the plan or PR description to list the additional touched files as in-scope follow-on for #2417
- **Suggested revision**: Address the concern above.

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

### FINDING_13: code-quality: scripts/render-specialist-prompt.sh:5131-5133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan item 8 requested a literal # Refs: #2417 comment; implementation uses different prose only. Minor plan/traceability mismatch only. Add the exact # Refs: #2417 marker alongside the existing note.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/render-specialist-prompt.sh:TAGGING_DIFF block
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan asked for literal comment `# Refs: #2417` next to shape pinning Minor mismatch vs written spec; future grep-for-Refs audits may miss the anchor Add `# Refs: #2417` (or update the plan to accept the current prose comment)
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: skills/shared/voting-protocol.md:59-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] voting-protocol describes a mixed-panel exoneration path (claims 0Y/1N/1E exonerates) that classify_result does not implement. Operator follows voting-protocol for a 0Y/1N/1E tally expecting exonerated labeling; lib-vote-tally.sh returns rejected (also asserted by test-lib-vote-tally.sh), so docs and runtime disagree. Rewrite the tie-break section to match scripts/lib-vote-tally.sh and scripts/lib-vote-tally.md (remove incorrect 0Y/1N/1E exonerates claim).
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: skills/shared/voting-protocol.md:59-65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New tie-break prose contradicts classify_result() and tests. Readers expect 0Y/1N/1E to exonerate and broader EXONERATE rules; code rejects those counts and only exonerates multi-voter when YES>0, EXONERATE>0, NO==0. Malign or update voting-protocol.md to match scripts/lib-vote-tally.sh and scripts/lib-vote-tally.md (or implement and test the documented rule if that was the intent).
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/shared/voting-protocol.md:59-65
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] New tie-break prose claims 0Y/1N/1E exonerates and broader EXONERATE rules; lib-vote-tally classify_result and tests still reject 0Y/1N/1E and only exonerate multi-judge panels when YES>0 with EXONERATE>0 and NO==0. Operators following voting-protocol.md expect exonerated scoreboard/tally behavior that the implementation does not produce. Align voting-protocol.md with scripts/lib-vote-tally.sh and scripts/lib-vote-tally.md (or change code+tests if the document is authoritative).
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/lint-fix-loop.sh:5079-5085
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] emit_submodule_prohibition receives forbidden_paths_file whose first line is .gitmodules, so the PROHIBITION bullets mislabel that file as a submodule path. Model may over-interpret “do not read” for .gitmodules when the intent is narrower submodule worktree protection. Pass submodule_paths-only list into emit_submodule_prohibition; keep .gitmodules only on the mechanical forbidden-path list.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/lint-fix-loop.sh:compose_prompt → scripts/lib-submodule-prohibition.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] PROHIBITION list source mixes `.gitmodules` with submodule roots under a “submodule paths” lead-in Slight conceptual imprecision; unlikely to weaken enforcement because of the trailing catch-all Filter `.gitmodules` out of the bulleted list or adjust the lead-in sentence for mixed path kinds
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/scout-dynamic-archetypes.sh:380-384
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Closing-sentence repair can append the full required sentence when a trailing substring already matched part of it. prompt_body can contain duplicated contradictory closing instructions for dynamic reviewers. Tighten jq repair to strip partial suffixes or only append when the full sentence is truly absent.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-prompt-template-invariants.sh:146-185
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness uses find -print -quit GNU-only find flag can break make lint on BSD/macOS find where -quit is unsupported Use POSIX find-to-head-n1 or read-first-match loop
- **Suggested revision**: Address the concern above.

