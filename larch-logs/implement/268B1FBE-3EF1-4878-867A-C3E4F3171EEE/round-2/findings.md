### FINDING_1: **Important** (`risk-integration`, `scripts/dispatch-plan-voters.sh:133-174` vs `scripts/test-dispatch-plan-voters.sh:34-39` and `scripts/test-prompt-template-invariants.sh:123-128`) — Parse-rate retry is implemented for both branches (`launch-claude-review.sh` when `voter_tool==claude`, and `dispatch-with-waterfall.sh` for Codex/Cursor). **Both** `test-dispatch-plan-voters.sh` and the plan-voter section of `test-prompt-template-invariants.sh` run with `--codex-available false --cursor-available false`, so only the **Claude fallback retry** path is exercised. Bugs in the **Codex/Cursor retry manifest** path (wrong `retry_output` naming, slot wiring, or waterfall flags) would not fail CI.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration`, `scripts/dispatch-plan-voters.sh:133-174` vs `scripts/test-dispatch-plan-voters.sh:34-39` and `scripts/test-prompt-template-invariants.sh:123-128`) — Parse-rate retry is implemented for both branches (`launch-claude-review.sh` when `voter_tool==claude`, and `dispatch-with-waterfall.sh` for Codex/Cursor). **Both** `test-dispatch-plan-voters.sh` and the plan-voter section of `test-prompt-template-invariants.sh` run with `--codex-available false --cursor-available false`, so only the **Claude fallback retry** path is exercised. Bugs in the **Codex/Cursor retry manifest** path (wrong `retry_output` naming, slot wiring, or waterfall flags) would not fail CI.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** (`risk-integration`, `skills/design/scripts/test-classify-issue.sh:88-135`, source: **plan**) — Improvement 13’s test matrix explicitly called for a **“True negative (deterministic misclassifies doc-only as SIMPLE, cursor catches)”** case. The added “Ratifier pattern regression cases” cover HARD confirmation, runtime-markdown escalation (deterministic `SIMPLE` + Cursor `HARD`), a borderline malformed-Cursor fallback, and clear doc-only under `CLASSIFY_ISSUE_SKIP_CURSOR=true`, but **none** of them set up deterministic `SIMPLE` on a **doc-only**-shaped change and then prove Cursor ratifies down to `TRIVIAL_DOC_ONLY`. If that scenario is still reachable with current heuristics, it is untested; if it is no longer reachable, the plan text and harness docstring should be reconciled so the matrix matches reality.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `skills/design/scripts/test-classify-issue.sh:88-135`, source: **plan**) — Improvement 13’s test matrix explicitly called for a **“True negative (deterministic misclassifies doc-only as SIMPLE, cursor catches)”** case. The added “Ratifier pattern regression cases” cover HARD confirmation, runtime-markdown escalation (deterministic `SIMPLE` + Cursor `HARD`), a borderline malformed-Cursor fallback, and clear doc-only under `CLASSIFY_ISSUE_SKIP_CURSOR=true`, but **none** of them set up deterministic `SIMPLE` on a **doc-only**-shaped change and then prove Cursor ratifies down to `TRIVIAL_DOC_ONLY`. If that scenario is still reachable with current heuristics, it is untested; if it is no longer reachable, the plan text and harness docstring should be reconciled so the matrix matches reality.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `correctness` `scripts/dispatch-plan-voters.sh:165` — The retry path dispatches through `dispatch-with-waterfall.sh` but discards that helper’s `ALL_OUTPUT_FILES`, so a successful phase-2/phase-3 retry is ignored. Concrete failing scenario: Codex emits narrative first, its retry launch fails, Cursor fallback writes valid votes to `*-parse-retry-phase2.txt`; `retry_voter` checks only `*-parse-retry.txt`, keeps the narrative first pass, and the tally sees `JUDGE_ERROR` votes instead of the valid retry votes. Suggested fix: capture and parse the retry waterfall output just like the first dispatch, then validate and move the actual returned output path.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `scripts/dispatch-plan-voters.sh:165` — The retry path dispatches through `dispatch-with-waterfall.sh` but discards that helper’s `ALL_OUTPUT_FILES`, so a successful phase-2/phase-3 retry is ignored. Concrete failing scenario: Codex emits narrative first, its retry launch fails, Cursor fallback writes valid votes to `*-parse-retry-phase2.txt`; `retry_voter` checks only `*-parse-retry.txt`, keeps the narrative first pass, and the tally sees `JUDGE_ERROR` votes instead of the valid retry votes. Suggested fix: capture and parse the retry waterfall output just like the first dispatch, then validate and move the actual returned output path.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file references written as markdown links, but the new reviewer prompt contract asks for raw backticked `path:line` tokens. Concrete failing scenario: an OOS bullet like `- **risk-integration** \`scripts/foo.sh:12\` — ...` is rewritten to `[OUT_OF_SCOPE] risk-integration`, dropping the path from the OOS title that later becomes the public issue title. Suggested fix: also extract the first raw backticked file token, preferably `path[:line[-line]]`, before falling back to category-only, and add a regression matching the new prompt shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/scripts/collect-findings.sh:398` — The new OOS normalizer only preserves file references written as markdown links, but the new reviewer prompt contract asks for raw backticked `path:line` tokens. Concrete failing scenario: an OOS bullet like `- **risk-integration** \`scripts/foo.sh:12\` — ...` is rewritten to `[OUT_OF_SCOPE] risk-integration`, dropping the path from the OOS title that later becomes the public issue title. Suggested fix: also extract the first raw backticked file token, preferably `path[:line[-line]]`, before falling back to category-only, and add a regression matching the new prompt shape.
- **Suggested revision**: Address the concern above.

