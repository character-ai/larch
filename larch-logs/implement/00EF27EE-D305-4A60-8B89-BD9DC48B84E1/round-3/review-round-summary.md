# Review Round 3

- Mode: `diff`
- 14 accepted, 7 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: risk-integration: SECURITY.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Tier 2 help/flag narrative says stdout-only and no stderr merge, but probe_help redirects stderr into the same capture used for flag matching. Security/trust reviewers and operators may rely on SECURITY.md and assume stderr cannot affect Tier 2 positives/negatives; actual behavior merges streams. Align SECURITY.md with validate-plan-commands.md and probe_help, or split stdout vs stderr in code and document the split.
- **Suggested revision**: Address the concern above.


### FINDING_10: security: SECURITY.md:32 skills/design/scripts/validate-plan-commands.sh:115-139
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] SECURITY Tier2 prose claims stdout-only help and no stderr merge but code merges stderr into the help capture Trust model and operator expectations diverge from implementation Update SECURITY paragraph to match validate-plan-commands.md merged-capture contract
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/scripts/test-validate-plan-commands.sh:17-32
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Wrapper KV tests omit VALIDATE_SKIPPED_COUNT and VALIDATE_UNSAFE_TOKEN_COUNT Mis-emitting those KVs from validate-plan.sh would pass CI Add grep assertions where counts are non-zero
- **Suggested revision**: Address the concern above.


### FINDING_12: security: skills/design/scripts/validate-plan-commands.sh:346-358; skills/design/SKILL.md:863-866
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Tier 3 dry-run appends full child stdout/stderr to validate-plan-commands.log; Override appends that log via append-tool-failure without --redact A plan line can pass a long secret as a flag value (allowed by unsafe_token); a registered dry-run script prints argv or errors; the secret is persisted in DESIGN_TMPDIR logs and can be copied into execution-issues.md and published with design logs Redact or truncate Tier 3 subprocess capture; use append-tool-failure --redact (or a redacted excerpt) on Override; tighten SECURITY.md trust model text to cover plan-derived argv echoing
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/design/scripts/validate-plan.sh:64-96
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] VALIDATE_LOG_FILE can name a temp log that EXIT trap deletes when DESIGN_TMPDIR copy branch does not run. Operator or tooling follows VALIDATE_LOG_FILE from validate-plan.sh stdout after a local/harness invocation without DESIGN_TMPDIR and finds ENOENT or flaky reads. Persist logs on that path before trap cleanup or document that VALIDATE_LOG_FILE is unstable unless copied under DESIGN_TMPDIR; adjust harness if a stable log is required.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: SECURITY.md:179 vs skills/design/scripts/validate-plan-commands.sh:115-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SECURITY claims Tier 2 --help uses stdout-only without stderr merged into help detection; probe_help merges stderr into the capture via 2>&1. Trust-model audit assumes stderr cannot satisfy or distort help detection; actual implementation may classify stderr-only usage differently than documented. Align SECURITY text with merged capture or split streams and apply the documented rule in code.
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: skills/design/scripts/parse-plan-commands.awk:37-44 and skills/design/scripts/validate-plan-commands.sh:249-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] NEW-script skip is exact string match on script_path without shared normalization with allow-list paths. Plan lists NEW path spelling that differs slightly from fenced command spelling; validator does not skip new script and reports missing-script or unknown-flag until Override. Normalize paths consistently for allow-list and invocations or document strict spelling parity.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/design/SKILL.md:496-497
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2b prose calls the pre-validation driver line “plan-validation” and claims it writes diff-lines.txt, but the block is ACTION=EMIT_PLAN. Executors may run the wrong mental model (skip EMIT_PLAN, or conflate validation with diff emission) and mis-route failures. Reword: name EMIT_PLAN as the diff-lines writer; describe plan-command validation only in the following block.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: skills/design/scripts/validate-plan-commands.sh:133-139; skills/design/scripts/validate-plan-commands.md:14-15
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Tier 2 help gate accepts only exit 0, omitting planned recognized non-zero usage exits Any repo script whose --help prints usage then exits non-zero skips all long-flag checks (SKIPPED_FLAG_CHECK), so bad flags in plans are not caught despite readable help text Extend probe_help to honor a small allowlist of non-zero RCs with non-empty merged capture (and document), or make --help exit 0 across probed scripts; add harness coverage for non-zero-help RC
- **Suggested revision**: Address the concern above.


### FINDING_24: architecture: skills/design/SKILL.md:869-876
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan helper contracts omit invoke-plan-validator-if-not-quick.sh and read-design-review-budget.sh Footer incomplete versus #2674 helper enumeration for agent-lint literal-path reachability Add bullets with full ${CLAUDE_PLUGIN_ROOT}/… paths and sibling docs
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: skills/design/scripts/test-validate-plan-commands.sh:1-194
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No harness for Tier2 SKIPPED_FLAG_CHECK no-help path Regression in probe_help or help-availability gating could change which plans pass Tier2 without any CI failure Add fixture script plus plan snippet asserting SKIPPED_FLAG_CHECK and summary SKIPPED_COUNT
- **Suggested revision**: Address the concern above.


### FINDING_7: risk-integration: skills/design/scripts/test-parse-plan-commands.sh:35-42 and skills/design/scripts/fixtures/parse-plan-commands/
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Parser golden tests omit backslash continuation and env-prefixed commands promised in plan acceptance Those real plan syntaxes could break silently in production /design Extend golden fixtures for line continuation and VAR=value command prefix
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: skills/design/scripts/read-design-review-budget.sh:1-52 skills/design/scripts/invoke-plan-validator-if-not-quick.sh:1-23
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New review_budget gating lacks direct unit coverage Fallback bugs could run validator on quick tier or skip on full tier Add small temp-json harness covering python jq and grep-only paths
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/design/scripts/test-validate-plan-commands.sh:124-160
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Tier3 --validate-only registry hook never exercised Argv branch for hook=--validate-only could break unnoticed Add one registry row and fixture script using --validate-only only
- **Suggested revision**: Address the concern above.


