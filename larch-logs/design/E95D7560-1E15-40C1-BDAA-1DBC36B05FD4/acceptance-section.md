## Acceptance

- `launch_codex_exec_main` fast-fails on a Codex `exec_command` policy rejection: it detects both the `exec_command failed` family and the `blocked by policy` / `Rejected(` family in the events stream, terminates the child, writes a `policy-rejection` diagnostic to `${output}.diag`, returns `LAUNCHER_EXIT=1` (not `124`), and skips the auth / unclassified-empty retry branches.
- Unrelated event text matching only one token family does not trigger fast-fail.
- The Codex lint-fix tier (`_run_codex`) appends a Codex-only edit-only appendix bound to the `run_lint_fix` `site`: it tells Codex to make file edits only, forbids Codex-side `exec_command` / shell / ad-hoc `/tmp` verification, and leaves verification to the orchestrator. The shared `_compose_prompt` body and the Claude/Cursor tiers stay unchanged.
- `_build_codex_argv` adds no session-root / `implement_tmpdir` `--add-dir`; only the existing `run_dir` and repo-root grants remain.
- `_RUN_EXTERNAL_TIMEOUT` stays `300`. The lint-fix budget, tier order, and the `dispatch-failed` to `main-agent-required` mapping are unchanged.
- Read-only Codex lanes (research, validation, voter, judge, OOS-combine, design drafter) and the other workspace-write callers (plan auto-fix, review-and-fix) are unchanged except for benefiting from the shared launcher fast-fail when an events stream is present.
- `SECURITY.md` documents the non-retryable policy-rejection fast-fail, the task-split verification model, and that Codex lint-fix receives no session-root write grant.
- Regression coverage added or updated: `python/test_agents.py` (fast-fail plus no-retry), `python/test_checks.py` (Codex appendix, `_run_codex` `site` argument, all four existing call sites updated, no session-root add-dir), and `scripts/test-prompt-template-invariants.sh` (combined Codex prompt markers plus the negative shared-prompt guard).
- `make py-lint`, `make py-test`, and `make lint` pass.