### FINDING_5: **Latent** (`risk-integration`, `scripts/scout-dynamic-archetypes.sh:380-391` vs `scripts/test-scout-dynamic-archetypes.sh`) — Improvement 14’s **jq-level `prompt_body` closing-sentence repair** (`repaired_body`) has **no behavioral fixture** in `test-scout-dynamic-archetypes.sh`; `test-prompt-template-invariants.sh` only greps static source markers (`repaired_body`, constraint prose). A future jq refactor could drop or alter the repair while the scout harness still passes.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Latent** (`risk-integration`, `scripts/scout-dynamic-archetypes.sh:380-391` vs `scripts/test-scout-dynamic-archetypes.sh`) — Improvement 14’s **jq-level `prompt_body` closing-sentence repair** (`repaired_body`) has **no behavioral fixture** in `test-scout-dynamic-archetypes.sh`; `test-prompt-template-invariants.sh` only greps static source markers (`repaired_body`, constraint prose). A future jq refactor could drop or alter the repair while the scout harness still passes.
- **Suggested revision**: Address the concern above.

### FINDING_6: **focus-area**: architecture  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **focus-area**: architecture
- **Suggested revision**: Address the concern above.

### FINDING_7: **focus-area**: correctness  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **focus-area**: correctness
- **Suggested revision**: Address the concern above.

### FINDING_8: **focus-area**: risk-integration  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **focus-area**: risk-integration
- **Suggested revision**: Address the concern above.

### FINDING_9: **issue**: Contract doc says lint-fix passes an empty argument so `emit_submodule_prohibition` uses the no-submodules branch; the script passes `$forbidden_paths_file` (built from `.gitmodules` and `submodule_paths`), so behavior and documentation disagree.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: Contract doc says lint-fix passes an empty argument so `emit_submodule_prohibition` uses the no-submodules branch; the script passes `$forbidden_paths_file` (built from `.gitmodules` and `submodule_paths`), so behavior and documentation disagree.
- **Suggested revision**: Address the concern above.

### FINDING_10: **issue**: Improvement 9c asked to drop the duplicate “Do NOT touch `.git/` / `.gitmodules` …” sentence after “Edit only files …” while keeping the centralized PROHIBITION; `emit_submodule_prohibition` already ends with that rule, and the following line still repeats the same constraint in prose.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: Improvement 9c asked to drop the duplicate “Do NOT touch `.git/` / `.gitmodules` …” sentence after “Edit only files …” while keeping the centralized PROHIBITION; `emit_submodule_prohibition` already ends with that rule, and the following line still repeats the same constraint in prose.
- **Suggested revision**: Address the concern above.

### FINDING_11: **issue**: New logic covers claude fallback + retry and prompt text, but the harness no longer proves codex/cursor dispatch wiring (e.g. `--output-last-message`, JSON mode) on the primary path; regressions there would slip until integration.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: New logic covers claude fallback + retry and prompt text, but the harness no longer proves codex/cursor dispatch wiring (e.g. `--output-last-message`, JSON mode) on the primary path; regressions there would slip until integration.
- **Suggested revision**: Address the concern above.

