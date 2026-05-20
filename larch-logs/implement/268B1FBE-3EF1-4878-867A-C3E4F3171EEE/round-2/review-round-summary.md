# Review Round 2

- Mode: `diff`
- Accepted findings: 16
- Rejected findings: 25
- Exonerated findings: 3
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** (`risk-integration`, `scripts/dispatch-plan-voters.sh:133-174` vs `scripts/test-dispatch-plan-voters.sh:34-39` and `scripts/test-prompt-template-invariants.sh:123-128`) — Parse-rate retry is implemented for both branches (`launch-claude-review.sh` when `voter_tool==claude`, and `dispatch-with-waterfall.sh` for Codex/Cursor). **Both** `test-dispatch-plan-voters.sh` and the plan-voter section of `test-prompt-template-invariants.sh` run with `--codex-available false --cursor-available false`, so only the **Claude fallback retry** path is exercised. Bugs in the **Codex/Cursor retry manifest** path (wrong `retry_output` naming, slot wiring, or waterfall flags) would not fail CI.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **Important** (`risk-integration`, `scripts/dispatch-plan-voters.sh:133-174` vs `scripts/test-dispatch-plan-voters.sh:34-39` and `scripts/test-prompt-template-invariants.sh:123-128`) — Parse-rate retry is implemented for both branches (`launch-claude-review.sh` when `voter_tool==claude`, and `dispatch-with-waterfall.sh` for Codex/Cursor). **Both** `test-dispatch-plan-voters.sh` and the plan-voter section of `test-prompt-template-invariants.sh` run with `--codex-available false --cursor-available false`, so only the **Claude fallback retry** path is exercised. Bugs in the **Codex/Cursor retry manifest** path (wrong `retry_output` naming, slot wiring, or waterfall flags) would not fail CI.
- **Suggested revision**: Address the concern above.


### FINDING_10: **issue**: Improvement 9c asked to drop the duplicate “Do NOT touch `.git/` / `.gitmodules` …” sentence after “Edit only files …” while keeping the centralized PROHIBITION; `emit_submodule_prohibition` already ends with that rule, and the following line still repeats the same constraint in prose.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: Improvement 9c asked to drop the duplicate “Do NOT touch `.git/` / `.gitmodules` …” sentence after “Edit only files …” while keeping the centralized PROHIBITION; `emit_submodule_prohibition` already ends with that rule, and the following line still repeats the same constraint in prose.
- **Suggested revision**: Address the concern above.


### FINDING_11: **issue**: New logic covers claude fallback + retry and prompt text, but the harness no longer proves codex/cursor dispatch wiring (e.g. `--output-last-message`, JSON mode) on the primary path; regressions there would slip until integration.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: New logic covers claude fallback + retry and prompt text, but the harness no longer proves codex/cursor dispatch wiring (e.g. `--output-last-message`, JSON mode) on the primary path; regressions there would slip until integration.
- **Suggested revision**: Address the concern above.


### FINDING_13: **issue**: The written plan enumerates specific files for #2421; the branch also changes vote exoneration logic, finding category extraction, OOS title normalization, version/changelog/agent-lint, and ships a full implement run-log — none of which are in that enumerated set, so traceability from “this PR is only the 16 prompt tweaks” is broken unless the plan is updated.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: The written plan enumerates specific files for #2421; the branch also changes vote exoneration logic, finding category extraction, OOS title normalization, version/changelog/agent-lint, and ships a full implement run-log — none of which are in that enumerated set, so traceability from “this PR is only the 16 prompt tweaks” is broken unless the plan is updated.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** (`risk-integration`, `skills/design/scripts/test-classify-issue.sh:88-135`, source: **plan**) — Improvement 13’s test matrix explicitly called for a **“True negative (deterministic misclassifies doc-only as SIMPLE, cursor catches)”** case. The added “Ratifier pattern regression cases” cover HARD confirmation, runtime-markdown escalation (deterministic `SIMPLE` + Cursor `HARD`), a borderline malformed-Cursor fallback, and clear doc-only under `CLASSIFY_ISSUE_SKIP_CURSOR=true`, but **none** of them set up deterministic `SIMPLE` on a **doc-only**-shaped change and then prove Cursor ratifies down to `TRIVIAL_DOC_ONLY`. If that scenario is still reachable with current heuristics, it is untested; if it is no longer reachable, the plan text and harness docstring should be reconciled so the matrix matches reality.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **Important** (`risk-integration`, `skills/design/scripts/test-classify-issue.sh:88-135`, source: **plan**) — Improvement 13’s test matrix explicitly called for a **“True negative (deterministic misclassifies doc-only as SIMPLE, cursor catches)”** case. The added “Ratifier pattern regression cases” cover HARD confirmation, runtime-markdown escalation (deterministic `SIMPLE` + Cursor `HARD`), a borderline malformed-Cursor fallback, and clear doc-only under `CLASSIFY_ISSUE_SKIP_CURSOR=true`, but **none** of them set up deterministic `SIMPLE` on a **doc-only**-shaped change and then prove Cursor ratifies down to `TRIVIAL_DOC_ONLY`. If that scenario is still reachable with current heuristics, it is untested; if it is no longer reachable, the plan text and harness docstring should be reconciled so the matrix matches reality.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Important** `correctness` `scripts/dispatch-plan-voters.sh:165` — The retry path dispatches through `dispatch-with-waterfall.sh` but discards that helper’s `ALL_OUTPUT_FILES`, so a successful phase-2/phase-3 retry is ignored. Concrete failing scenario: Codex emits narrative first, its retry launch fails, Cursor fallback writes valid votes to `*-parse-retry-phase2.txt`; `retry_voter` checks only `*-parse-retry.txt`, keeps the narrative first pass, and the tally sees `JUDGE_ERROR` votes instead of the valid retry votes. Suggested fix: capture and parse the retry waterfall output just like the first dispatch, then validate and move the actual returned output path.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `scripts/dispatch-plan-voters.sh:165` — The retry path dispatches through `dispatch-with-waterfall.sh` but discards that helper’s `ALL_OUTPUT_FILES`, so a successful phase-2/phase-3 retry is ignored. Concrete failing scenario: Codex emits narrative first, its retry launch fails, Cursor fallback writes valid votes to `*-parse-retry-phase2.txt`; `retry_voter` checks only `*-parse-retry.txt`, keeps the narrative first pass, and the tally sees `JUDGE_ERROR` votes instead of the valid retry votes. Suggested fix: capture and parse the retry waterfall output just like the first dispatch, then validate and move the actual returned output path.
- **Suggested revision**: Address the concern above.


