### FINDING_1: code-quality: scripts/test-mermaid-fragments.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Plan-required Item C regression for embedded = in REASON_TOKEN aggregation is missing from the branch Developer reverts sanitize-mermaid-fragment.sh:283 to awk -F'[ =]'; CI stays green because no harness asserts future=token preservation in warnings aggregation Add planned test case with REASON_TOKEN=future=token fence=mermaid line=9 and assert future=token appears in aggregated tokens
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/test-mermaid-fragments.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Planned Item C/F23 regression test for embedded = in REASON_TOKEN aggregation is absent from the branch diff. An incorrect revert of the line-283 awk to -F'[ =]' would pass CI except for this case and truncate REASON_TOKEN=future=token to future in warnings-log aggregation. Add the harness case from the plan: fixture reasons file with REASON_TOKEN=future=token fence=mermaid line=9 and assert both normal-token and future=token appear in aggregated output.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: skills/implement/scripts/test-step-7a.sh:475-478
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness failure messages still use the old diagram-generation-failure label after the case was renamed to diagram-failure. Test failures print a misleading case name; assertions and behavior are unaffected. Rename assert message strings from diagram-generation-failure to diagram-failure.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:368-380
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CODE_FLOW_SKIP_REASON is not passed through sanitize_diagnostic_line before issue upsert (plan narrowed Item E). A malformed sanitizer log could embed C0 control bytes into the larch:diagrams comment via the new SKIP_REASON relay path. Optionally pipe CODE_FLOW_SKIP_REASON through sanitize_diagnostic_line in compose_summary_diagrams in a follow-up; not required by the accepted plan.
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: scripts/test-mermaid-fragments.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required Item C/F23 regression for REASON_TOKEN aggregation with embedded = was not added despite changing sanitize-mermaid-fragment.sh:283. Revert to awk -F'[ =]' could ship undetected; warnings-log would truncate future=token to future while test-mermaid-fragments and test-generate-code-flow-diagram still pass. Add harness case with REASON_TOKEN=normal-token and REASON_TOKEN=future=token fence=mermaid line=9 asserting both tokens appear in aggregated warnings output.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: skills/implement/scripts/step-7a.sh:371-372,381-382,386-390
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Empty-SKIP_REASON fallback on skipped/failed branches is untested; generator-crash hits wildcard *) not kv_value fallback. Regression in else branches on skipped/failed would not fail CI; only production envelope gaps would surface. Add stub mode with STATUS=failed or skipped and no SKIP_REASON line, or document wildcard as sole empty-envelope path.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: skills/implement/scripts/test-step-7a.sh:475-479
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Assertion labels still say diagram-generation-failure after case rename to diagram-failure. Harness failure output mislabels the case during triage. Rename assertion messages to diagram-failure.
- **Suggested revision**: Address the concern above.

### FINDING_8: security: skills/implement/scripts/step-7a.sh:368-382
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Generator SKIP_REASON is copied into CODE_FLOW_SKIP_REASON and published on the tracking issue without sanitize_diagnostic_line or markdown neutralization. If gen_out ever carries C0 controls or embedded newlines in SKIP_REASON, the larch:diagrams comment body or rendered GitHub markdown could be corrupted or structurally manipulated before redact-secrets runs. Pipe _skip_reason through sanitize_diagnostic_line (and optionally reject newline-containing values) before assigning CODE_FLOW_SKIP_REASON.
- **Suggested revision**: Address the concern above.

### FINDING_9: security: scripts/ci-failed-jobs.sh:100-134
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Item D strips control bytes and drops empty names but still emits printable metacharacters from gh job names into TSV rows and downstream KV consumers when regex classification accepts them. A hostile or crafted workflow job name with shell or markdown metacharacters could still reach operator-visible TSV/KV surfaces; sanitize_list does not scrub per-row TSV cells. Apply job_re-style allowlist filtering at the parse boundary before TSV/KV emit, or document residual risk and verify ship-pr per-job fix loop never interpolates raw TSV fields unsafely.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] security: scripts/lib-quiet.sh:105-122
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] larch_err/larch_errf unchanged; sanitize_diagnostic_line is opt-in per caller. External stderr forwarded verbatim to operator channels remains possible at unaudited call sites. Route new and high-risk external passthrough sites through sanitize_diagnostic_line per lib-quiet.sh comment contract.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] security: scripts/ship-pr.sh:719-723
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ship-pr failure-log relay to larch_err without shared sanitizer. CI/vendor stderr with control bytes or ANSI sequences can still reach operator-visible stderr. Apply per-line sanitize_diagnostic_line when relaying captured failure logs.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: scripts/test-mermaid-fragments.sh
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Planned Item C embedded-= regression test not added in implementation commit. REASON_TOKEN aggregation at sanitize-mermaid-fragment.sh:283 could regress without CI signal. Add the planned harness case asserting embedded = is preserved in warnings token aggregation.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/test-mermaid-fragments.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Item C parser change at sanitize-mermaid-fragment.sh:283 has no dedicated regression test required by plan F23 A future REASON_TOKEN like future=token would again truncate to future in ### Warnings entries while generator SKIP_REASON still looks correct Add harness case with synthetic reasons file asserting future=token is preserved in warnings aggregation
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: scripts/lib-quiet.sh:101-103
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] sanitize_diagnostic_line not adopted repo-wide per narrowed Item E scope Other larch_err passthrough sites still forward unsanitized external lines Follow-up audit if broader diagnostic hardening is desired
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/test-mermaid-fragments.sh (plan Item C / F23)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned embedded-= REASON_TOKEN regression test for sanitize-mermaid-fragment.sh:283 warnings aggregation was not added The branch rewrites the line-283 awk consumer but leaves test-mermaid-fragments.sh unchanged, so a parser regression that truncates REASON_TOKEN=future=token at the first = would not fail CI; acceptance criteria citing F23 mitigation and bash scripts/test-mermaid-fragments.sh are unmet Add the planned harness case with REASON_TOKEN=normal-token and REASON_TOKEN=future=token fence=mermaid line=9, run the same awk aggregation as line 283, and assert both normal-token and future=token are preserved
- **Suggested revision**: Address the concern above.

