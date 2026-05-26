### FINDING_1: code-quality: skills/implement/scripts/test-write-final-report.sh:38-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness temp CLAUDE_PLUGIN_ROOT omits append-tool-failure.sh so append_render_warning no-ops in all fallback tests. Degraded-path tests pass with WARN_N=0 and never validate plan-required warning append plus refresh after renderer failure. Copy or stub append-tool-failure.sh and append-execution-issue.sh under the temp plugin root; assert - **Warnings**: increases after forced fallback.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: skills/implement/scripts/test-write-final-report.sh:320-334
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Fallback Stage 2 schema test pins Warnings: 0 and never verifies post-append warning refresh required by the plan. If append-tool-failure increments warnings in production, CI would not detect a regression where the self-composed body still shows 0 while execution-issues.md has entries. Add a fallback test that triggers append_render_warning, asserts refreshed WARN_N in the composed summary (e.g. Warnings: 1+), and mirror for design WARNINGS.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/scripts/test-render-final-summary.sh:137-141
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Renderer-fail self-compose for cancelled-clarify checks Outcome only, not Cost N/A. A broken compose_self_fallback could drop the cost bullet on cancellation degraded paths while CI stays green. Assert grep for - **Cost**: N/A on final-summary.md and stdout in the std_fb_cancel block.
- **Suggested revision**: Address the concern above.


### FINDING_15: security: skills/design/scripts/render-final-summary.sh:142-189
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] token-report failure logging still calls append-tool-failure.sh without --redact while copying raw stderr into execution-issues.md A failed token-report.sh run writes API/auth errors into execution-issues.md and committed design run logs without redaction Add --redact to token-report and timing-report append-tool-failure.sh calls (and align upsert-failure path)
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/design/scripts/render-final-summary.sh:382-387
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Post-phase render failure preserves any non-empty final-summary.md and skips compose_self_fallback even after append_render_warning refreshes warning counts. Phase-1 writes final-summary.md; publish appends warnings; Phase-2 render-run-summary.sh fails; chat/upsert still show Phase-1 Warnings/Exec issues counts while execution-issues.md records the new failure. Recompose on post failure using refreshed WARNINGS/EXEC_ISSUES; only preserve cost text via summary_has_usable_cost; add two-phase failure harness.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: skills/design/scripts/render-final-summary.sh:368-385
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Post-phase preserve can keep a stale per-agent Cost line after token-report.sh reruns. Phase-1 summary shows Codex dollars; Phase-2 token refresh changes totals; renderer fails; user/orchestrator emit old breakdown from final-summary.md. Do not preserve cross-phase files by -s alone; recompose or require same-invocation artifact before preserve.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/implement/SKILL.md:1807-1821
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 18 refreshes token data and rewrites summary files but suppresses chat print and verbatim cost re-emit when .step17-printed exists. Step 17 prints Cost N/A or early totals; Step 18 obtains full token-report-rendered.json; tracking comment updates but chat cost line stays Step-17 stale. Re-emit/re-print when summary-final.md Cost line changes after Step-18 render, or skip Step-18 token refresh when sentinel present.
- **Suggested revision**: Address the concern above.


### FINDING_21: code-quality: skills/design/scripts/render-final-summary.md:23-32
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Docs omit post-phase preserve-on-failure semantics now encoded in tests. Maintainer changes render_or_fallback assuming full recompose; regress stale-count behavior without doc/test cue. Document post-phase preserve rules beside two-phase section.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: skills/design/scripts/render-final-summary.sh:382-387
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] render_or_fallback skips self-composed fallback when post-phase render exits non-zero but final-summary.md is non-empty Post-publish re-render fails after warnings were appended during publish; chat still prints the Phase-1 file with stale Warnings/Exec issues and may omit bullets if the partial file was truncated Remove or narrow the post-phase early return; fall back when rr!=0 unless the file passes full schema validation
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: skills/design/scripts/render-final-summary.sh:382-387
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Same early return contradicts plan degraded-render rule (fallback on nonzero OR empty) Renderer failure with a stub/incomplete body leaves chat without the mandated design-schema fallback and without refreshed warning counts Always compose_self_fallback (or Stage-1 re-invoke with --cost-unavailable) after append_render_warning when rr!=0
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: skills/design/scripts/test-render-final-summary.sh:113-136
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Test asserts preserving stale file on post render failure, encoding non-plan behavior CI green while implementation diverges from plan acceptance for render-final-summary degraded path Split tests: full fallback on empty/failed render; only add preserve-cost test if product explicitly overrides plan
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: skills/design/scripts/render-final-summary.sh:382-387
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Post-phase render failure keeps non-empty pre-publish final-summary.md instead of recomposing. Publish-time warnings in execution-issues.md may not appear in chat or tracking summary when post render fails but pre file had a cost line. Document trade-off or refresh warning/exec bullets on post failure before chat print.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: skills/design/scripts/render-final-summary.md:23-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc omits post-phase preserve-prior-file behavior that tests now require. Operators reading only the md misexpect full fallback whenever post render exits non-zero. Add subsection describing post failure retention of pre-publish file.
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/scripts/write-final-report.sh:226-438
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] refresh_issue_counts is only called after render failure, not before primary render; EXEC_N/WARN_N are seeded from ndjson only. Step 17 with five warnings in execution-issues.md but WARNINGS=2 in ndjson prints - **Warnings**: 2; after fallback append to a previously empty md file, ndjson-only warnings vanish from the summary. Call refresh_issue_counts once before the first run_body_render and remove the duplicate ndjson-only seeding block.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/render-final-summary.sh:376-388
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Post-phase render failure preserves a non-empty pre-publish final-summary when summary_has_usable_cost passes. Post-publish render fails after new warnings were appended; chat still shows pre-publish Warnings: 0 and stale exec counts while cost line looks correct. In PHASE=post, do not return early on stale files; re-render or always compose_self_fallback with refreshed counts after failure.
- **Suggested revision**: Address the concern above.


