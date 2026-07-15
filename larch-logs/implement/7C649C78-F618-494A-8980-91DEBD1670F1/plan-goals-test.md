## Goal
Implement issue #7340: [IMPLEMENTING] [FOLLOW-UP] Complete deferred /implement plan work.

## Implementation Plan
# Deferred /implement plan inventory

Parent tracking issue: #6999

## Deferred plan inventory

Untouched firm plan paths:
- `python/tests/core/test_kv_cli.py`
- `python/tests/design/test_design_router.py`
- `python/larch/design/design_summary.py`
- `python/larch/design/design_oos.py`
- `python/larch/design/design_step_log.py`
- `python/tests/design/test_design_step_log.py`
- `python/larch/implement/ship.py`
- `python/tests/implement/test_ship.py`
- `python/larch/state/session_env.py`
- `python/larch/git/push.py`
- `python/larch/git/pr.py`
- `python/larch/git/merge.py`
- `python/larch/git/git.py`
- `python/larch/implement/ci.py`
- `python/larch/git/pr_body.py`
- `python/larch/issue/deps_audit.py`
- `python/larch/state/admission.py`
- `python/larch/agents/_types.py`
- `python/larch/agents/_auth.py`
- `python/larch/agents/_ci_launcher.py`
- `python/larch/agents/_claude_runner.py`
- `python/larch/agents/_drafter.py`
- `python/larch/agents/_failure_diag.py`
- `python/larch/agents/_launch_failure.py`
- `python/larch/agents/_review_launcher.py`
- `python/larch/agents/_run_external.py`
- `python/larch/agents/agents.py`
- `python/tests/agents/test_agents.py`
- `skills/design/scripts/design-step3-mav.sh`
- `skills/implement/scripts/refresh-execution-issues.sh`
- `skills/implement/scripts/post-tracking-issue.sh`
- `skills/implement/scripts/step-18.sh`

Manifest todos left:
- Migrate the remaining plan-listed design, agent, ship, session, and Bash reader call sites to the shared codec.
- Replace the remaining private KEY=value emitters with logging_util.emit_kv and add their focused parity tests.

## Test plan
(no test plan section in plan-file)