### FINDING_35: architecture: scripts/lib-vote-tally.sh;scripts/lib-vote-tally.md;scripts/test-lib-vote-tally.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Vote exoneration logic changed outside the pasted #2421 plan Vote tallies drift from main without clear issue attribution Document/split PR scope or tie to its own tracked issue
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


### FINDING_42: correctness: scripts/lib-vote-tally.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Vote exoneration/classification rules broadened beyond prior classify_result Per-finding labels (e.g. 0Y/1N/1E, 0Y/0N/3E) change vs previous release; consumers may see different accept/reject/exonerate outcomes Document semantics explicitly in changelog/release notes or isolate into its own change narrative
- **Suggested revision**: Address the concern above.


### FINDING_44: correctness: scripts/scout-dynamic-archetypes.sh:381-383
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Scout jq repair treats a suffix of the required closing sentence as sufficient; full sentence is not enforced. prompt_body="… follow the output-format rules from your outer wrapper exactly." passes validation without "Cite specific file paths…", violating improvement 14 and weakening scout→wrapper alignment. Test for the full closing sentence (or prefix "Cite specific file paths" plus the tail), not only the "follow the output-format rules…" suffix.
- **Suggested revision**: Address the concern above.


### FINDING_46: risk-integration: scripts/lib-submodule-prohibition.md:9-10
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc says lint-fix passes an empty string to emit_submodule_prohibition; code passes forbidden_paths_file. Maintainers may "correct" lint-fix to pass "" and unintentionally drop submodule path listing. Update Primary Callers to describe forbidden_paths_file / submodule path discovery accurately.
- **Suggested revision**: Address the concern above.


### FINDING_48: risk-integration: scripts/test-dispatch-plan-voters.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Harness no longer runs codex+cursor-present plan-voter path Regressions in primary external plan-voter dispatch or prompts may pass CI unnoticed Re-add a stubbed healthy-externals case asserting prompts and parseable vote output
- **Suggested revision**: Address the concern above.


### FINDING_5: **Latent** (`risk-integration`, `scripts/scout-dynamic-archetypes.sh:380-391` vs `scripts/test-scout-dynamic-archetypes.sh`) — Improvement 14’s **jq-level `prompt_body` closing-sentence repair** (`repaired_body`) has **no behavioral fixture** in `test-scout-dynamic-archetypes.sh`; `test-prompt-template-invariants.sh` only greps static source markers (`repaired_body`, constraint prose). A future jq refactor could drop or alter the repair while the scout harness still passes.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **Latent** (`risk-integration`, `scripts/scout-dynamic-archetypes.sh:380-391` vs `scripts/test-scout-dynamic-archetypes.sh`) — Improvement 14’s **jq-level `prompt_body` closing-sentence repair** (`repaired_body`) has **no behavioral fixture** in `test-scout-dynamic-archetypes.sh`; `test-prompt-template-invariants.sh` only greps static source markers (`repaired_body`, constraint prose). A future jq refactor could drop or alter the repair while the scout harness still passes.
- **Suggested revision**: Address the concern above.


### FINDING_9: **issue**: Contract doc says lint-fix passes an empty argument so `emit_submodule_prohibition` uses the no-submodules branch; the script passes `$forbidden_paths_file` (built from `.gitmodules` and `submodule_paths`), so behavior and documentation disagree.  
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **issue**: Contract doc says lint-fix passes an empty argument so `emit_submodule_prohibition` uses the no-submodules branch; the script passes `$forbidden_paths_file` (built from `.gitmodules` and `submodule_paths`), so behavior and documentation disagree.
- **Suggested revision**: Address the concern above.


