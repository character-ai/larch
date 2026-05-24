# Review Round 4

- Mode: `diff`
- 15 accepted, 6 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: code-quality: larch-logs/design/131FD254-E52D-49E7-BE0D-3E2D491A15E8/*
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Massive committed design-session artifact tree dominates the PR diff beside the validator. Reviewers must sift thousands of lines of prompts/transcripts to find functional regressions; consumers inherit noisy absolute paths and run-local content unrelated to the validator contract. Omit or separately PR the full design log dump; keep the branch focused on scripts/docs/harnesses/topology/SECURITY.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/design/scripts/test-read-design-review-budget-invoke.sh:43-55
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Non-quick invoke path is untested Regression in invoke-plan-validator or read-design-review-budget gating could skip or mis-dispatch validation for all full-tier /design runs while CI stays green Add a full-tier tmp DESIGN_TMPDIR fixture asserting design-driver completes VALIDATE_PLAN_COMMANDS with ok status
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/test-design-structure.sh:424-499
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Reference docs lack structural pins for EMIT_PLAN+VALIDATE pairing Gate B / discussion-round prose could drift and drop validator instructions without failing test-design-structure Add grep/awk assertions on approval-gates.md and discussion-rounds.md mirroring SKILL Step 2b contract
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/design/scripts/test-parse-plan-commands.sh:35-45
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Quoted-arg parse coverage is thin vs acceptance Quoting regressions in parse-plan-commands.awk/sh may slip until Tier2 misbehaves Add golden fixture for quoted script path or quoted flag value at parse layer
- **Suggested revision**: Address the concern above.


### FINDING_15: security: skills/design/scripts/validate-plan-commands.md:23-25;skills/design/scripts/validate-plan-commands.sh:345-372
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Tier3 dry-run argv replays long flags only; positionals and short flags are omitted Registry dry-run can pass while the real plan command still violates containment or other argv-sensitive checks if those checks depend on omitted tokens Replay a safe literal argv superset under the same hardening rules or tighten registry/docs so opt-in scripts cannot rely on positionals/short flags for safety-critical checks
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: skills/design/scripts/design-driver.sh:143-146;skills/design/scripts/invoke-plan-validator-if-not-quick.sh:21-22
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] ARGS reconstructed via whitespace split without shell-quoting generation Plan paths or ARGS containing spaces split into wrong argv; validation may target wrong file or error ambiguously Quote ARGS tokens at generation time and parse safely or enforce no-space tmpdir paths at creation
- **Suggested revision**: Address the concern above.


### FINDING_18: architecture: skills/design/scripts/validate-plan-commands.sh:337-390
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tier 3 argv omits all positional plan tokens; only script + long flags are executed. Dry-run can pass while the real plan command still fails containment or semantics when behavior depends on positional paths or subcommands. Model positional tokens in TSV for Tier 3 or narrow the Tier 3 contract and document the gap vs R4-style defects.
- **Suggested revision**: Address the concern above.


### FINDING_19: risk-integration: skills/design/scripts/design-driver.sh:143-146
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] ACTION ARGS are reparsed with unquoted read -a splitting on whitespace only. If --plan-file paths ever contain spaces or metacharacters argv is corrupted and validation targets the wrong file or errors opaquely. Document strict path constraints at emit sites or parse ARGS without whitespace-splitting assumptions.
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: skills/design/SKILL.md:5544-5546
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Fix-and-retry only re-runs EMIT_PLAN when plan.txt is edited, but Step 5c validates composed-plan.md. Operator fixes fenced commands only in composed-plan.md; diff_lines inside composed-plan can disagree with diff-lines.txt because EMIT_PLAN never reran. Require reconciling diff_lines with diff-lines.txt after composed-plan edits, or mandate syncing plan.txt / re-emit whenever diff_lines changes.
- **Suggested revision**: Address the concern above.


### FINDING_3: risk-integration: skills/design/scripts/invoke-plan-validator-if-not-quick.sh:15-22;skills/design/scripts/read-design-review-budget.sh:86-88
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Missing/unreadable run-params.json defaults review_budget to full for the invoke gate. If run-params is absent while the tier is trivial (quick), the validator still dispatches, contradicting flags.md and Step 3 quick_mode fallback prose. Align invoke defaults with Step 3 quick_mode fallback or fail-closed when run-params is missing.
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: skills/design/references/approval-gates.md:5591-5593;skills/design/references/discussion-rounds.md:5640
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] References cite raw ACTION=VALIDATE_PLAN_COMMANDS while SKILL uses invoke-plan-validator-if-not-quick.sh. Orchestrator following only the reference could diverge from the mechanical wrapper path in a future gate edit. Reference the invoke helper explicitly (or state equivalence) to keep one dispatch story.
- **Suggested revision**: Address the concern above.


### FINDING_6: code-quality: skills/design/scripts/parse-plan-commands.awk:6235-6236
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra cmd_uid column vs the six-column plan narrative in the issue body. Harness/docs readers may assume the wrong column count when diffing against the written plan. Document cmd_uid in the normative contract or remove it if not needed.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/design/scripts/parse-plan-commands.awk:88-96
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Bracketed ### NEW [path]: / ### UPDATED [path]: headings are not allow-listed; only ### NEW: / ### UPDATED: forms match. A plan uses ### NEW [skills/foo.sh]: with a fenced bash call to that new path; no new_script row is emitted so Tier 2 reports missing-script (or unrelated flag defects) until headings are rewritten or overridden. Extend AWK matchers and docs for the bracket grammar, or formally deprecate that heading variant in requirements.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/design/scripts/validate-plan-commands.sh:337-372
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Tier 3 argv omits all positional tokens from the fenced command; only the script path and extracted long flags are passed. A dry-run-only check that depends on a positional operand (path ordering/containment) never runs with that argv, so Tier 3 can pass while the real plan command would fail. Extend TSV/schema to carry vetted positionals or document and test a flags-only Tier 3 contract.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/design/scripts/validate-plan-commands.sh:368-372;scripts/dry-runnable-scripts.md:9-11
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Registry hook column values other than --validate-only silently use the LARCH_DRY_RUN=1 execution branch. Operator sets hook=my-mode expecting documented behavior; Tier 3 still injects only LARCH_DRY_RUN=1, masking misconfiguration. Reject unknown hook values or map them explicitly with tests.
- **Suggested revision**: Address the concern above.


