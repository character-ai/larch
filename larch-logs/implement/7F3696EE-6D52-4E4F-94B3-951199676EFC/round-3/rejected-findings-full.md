### [rejected] FINDING_10

### FINDING_10: code-quality: scripts/test-launch-cursor-ci.sh:3467-3470 (and codex twin)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New launcher tests rely on grep for prompt substrings, duplicated across Cursor and Codex harnesses. Fragile coupling to marketing-style prompt text; a wording tweak breaks tests in two files without catching a functional argv regression. Optional: centralize expected markers or assert argv construction more structurally if the harness can do so cheaply.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

### FINDING_12: correctness: scripts/auto-resolve-changelog.sh:190-223
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Line-level merge under one Unreleased heading flattens structure. Divergent subsection layouts can yield duplicate or misleading ### headers while appearing valid. Detect structural mismatch and exit 1 or document limitation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

### FINDING_13: correctness: scripts/auto-resolve-changelog.sh:209-217
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Markdown first-section merge dedupes by exact line text only. Two contributors add the same changelog bullet with different trailing spaces or minor punctuation; auto-resolve keeps both lines, producing a duplicate-looking release note. Normalize for comparison (e.g. rtrim) or document limitation and defer to vendor merge.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

### FINDING_15: correctness: scripts/launch-cursor-ci.sh:71-74;scripts/launch-codex-ci.sh:71-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CSV path validation is whole-string, not per-segment. If a future caller concatenates paths incorrectly, a malicious or mistaken absolute segment could slip past checks that only look at the full string prefix. Split CSV and validate each path segment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

### FINDING_17: risk-integration: branch diff (e.g. scripts/lib-vote-tally.sh; docs/voting-process.md; agent-lint.toml; Makefile; CHANGELOG.md; .claude-plugin/plugin.json; larch-logs/implement/**)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Non-plan files and whole run-log trees change alongside the ship-pr changelog work. Plan-fidelity reviewers cannot map a large fraction of the diff to the stated implementation plan; release notes and risk review mix unrelated behavioral changes with the rebase-conflict feature. Split unrelated changes into separate PRs or expand the written plan to enumerate and justify every touched path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

### FINDING_18: risk-integration: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Mechanical git checkout --ours for go.sum/version.go on conflict. Branch-side dependency or version edits can be dropped while the index looks clean, causing later CI/build failures. Narrow the rule or route go.sum to vendor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

### FINDING_19: risk-integration: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unscoped git checkout --ours for any version.go or go.sum Auto-resolving nested/vendored Go metadata conflicts to ours can drop upstream security-relevant dependency changes. Allowlist canonical paths or send ambiguous nested paths to vendor only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

### FINDING_20: risk-integration: scripts/ship-pr.sh:1353-1369
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] After failed git rebase --continue, vendor CSV is rebuilt from diff-filter=U only. Unmerged list can be empty while rebase is still in progress, so vendor may get no --conflict-files. Fallback to original CONFLICT_FILES or richer git status in prompt/log.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

### FINDING_22: risk-integration: scripts/test-launch-cursor-ci.sh:13-44 and scripts/test-launch-codex-ci.sh:13-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Grep-only assertions for conflict prompt wiring. String rename or wiring bug could leave prompt broken while tests pass. Add minimal invocation asserting prompt contains CSV paths and instructions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

### FINDING_23: risk-integration: scripts/test-launch-cursor-ci.sh:33-37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] --conflict-files tests are mostly substring greps, not an argv/prompt contract exercise. A future refactor could drop the flag from the real parse path while tests still pass via unrelated matches. Add one minimal successful invocation asserting accepted argv or prompt file contents.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

### FINDING_24: security: scripts/launch-codex-ci.sh:84-101
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Same raw CONFLICT_FILES in Codex PROMPT Same steering risk for Codex as for Cursor on malicious or odd paths. Mirror Cursor-side hardening: delimiter block, charset checks, or structured attachment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

### FINDING_25: security: scripts/launch-cursor-ci.sh:2926-2930 and scripts/launch-codex-ci.sh:2769-2773
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] CSV path validation is whole-string not per-token. Hypothetical future caller could pass mixed safe and absolute-looking segments without tripping current checks. Split CSV validate each segment for .. and absolute paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

### FINDING_26: security: scripts/launch-cursor-ci.sh:88-102
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] CONFLICT_FILES embedded raw in vendor prompt with minimal validation Collaborator-controlled conflict path strings can steer or split the external Cursor agent prompt (indirect prompt injection). Wrap list in strict delimiters; sanitize or reject non-printable and markdown-breakout characters per segment; prefer non-inline path list.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

### FINDING_27: security: scripts/launch-cursor-ci.sh:88-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Raw CSV paths embedded in prompt. Low risk delimiter/prompt injection if paths were ever exotic. Use newline-separated list or structured block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

### FINDING_28: security: scripts/ship-pr.sh:345-347
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] kv_value line-based parse vs multi-line CONFLICT_FILES values A hypothetical multi-line value breaks one-line KV assumptions for CONFLICT_FILES parsing. Reject or escape embedded newlines in KV values; or avoid KV for path lists.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

### FINDING_7: architecture: scripts/auto-resolve-changelog.sh:1-274
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation is far larger and more capable than the plan’s ~35-line Bash sketch. Traceability from the plan’s “small helper” framing to the final artifact is weak even though behavior may be desirable. Update planning templates to avoid misleading size guesses, or keep a deliberately minimal script if that was a hard constraint.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

### FINDING_8: code-quality: Branch diff vs feature_description
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The branch bundles unrelated vote-tally/docs/version work with the ship-pr conflict automation described in the feature text. Bisect and revert become harder: a regression in either subsystem is tied to the same merge unit, and reviewers must mentally partition two different risk profiles. Split unrelated concerns into separate PRs/commits where practical.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/auto-resolve-changelog.sh:1-274
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The auto-resolver grew into a large Bash+awk subsystem (MD+RST+extensionless) versus the plan's short deterministic script sketch. Higher maintenance and review cost for a helper that was originally scoped as a small pre-pass; future edits risk unintended changelog corruption because many rules live in one awk blob. Either document intentional scope expansion vs the plan or refactor (split awk to a file / split modes) to recover a smaller reviewable unit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

