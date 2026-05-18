### FINDING_1: **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/codex-generalist-output.txt.meta:8` — The committed run logs still expose an unredacted operator-local repo path via `OUTER_LAUNCHER_WORKDIR`; the same leak pattern appears in multiple `round-1/*output.txt.meta` files and in `larch-logs/implement/D1984F57-A5A7-4632-8114-6533205051D3/round-1/coder-prompt.md:11`. Concrete scenario: this PR is merged and ships public `larch-logs/implement/...` artifacts containing the operator’s local home/repo path, which is the privacy leak class called out in the feature description. Scrub the committed log files before merge and update `scripts/redact-tmpdir-paths.sh` to redact `/Users/<user>/<repo>` or `/home/<user>/<repo>` when the repo path appears at end-of-value/end-of-line or before punctuation, then add a regression case for `OUTER_LAUNCHER_WORKDIR=/Users/name/repo`.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: Branch diff aggregate
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Wide PR mixes larch-log pathspec fix, ship-pr semver/reasoning rewrite, apply-bump guard, and bulk run-log commit Higher review cost and coupling than a minimal pathspec-only change Prefer smaller stacked PRs when process allows (observation only)
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: SECURITY.md (policy vs branch diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] No SECURITY.md update alongside privacy-relevant commit-behavior change Policy asks for SECURITY updates on security-relevant changes; reviewers may miss documenting reduced accidental run-dir commit risk Consider a short SECURITY note when implementing (not required for this read-only review)
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/**/manifest.json (historical)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Legacy manifests mix done status and older operator path fields. Noise when reconciling new run-logs prose with the repo snapshot. Treat as historical context when editing docs; not required for the commit pathspec fix.
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/larch-log.sh:425-428
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] rel hardcodes larch-logs layout parallel to larch_log_repo_run_dir. Future helper-only path layout change could desync commit pathspec from actual repo_path. Share one helper for the relative path or derive from normalized repo_path + REPO_ROOT.
- **Suggested revision**: Address the concern above.

### FINDING_6: architecture: scripts/ship-pr.sh:385-395 + .claude/skills/bump-version/scripts/apply-bump.sh:42-52
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicate semver_lt implementations in the same PR. Divergent edits could yield inconsistent ordering semantics across apply-bump vs run_rebase_rebump. Extract a single shared semver comparison helper and source it from both scripts.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: docs/run-logs.md:71-73
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Adjacent prose suggests manifest holds final status while next line says committed status is always in-progress Readers treat the section as contradictory and mistrust one of the two statements Qualify the first sentence so live schema vs committed snapshot is explicit
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/ship-pr.sh:385-395
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate semver_lt alongside apply-bump.sh Future semver/validation edits in one copy leave run_rebase_rebump and apply-bump disagreeing on regression detection Source or share one semver helper used by ship-pr.sh and apply-bump.sh
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-larch-log.sh:188-212
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale-run test depends on $_cpayload from the prior subtest Reordering or deleting the earlier block breaks this test with unclear failure Define payload inside the stale block or document the coupling explicitly
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: docs/run-logs.md (manifest.json section)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] New doc claims committed manifest status is always "in-progress". Other lifecycle docs describe partial/stalled manifest tagging under tmpdir-driven recovery; an absolute "always" can mislead readers if a non-in-progress snapshot were ever flushed. Soften to "normally" or enumerate exceptions and link to the manifest contract.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: docs/run-logs.md (manifest.json section, new status paragraph)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] New docs claim committed manifest status is always in-progress and done exists only post-merge in tmpdir. Contradicts many committed larch-logs/implement/*/manifest.json files with status done (e.g. larch-logs/implement/FA318108-514A-405E-B331-3664A952C94A/manifest.json:10); misleads consumers auditing the tree. Reword to match actual committed corpus and lifecycle (legacy done vs current intent), or document the transition explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: docs/run-logs.md:71-73
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress; adjacent line still says final run status; manifest subcommand allows status updates. Operator or test runs manifest --field status=done then commit; committed JSON shows done contradicting always in-progress. Rewrite to describe typical implement flush snapshots; allow exceptions; align line 71 wording.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New paragraph claims committed manifest status is always in-progress and done is never committed. Contradicts many existing committed larch-logs/implement/*/manifest.json files with status done; operators or tools may encode a false invariant. Reword to match observed committed data and SKILL/larch-log contracts, or narrow the claim to the intended lifecycle window.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: docs/run-logs.md:73
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Committed manifest status documented as always "in-progress" Readers infer committed status is a complete lifecycle truth; contradicts recovery paths that can set e.g. partial before a flush, so operational and audit conclusions about a run can be wrong Replace absolute "always" with accurate lifecycle wording; enumerate or defer to scripts/larch-log.md for committed vs tmpdir-only statuses
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/ship-pr.sh:1231-1235
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] semver_lt runs on new_version without the same strict semver regex used for origin. Malformed or empty NEW_VERSION can confuse the regression guard or trip brittle numeric compares under error-sensitive settings. Validate new_version with ^[0-9]+.[0-9]+.[0-9]+$ before semver_lt or skip correction when invalid.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.sh:397-421
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] rewrite_reasoning_new_version treats awk success as rewrite success even when the New version line never matched. Template drift leaves stale New version while bump and PR title use corrected semver; version-bump-reasoning batch can still lie. Verify corrected line exists after awk (grep/cmp) and return failure to trigger existing WARN path when rewrite was a no-op.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/test-larch-log.sh:188-214
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Stale-run regression covers sibling dirs under the same staging root but not symlink REPO_ROOT vs LARCH_LOG_REPO_ROOT mismatch from the plan rationale. Less lock-in on the exact prefix-strip bug class named in the implementation plan. Optional: add a symlinked-repo variant if that edge remains load-bearing.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/ship-pr.sh:1231-1234
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] semver_lt applied to classify NEW_VERSION without prior strict semver validation Malformed NEW_VERSION can break [[ numeric compares or error under set -e, derailing run_rebase_rebump Validate new_version with the same ^[0-9]+.[0-9]+.[0-9]+$ pattern (or skip regression logic) before semver_lt
- **Suggested revision**: Address the concern above.

