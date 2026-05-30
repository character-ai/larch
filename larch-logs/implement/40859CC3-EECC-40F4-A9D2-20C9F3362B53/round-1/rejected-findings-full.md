### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Branch bundles Stage 5 with unrelated commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The PR/branch diff bundles Stage 5 hardening (`423c07a3e`) with #3212 cleanup, #3209 ship-pr rebase/fixup work, and larch-logs flushes. Reviewers cannot bisect or revert Stage 5 in isolation; CI/review failure on cleanup, rebump, or log commits blocks or misattributes the security hardening merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or strictly separate commits with a Stage-5-only review surface.
  - From cursor-specialist-testing-output.txt: Split/rebase PR to isolate 423c07a3e; run plan harness list on that commit alone before merge.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Ancestor guard does not revalidate physical path / in-tree symlink swap
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Ancestor guard permits in-tree parent symlinks; `rel`/allowlist are not revalidated against physical paths after `pwd -P`. An attacker with `DESIGN_TMPDIR` write who swaps an intermediate directory to a symlink to another in-tree location before staging may preserve allowlisted `rel` while `cp` pulls bytes from elsewhere under the root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Recompute `rel` from physical path after `pwd -P` and re-run allowlist checks before `cp`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `sanitize_diagnostic_line` strips TAB from relayed diagnostics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Relay sanitization strips all `[:cntrl:]` including TAB (`scripts/lib-quiet.sh:86-88`). CI stderr with tab-aligned columns loses alignment in `larch_err` replay lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document in lib-quiet.md or narrow `tr` delete set if tab preservation is required.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicate CLAUDE_PLUGIN_ROOT relay harness setup in collect-findings tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Collector and wait relay harnesses duplicate the same `CLAUDE_PLUGIN_ROOT` tree setup (`skills/review/scripts/test-collect-findings.sh:2649-2730`). Future relay-path changes must be edited twice; easy to update one case and miss the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared `make_collect_findings_relay_harness` helper parameterized by stub script.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicated BEL/ESC strip assertions in test-ship-pr harnesses
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: BEL/ESC strip assertions are duplicated across four new harness cases (mirroring T8). Assertion drift if one file changes grep flags or fixture bytes without updating the others.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional shared `assert_merged_capture_strips_c0_controls` helper sourced from one canonical test.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Inline `sanitize_diagnostic_line` wraps without shared relay helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Seven inline `sanitize_diagnostic_line` wraps with no shared relay helper (plan forbade new API). A future `larch_err` relay may copy `redact-secrets` only and skip sanitize, re-opening control-byte leakage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Maintain lib-quiet.md audit; consider `larch_err_relay_line` helper in a follow-up.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: No ancestor-race harness for `.completed` subtree
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `.completed` ancestor guard shipped in `design-log-publish.sh` without a matching ancestor-race harness (plan only required render-cache and plan-review). Regression in pause `.completed` staging could slip past CI until a nested layout appears or allowlist changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add optional pause ancestor case or document intentional omission in test-design-log-publish.md.
  - From cursor-specialist-edge-cases-output.txt: Add a third ancestor-race case with pause REASON, step-* layout, merged 2>&1, and `.completed` ancestor `larch_err` substring.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Relay sanitization tests cover success path only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Relay sanitization tests cover `redact-secrets` success path only, not `||` fallback or no-redactor branches (`ship-pr.sh`, `collect-findings.sh`, `collect-agent-results.sh`). A partial edit could break fallback branches while primary-path harness stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one case per site with redact-secrets disabled or failing; assert BEL/ESC absent on merged 2>&1.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Fallback relay case runs outside `--section` gates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Fallback relay case runs outside `--section` gates on every sharded `test-ship-pr-*` invocation. Shard runtime grows and section targets no longer mean section-only coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document global execution in test-ship-pr.md or isolate into a dedicated make target.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Residual TOCTOU between ancestor check and `cp`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Residual TOCTOU remains between `design_publish_ancestor_within_root` (and related checks) and `cp` inside `design_publish_stage_file`. Per-file re-resolution closes the parent-directory race per plan but does not eliminate all staging races; a local racer may still replace file contents or leaf after checks pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: (Inherent limitation; plan treats per-file re-resolution as closing the parent-directory race, not eliminating all staging races.)
  - From cursor-specialist-security-output.txt: Re-check `-L` and ancestor containment immediately before `cp` or use `O_NOFOLLOW` open from a verified directory.
  - From cursor-specialist-edge-cases-output.txt: Document as accepted residual window or add a final ancestor/leaf recheck immediately before `cp` if stricter closure is required.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

