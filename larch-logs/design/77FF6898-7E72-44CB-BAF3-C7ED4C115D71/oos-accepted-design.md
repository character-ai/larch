### OOS_1: Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`
- **Description**: Assessment invokes bare `claude --print` instead of `python/cli.py agent launch-claude-subprocess`. Scenario: Assessment prompts skip the containment, timeout caps, timing sidecars, and stderr capture that `launch_claude_subprocess_main` provides elsewhere; failures are harder to diagnose in run logs
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/exec_issue_detail.py:105-108
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/5082