### FINDING_12: **issue**: The plan asked for a `# Refs: #2417` comment; the diff uses a different sentence (“OOS parser in #2417 …”). Functionally fine, but not plan-literal.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: The plan asked for a `# Refs: #2417` comment; the diff uses a different sentence (“OOS parser in #2417 …”). Functionally fine, but not plan-literal.
- **Suggested revision**: Address the concern above.

### FINDING_13: **issue**: The written plan enumerates specific files for #2421; the branch also changes vote exoneration logic, finding category extraction, OOS title normalization, version/changelog/agent-lint, and ships a full implement run-log — none of which are in that enumerated set, so traceability from “this PR is only the 16 prompt tweaks” is broken unless the plan is updated.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: The written plan enumerates specific files for #2421; the branch also changes vote exoneration logic, finding category extraction, OOS title normalization, version/changelog/agent-lint, and ships a full implement run-log — none of which are in that enumerated set, so traceability from “this PR is only the 16 prompt tweaks” is broken unless the plan is updated.
- **Suggested revision**: Address the concern above.

### FINDING_14: **location**: Diff vs [implementation plan in user message](implementation_plan) (e.g. [scripts/lib-vote-tally.sh](scripts/lib-vote-tally.sh), [scripts/compose-review-findings.sh](scripts/compose-review-findings.sh), [skills/review/scripts/collect-findings.sh](skills/review/scripts/collect-findings.sh), large `larch-logs/` tree)  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **location**: Diff vs [implementation plan in user message](implementation_plan) (e.g. [scripts/lib-vote-tally.sh](scripts/lib-vote-tally.sh), [scripts/compose-review-findings.sh](scripts/compose-review-findings.sh), [skills/review/scripts/collect-findings.sh](skills/review/scripts/collect-findings.sh), large `larch-logs/` tree)
- **Suggested revision**: Address the concern above.

### FINDING_15: **location**: [scripts/lib-submodule-prohibition.md](scripts/lib-submodule-prohibition.md) vs [scripts/lint-fix-loop.sh](scripts/lint-fix-loop.sh) (compose_prompt caller)  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **location**: [scripts/lib-submodule-prohibition.md](scripts/lib-submodule-prohibition.md) vs [scripts/lint-fix-loop.sh](scripts/lint-fix-loop.sh) (compose_prompt caller)
- **Suggested revision**: Address the concern above.

### FINDING_16: **location**: [scripts/render-specialist-prompt.sh](scripts/render-specialist-prompt.sh) (`TAGGING_DIFF` / `#2417` comment)  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **location**: [scripts/render-specialist-prompt.sh](scripts/render-specialist-prompt.sh) (`TAGGING_DIFF` / `#2417` comment)
- **Suggested revision**: Address the concern above.

### FINDING_17: **location**: [scripts/test-dispatch-plan-voters.sh](scripts/test-dispatch-plan-voters.sh) vs prior behavior (diff removes codex stub and JSON/CLI assertions)  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **location**: [scripts/test-dispatch-plan-voters.sh](scripts/test-dispatch-plan-voters.sh) vs prior behavior (diff removes codex stub and JSON/CLI assertions)
- **Suggested revision**: Address the concern above.

### FINDING_18: **location**: [skills/review-and-fix/scripts/review-and-fix.sh](skills/review-and-fix/scripts/review-and-fix.sh) (`compose_coder_prompt`)  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **location**: [skills/review-and-fix/scripts/review-and-fix.sh](skills/review-and-fix/scripts/review-and-fix.sh) (`compose_coder_prompt`)
- **Suggested revision**: Address the concern above.

### FINDING_19: **severity**: Important  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **severity**: Important
- **Suggested revision**: Address the concern above.

### FINDING_20: **severity**: Latent  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **severity**: Latent
- **Suggested revision**: Address the concern above.

### FINDING_21: **severity**: Nit  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **severity**: Nit
- **Suggested revision**: Address the concern above.

### FINDING_22: **suggested fix**: Add the exact `# Refs: #2417` token next to the existing comment if strict plan traceability matters.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **suggested fix**: Add the exact `# Refs: #2417` token next to the existing comment if strict plan traceability matters. ### FINDING_5: Plan-voter harness no longer exercises codex/cursor happy path
- **Suggested revision**: Address the concern above.

