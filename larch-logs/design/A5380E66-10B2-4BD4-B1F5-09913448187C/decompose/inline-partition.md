## Pieces

### Piece 1: Codec + CLI foundation
- Scope: `python/larch/io.py`, `python/larch/core/kv_cli.py`, `python/larch/core/logging_util.py`, `python/tests/test_larch_io.py`, `python/tests/core/test_kv_cli.py`, `python/tests/core/test_logging_util.py`
- Firm-headings: python/larch/io.py, python/tests/test_larch_io.py, python/larch/core/kv_cli.py, python/tests/core/test_kv_cli.py, python/larch/core/logging_util.py, python/tests/core/test_logging_util.py
- Acceptance: focused pytest modules for io, kv_cli, and logging_util pass; existing callers remain byte-compatible; `--match first|last` forwarded correctly; `make py-lint-checks-fast` and pyright pass
- Dependencies: none
- Size estimate: ~100 diff lines

### Piece 2: Emit unification (delete private wrappers)
- Scope: `python/larch/git/push.py`, `python/larch/git/pr.py`, `python/larch/git/pr_body.py`, `python/larch/git/merge.py`, `python/larch/git/git.py`, `python/larch/implement/ci.py`, `python/larch/state/admission.py`, `python/larch/issue/deps_audit.py`, `python/larch/agents/_types.py`, `python/larch/agents/_auth.py`, `python/larch/agents/_ci_launcher.py`, `python/larch/agents/_claude_runner.py`, `python/larch/agents/_drafter.py`, `python/larch/agents/_failure_diag.py`, `python/larch/agents/_launch_failure.py`, `python/larch/agents/_review_launcher.py`, `python/larch/agents/_run_external.py`, `python/larch/agents/agents.py`, `python/tests/agents/test_agents.py`
- Firm-headings: python/larch/git/push.py, python/larch/git/pr.py, python/larch/git/pr_body.py, python/larch/git/merge.py, python/larch/git/git.py, python/larch/implement/ci.py, python/larch/state/admission.py, python/larch/issue/deps_audit.py, python/larch/agents/_types.py, python/larch/agents/_auth.py, python/larch/agents/_ci_launcher.py, python/larch/agents/_claude_runner.py, python/larch/agents/_drafter.py, python/larch/agents/_failure_diag.py, python/larch/agents/_launch_failure.py, python/larch/agents/_review_launcher.py, python/larch/agents/_run_external.py, python/larch/agents/agents.py, python/tests/agents/test_agents.py
- Acceptance: no `_emit_kv` wrapper in scope files; all call sites route through `logging_util.emit_kv`; pyright and `make py-lint-checks-fast` pass; git and agents harnesses pass
- Dependencies: blocked-by Piece 1
- Size estimate: ~200 diff lines

### Piece 3: Python read migration
- Scope: `python/larch/design/design_core.py`, `python/larch/design/design_router.py`, `python/larch/design/design_publish.py`, `python/larch/design/design_pause.py`, `python/larch/design/design_summary.py`, `python/larch/design/design_oos.py`, `python/larch/design/design_terminal.py`, `python/larch/design/clarify.py`, `python/larch/implement/preflight.py`, `python/larch/state/session_env.py`, `python/larch/run_context.py`, `python/larch/state/ship_state.py`, `python/tests/state/test_session_env.py`
- Firm-headings: python/larch/design/design_core.py, python/larch/design/design_router.py, python/larch/design/design_publish.py, python/larch/design/design_pause.py, python/larch/design/design_summary.py, python/larch/design/design_oos.py, python/larch/design/design_terminal.py, python/larch/design/clarify.py, python/larch/implement/preflight.py, python/larch/state/session_env.py, python/tests/state/test_session_env.py
- Acceptance: no ad-hoc `split("=", 1)` env loops in scope files; existing design and implement harnesses pass; duplicate-policy behavior pinned with new tests; `make py-lint-checks-fast` and pyright pass
- Dependencies: blocked-by Piece 1
- Size estimate: ~400 diff lines

### Piece 4: Bash funnel + adoption-ratchet lint
- Scope: `scripts/sessionstart-health.sh`, `scripts/hook-deny-run-in-background.sh`, `skills/design/scripts/design-step3-mav.sh`, `skills/implement/scripts/refresh-execution-issues.sh`, `skills/implement/scripts/post-tracking-issue.sh`, `skills/implement/scripts/step-0-bootstrap.sh`, `skills/implement/scripts/step-18.sh`, `python/larch/lint/lint_kv_codec.py`, `python/kv-codec-baseline.json`, `python/tests/lint/test_lint_kv_codec.py`, `python/larch/cli.py`, `python/tests/test_cli.py`, `Makefile`, `docs/linting.md`
- Firm-headings: scripts/sessionstart-health.sh, scripts/hook-deny-run-in-background.sh, skills/design/scripts/design-step3-mav.sh, skills/implement/scripts/refresh-execution-issues.sh, skills/implement/scripts/post-tracking-issue.sh, skills/implement/scripts/step-0-bootstrap.sh, skills/implement/scripts/step-18.sh, python/larch/lint/lint_kv_codec.py, python/kv-codec-baseline.json, python/tests/lint/test_lint_kv_codec.py, python/larch/cli.py, python/tests/test_cli.py, Makefile, docs/linting.md
- Acceptance: `make lint-kv-codec` and `make test-lint-kv-codec` pass; `make py-lint-checks-fast` includes the new lint; baseline contains only grandfathered rows with reasons; affected Bash harnesses pass; docs document scope, exclusions, baseline schema, and Makefile targets
- Dependencies: blocked-by Piece 1, Piece 2, Piece 3
- Size estimate: ~250 diff lines
