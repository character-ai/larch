### FINDING_1: [OUT_OF_SCOPE] architecture: d0d32d93..HEAD commit bundle
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Branch bundles vote-tally fix with ship-pr changelog work. Larger unrelated surface in one PR. Split PRs or document intentional coupling for reviewers.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Large committed implement run-log tree in branch diff. Intentional repo logging artifacts per docs/run-log policy; not a feature regression. None (branch packaging / process).
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large committed run logs Transcripts may include sensitive operational text if runs ever log secrets. Policy already accepts logs; ensure secrets never enter run logs globally (pre-existing hygiene).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh (parallel commits)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Vote-tally and related collateral on same branch not reviewed for this feature. Unrelated regressions would not be caught by this pass. Separate focused review if shipping together.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh:115-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Bundled unrelated vote-tally behavior change on same branch. Not part of the changelog auto-resolve requirement set for this review. Track/review in its own PR context if desired.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh:129-136
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Exoneration classification broadened Multi-voter panels may classify some vote mixes as exonerated where the old rule did not. Not part of conflict-resolution trust boundary; review separately if tally semantics matter for your governance.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/auto-resolve-changelog.sh:1-274
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation is far larger and more capable than the plan’s ~35-line Bash sketch. Traceability from the plan’s “small helper” framing to the final artifact is weak even though behavior may be desirable. Update planning templates to avoid misleading size guesses, or keep a deliberately minimal script if that was a hard constraint.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: Branch diff vs feature_description
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The branch bundles unrelated vote-tally/docs/version work with the ship-pr conflict automation described in the feature text. Bisect and revert become harder: a regression in either subsystem is tied to the same merge unit, and reviewers must mentally partition two different risk profiles. Split unrelated concerns into separate PRs/commits where practical.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/auto-resolve-changelog.sh:1-274
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The auto-resolver grew into a large Bash+awk subsystem (MD+RST+extensionless) versus the plan's short deterministic script sketch. Higher maintenance and review cost for a helper that was originally scoped as a small pre-pass; future edits risk unintended changelog corruption because many rules live in one awk blob. Either document intentional scope expansion vs the plan or refactor (split awk to a file / split modes) to recover a smaller reviewable unit.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/test-launch-cursor-ci.sh:3467-3470 (and codex twin)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New launcher tests rely on grep for prompt substrings, duplicated across Cursor and Codex harnesses. Fragile coupling to marketing-style prompt text; a wording tweak breaks tests in two files without catching a functional argv regression. Optional: centralize expected markers or assert argv construction more structurally if the harness can do so cheaply.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/auto-resolve-changelog.sh:160-178
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Extensionless CHANGELOG without ## forces RST merge mode. Markdown-only root CHANGELOG without level-2 headings can be mis-merged or exit 1 unpredictably versus a human merge. Restrict auto-merge by suffix or detect markdown before choosing RST.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/auto-resolve-changelog.sh:190-223
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Line-level merge under one Unreleased heading flattens structure. Divergent subsection layouts can yield duplicate or misleading ### headers while appearing valid. Detect structural mismatch and exit 1 or document limitation.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/auto-resolve-changelog.sh:209-217
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Markdown first-section merge dedupes by exact line text only. Two contributors add the same changelog bullet with different trailing spaces or minor punctuation; auto-resolve keeps both lines, producing a duplicate-looking release note. Normalize for comparison (e.g. rtrim) or document limitation and defer to vendor merge.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/auto-resolve-changelog.sh:2453-2607
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Merge logic requires identical post-first-section tails for :2: and :3: before writing output. Rebases where Unreleased merges cleanly but a later section (e.g. a versioned heading body) differs between upstream and the replayed commit will not auto-resolve and will still invoke the vendor, even though the plan text reads like always taking upstream’s tail after the first heading. Align the plan with the implemented tail guard, or change the script to always append the upstream tail when the first heading matches if that simpler semantics was intended.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/launch-cursor-ci.sh:71-74;scripts/launch-codex-ci.sh:71-74
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CSV path validation is whole-string, not per-segment. If a future caller concatenates paths incorrectly, a malicious or mistaken absolute segment could slip past checks that only look at the full string prefix. Split CSV and validate each path segment.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/ship-pr.sh:1327-1334
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] plugin.json auto-resolve guard uses pattern '*/.claude-plugin/plugin.json' only, which misses the usual repo-relative path '.claude-plugin/plugin.json' from git's conflict listing. Rebase conflicts that only touch the real plugin manifest skip the intended 'git checkout --ours' fast path and still route through the vendor resolver (or mark the file unresolved), so the plan's deterministic handling for that file often never runs. Also match '.claude-plugin/plugin.json' at repo root (or use a prefix-agnostic test) and add a regression case in test-ship-pr.sh that conflicts only on that path.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: branch diff (e.g. scripts/lib-vote-tally.sh; docs/voting-process.md; agent-lint.toml; Makefile; CHANGELOG.md; .claude-plugin/plugin.json; larch-logs/implement/**)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Non-plan files and whole run-log trees change alongside the ship-pr changelog work. Plan-fidelity reviewers cannot map a large fraction of the diff to the stated implementation plan; release notes and risk review mix unrelated behavioral changes with the rebase-conflict feature. Split unrelated changes into separate PRs or expand the written plan to enumerate and justify every touched path.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Mechanical git checkout --ours for go.sum/version.go on conflict. Branch-side dependency or version edits can be dropped while the index looks clean, causing later CI/build failures. Narrow the rule or route go.sum to vendor.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unscoped git checkout --ours for any version.go or go.sum Auto-resolving nested/vendored Go metadata conflicts to ours can drop upstream security-relevant dependency changes. Allowlist canonical paths or send ambiguous nested paths to vendor only.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/ship-pr.sh:1353-1369
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] After failed git rebase --continue, vendor CSV is rebuilt from diff-filter=U only. Unmerged list can be empty while rebase is still in progress, so vendor may get no --conflict-files. Fallback to original CONFLICT_FILES or richer git status in prompt/log.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-auto-resolve-changelog.sh:1-146
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Tail-guard failure mode untested in offline harness. If awk tail comparison regresses merged tails could be wrong or script could mis-exit without a targeted failing test. Add fixture where tails after second heading differ expect exit 1.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-launch-cursor-ci.sh:13-44 and scripts/test-launch-codex-ci.sh:13-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Grep-only assertions for conflict prompt wiring. String rename or wiring bug could leave prompt broken while tests pass. Add minimal invocation asserting prompt contains CSV paths and instructions.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-launch-cursor-ci.sh:33-37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] --conflict-files tests are mostly substring greps, not an argv/prompt contract exercise. A future refactor could drop the flag from the real parse path while tests still pass via unrelated matches. Add one minimal successful invocation asserting accepted argv or prompt file contents.
- **Suggested revision**: Address the concern above.

### FINDING_24: security: scripts/launch-codex-ci.sh:84-101
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Same raw CONFLICT_FILES in Codex PROMPT Same steering risk for Codex as for Cursor on malicious or odd paths. Mirror Cursor-side hardening: delimiter block, charset checks, or structured attachment.
- **Suggested revision**: Address the concern above.

### FINDING_25: security: scripts/launch-cursor-ci.sh:2926-2930 and scripts/launch-codex-ci.sh:2769-2773
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] CSV path validation is whole-string not per-token. Hypothetical future caller could pass mixed safe and absolute-looking segments without tripping current checks. Split CSV validate each segment for .. and absolute paths.
- **Suggested revision**: Address the concern above.

### FINDING_26: security: scripts/launch-cursor-ci.sh:88-102
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] CONFLICT_FILES embedded raw in vendor prompt with minimal validation Collaborator-controlled conflict path strings can steer or split the external Cursor agent prompt (indirect prompt injection). Wrap list in strict delimiters; sanitize or reject non-printable and markdown-breakout characters per segment; prefer non-inline path list.
- **Suggested revision**: Address the concern above.

### FINDING_27: security: scripts/launch-cursor-ci.sh:88-92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Raw CSV paths embedded in prompt. Low risk delimiter/prompt injection if paths were ever exotic. Use newline-separated list or structured block.
- **Suggested revision**: Address the concern above.

### FINDING_28: security: scripts/ship-pr.sh:345-347
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] kv_value line-based parse vs multi-line CONFLICT_FILES values A hypothetical multi-line value breaks one-line KV assumptions for CONFLICT_FILES parsing. Reject or escape embedded newlines in KV values; or avoid KV for path lists.
- **Suggested revision**: Address the concern above.

