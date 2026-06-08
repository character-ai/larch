### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-skill-md-flag-signature.sh:74-91; scripts/test-lint-skill-md-flag-signature.sh:121-146; plan.txt:86
- **Concern**: [SCOPE-REDUCTION] Plan retargets shell-only flag-signature fixtures to python/cli.py without changing the linter resolver. Scenario: The resolver only inspects */scripts/*.sh tokens, so a fixture using python3 .../cli.py session write-run-params is ignored; existing assert_lint_fails_for cases then fail or lose verification, blocking make lint
- **Proposed resolution**: Do not point this shell-linter fixture at the Python CLI unless the linter gains a session-verb metadata source; minimum-change fix is to replace the retired write-run-params fixture with a non-retired shell fixture and cover write-run-params flags in test_session_env.py

### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:121
- **Concern**: [SCOPE-REDUCTION] Stale-reference sweep says ALL tracked files even though retired-script lint excludes larch-logs and CHANGELOG. Scenario: Implementer may churn historical larch-logs references that are intentionally excluded by python/migration_lint.py and docs/python-migration.md, creating unnecessary scope and merge risk
- **Proposed resolution**: Limit the sweep to lint-retired-scripts scanned files: exclude larch-logs, CHANGELOG.md, and the manifest itself

### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-finalize-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:628-631 scripts/cleanup-tmpdir.sh:27-28 plan.txt:23-25 plan.txt:64-65
- **Concern**: [SCOPE-REDUCTION] Single shared cache_sessions_root() cannot satisfy both consumers without picking a semantics winner. Scenario: Plan moves cache_sessions_root into session_env as the sole owner (plan.txt:64-65) while requiring is_allowed_session_tmpdir to match cleanup-tmpdir.sh (plan.txt:23). Today bash uses ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions (cleanup-tmpdir.sh:27-28) but finalize uses absolute-XDG-only else Path.home()/.cache (finalize.py:628-631). Unifying on either side changes cleanup-tmpdir parity or ship teardown/_tmpdir_under_allowed_root allowlists (ship.py:1051-1058)
- **Proposed resolution**: Keep two explicit helpers in session_env.py (e.g. cleanup_cache_sessions_root mirroring bash expansion vs finalize_cache_sessions_root mirroring finalize.py:628-631) or document one canonical function plus a thin bash-parity wrapper; pin both with targeted pytest cases (relative XDG, empty HOME) before deleting cleanup-tmpdir.sh
