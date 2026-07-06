## Decision 1: TemporaryDirectory in lint scope
- **Question**: Should `tempfile.TemporaryDirectory` (context-managed, auto-cleaned) be flagged by the new lint?
- **Resolution**: Yes. Auto-cleanup removes the leak risk, but creation still fails on a malformed `$TMPDIR`. Include it alongside `mkstemp`, `mkdtemp`, and `NamedTemporaryFile`.
- **Source**: user

## Decision 2: Fix vs. baseline categorization
- **Question**: Which of the 37 sites should have `dir=` threaded in, and which should be baselined with a reason?
- **Resolution**: 15 sites are fixable (a run-scoped tmpdir is accessible). 22 sites should be baselined with reasons.
  - **Fix** (thread `dir=`): `design/design_step0.py:338,454` (design_tmpdir param), `design/design_step0_env.py:370`, `design/design_log_publish_flow.py:310`, `design/design_pause.py:354`, `review/review_collect.py:114` (thread review_tmpdir), `review/review_tally.py:1240` (thread review_tmpdir), `review/review_aggregate.py:187` (thread review_tmpdir), `review/compose_review.py:171,335` (read REVIEW_TMPDIR env), `review/plan_review_tally.py:642` (use design_tmpdir), `report/run_log_flush.py:883,884` (thread --tmpdir param to capture_transcript_main), `report/run_log_batch.py:307` (thread log_root.parent to _redact_to_temp), `implement/checks_run_relevant.py:1002` (thread canonical_tmp to _run_contains_pin_phase).
  - **Baseline** (reason-bearing JSON): `agents/_ci_launcher.py:242,343,802` (external tool auth/config home, must be system-accessible), `agents/_claude_runner.py:150` (subprocess stdin/stdout piping TemporaryDirectory), `agents/_drafter.py:255` (Codex exec home TemporaryDirectory), `agents/_review_launcher.py:890` (Cursor config dir), `git/gh.py:214,1436,1645` (gh --body-file staging, deleted in finally), `git/git.py:548` (commit message staging, transient git utility), `core/forked_repo.py:397` (mirror clone workspace), `lint/lint_mermaid_fences.py:274` (standalone linter TemporaryDirectory, auto-cleaned), `issue/audit_runs.py:1097` (gh body staging), `issue/deps_audit.py:775` (gh --body-file staging), `issue/issue_create.py:522,711` (gh issue create/API body staging), `rendering/_rendering_generators.py:367` (standalone generator workspace), `report/exec_issue_detail.py:438` (Claude subprocess TemporaryDirectory, auto-cleaned), `report/report_tokens_cli.py:172` (standalone report, creates own session tmpdir), `report/report_tokens_render.py:222` (fallback cache root), `research/research_eval.py:838` (standalone eval, creates own work_dir), `release/release_finish.py:108` (release utility, no session tmpdir).
- **Source**: codebase

## Decision 3: Lint format and CI integration
- **Question**: How should the lint baseline and CI integration work?
- **Resolution**: Follow the `lint_subprocess_via_runner.py` pattern: AST-based module at `python/larch/lint/lint_tempfile_dir.py`, JSON baseline at `python/tempfile-dir-baseline.json`, plugged into `py-lint-checks-fast` via `$(PYTHON) python/cli.py lint tempfile-dir`, `regen-tempfile-dir-baseline` Makefile target, tests at `python/tests/lint/test_lint_tempfile_dir.py`.
- **Source**: codebase
