Normalized aggregator output from the supplied reviewer slots. Positive verification notes (structure/correctness **FINDING_7** and **FINDING_8**) are omitted—they describe implemented behavior, not a fixable risk. Merged blocks follow first-seen order among retained issues.

### FINDING_1: Branch bundles Stage 5 with unrelated commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The PR/branch diff bundles Stage 5 hardening (`423c07a3e`) with #3212 cleanup, #3209 ship-pr rebase/fixup work, and larch-logs flushes. Reviewers cannot bisect or revert Stage 5 in isolation; CI/review failure on cleanup, rebump, or log commits blocks or misattributes the security hardening merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or strictly separate commits with a Stage-5-only review surface.
  - From cursor-specialist-testing-output.txt: Split/rebase PR to isolate 423c07a3e; run plan harness list on that commit alone before merge.

### FINDING_2: Duplicate CLAUDE_PLUGIN_ROOT relay harness setup in collect-findings tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Collector and wait relay harnesses duplicate the same `CLAUDE_PLUGIN_ROOT` tree setup (`skills/review/scripts/test-collect-findings.sh:2649-2730`). Future relay-path changes must be edited twice; easy to update one case and miss the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared `make_collect_findings_relay_harness` helper parameterized by stub script.

### FINDING_3: Duplicated BEL/ESC strip assertions in test-ship-pr harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: BEL/ESC strip assertions are duplicated across four new harness cases (mirroring T8). Assertion drift if one file changes grep flags or fixture bytes without updating the others.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional shared `assert_merged_capture_strips_c0_controls` helper sourced from one canonical test.

### FINDING_4: Inline `sanitize_diagnostic_line` wraps without shared relay helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Seven inline `sanitize_diagnostic_line` wraps with no shared relay helper (plan forbade new API). A future `larch_err` relay may copy `redact-secrets` only and skip sanitize, re-opening control-byte leakage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Maintain lib-quiet.md audit; consider `larch_err_relay_line` helper in a follow-up.

### FINDING_5: Missing test-ship-pr.md for append_tool_failure_local fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New `append_tool_failure_local` fallback relay coverage (`scripts/test-ship-pr.sh:6094-6122`) lacks the sibling `scripts/test-ship-pr.md` update required by plan acceptance. Future harness edits won't be discoverable; script-md-sibling convention drifts; reviewers miss merged `2>&1` and BEL/ESC contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test-ship-pr.md bullet documenting fallback forcing, fixture, and assertions (mirror other relay harness .md files).