### FINDING_23: **suggested fix**: Align the doc with the real argument (or change the caller to match the documented empty-string policy if that was the intended contract).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **suggested fix**: Align the doc with the real argument (or change the caller to match the documented empty-string policy if that was the intended contract). ### FINDING_2: Plan item 9c only partly satisfied (duplicate prohibition prose)
- **Suggested revision**: Address the concern above.

### FINDING_24: **suggested fix**: Either narrow the branch to the plan’s file surface or extend the plan/issue text to explicitly cover the #2417 / tally / collector follow-ups and any intentional log flush.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **suggested fix**: Either narrow the branch to the plan’s file surface or extend the plan/issue text to explicitly cover the #2417 / tally / collector follow-ups and any intentional log flush. ### FINDING_4: Improvement 8 wording does not match the plan literally
- **Suggested revision**: Address the concern above.

### FINDING_25: **suggested fix**: Remove or shorten the trailing “Edit only files …” line so it points at the PROHIBITION block without repeating the same rule text.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **suggested fix**: Remove or shorten the trailing “Edit only files …” line so it points at the PROHIBITION block without repeating the same rule text. ### FINDING_3: Branch work exceeds the stated implementation-plan file list
- **Suggested revision**: Address the concern above.

### FINDING_26: **suggested fix**: Restore a minimal dual-tool stub path (or add a second section) that still asserts launch flags while keeping the new retry assertions.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **suggested fix**: Restore a minimal dual-tool stub path (or add a second section) that still asserts launch flags while keeping the new retry assertions.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] architecture: branch vs main (aggregate diff)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Large tangled changes outside the enumerated 16 prompt edits (vote tally, compose JSONL, logs, version bumps). Review surface is wide; harder to reason about blast radius of the PR as a pure “prompt audit”. None required for this review; split or document intent when merging.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed implement run logs ship with the PR. Low: future log content could include sensitive host or env text if capture/redaction fails. Maintain redaction discipline; avoid logging secrets; rely on existing redact tooling in collectors.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] code-quality: larch-logs/implement/** (bulk)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large run-log artifacts in diff noise review surface Not introduced as a functional defect per repo logging policy None required for this review
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/render-plan-review-prompt.sh:unquoted-heredoc
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unquoted heredoc expands PLAN_FILE when building the plan-review prompt. If a caller ever passed a PLAN_FILE value containing shell command substitution, bash could execute it while composing the prompt. Keep path variables out of unquoted heredocs; use printf or a quoted heredoc.
- **Suggested revision**: Address the concern above.

### FINDING_31: `2818d6c4` Subagent prompt audit: 16 improvements to reduce NS-retry rate and pin output formats
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `2818d6c4` Subagent prompt audit: 16 improvements to reduce NS-retry rate and pin output formats
- **Suggested revision**: Address the concern above.

### FINDING_32: `7720a3ee` Bump version to 29.8.35 (#2424)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `7720a3ee` Bump version to 29.8.35 (#2424)
- **Suggested revision**: Address the concern above.

### FINDING_33: `b693038c` Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `b693038c` Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_34: `bc4b3497` Bump version to 29.8.34 (#2423)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - `bc4b3497` Bump version to 29.8.34 (#2423) The cached diff is dominated by committed `larch-logs/implement/**` artifacts; per your scope rules those are intentionally out of scope for noise review. Below focuses on executable/scripts, harnesses, Makefile/CI config, and the plan’s testing obligations.
- **Suggested revision**: Address the concern above.

### FINDING_35: architecture: scripts/lib-vote-tally.sh;scripts/lib-vote-tally.md;scripts/test-lib-vote-tally.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Vote exoneration logic changed outside the pasted #2421 plan Vote tallies drift from main without clear issue attribution Document/split PR scope or tie to its own tracked issue
- **Suggested revision**: Address the concern above.

### FINDING_36: architecture: scripts/scout-dynamic-archetypes.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Case-sensitive closing-sentence detection for jq repair Rare duplicate appended closing sentence Normalize case or strengthen equality check before appending
- **Suggested revision**: Address the concern above.

