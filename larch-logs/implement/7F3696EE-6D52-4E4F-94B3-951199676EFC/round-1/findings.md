### FINDING_1: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Bulk committed implement run logs present in the diff. Intentional per docs/run-logs.md; not a security regression from this feature. No action required for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh scripts/test-lib-vote-tally.sh docs/voting-process.md CHANGELOG.md (29.8.49 / #2446)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Branch bundles #2446 vote-tally behavior and docs outside the changelog rebase plan. Not a defect in the changelog feature itself; reviewers expecting a single-feature PR should be aware the diff vs main includes unrelated merged work. Treat as separate change set or split PRs if scope purity matters.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: scripts/auto-resolve-changelog.sh:2388-2428 scripts/ship-pr.sh:1320-1325
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] CHANGELOG.rst is routed through a Markdown ##-only merger. Real .rst changelogs rarely use ## headings, so auto-resolve exits 1 and the 30-minute vendor path is still used for .rst-only conflicts, contrary to the plan’s intent to treat .rst like .md for deterministic resolution. Add RST-aware parsing, or restrict the auto branch to supported formats and document .rst as vendor-only so the plan matches behavior.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/ship-pr.sh:1320-1336
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] case arm uses .claude-plugin/plugin.json against basename _base_cf so plugin.json conflicts never hit git checkout --ours Rebase conflicts on .claude-plugin/plugin.json always go to vendor instead of deterministic ours resolution; extra latency/cost and diverges from implementation plan Match basename plugin.json with path guard on $_cf or case on full relative path for .claude-plugin/plugin.json
- **Suggested revision**: Address the concern above.

### FINDING_5: risk-integration: scripts/lib-vote-tally.sh:127-138
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Broader multi-voter exoneration (EXONERATE can outvote NO without YES under the new condition). If consumers treat exonerated security findings as non-actionable, more ballot patterns now map to exonerated without YES consensus. Align docs and any security-specific gates with the new rule set; add a stricter branch for security-tagged findings if required.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/ship-pr.sh:1305-1357
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Missing CONFLICT_FILES= in rebase stdout leaves vendor_conflict_csv empty. Vendor runs without --conflict-files even though conflicts may exist, so the plan’s conflict context injection is skipped on parse failure or stale helpers. Fall back to git diff --name-only --diff-filter=U when kv_value is empty before launching the vendor.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: scripts/test-launch-cursor-ci.sh:33-36
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Launcher tests rely on grep for static strings not full argv/prompt contract Weaker guard against accidental removal of CONFLICT_FILES interpolation Add stricter contract test or test-mode prompt dump
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: scripts/test-ship-pr.sh:417-578
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness for CHANGELOG.rst or bare CHANGELOG in run_rebase_rebump pre-pass Regression in non-md changelog handling or case wiring could ship untested Extend fixtures to cover CHANGELOG.rst and CHANGELOG conflict filenames
- **Suggested revision**: Address the concern above.

### FINDING_9: security: scripts/launch-codex-ci.sh:71-93
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Mirrors launch-cursor-ci CONFLICT_FILES validation and inline prompt embedding. Same trust-boundary gap on the Codex resolve-conflict path. Share one validation helper between both launchers before building CONFLICT_CONTEXT.
- **Suggested revision**: Address the concern above.

### FINDING_10: security: scripts/launch-cursor-ci.sh:71-93
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] CONFLICT_FILES prompt context only rejects .. and leading slash on the whole CSV; no per-field control-character or path allowlist. A pathological CSV could add extra prompt lines or odd pathspecs if a caller ever passed unsanitized data, shifting vendor behavior away from the intended conflict list. Split validate each path segment with strict allowlist or pass paths via a file reference instead of raw CSV in the prompt.
- **Suggested revision**: Address the concern above.

### FINDING_11: security: scripts/ship-pr.sh:1322-1331
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Conflict paths from parsed rebase stdout are fed to git without launcher-equivalent validation. Low practical risk while rebase-push is trusted, but weaker defense in depth than the vendor CLI layer. Call a shared validate_repo_relative_path on each _cf before git commands.
- **Suggested revision**: Address the concern above.

