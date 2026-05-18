### FINDING_1: **Important** `security` `scripts/redact-tmpdir-paths.sh:20` — The new operator-path redaction regex treats any punctuation as the end of the repo directory, so valid repo names containing punctuation are only partially redacted. Concrete scenario: `<OPERATOR_REPO_PATH>/scripts/foo.sh` now becomes `<OPERATOR_REPO_PATH>+repo/scripts/foo.sh`, while the previous slash-terminated rule redacted it to `<OPERATOR_REPO_PATH>/scripts/foo.sh`; committed logs can still expose operator repo-name fragments and suffix paths. Restore the broader component match for slash-terminated paths and add coverage for punctuation-bearing repo names, then handle root-before-punctuation as a separate case that does not split inside valid directory names.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/redact-tmpdir-paths.sh:20` — The new operator-path redaction regex treats any punctuation as the end of the repo directory, so valid repo names containing punctuation are only partially redacted. Concrete scenario: `<OPERATOR_REPO_PATH>/scripts/foo.sh` now becomes `<OPERATOR_REPO_PATH>+repo/scripts/foo.sh`, while the previous slash-terminated rule redacted it to `<OPERATOR_REPO_PATH>/scripts/foo.sh`; committed logs can still expose operator repo-name fragments and suffix paths. Restore the broader component match for slash-terminated paths and add coverage for punctuation-bearing repo names, then handle root-before-punctuation as a separate case that does not split inside valid directory names.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: larch-logs/implement/*/ (diff additions)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Large committed run-log JSON blobs in same branch diff. Intentional per repo policy; not PR noise for this review. No change required per review brief.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh vs scripts/apply-bump.sh
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Duplicate semver_lt helpers across scripts. Pre-existed as pattern; branch continues duplication. Factor shared semver helper in a follow-up if desired.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large committed implement run logs with embedded external tool output. Not introduced solely by commit pathspec fix per review scope rules; ongoing redaction discipline at capture time. N/A for this PR; rely on existing redact pipeline at publish boundaries.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh vs .claude/skills/bump-version/scripts/apply-bump.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate semver_lt helper pattern if present in both files. Long-term maintainability only; not specific to larch-log pathspec fix. Optional shared helper if desired.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/ship-pr.sh:385-395,.claude/skills/bump-version/scripts/apply-bump.sh:42-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Duplicate semver_lt implementations in ship-pr and apply-bump. Future edit updates one helper only; rebase correction and apply-bump guard diverge. Share one sourced semver helper or one canonical implementation.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/larch-log.sh:430-432
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment cites LARCH_LOG_REPO_ROOT vs REPO_ROOT symlink mismatch though both roots come from the same rev-parse at load. Maintainers chase the wrong root-cause story when debugging pathspec issues. Reword comment to describe prefix/pathspec hardening accurately.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/test-apply-bump.md:1-2
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Purpose line still emphasizes only same-version probe after adding regression-guard coverage. Doc skim hides the new H case motivation. Update Purpose to mention regression guard alongside same-version probe.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: skills/implement/SKILL.md (~Step 8/10 ship-pr paragraph in diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Wording suggests BUMP_REASONING_FILE itself is rewritten rather than file contents. Minor reader confusion about state machine vs filesystem. Clarify "reasoning markdown contents at BUMP_REASONING_FILE path."
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: docs/run-logs.md:378-383
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Doc text softens plan s always in-progress status claim to normally plus exceptions. Readers following the written plan literally may assume a stronger invariant than the repo documents. Reconcile plan and doc wording explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: docs/run-logs.md:69-73
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Manifest status doc diverges from the implementation plan: plan required an absolute rule (committed status always in-progress; completion from PR merge only); implementation documents a weaker normal-case plus exceptions and tells readers to use status as one signal among several. Operators following the plan’s intended contract may still over-trust or misread committed manifest status because the doc now legitimizes done-in-repo and multi-signal interpretation, undermining the stated goal of steering completion checks to PR merge state. Restore the plan’s blockquote (or equivalent text): committed `/implement` manifests in the normal path always show in-progress; done is tmpdir-only after the last commit window; completion is PR merge (not committed status), with at most a brief footnote if historical anomalies must be mentioned.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/redact-tmpdir-paths.sh:2714-2717
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Operator path regex segments narrowed to [[:alnum:]_.-]+ vs former [^/"[:space:]]+. Path like <OPERATOR_REPO_PATH>/... no longer matches; operator path can leak into committed or published logs. Widen segment charset (e.g. include +) or document and test; keep EOL/punctuation behavior.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/ship-pr.sh:1238-1241
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] new_version passed to semver_lt without same strict semver regex as _origin_ver. Malformed NEW_VERSION from classify/parsing can make numeric compares wrong or unpredictable for regression guard. Validate new_version with ^[0-9]+.[0-9]+.[0-9]+$ before semver_lt or fail closed.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/ship-pr.sh:1238-1241
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] semver_lt runs on NEW_VERSION without the same strict semver validation used for origin version. Malformed NEW_VERSION can mis-compare or interact badly with bash integer tests under set -e. Validate both operands with the same semver regex or teach semver_lt to fail closed on bad input.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/ship-pr.sh:2789-2943 semver_lt and run_rebase_rebump
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] new_version from classify is not strict-semver-validated before semver_lt while origin version is. Garbage or odd NEW_VERSION can make regression detection wrong or trigger bash integer comparison errors under set -e during rebase rebump. Validate new_version with the same ^[0-9]+.[0-9]+.[0-9]+$ pattern (or shared helper) before semver_lt.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/test-larch-log.sh:164-224
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Regression test uses a new _stale_payload instead of reusing an existing plan-goals-test fixture as the plan specified. Slight maintenance duplication; no functional gap if payloads stay valid. Reuse _cpayload for the fresh-run write (or move a shared fixture above all consumers) unless the distinct text is intentional for test readability.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: docs/run-logs.md (manifest.json section)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed manifest status wording softened vs implementation_plan absolute "always in-progress" claim. External checklist written against the plan literal could disagree with shipped docs; no runtime failure. Reconcile external text or add a short note if consumers were promised "always."
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/ship-pr.sh:1252-1289
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Rewrite failure is non-fatal but larch-log write still ingests uncorrected reasoning_file. Awk or grep validation fails; version-bump-reasoning batch still shows pre-correction NEW_VERSION while plugin.json and PR title show corrected bump. Gate larch-log write on successful rewrite, inject synthetic correction content, or stall until reconciled.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-larch-log.sh (stale-run isolation block)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan asked to reuse $_spayload; test uses a bespoke _stale_payload heredoc. None functionally today; weak plan/traceability fidelity. Reuse the shared payload if strict plan alignment matters.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-larch-log.sh (stale-run isolation block)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression test checks repo path absence but not git object paths for the flush commit. Stale content written under an unexpected prefix could evade the -e check on the expected directory only. Optional: assert git diff-tree / ls-tree has no stale run-id paths.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-larch-log.sh:3076-3133
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan asked to reuse $_spayload; test uses separate _stale_payload heredoc. Duplicate payload text can drift from other harness cases over time. Use $_spayload for write if sanitizer-compatible.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/redact-tmpdir-paths.sh:20-21
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Operator path redaction now matches only [alnum._-] per path segment; some valid path characters no longer match the full segment. Example <OPERATOR_REPO_PATH>/repo/... can partially match and rewrite to a corrupted line while leaving +bar/repo... unredacted. Widen segment class safely or layer patterns; add regression tests for + and similar filename characters.
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/redact-tmpdir-paths.sh:20-21
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Operator path segments restricted to [[:alnum:]_.-]+ vs prior broader class. Unusual clone directory names may no longer redact and could leak into published artifacts. Add tests or widen allowed characters without breaking boundaries.
- **Suggested revision**: Address the concern above.

### FINDING_24: security: scripts/redact-tmpdir-paths.sh:2714-2717
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Narrow ASCII-only path segments and locale-sensitive alnum for operator-repo redaction. Operator home or repo dir names with characters outside [[:alnum:]_.-] or locale quirks can leave literal /Users/... or /home/... paths in published text despite SECURITY.md claiming broader coverage. Document ASCII-only assumption set LC_ALL=C at scrubber entry or add a conservative second pass for /Users and /home prefixes.
- **Suggested revision**: Address the concern above.

