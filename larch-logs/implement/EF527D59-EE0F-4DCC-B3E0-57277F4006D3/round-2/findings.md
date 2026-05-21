### FINDING_1: **architecture** `docs/run-logs.md:144-148` — The updated contract describes only the new per-finding key set (`schema_version` / `reviewer_slots`) as if it were universal for `review-findings-full.jsonl`, but the repository still contains many historical committed rows under `larch-logs/**/review-findings-full.jsonl` that use the legacy `reviewer` string and omit `schema_version` (and at least one stub line uses yet another envelope shape). A whole-repo or cross-run miner that keys strictly off the documented v2 fields will silently drop reviewer attribution on older lines or mis-handle mixed streams. **Suggested fix:** Add an explicit backward-compatibility note in this section (and optionally a one-liner in `scripts/compose-review-findings.md` near the field table) stating that consumers must treat `reviewer_slots`+`schema_version` as v2 when present, and fall back to legacy `reviewer` (and absence of `schema_version`) for older committed batches, or branch on `has("reviewer_slots")` / `has("reviewer")`.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - **architecture** `docs/run-logs.md:144-148` — The updated contract describes only the new per-finding key set (`schema_version` / `reviewer_slots`) as if it were universal for `review-findings-full.jsonl`, but the repository still contains many historical committed rows under `larch-logs/**/review-findings-full.jsonl` that use the legacy `reviewer` string and omit `schema_version` (and at least one stub line uses yet another envelope shape). A whole-repo or cross-run miner that keys strictly off the documented v2 fields will silently drop reviewer attribution on older lines or mis-handle mixed streams. **Suggested fix:** Add an explicit backward-compatibility note in this section (and optionally a one-liner in `scripts/compose-review-findings.md` near the field table) stating that consumers must treat `reviewer_slots`+`schema_version` as v2 when present, and fall back to legacy `reviewer` (and absence of `schema_version`) for older committed batches, or branch on `has("reviewer_slots")` / `has("reviewer")`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `skills/review/scripts/aggregate-findings.sh:229-277` — OOS classification for both input and merged output uses `is_oos = "[OUT_OF_SCOPE]" in head` / `is_oos_out = "[OUT_OF_SCOPE]" in head` on the entire first line of the block (`### FINDING_n: …`), not the post-colon title. Any in-scope finding whose title mentions the marker as prose (for example a discussion of out-of-scope handling) would be treated as OOS for slot accounting, shrinking `in_scope` and inflating `oos`, so `only_oos` can omit reviewers who truly also have normal in-scope rows. Conversely, a merged heading that keeps reviewers who are OOS-only but decorates the title with `[OUT_OF_SCOPE]` only as a substring after other text could set `is_oos_out` true and skip the guard that is meant to catch dropping the tag from the merged first line, weakening the rejection the scout notes describe. **Suggested fix:** parse the `### FINDING_n:` line, take the substring after the first colon (the same title surface `collect-findings.sh` emits), and treat a row as OOS only when that title strip-prefix-matches `[OUT_OF_SCOPE]` the same way downstream consumers expect (for example `title.strip().startswith("[OUT_OF_SCOPE]")`), then run `only_oos_reviewer_slots` and the non-OOS output checks against that boolean.
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:229-277` — OOS classification for both input and merged output uses `is_oos = "[OUT_OF_SCOPE]" in head` / `is_oos_out = "[OUT_OF_SCOPE]" in head` on the entire first line of the block (`### FINDING_n: …`), not the post-colon title. Any in-scope finding whose title mentions the marker as prose (for example a discussion of out-of-scope handling) would be treated as OOS for slot accounting, shrinking `in_scope` and inflating `oos`, so `only_oos` can omit reviewers who truly also have normal in-scope rows. Conversely, a merged heading that keeps reviewers who are OOS-only but decorates the title with `[OUT_OF_SCOPE]` only as a substring after other text could set `is_oos_out` true and skip the guard that is meant to catch dropping the tag from the merged first line, weakening the rejection the scout notes describe. **Suggested fix:** parse the `### FINDING_n:` line, take the substring after the first colon (the same title surface `collect-findings.sh` emits), and treat a row as OOS only when that title strip-prefix-matches `[OUT_OF_SCOPE]` the same way downstream consumers expect (for example `title.strip().startswith("[OUT_OF_SCOPE]")`), then run `only_oos_reviewer_slots` and the non-OOS output checks against that boolean.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `skills/review/scripts/test-aggregate-findings.sh:220-246` — The `oos_drop_tag` case proves the “OOS-only reviewer merged into a non-tagged block” rejection path, but there is no counterpart proving the mixed case the scout notes call out: the same slot label appearing on both an `[OUT_OF_SCOPE]`-tagged input finding and an in-scope input finding must not land in `only_oos`, so a stubbed merged in-scope block that lists that slot should still validate and replace `findings.md`. **Suggested fix:** add a stub merge kind plus fixture with two input blocks sharing one reviewer label across in-scope and OOS titles, assert `AGGREGATED=true` / `REASON=ok`, and assert the merged file content matches the stub so future edits to `only_oos_reviewer_slots` cannot regress that set difference without failing CI.
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-aggregate-findings.sh:220-246` — The `oos_drop_tag` case proves the “OOS-only reviewer merged into a non-tagged block” rejection path, but there is no counterpart proving the mixed case the scout notes call out: the same slot label appearing on both an `[OUT_OF_SCOPE]`-tagged input finding and an in-scope input finding must not land in `only_oos`, so a stubbed merged in-scope block that lists that slot should still validate and replace `findings.md`. **Suggested fix:** add a stub merge kind plus fixture with two input blocks sharing one reviewer label across in-scope and OOS titles, assert `AGGREGATED=true` / `REASON=ok`, and assert the merged file content matches the stub so future edits to `only_oos_reviewer_slots` cannot regress that set difference without failing CI.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/collect-findings.sh:409-414` — Normal `findings.md` rows always include a parseable `- **Reviewer**:` line after label validation, so the validator’s reliance on `reviewer_line_slots` for OOS bookkeeping is aligned with the primary producer; remaining risk is mostly hand-edited or foreign-generated `findings.md`, which is outside the usual panel path.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Repo-wide search of `scripts/`, `skills/`, and `docs/` shows no remaining shell `jq` or other harness logic that projects `.reviewer` from `review-findings-full.jsonl`; `skills/review-and-fix/scripts/review-and-fix.sh:514-527` derives tallies from `phase`/`outcome` only; `scripts/larch-log-batches.md:51-55`, `scripts/compose-review-findings.md`, `scripts/test-compose-review-findings.sh`, `skills/implement/SKILL.md` (Step 5 batch section), and `.claude/skills/audit-runs/scans.tsv` were updated or do not depend on the removed key.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - Repo-wide search of `scripts/`, `skills/`, and `docs/` shows no remaining shell `jq` or other harness logic that projects `.reviewer` from `review-findings-full.jsonl`; `skills/review-and-fix/scripts/review-and-fix.sh:514-527` derives tallies from `phase`/`outcome` only; `scripts/larch-log-batches.md:51-55`, `scripts/compose-review-findings.md`, `scripts/test-compose-review-findings.sh`, `skills/implement/SKILL.md` (Step 5 batch section), and `.claude/skills/audit-runs/scans.tsv` were updated or do not depend on the removed key.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] `CHANGELOG.md` and archived `larch-logs/**/session-transcript.jsonl` examples still show historical jq snippets and prose tied to older shapes; that is historical narrative, not a runtime coupling in shipped automation.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - `CHANGELOG.md` and archived `larch-logs/**/session-transcript.jsonl` examples still show historical jq snippets and prose tied to older shapes; that is historical narrative, not a runtime coupling in shipped automation.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.md:38-40
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract doc omits Reviewer(s) forms supported in lib-vote-tally.sh after this branch. Readers of .md only see a narrower contract than .sh implements. Sync lib-vote-tally.md with the expanded attribution line shapes when doing a doc pass.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: skills/review/scripts/tally-code-votes.md:78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness coverage prose omits the new merged ballot comma-split scoreboard test. Doc-only gap; tests cover the behavior. Extend the coverage sentence when editing tally-code-votes.md next.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.sh:165-171
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] append_review_execution_issue already swallowed append failures and stderr before this feature landed, so aggregator is not the first silent-execution-issue surface. Any fix should centralize append handling rather than blaming only aggregate-findings.sh. Refactor shared append helper with dispatch-panel-style error capture when touching this area.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] security: scripts/compose-review-findings.sh:171-188
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] jq-based JSONL emission with redacted reviewer fields Existing compose path already avoids shell expansion of reviewer prose; schema split to reviewer_slots does not materially change injection class. No change required for this review scope beyond maintaining redact-then-jq discipline.
- **Suggested revision**: Address the concern above.

