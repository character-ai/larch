### OOS_2: Live Step 3 composite still skips FINDING_5 pre-arm cleanup
- **Description**: Live Step 3 composite still skips FINDING_5 pre-arm cleanup. Scenario: `checks_commit_route_main` arms `implement-step3-checks` on the production `/implement` Step 3 path but never deletes stale `.completed/step-3-terminal` or `bg-poll-guard-probe-denials.step-3-terminal.count` before writing `.bg-wait-active`. `run-step-checks.sh` and `design_core._bg_wait_marker_context` both clear these; a leftover sentinel makes `marker_step_completed` treat the new wait as already finished and hook denial can stay off on resume.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:896-898
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6305
