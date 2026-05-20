### FINDING_1: **architecture** `.claude/skills/audit-runs/SKILL.md:13-30` — Usage and Args document that `--no-fix-issues` is gone, but the skill never tells the orchestrator to treat a present `--no-fix-issues` as a hard usage error, while the updated harness in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:354-377` pins exactly that rejection contract. That splits the “removed flag” behavior across a test-only stub and markdown, so a legacy invocation can be silently ignored instead of failing fast, and the harness is not a faithful stand-in for anything the skill text requires. **Suggested fix:** Add an explicit Args or Pre-flight bullet: if any argv token is `--no-fix-issues`, refuse with a clear usage error (flag removed); keep the harness aligned with that single normative sentence.
- **Reviewer**: dyn-user-gate-completeness-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/SKILL.md:13-30` — Usage and Args document that `--no-fix-issues` is gone, but the skill never tells the orchestrator to treat a present `--no-fix-issues` as a hard usage error, while the updated harness in `.claude/skills/audit-runs/scripts/test-audit-runs.sh:354-377` pins exactly that rejection contract. That splits the “removed flag” behavior across a test-only stub and markdown, so a legacy invocation can be silently ignored instead of failing fast, and the harness is not a faithful stand-in for anything the skill text requires. **Suggested fix:** Add an explicit Args or Pre-flight bullet: if any argv token is `--no-fix-issues`, refuse with a clear usage error (flag removed); keep the harness aligned with that single normative sentence.
- **Suggested revision**: Address the concern above.

### FINDING_2: **architecture** `.claude/skills/audit-runs/SKILL.md:199-207` — The new `## Output to chat` section lists the body, URL, and short-circuit vs 3-way prompt but does not restate the sequencing precondition spelled out in `### Post-report user prompt` (lines 112–114: only after the new audit report is filed and **Close Prior Reports** has run). An orchestrator that jumps to the tail section could emit the chat contract before superseding/closing prior `audit-report` issues, which is inconsistent with the earlier gate even though it is not a bug-issue auto-file path. **Suggested fix:** Open `## Output to chat` with the same one-line precondition as `### Post-report user prompt` (after filing and after prior-report handling), so ordering is single-sourced.
- **Reviewer**: dyn-user-gate-completeness-output.txt
- **Concern**: - **architecture** `.claude/skills/audit-runs/SKILL.md:199-207` — The new `## Output to chat` section lists the body, URL, and short-circuit vs 3-way prompt but does not restate the sequencing precondition spelled out in `### Post-report user prompt` (lines 112–114: only after the new audit report is filed and **Close Prior Reports** has run). An orchestrator that jumps to the tail section could emit the chat contract before superseding/closing prior `audit-report` issues, which is inconsistent with the earlier gate even though it is not a bug-issue auto-file path. **Suggested fix:** Open `## Output to chat` with the same one-line precondition as `### Post-report user prompt` (after filing and after prior-report handling), so ordering is single-sourced.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:374-427` — Test 15 only exercises the all-empty proposal case; there is no complementary case where `proposed_new_issues` or `proposed_augmentations` is non-empty (including asymmetric mixes such as one list empty and the other populated), so the harness never proves the post-report path emits the 3-way prompt instead of the short-circuit line. **Suggested fix:** Add one or two fixtures (e.g. non-empty `proposed_new_issues` with `proposed_augmentations: []`, and the reverse) and assert `audit_report_post_report_chat_block` output contains the 3-way question substring and does not contain `No findings — no bug issues to file.`
- **Reviewer**: dyn-test-coverage-gap-output.txt
- **Concern**: - **correctness** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:374-427` — Test 15 only exercises the all-empty proposal case; there is no complementary case where `proposed_new_issues` or `proposed_augmentations` is non-empty (including asymmetric mixes such as one list empty and the other populated), so the harness never proves the post-report path emits the 3-way prompt instead of the short-circuit line. **Suggested fix:** Add one or two fixtures (e.g. non-empty `proposed_new_issues` with `proposed_augmentations: []`, and the reverse) and assert `audit_report_post_report_chat_block` output contains the 3-way question substring and does not contain `No findings — no bug issues to file.`
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-test-coverage-gap-output.txt
- **Concern**: - **code-quality** `.claude/skills/audit-runs/scripts/test-audit-runs.sh:307-319` — Test 13a models rejection as a stdout token (`usage_error:…`) rather than a non-zero exit code; that matches the rest of this file’s echo-based stubs but does not pin argv-order edge cases (e.g. `--no-fix-issues` first) unless added.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] The branch diff also adds under `larch-logs/implement/978A1866-C009-4359-81D0-3E70F5B0930E/` run metadata and plan text; that is unrelated to the audit-runs harness contract the scout notes targeted.
- **Reviewer**: dyn-test-coverage-gap-output.txt
- **Concern**: - The branch diff also adds under `larch-logs/implement/978A1866-C009-4359-81D0-3E70F5B0930E/` run metadata and plan text; that is unrelated to the audit-runs harness contract the scout notes targeted.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: larch-logs/implement/978A1866-C009-4359-81D0-3E70F5B0930E/manifest.json:17
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Flush manifest status in-progress is cosmetic for this feature review. N/A per committed run-log policy. N/A
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/SKILL.md:gh-issue-search-instructions
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] gh search strings built from scan finding text can break or broaden queries if interpolated into a shell without strict quoting. Pre-existing pattern in the skill; not introduced or materially expanded by this diff. Keep quoting/escaping discipline when implementing issue search from untrusted log-derived strings.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: .claude/skills/audit-runs/SKILL.md:178-186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] ## Output to chat omits the explicit Close Prior Reports ordering stated in Post-report user prompt. An orchestrator might print the mandatory chat block before superseding prior audit-report issues. Mirror the post-report precondition sentence under ## Output to chat.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: .claude/skills/audit-runs/SKILL.md:199-211
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dual headings Output to chat vs Output invite mis-read of which is mandatory. Operators conflate optional stdout summary with mandatory chat contract. Rename or nest the optional section under the chat contract.
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: .claude/skills/audit-runs/scripts/test-audit-runs.md:17
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan labels Test 13a as argparse rejection but the harness only embeds a bash argv loop in test-audit-runs.sh with no shared entrypoint under test. A future real argv parser could accept the removed flag while tests still pass giving false confidence. Rename the contract to argv or invocation-level rejection and match comments in the shell harness.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: .claude/skills/audit-runs/SKILL.md:112-118 vs 199-207
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-report prompt orders chat after Close Prior Reports; Output to chat omits that dependency. Orchestrator prints URL before prior audit-report issues are superseded/closed, confusing timeline. Mention Close Prior Reports ordering under Output to chat or merge sections.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:304-319
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 13a comments say argparse but only argv loop stub exists. Maintainers may believe argparse/CLI is covered when only a toy loop is tested. Rename comments to argv scan or test real entrypoint.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:378-394
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate grep logic in audit_report_post_report_chat_block and has_empty_proposals. One helper updated without the other could yield inconsistent harness behavior. Factor shared empty-proposal predicate.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: .claude/skills/audit-runs/scripts/test-audit-runs.sh:420-427
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Test 15b uses manual FAIL/PASS instead of assert_equal. Inconsistent failure diagnostics vs rest of harness. Use assert_equal or shared assert helper for uniformity.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: .claude/skills/audit-runs/SKILL.md:112-118
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Feature blurb says always ask the 3-way question; skill skips it when both proposal lists are empty. Stakeholder expects a 3-way prompt after every audit; clean audits get no prompt though the feature text says always ask. Align requirements text with the short-circuit or remove the short-circuit if always is literal.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: .claude/skills/audit-runs/SKILL.md:116-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Short-circuit keys only off empty proposal YAML lists, not off scan or narrative sections. Orchestrator emits empty lists while Per-PR findings still list problems; chat prints No findings and skips the 3-way gate. Tie short-circuit to scan outcomes or forbid inconsistent report bodies; document as anti-pattern.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: .claude/skills/audit-runs/SKILL.md:99-105
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Zero-findings short-circuit keys only on empty proposal YAML lists, not on actual scan outcomes. Mis-built frontmatter can show empty proposals while other report sections still describe scan failures, producing a false No findings message and skipping the 3-way question. Tie short-circuit to scan pass state or a single explicit zero-findings counter in frontmatter aligned with scan results.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: .claude/skills/audit-runs/scripts/test-audit-runs.sh:378-394
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Test 15 uses whole-document line grep for empty proposal lists instead of frontmatter-scoped parsing. Echoed lines or non-matching YAML spellings can make the harness disagree with real YAML semantics, giving false confidence in CI. Parse only the first --- delimited frontmatter block or use a small YAML parse in the harness.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: .claude/skills/audit-runs/SKILL.md:119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Augmentation step documents bare gh issue comment without --body-file. Multi-line markdown tables and special characters are easy to mis-quote in inline gh invocations; risk of failed posts or accidental shell metacharacter expansion compared to prior body-file pattern. Document gh issue comment N --body-file path.tmp matching create-one.sh style.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: .claude/skills/audit-runs/SKILL.md:13-30
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Removing --no-fix-issues drops the only documented single-shot way to complete an audit run with a filed audit report and guaranteed no bug-issue follow-up without a second chat turn. Scripted or unattended workflows that relied on the flag cannot express the same contract; they may need to stop mid-skill or incorrectly assume they can skip human gating. Add a migration note for unattended use or a supported non-interactive contract if that mode must remain.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.md:5-8;docs/linting.md:191
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Docs and harness copy imply CI-validated production rejection of --no-fix-issues while only a test-local bash helper encodes that check. Operators or wrappers may assume the flag is hard-rejected; passing it still relies on the LLM following SKILL with no script-level fail-fast, weakening the intended trust boundary. Reword contract rows to “pins expected orchestrator argv rules” or add one canonical argv preflight script and call it from the real entry path plus tests.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:306-312
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Removed-flag test only rejects exact --no-fix-issues. Variant spellings would pass the toy test while a stricter CLI would reject them. Document canonical rejection or add cases aligned with any future real argv parser.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:307-319
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Removed-flag rejection is tested only via an inline helper in the harness, not a shared production argv parser. A regression where SKILL text and harness drift from actual orchestrator behavior would still pass CI while operators accept the removed flag silently. Factor shared argv validation into a real entrypoint when one exists, or add a static contract test (e.g. SKILL usage/Args must not document --no-fix-issues) wired into the harness.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:377-427
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Test 15 covers only the zero-proposals branch; no assertion that non-empty proposals emit the 3-way prompt and suppress the short-circuit message. A logic inversion or partial implementation could pass CI while breaking the primary operator flow when findings exist. Add a companion fixture with non-empty proposed_new_issues or proposed_augmentations and assert the 3-way line is emitted and the short-circuit string is absent.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:378-385
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test 15 uses strict line-regex for empty proposal arrays. YAML with trailing comment or different formatting fails the empty check; test mis-signals vs intended schema. Parse YAML in the harness or relax patterns to match allowed emitters.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: .claude/skills/audit-runs/scripts/test-audit-runs.sh:378-385
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Empty-list detection relies on anchored grep over the full body, not structured YAML parsing. Alternate empty-list YAML spellings or CRLF could mis-classify empty vs non-empty in copied logic. Constrain tests to canonical generator formatting or parse the YAML frontmatter block explicitly.
- **Suggested revision**: Address the concern above.