### FINDING_11: architecture: aggregate-findings.sh:102-112
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] strip_agent_frontmatter yields an empty instruction body unless two --- fences exist. A future bad edit to orchestrator-aggregator.md could strip all guidance, producing unpredictable LLM output while still running dispatch. Detect empty stripped bodies and fail closed or inline a hard-coded minimum contract when frontmatter stripping removes everything.
- **Suggested revision**: Address the concern above.

### FINDING_12: architecture: skills/review/SKILL.md:10
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Opening Skill prose still documents gather→dispatch→collect→vote→emit with no aggregate stage. Operators and orchestrators relying on SKILL.md for the round pipeline get a stage list that does not match review-core (aggregate between collect and voters). Update the pipeline string to include aggregate (and when it is skipped), consistent with review-core.md and aggregate-findings.md.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/lib-vote-tally.sh:32-35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] reviewer_for_block comment omits Reviewer(s) label variants that the awk now matches. Future edits may re-break matching if authors trust the stale comment. Extend the comment to list **Reviewer(s)**: and Reviewer(s): alongside existing forms.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: aggregate-findings.sh:205-216
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Validator + downstream scoreboard/JSONL assume strict markdown and comma-separated reviewer slots. A model output like `- **Reviewer(s)** : foo` or `foo; bar` fails validation or mis-splits slots, so production silently stays on duplicate-heavy ballots despite healthy external tools. Align regex tolerances with lib-vote-tally / extract_reviewer_from_body or add a normalization pass before validation.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: aggregate-findings.sh:94-99
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] LARCH_AGGREGATOR_DISABLED=1 reports INPUT_COUNT=0 and MERGED_COUNT=0 without inspecting findings.md. Round telemetry or grep-based monitors may conclude “zero findings” while voting still consumes a non-empty ballot, complicating post-mortems when aggregation is intentionally disabled mid-debug. Emit accurate counts (e.g., run count_finding_blocks before early exit) or rename keys to avoid implying scanned findings.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/compose-review-findings.sh:176 and skills/review/scripts/tally-code-votes.sh:334-342
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Merged reviewer attribution is split only on commas for JSONL and scoreboard rows. A slot label or LLM typo that contains a comma (or uses non-comma separators) becomes multiple bogus slots; scoreboard and reviewer_slots diverge from real output basenames while votes still attach to one FINDING id. Define atomic slot parsing (e.g. split only on comma when each token matches *-output.txt) or change the aggregator contract/tests accordingly.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: skills/review/scripts/aggregate-findings.sh:115-186
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] MERGED_COUNT is seeded to INPUT_COUNT and left unchanged on several failure exits before emit_result. Stdout can show MERGED_COUNT equal to pre-merge input block count while AGGREGATED=false, so automated consumers may treat MERGED_COUNT as post-merge output size and mis-report merge outcomes. On failed dispatch or empty output, set MERGED_COUNT to a value that reflects unchanged ballot (e.g. 0 or a fresh count from findings.md) or document clearly that MERGED_COUNT means input cardinality unless AGGREGATED=true.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: skills/review/scripts/collect-findings.sh:1485-1486
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Removing sort -u drops identical-row dedupe before findings are numbered. Two identical TSV rows from overlapping collectors produce duplicate FINDING blocks and inflated counts until aggregation; aggregation may leave duplicates if they are not semantically merged. Dedupe stable keys with first-seen order preserved or add a targeted regression if double-emission is impossible by construction.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: SECURITY.md:58-72
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New pre-vote LLM aggregation dispatches full findings.md through external tools but SECURITY.md only tweaks compose wording; no explicit trust/telemetry bullet for aggregate-findings + dispatch-with-waterfall. Compliance reviews and on-call triage lack a documented statement that aggregator prompts live under the session tmpdir, inherit the same argv/.meta visibility model as other launch-review lanes, and feed untrusted reviewer prose into another model pass before mechanical validation. Add a concise SECURITY.md subsection describing aggregator prompt construction, dispatch surface, tmpdir containment, validation-before-replace, and pointer to execution-issues warnings on fallback.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: aggregate-findings.sh:63-69
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] append_warning discards stderr and forces success even when append-execution-issue.sh cannot write execution-issues.md. When the log volume fills the tmp filesystem, every aggregator failure path could lose its markdown trail while stdout KVs still claim dispatch/validation reasons—operators only discover failures indirectly. Capture append exit codes and echo failures to larch_err/emit_breadcrumb similar to dispatch-panel’s append handling.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/compose-review-findings.sh:169-189
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] JSONL schema replaces reviewer string with schema_version plus reviewer_slots. External tooling that still expects .reviewer on review-findings-full.jsonl breaks after upgrade without code changes. Announce breaking schema in CHANGELOG and optionally dual-write for one release if external compatibility is required.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-lib-vote-tally.sh:89-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] reviewer_for_block unit harness not extended for new Reviewer(s) awk alternations awk typo could ship while only integration comma-merge case passes add **Reviewer(s)** and Reviewer(s): fixtures with expected strings
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: skills/review/scripts/aggregate-findings.sh:94-100
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] disabled branch emits INPUT_COUNT=0 MERGED_COUNT=0 telemetry consumers see zero findings despite unchanged ballot count blocks before disabled early exit
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: skills/review/scripts/collect-findings.sh:371
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] sort -u removal drops identical-row collapse aggregation off/failed path can duplicate identical TSV-derived findings vs old behavior add collect harness or document escape-hatch trade-off
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/review/scripts/tally-code-votes.sh:334-342
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] comma-only reviewer string split for scoreboard rows comma inside a slot label would fan out into wrong scoreboard credits document comma-free slot invariant or use safer delimiter plus test
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/review/scripts/test-review-core.sh:2268-2276
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] most review-core tests disable aggregation LARCH_AGGREGATOR_DISABLED=1 hides regressions in aggregate-enabled wiring except ordering probe add optional enabled-aggregate stubbed failure/success case
- **Suggested revision**: Address the concern above.

### FINDING_27: security: skills/review/scripts/aggregate-findings.sh:40-41,137-141,294-303
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Symlink-following reads of findings and aggregator output before external LLM dispatch A symlinked findings.md (or output path) can pivot reads to another local regular file; contents are embedded into aggregator-prompt.md and sent to external review tools, leaking unintended file bytes to the vendor. Reject symlinks; resolve paths and require they remain under the session review tmpdir; or use non-following open semantics before building the prompt.
- **Suggested revision**: Address the concern above.

