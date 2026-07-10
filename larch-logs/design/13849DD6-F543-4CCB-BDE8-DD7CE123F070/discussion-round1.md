## Decision 1: PID-residual scope
- **Question**: How much should `step0-abort-cleanup` clean up?
- **Resolution**: Reap all three PID files: `current-design-env-$PPID.sh` (dangling symlink), `design-run-$PPID.sh` (launcher), and `step0-parsed-$PPID.env`.
- **Source**: user

## Decision 2: Banner/log fix approach
- **Question**: Parameterize `--reason`/`--tool` or add a separate postpone verb?
- **Resolution**: Parameterize `step0_abort_cleanup_main` with optional `--reason <text>` and `--tool <name>`, both defaulting to today's degraded-tools strings for backward compat.
- **Source**: user

## Decision 3: Step 6 scope
- **Question**: Fix only the abort path or also fix Step 6 happy-path cleanup?
- **Resolution**: Also extend `step6_cleanup_core` to reap PID residuals (same three files) after the tmpdir is removed.
- **Source**: user
