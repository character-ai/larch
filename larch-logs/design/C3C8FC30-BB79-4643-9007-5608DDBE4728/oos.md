### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:104-196; python/larch/design/design_lifecycle.py:172-196; python/larch/issue/oos_filer.py:53-100
- **Concern**: [SCOPE-REDUCTION] The plan adds a second label-only retry state machine and durable cross-session sidecars. Scenario: The MVP already has to add priority labeling and a backlog section. This retry plumbing expands the surface area into new prepare/annotate actions, cache restore logic, and extra completion rules that are not needed to satisfy the stated feature
- **Proposed resolution**: Remove the label-only retry and durable sidecar branches unless a concrete correctness failure requires them. Keep the change to same-run filing-time labeling plus backlog reporting


Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_1: Cross-session label-retry cache keys are issue-number-only.
- **Description**: Cross-session label-retry cache keys are issue-number-only.. Scenario: `~/.cache/larch/design-oos-filed/<issue>.*` sidecars can collide across repos sharing a numeric issue id, restoring another repo's pending/combined/sentinel state.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:97-100
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Backlog section ignores pre-existing open correctness OOS without `oos-correctness`
- **Description**: [OUT_OF_SCOPE] Backlog section ignores pre-existing open correctness OOS without `oos-correctness`. Scenario: The new `## High-risk OOS Backlog` filters on the label this MVP adds at filing time. Open `[OOS]` issues filed before the change stay invisible even when bodies carry `Focus area: correctness`, so `/analyze-issues` cannot surface the defer-to-fix latency the issue targets for historical backlog.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_issues.py
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Label-only success does not refresh the main cross-session sentinel cache
- **Description**: [OUT_OF_SCOPE] Label-only success does not refresh the main cross-session sentinel cache. Scenario: After durable label-only retry succeeds, pending sidecars clear but the plan does not require `_sync_cross_session_cache()` on `annotate-label-complete`. Later sessions depend on failure-time sentinel sync; if only pending/combined sidecars were written, a finished run may still miss cache refresh.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] `issue create-one` may still drop `--label` when `_valid_labels` search lags create
- **Description**: [OUT_OF_SCOPE] `issue create-one` may still drop `--label` when `_valid_labels` search lags create. Scenario: Even with lazy `gh label create --force`, `_valid_labels()` uses `gh label list --search` and can WARN-skip a freshly created label. The plan mitigates with a follow-up `gh issue edit --add-label`, but a create path that omits the edit on duplicate-only matches could still file unlabeled if both calls fail silently.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py:335-348
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_5: Durable label-retry sidecars are keyed only by issue number
- **Description**: Durable label-retry sidecars are keyed only by issue number. Scenario: `~/.cache/larch/design-oos-filed/<issue>.*` matches today's sentinel cache shape. Issue numbers are repo-local; the same numeric id in another repo can restore another repo's pending/combined/sentinel bundle and mis-apply `oos-correctness` labels.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

