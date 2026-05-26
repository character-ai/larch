### FINDING_1: code-quality: skills/implement/scripts/test-write-final-report.sh:2480-2510
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nine-outcome matrix omits per-fixture token-report.json with nonzero buckets; matrix mostly asserts generic - **Cost**: presence. Regression of merged/pr-created paths that should show 💰 TOTAL and per-agent dollars could slip through CI while only N/A paths are exercised. Seed token-report.json (or stub token-report.sh) for matrix fixtures and assert full cost-line markers on happy outcomes.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/implement/scripts/test-write-final-report.sh:288-294
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stage 2 self-compose fallback tests only spot-check bullets, not full renderer-ordered schema. Future compose_self_fallback edits can drop or reorder bullets (e.g. Warnings count, PR conditional) without CI failure. Add ordered-schema assertion helper and use it for Stage 2 fallback output.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-write-final-report.sh:330-335
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Step 18 sentinel suppression test does not verify empty structured body, only absence of summary title. Regressions that still print partial summary text outside the title line would not be caught. Assert no lines matching ^## /implement run or - **Cost**: in stdout when sentinel is present and --print-stdout omitted.
- **Suggested revision**: Address the concern above.


### FINDING_13: security: skills/design/scripts/render-final-summary.sh:321-332
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New append_render_warning omits --redact while implement write-final-report.sh always redacts degraded-render stderr. When render-run-summary.sh fails, raw stderr (possibly containing API keys or auth errors) is appended to execution-issues.md and may be published in design run logs. Pass --redact to append-tool-failure.sh in design append_render_warning; document both skills in SECURITY.md; pin with a test grep.
- **Suggested revision**: Address the concern above.


### FINDING_16: architecture: skills/design/scripts/render-final-summary.sh:384-397
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Post-phase render_or_fallback overwrites final-summary.md on failure without checking for a valid pre-publish file. Pre-publish writes a full cost breakdown; post-publish render fails; compose_self_fallback replaces it with Cost N/A and upserts/prints that body. On post failure reuse existing final-summary.md when it already has a non-N/A cost line; fall back only if missing or empty.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/design/scripts/test-render-final-summary.sh:291-311
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] The ten-outcome design matrix only asserts final-summary.md because post-publish stdout is redirected to /dev/null. A bug that breaks the PHASE=post chat-print loop but still writes final-summary.md would pass CI for nine design outcomes; users could again see no collapsed Bash summary in chat while logs look correct. Capture stdout for each matrix outcome, assert cost line and sentinel on stdout, and cmp stdout to final-summary.md (mirror the implement matrix and the existing approved cmp test).
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/implement/scripts/write-final-report.sh:226-293
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unconditional refresh_issue_counts prefers non-empty execution-issues.md over ndjson counts. Final summary Warnings/Exec issues can disagree with committed run-log ndjson when md and ndjson diverge. Limit refresh to fallback paths after append_render_warning, or document and implement explicit merge/precedence.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/design/scripts/render-final-summary.sh:367-381
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] render_or_fallback allow_fallback=false branch is never used. Dead code adds review noise and suggests unfinished API. Remove parameter or add a real strict caller.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/design/scripts/render-final-summary.sh:374-380
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Post-phase render_or_fallback overwrites a valid pre-published final-summary.md when invoke_render fails but the file is still non-empty. Pre-publish writes a full cost breakdown; post-publish render exits non-zero; compose_self_fallback replaces the good file with Cost N/A and chat/upsert show the degraded summary. Only compose_self_fallback when render failed and final-summary.md is missing or empty; if the file is already populated, keep it, append the warning, and print the existing file.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/implement/scripts/test-write-final-report.sh:2480-2510
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Nine-outcome matrix lacks per-outcome token-report.json with nonzero buckets; most cases only assert generic Cost bullet presence. Merged/pr-created matrix runs emit Cost: N/A instead of per-agent breakdown; plan acceptance #2/#4 happy-path coverage is only in the single impl-cost case. Seed token-report.json (nonzero BUCKETS_*) for each matrix fixture and assert TOTAL/Claude/Codex/Cursor/Tokens on success outcomes.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-render-cost-line-callsites.sh:34-49
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Callsite lint omits Step 18 orchestrator-text cost-line emit prose required by the plan. Step 18 bail-path collapse-resistant cost line can be deleted from SKILL.md without failing make lint. Add grep -Fq for Step 18 conditional cost-line emit anchor text in skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.


