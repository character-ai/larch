### FINDING_1: risk-integration: SECURITY.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Tier 2 help/flag narrative says stdout-only and no stderr merge, but probe_help redirects stderr into the same capture used for flag matching. Security/trust reviewers and operators may rely on SECURITY.md and assume stderr cannot affect Tier 2 positives/negatives; actual behavior merges streams. Align SECURITY.md with validate-plan-commands.md and probe_help, or split stdout vs stderr in code and document the split.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: skills/design/SKILL.md:496-497
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 2b prose calls the pre-validation driver line “plan-validation” and claims it writes diff-lines.txt, but the block is ACTION=EMIT_PLAN. Executors may run the wrong mental model (skip EMIT_PLAN, or conflate validation with diff emission) and mis-route failures. Reword: name EMIT_PLAN as the diff-lines writer; describe plan-command validation only in the following block.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/invoke-plan-validator-if-not-quick.sh:21-22|skills/design/scripts/design-driver.sh:144-146
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra wrapper indirection and word-split ARGS parsing for VALIDATE_PLAN_COMMANDS. Low risk today because tmp paths are space-free; slightly harder to trace than a single callsite. Document the space-free ARGS contract or quote ARGS; keep wrapper if DRY outweighs indirection.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/parse-plan-commands.sh:73-74|skills/design/scripts/parse-plan-commands.awk:5-6
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] TSV gains cmd_uid and logic spans awk+sh beyond the original “one helper script” sketch. Slightly higher maintenance burden when evolving the schema. Document cmd_uid as normative internal column or absorb into fewer artifacts if complexity grows.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: larch-logs/design/131FD254-E52D-49E7-BE0D-3E2D491A15E8/*
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Large committed design log flush inflates the PR diff. Obscures feature diff in raw views; expected for larch-logs policy. No action required for Lesson 5 correctness; use path filters when reviewing.
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

### FINDING_13: risk-integration: skills/design/scripts/design-driver.sh:143-146
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] ARGS for driver actions are parsed with read -a from a single line; spaced paths would split incorrectly If TMPDIR or plugin paths ever contain spaces the validate action could target the wrong file or fail open Keep space-free path invariant explicit in callers or use safer argv framing
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture: larch-logs/** (branch diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large run-log trees ship by repo convention Operational noise and possible sensitive content in historical logs is a broader logging policy topic not specific to the new validator helpers None required for this PR beyond normal run-log hygiene practices
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/design/scripts/validate-plan.sh:64-96
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] VALIDATE_LOG_FILE can name a temp log that EXIT trap deletes when DESIGN_TMPDIR copy branch does not run. Operator or tooling follows VALIDATE_LOG_FILE from validate-plan.sh stdout after a local/harness invocation without DESIGN_TMPDIR and finds ENOENT or flaky reads. Persist logs on that path before trap cleanup or document that VALIDATE_LOG_FILE is unstable unless copied under DESIGN_TMPDIR; adjust harness if a stable log is required.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: SECURITY.md:179 vs skills/design/scripts/validate-plan-commands.sh:115-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SECURITY claims Tier 2 --help uses stdout-only without stderr merged into help detection; probe_help merges stderr into the capture via 2>&1. Trust-model audit assumes stderr cannot satisfy or distort help detection; actual implementation may classify stderr-only usage differently than documented. Align SECURITY text with merged capture or split streams and apply the documented rule in code.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: skills/design/scripts/parse-plan-commands.awk:372-455 and skills/design/scripts/validate-plan-commands.sh:327-353
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Tier 3 argv omits positional plan arguments; only long flags are replayed. Dry-run registry script needs positional args to exercise path-containment checks; Tier 3 may pass while real plan command would fail. Document limitation in validate-plan-commands.md and/or extend TSV with argv tail behind existing metacharacter rules.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/design/scripts/parse-plan-commands.awk:37-44 and skills/design/scripts/validate-plan-commands.sh:249-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] NEW-script skip is exact string match on script_path without shared normalization with allow-list paths. Plan lists NEW path spelling that differs slightly from fenced command spelling; validator does not skip new script and reports missing-script or unknown-flag until Override. Normalize paths consistently for allow-list and invocations or document strict spelling parity.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/design/scripts/design-driver.sh:125-170
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] no_sentinel prevents skip-on-replay but success still writes a completion sentinel; naming suggests otherwise. Future contributor changes resume logic assuming no sentinel file exists for VALIDATE_PLAN_COMMANDS. Clarify inline that sentinel is written for bookkeeping only and must not gate skipping.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] code-quality: skills/design/scripts/parse-plan-commands.awk:249-320
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] split_segments ignores standalone shell & background operator. Hypothetical plan uses cmd & cmd in one fenced line; parsing may bundle oddly. Ignore unless real plan style adopts lone &.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/design/scripts/validate-plan-commands.sh:133-139; skills/design/scripts/validate-plan-commands.md:14-15
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Tier 2 help gate accepts only exit 0, omitting planned recognized non-zero usage exits Any repo script whose --help prints usage then exits non-zero skips all long-flag checks (SKIPPED_FLAG_CHECK), so bad flags in plans are not caught despite readable help text Extend probe_help to honor a small allowlist of non-zero RCs with non-empty merged capture (and document), or make --help exit 0 across probed scripts; add harness coverage for non-zero-help RC
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: skills/design/references/approval-gates.md:86-87; skills/design/references/discussion-rounds.md:121
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Gate B / discussion docs show raw ACTION=VALIDATE_PLAN_COMMANDS pipe instead of invoke-plan-validator-if-not-quick.sh An executor copy-pastes the ACTION line without the review_budget guard and runs validation on trivial (review_budget=quick), violating the tier skip contract Point Gate B and discussion-round2 prose at invoke-plan-validator-if-not-quick.sh "$DESIGN_TMPDIR/plan.txt" like SKILL Step 2b
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/design/scripts/parse-plan-commands.md:16-20; skills/design/scripts/validate-plan-commands.sh:218-247
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Parser TSV adds cmd_uid beyond the six-column plan schema Fixtures and consumer awk target seven fields; external readers of the old plan could mis-implement column offsets Amend archived plan text to seven columns or remove cmd_uid if strict six-column wire is required
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: skills/design/SKILL.md:869-876
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan helper contracts omit invoke-plan-validator-if-not-quick.sh and read-design-review-budget.sh Footer incomplete versus #2674 helper enumeration for agent-lint literal-path reachability Add bullets with full ${CLAUDE_PLUGIN_ROOT}/… paths and sibling docs
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] architecture: larch-logs/design/** (diff bulk)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Large larch-logs diff volume Obscures functional diff when reviewing only diff.txt sidecar None for Lesson 5 fidelity; use path-filtered diffs for reviews
- **Suggested revision**: Address the concern above.