### FINDING_37: code-quality: CHANGELOG.md:29.8.35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Changelog cites #2417 while headline work is #2421 Consumers miss which issue drove which surface Clarify multiple closed issues or separate bullets
- **Suggested revision**: Address the concern above.

### FINDING_38: code-quality: scripts/lib-submodule-prohibition.md:9-10
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Contract doc says lint-fix passes empty string to emit_submodule_prohibition Operators mis-model lint-fix submodule prohibition vs actual forbidden_paths_file handoff Update Primary Callers to match lint-fix-loop compose_prompt's real argument
- **Suggested revision**: Address the concern above.

### FINDING_39: code-quality: scripts/render-specialist-prompt.sh:TAGGING_DESCRIPTION vs TAGGING_DIFF
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Description-mode tagging instructions not updated to pinned bullet grammar Inconsistent reviewer output shape across modes Align TAGGING_DESCRIPTION with TAGGING_DIFF bullet contract if parsers expect parity
- **Suggested revision**: Address the concern above.

### FINDING_40: code-quality: skills/review-and-fix/scripts/review-and-fix.sh:compose_coder_prompt
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Residual duplicate .git/.gitmodules prohibition line after centralizing PROHIBITION into the library (plan 9c). Redundant prompt text; minor confusion for models parsing constraints. Remove the redundant sentence and rely on emit_submodule_prohibition + a single edit-scope line if still needed.
- **Suggested revision**: Address the concern above.

### FINDING_41: code-quality: skills/review/scripts/dispatch-panel.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Heading says fixed checklist with one item only Minor prompt clarity noise Reword heading to match single-item checklist
- **Suggested revision**: Address the concern above.

### FINDING_42: correctness: scripts/lib-vote-tally.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Vote exoneration/classification rules broadened beyond prior classify_result Per-finding labels (e.g. 0Y/1N/1E, 0Y/0N/3E) change vs previous release; consumers may see different accept/reject/exonerate outcomes Document semantics explicitly in changelog/release notes or isolate into its own change narrative
- **Suggested revision**: Address the concern above.

### FINDING_43: correctness: scripts/scout-dynamic-archetypes.sh jq repaired_body
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Narrow regex for required closing sentence Duplicate or awkward prompt_body closing sentences on near matches Broaden presence detection or normalize before append
- **Suggested revision**: Address the concern above.

### FINDING_44: correctness: scripts/scout-dynamic-archetypes.sh:381-383
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Scout jq repair treats a suffix of the required closing sentence as sufficient; full sentence is not enforced. prompt_body="… follow the output-format rules from your outer wrapper exactly." passes validation without "Cite specific file paths…", violating improvement 14 and weakening scout→wrapper alignment. Test for the full closing sentence (or prefix "Cite specific file paths" plus the tail), not only the "follow the output-format rules…" suffix.
- **Suggested revision**: Address the concern above.

### FINDING_45: correctness: skills/design/scripts/test-classify-issue.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Borderline ratifier case reuses prior diff fixture Test name suggests threshold edge but fixture may not exercise it Use a dedicated borderline diff or assert diff metrics for case 3
- **Suggested revision**: Address the concern above.

### FINDING_46: risk-integration: scripts/lib-submodule-prohibition.md:9-10
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says lint-fix passes an empty string to emit_submodule_prohibition; code passes forbidden_paths_file. Maintainers may "correct" lint-fix to pass "" and unintentionally drop submodule path listing. Update Primary Callers to describe forbidden_paths_file / submodule path discovery accurately.
- **Suggested revision**: Address the concern above.

### FINDING_47: risk-integration: scripts/lint-fix-loop.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Submodule prohibition list includes .gitmodules while library prose says submodule paths Slight operator confusion; low functional risk Align lib wording or filter list to submodule paths only
- **Suggested revision**: Address the concern above.

### FINDING_48: risk-integration: scripts/test-dispatch-plan-voters.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Harness no longer runs codex+cursor-present plan-voter path Regressions in primary external plan-voter dispatch or prompts may pass CI unnoticed Re-add a stubbed healthy-externals case asserting prompts and parseable vote output
- **Suggested revision**: Address the concern above.

### FINDING_49: risk-integration: scripts/test-dispatch-plan-voters.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness dropped codex+cursor happy-path argv assertions External plan-voter launch regressions may escape CI Restore minimal dual-external-present coverage alongside fallback/retry tests
- **Suggested revision**: Address the concern above.

