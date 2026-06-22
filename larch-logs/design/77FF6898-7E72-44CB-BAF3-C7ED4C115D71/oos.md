### OOS_1: Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`
- **Description**: Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`. Scenario: Assessment prompts skip the containment, timeout caps, timing sidecars, and stderr capture that `launch_claude_subprocess_main` provides elsewhere; failures are harder to diagnose in run logs
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/exec_issue_detail.py:105-108
- **Phase**: design




Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: `render_issue_detail_block` should short-circuit assessment when `listing_degraded=True`
- **Description**: `render_issue_detail_block` should short-circuit assessment when `listing_degraded=True`. Scenario: Header-only degraded output has empty detail tuples; calling Haiku anyway adds up to two subprocess attempts on a path that intentionally has no rows to assess. Harm is latency only; rows still render correctly.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/exec_issue_detail.py:109-122
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_3: `IssueEvent` / `IssueDetail` carry unused `label` and `description` fields
- **Description**: `IssueEvent` / `IssueDetail` carry unused `label` and `description` fields. Scenario: Rendering uses `display_text` and `count`; extra fields add dataclass surface without a call-site consumer.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/exec_issue_detail.py:44-47
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

