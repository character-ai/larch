### OOS_1: [OUT_OF_SCOPE] `_failed_reviewers` collector fallback may regress design `plan-review/round-N` layout
- **Description**: [OUT_OF_SCOPE] `_failed_reviewers` collector fallback may regress design `plan-review/round-N` layout. Scenario: The plan probes `round_dir.parent` when per-round `collector-results.env` is absent (implement layout). Design plan-review rounds live at `{tmpdir}/plan-review/round-N/` while `collector-results.env` sits at the design tmpdir root (`round_dir.parent.parent`, per existing tests). Rewriting `_failed_reviewers` without that walk can drop live collector failures from design final-summary `Reviewer slot failures` even though implement is the primary bug surface.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/progress_report.py:933-946
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_2: [OUT_OF_SCOPE] Standalone `/review` still cannot increment final-summary `Warnings` when `IMPLEMENT_TMPDIR` is unset
- **Description**: [OUT_OF_SCOPE] Standalone `/review` still cannot increment final-summary `Warnings` when `IMPLEMENT_TMPDIR` is unset. Scenario: `surface_warning` resolves `execution-issues.md` via `session_env_path` parent or `IMPLEMENT_TMPDIR` only. Standalone `/review --diff` runs without implement bootstrap, so dynamic-drop warnings from `_surface_dropped_reviewer_warning` can be computed but never reach operator-visible `Warnings` even after threshold fixes.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/review_tally.py:473-483
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Merging unrelated waterfall warnings into one semicolon-separated `WARN` value is broader than the dynamic-reviewer fix and changes the existing `WARN` contract.
- **Description**: [OUT_OF_SCOPE] Merging unrelated waterfall warnings into one semicolon-separated `WARN` value is broader than the dynamic-reviewer fix and changes the existing `WARN` contract.. Scenario: Exact-match `WARN` consumers can lose a single-condition signal or need new parsing even when the dynamic-drop warning path itself works.
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/agent_waterfall.py:1043-1050
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Preserve bounded dropped-slot diagnostics and commit them as new round artifacts.
- **Description**: [OUT_OF_SCOPE] Preserve bounded dropped-slot diagnostics and commit them as new round artifacts.. Scenario: The issue is already solved once dynamic reviewers count and warn. Adding `dropped-*-*.txt`, new run-log allowlists, and SECURITY.md guidance expands artifact surface without changing threshold math or warning behavior.
- **Reviewer**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/agent_waterfall.py:1023-1056
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

