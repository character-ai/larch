### OOS_1: [OUT_OF_SCOPE] Pre-commit `lint-bg-wait-writer-parity` `files:` glob skips Python-only writer edits
- **Description**: [OUT_OF_SCOPE] Pre-commit `lint-bg-wait-writer-parity` `files:` glob skips Python-only writer edits. Scenario: The hook triggers only on `^skills/(design|implement|review|review-and-fix)/`. This plan’s main writer move is `python/larch/implement/bg_wait.py` plus lint-module edits; those paths can merge without running the parity lint unless pytest/CI executes the new repo-root acceptance test every time.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:674-679
- **Phase**: design



### OOS_2: Live Step 3 composite still skips FINDING_5 pre-arm cleanup
- **Description**: Live Step 3 composite still skips FINDING_5 pre-arm cleanup. Scenario: `checks_commit_route_main` arms `implement-step3-checks` on the production `/implement` Step 3 path but never deletes stale `.completed/step-3-terminal` or `bg-poll-guard-probe-denials.step-3-terminal.count` before writing `.bg-wait-active`. `run-step-checks.sh` and `design_core._bg_wait_marker_context` both clear these; a leftover sentinel makes `marker_step_completed` treat the new wait as already finished and hook denial can stay off on resume.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_commit_route.py:896-898
- **Phase**: design



