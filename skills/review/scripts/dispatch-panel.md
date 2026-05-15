# dispatch-panel.sh Contract

`skills/review/scripts/dispatch-panel.sh` plans and launches `/review` reviewer slots.

It launches Cursor and Codex specialists through `scripts/launch-review.sh` when those tools are available. When a tool is unavailable, its specialist slots are skipped entirely (no Claude substitution for partial outages). Claude is never used as a code reviewer. When both external tools are down, no reviewer slots are launched, `SLOT_COUNT=0` is emitted, and `PANEL_MODE=both-down` is set so voting uses the no-external-reviewer shortcut.

Pass `--panel hard` for the full specialist topology: structure, correctness, testing, security, edge-cases, and plan-fidelity for each available external tool. Pass `--panel simple` for a reduced topology: Cursor `edge-cases` and Codex `structure`. In simple mode `plan-fidelity` is added for each available external tool only when `--plan-file` names an existing file.

`PANEL_MODE` remains availability-only (`normal|both-down`) because voting uses `both-down` to choose the no-external-reviewer shortcut. `PANEL_SHAPE=simple|hard` reports the selected topology shape.

Pass `--description-text` to thread the user's description through to both external and Claude reviewer prompts in description mode.

Pass `--session-env-path` in nested `/implement` runs. `SESSION_ENV_PATH` is exported after argument parsing so `launch-review.sh` subprocesses inherit it; `timing-ledger.sh record-vendor-task` resolves the per-run timing ledger via the `SESSION_ENV_PATH` fallback, enabling Vendor Task Averages in timing reports. Launch wrapper stdout/stderr is captured to `$REVIEW_TMPDIR/dispatch-<tool>-<slot>.log`; a non-zero launch exit appends that captured content verbatim via `scripts/append-tool-failure.sh` under `External Reviewer Issues`. The log path resolver uses `LARCH_EXECUTION_ISSUES_LOG` when set; otherwise it falls back through `$(dirname "$SESSION_ENV_PATH")/execution-issues.md`, `$IMPLEMENT_TMPDIR/execution-issues.md`, then `$REVIEW_TMPDIR/execution-issues.md`.

Use `--launch-review <path>` in harnesses to override the external reviewer launcher. The default remains `${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh`.

Stdout is `KEY=value` only: `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `PANEL_SHAPE`, `SLOT_COUNT`, `PANEL_MANIFEST`, and `DISPATCH_OK`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Harness: `skills/review/scripts/test-dispatch-panel.sh`, wired through `make test-dispatch-panel`.