### FINDING_6: No ancestor-race harness for `.completed` subtree
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.completed` ancestor guard shipped in `design-log-publish.sh` without a matching ancestor-race harness (plan only required render-cache and plan-review). Regression in pause `.completed` staging could slip past CI until a nested layout appears or allowlist changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add optional pause ancestor case or document intentional omission in test-design-log-publish.md.
  - From cursor-specialist-edge-cases-output.txt: Add a third ancestor-race case with pause REASON, step-* layout, merged 2>&1, and `.completed` ancestor `larch_err` substring.

### FINDING_7: Relay sanitization tests cover success path only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Relay sanitization tests cover `redact-secrets` success path only, not `||` fallback or no-redactor branches (`ship-pr.sh`, `collect-findings.sh`, `collect-agent-results.sh`). A partial edit could break fallback branches while primary-path harness stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one case per site with redact-secrets disabled or failing; assert BEL/ESC absent on merged 2>&1.

### FINDING_8: Fallback relay case runs outside `--section` gates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Fallback relay case runs outside `--section` gates on every sharded `test-ship-pr-*` invocation. Shard runtime grows and section targets no longer mean section-only coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document global execution in test-ship-pr.md or isolate into a dedicated make target.

### FINDING_9: Residual TOCTOU between ancestor check and `cp`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Residual TOCTOU remains between `design_publish_ancestor_within_root` (and related checks) and `cp` inside `design_publish_stage_file`. Per-file re-resolution closes the parent-directory race per plan but does not eliminate all staging races; a local racer may still replace file contents or leaf after checks pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (Inherent limitation; plan treats per-file re-resolution as closing the parent-directory race, not eliminating all staging races.)
  - From cursor-specialist-security-output.txt: Re-check `-L` and ancestor containment immediately before `cp` or use `O_NOFOLLOW` open from a verified directory.
  - From cursor-specialist-edge-cases-output.txt: Document as accepted residual window or add a final ancestor/leaf recheck immediately before `cp` if stricter closure is required.

### FINDING_10: Ancestor guard does not revalidate physical path / in-tree symlink swap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Ancestor guard permits in-tree parent symlinks; `rel`/allowlist are not revalidated against physical paths after `pwd -P`. An attacker with `DESIGN_TMPDIR` write who swaps an intermediate directory to a symlink to another in-tree location before staging may preserve allowlisted `rel` while `cp` pulls bytes from elsewhere under the root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Recompute `rel` from physical path after `pwd -P` and re-run allowlist checks before `cp`.

### FINDING_11: Cleanup may delete active sessions (top-level mtime only)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Cleanup prunes session trees by top-level mtime only, not newest in-tree activity (`skills/cleanup/scripts/cleanup.sh:39-43,81-85`). An active `/implement` or `/design` session can keep writing under a cache entry whose top-level directory is older than `LARCH_CLEANUP_RETENTION_DAYS`; `/cleanup` may delete the whole tree including secrets and `CMD_JSON` sidecars while Claude still runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restore descendant activity scanning or touch session roots on writes; avoid deleting when any descendant is newer than the cutoff; fail closed on `find` errors.

### FINDING_12: `sanitize_diagnostic_line` strips TAB from relayed diagnostics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Relay sanitization strips all `[:cntrl:]` including TAB (`scripts/lib-quiet.sh:86-88`). CI stderr with tab-aligned columns loses alignment in `larch_err` replay lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document in lib-quiet.md or narrow `tr` delete set if tab preservation is required.

### FINDING_13: [OUT_OF_SCOPE] Pre-rebase fixup commits all tracked dirty paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Pre-rebase `git add -u` fixup in `scripts/ship-pr.sh:934-951` / `2853-2868` commits all tracked dirty paths (#3209). Unrelated tracked edits during CI rebase—or tracked files with secrets modified during the run—can be swept into `chore: pre-rebase working-tree fixup` and pushed on the implement PR without redaction. Not Stage 5 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Narrow staging to known paths or document operator precondition.
  - From cursor-specialist-security-output.txt: Limit fixup to an allowlisted path set, run redact-secrets on staged content, or stall when dirty paths are outside that set.

### FINDING_14: [OUT_OF_SCOPE] Branch diff noise for Stage 5 reviewers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Three of five commits (#3212, #3209, larch-logs) and related harness/docs churn are outside the Stage 5 hardening plan. Increases review/merge surface for work labeled “Piece 5 of 5”; plan fidelity for STA-3120 Piece 5 should be judged on `423c07a3e`, not full `main..HEAD`. Large rebump/cleanup test blocks add CI time/flake risk when bisecting Stage 5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Consider splitting or rebasing so the hardening PR is reviewable in isolation.
  - From cursor-specialist-plan-fidelity-output.txt: None for Piece 5 code; consider splitting unrelated fixes into separate PRs if reviewers need a plan-pure diff.
  - From cursor-specialist-testing-output.txt: Keep rebump work in its own PR or commit range.
  - From cursor-specialist-testing-output.txt: Exclude cleanup hang-fix tests from Stage 5 PR via rebase/split.

### FINDING_15: [OUT_OF_SCOPE] Cleanup retention uses top-level mtime only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: #3212 replaces descendant activity scan with top-level `find … -mtime +N` only. Directories with stale top-level mtime but recent deep files—or active runs that only touch deep paths—may be deleted earlier than before, depending on filesystem parent-mtime behavior. Out of scope for Stage 5; verify #3212 acceptance separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: If that scenario matters in production, either restore a bounded descendant activity probe for directories only, or document that operators must touch the session root periodically; `SECURITY.md` already documents the top-level-mtime tradeoff.
  - From cursor-specialist-edge-cases-output.txt: Document operator discipline or restore descendant activity scan if false deletion is observed in production.

### FINDING_16: [OUT_OF_SCOPE] `review-and-fix.sh` follow-up uses `git add -A`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Follow-up commit uses `git add -A` (`skills/review-and-fix/scripts/review-and-fix.sh:441-502`), which can stage untracked files (e.g. `.env`) left between commits, not only tracked residue from the first commit. From #3209 / dirty-tree work, not Stage 5 hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Prefer `git add -u` (or an explicit path list) for the follow-up commit if only tracked residue should be captured.
  - From cursor-specialist-security-output.txt: Use `git add -u` for follow-up or path allowlist (separate change).

### FINDING_17: [OUT_OF_SCOPE] Cleanup swallows `find` enumeration errors
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `find` enumeration errors are swallowed (`skills/cleanup/scripts/cleanup.sh:43,85` and related). Permission denied or I/O failure can make cleanup exit 0 with zero removals while stale secrets persist—looks like successful no-op cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Consider surfacing find failures on stderr and non-zero exit when enumeration fails.
  - From cursor-specialist-edge-cases-output.txt: Surface find failures on stderr and exit non-zero when enumeration fails (separate from Stage 5).

### FINDING_18: [OUT_OF_SCOPE] SECURITY.md still references breadcrumbs helper
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Operator diagnostic section (`SECURITY.md:211-214`) still references breadcrumbs helper for design-log publish redaction—misleading for auditors reading the publication redaction path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update wording to name design-log-publish.sh / larch-log.sh pipelines directly in a follow-up doc fix.

### FINDING_19: [OUT_OF_SCOPE] Plan-complete note: `.completed` harness optional
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Ancestor guard for `.completed/` is implemented and documented; plan only required render-cache and plan-review harnesses—no dedicated ancestor-race harness is a plan-complete omission, not a fidelity gap. Optional future harness could mirror other subtrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot-specific fix beyond plan-fidelity acknowledgment; overlaps informational with **FINDING_6** if a harness is desired later.)
