# launch-cursor-implement.sh

**Purpose**: Spawn the Cursor implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `cursor agent -p --force --trust` (parallel to `launch-review.sh --tool cursor`) but redirects the wrapper's human-readable progress lines to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only: `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; any progress text leaking to stdout would be parsed as garbage.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see what went wrong.
- Cursor stdout is captured to `--transcript-path` via `run-external-agent.sh --capture-stdout-only`, with stderr routed to `<transcript>.diag` so Cursor JSON remains parseable. This file may grow large; it is intentionally NOT echoed to stdout.
- The Cursor command includes `--output-format json`; after the run, the wrapper best-effort parses `.usage` and records a `cursor_implement` vendor total via `scripts/token-ledger.sh`. Missing `jq`, malformed JSON, or absent usage is silent and non-fatal.
- Before token-ledger parsing or spawning Cursor, the wrapper rehydrates token context from `IMPLEMENT_TMPDIR` when present: `$IMPLEMENT_TMPDIR/session-id` overwrites any stale `LARCH_TOKEN_SESSION_ID`, and `$IMPLEMENT_TMPDIR/claude-source.env` becomes `LARCH_CLAUDE_SOURCE_FILE`.
- The launcher sources `scripts/lib-cursor-launcher-common.sh` for shared Cursor model-args hydration, auth-argv setup, outer `.meta` appends, and inner-sentinel promotion (canonical `*_append_outer_meta` and `*_promote_inner_done` bodies live in `scripts/lib-external-launcher-common.sh`).
- The launcher writes the composed prompt to `${TRANSCRIPT_PATH}.prompt` before launch, appends `OUTER_LAUNCHER`, `OUTER_LAUNCHER_PROMPT_FILE`, and `OUTER_LAUNCHER_WORKDIR` to `${TRANSCRIPT_PATH}.meta` after the inner wrapper exits, and uses `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done` so `${TRANSCRIPT_PATH}.done` is published only after token-ledger post-processing completes. These keys are a forward-compatibility hook; the collector does not currently replay Cursor implementer launches.
- The wrapper emits one best-effort `scripts/timing-ledger.sh record-vendor-task` row on the normal and Cursor-auth-preflight failure paths. `TIMING_START_S` is captured at wrapper entry after argv validation and before preflight, so preflight failures produce duration≈0 incomplete rows. `--timing-task-kind <kind>` defaults to `cursor-implement`; timing failures are silent and never affect the KEY=VALUE stdout envelope or wrapper exit behavior. **Validation**: when `--timing-task-kind` is supplied via the CLI, the value must be non-empty and must not begin with `--`; otherwise the launcher exits 2 with `--timing-task-kind requires a non-empty, non-flag-like value` on stderr (issue #1480 defense-in-depth against argv-shape collapse from a broken env-var-prefix expansion in the caller). Env-derived `LARCH_TIMING_TASK_KIND` that is empty or starts with `--` silently falls back to the per-launcher default (for example, `cursor-implement`). The CLI `--timing-task-kind` flag still hard-rejects empty / flag-shaped values with exit 2.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Cursor subprocess's exit code is reported via `LAUNCHER_EXIT=<int>` on stdout; the dispatcher decides whether that constitutes failure.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Cursor's `--workspace "$PWD" --trust` posture grants implicit write access to absolute paths passed via `--manifest-path` and `--qa-pending-path` (which today live under `--tmpdir`, typically rooted at `~/.cache/larch/sessions/...` per the `step2-implement.sh` convention). No analogous `--add-dir` flag is required (and Cursor CLI does not expose one). If a future Cursor release introduces a tighter sandbox, this contract must be revisited and the launcher updated to grant the manifest parent explicitly.
- Composes Cursor's prompt by concatenating `--agent-prompt` (`agents/cursor-implementer.md`) with this-invocation parameters and an optional resume block. Composition is in shell, not in agent-side prose, so the contract is mechanically inspectable.
- Reuses `agent-model-args.sh --tool cursor --with-effort`, reads its line-token stdout into a Bash array, then wraps the composed prompt with `cursor-wrap-prompt.sh` so Cursor max-mode is enforced exactly like the review path.
- The actual Cursor spawn is wrapped with `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and auth-startup outer retry loop. Retry classification checks both `SIDECAR_LOG` and `${TRANSCRIPT_PATH}.diag`, because `run-external-agent.sh --capture-stdout-only` routes Cursor stderr to the transcript diagnostic sidecar. Before the auth-retry loop the launcher calls `cursor_launcher_setup_private_config_dir` (from `lib-cursor-launcher-common.sh`) to export a fresh private `CURSOR_CONFIG_DIR` directory (seeded from `~/.cursor/cli-config.json` when present), eliminating the `cli-config.json` rename race when multiple implement invocations run in parallel; `cursor_launcher_cleanup_private_config_dir` runs inline after the loop.
- When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `SIDECAR_LOG` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including a verdict derived from both `SIDECAR_LOG` and `${TRANSCRIPT_PATH}.diag` plus the final auth-loop attempt count.
- Cursor argv shape is pinned to `scripts/launch-review.sh --tool cursor`: `cursor agent -p --force --trust --output-format json ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} --workspace "$PWD" "$WRAPPED_PROMPT"`. There is intentionally **no** `--api-key` argv element — Cursor authenticates from the inherited `CURSOR_API_KEY` env var (issue #3375). There is also intentionally no `--` end-of-options separator before the prompt; the wrapped prompt is the positional argument after `--workspace`.
- Sources `scripts/lib-cursor-auth.sh` and runs `cursor_auth_preflight` BEFORE invoking `run-external-agent.sh`. On Darwin with `CURSOR_API_KEY` empty AND no `cursor-user` / `cursor-access-token` keychain entry, emits the standard KV envelope (`LAUNCHER_EXIT=2 MANIFEST_WRITTEN=false QA_PENDING_WRITTEN=false TRANSCRIPT=... SIDECAR_LOG=...`), routes the actionable stderr to `$SIDECAR_LOG`, and exits 0 (the wrapper-level exit; `LAUNCHER_EXIT` value 2 is the failure signal the dispatcher reads). The existing wrapper process exit code 2 stays for genuine pre-flag-parsing wrapper errors that occur before `$SIDECAR_LOG` is even resolvable.
- Auth is delivered via the `CURSOR_API_KEY` environment variable (issue #3375) — no `--api-key` argv element. `cursor_launcher_setup_auth_argv` normalizes/exports `CURSOR_API_KEY` (whitespace-trim; `unset` on empty/whitespace/embedded-newline) and, on Darwin with an empty env var, first pre-reads the `cursor-user` / `cursor-access-token` keychain service into `CURSOR_API_KEY`. The Cursor child inherits that env var; when neither the env var nor a keychain entry is available it falls back to its default auth resolution.

`--replay-meta` mode and an implement-replay sidecar were considered but are intentionally not shipped: there is no current runtime caller for collector-driven implement replay. The prompt sidecar plus `OUTER_LAUNCHER*` metadata are the narrow forward-compatibility surface for a future PR.

**Stdout contract**:
```
LAUNCHER_EXIT=<int>            # exit code from run-external-agent.sh
MANIFEST_WRITTEN=<true|false>  # whether $MANIFEST_PATH exists and is non-empty
QA_PENDING_WRITTEN=<true|false># whether $QA_PENDING_PATH exists and is non-empty
TRANSCRIPT=<path>              # path to captured Cursor stdout
SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter
```

**Flags**:

| Flag | Required | Purpose |
|------|----------|---------|
| `--transcript-path PATH` | yes | Where captured Cursor stdout is written |
| `--sidecar-log PATH` | yes | Where wrapper progress chatter is captured |
| `--manifest-path PATH` | yes | Where Cursor MUST atomic-write `manifest.json` |
| `--qa-pending-path PATH` | yes | Where Cursor atomic-writes `qa-pending.json` on `needs_qa` |
| `--plan-file PATH` | yes | Plan to implement (read by Cursor through the composed prompt) |
| `--feature-file PATH` | yes | Original feature description (read by Cursor through the composed prompt) |
| `--agent-prompt PATH` | yes | `agents/cursor-implementer.md` system prompt body |
| `--timeout SECS` | yes | Wall-clock cap for Cursor subprocess |
| `--answers-file PATH` | optional | Operator answers from a prior `needs_qa` cycle (resume) |
| `--timing-task-kind KIND` | optional | Timing attribution kind; defaults to `cursor-implement` |
| `--token-budget-cap N` | optional | Combined vendor token cap; emits `LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit` on stdout and writes `STATUS=cap_hit` to `$TRANSCRIPT_PATH` when exceeded. `LARCH_TOKEN_BUDGET_CAP_IMPLEMENT` env var sets the cap when the flag is absent. |

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Test harness**: `skills/implement/scripts/test-cursor-implementer.sh`.

Coverage is split into two slices:
- Always-on offline launcher contract harness: validates flag errors, missing input handling, env-derived timing fallback, model-args preflight envelopes and retry classification, stdout KV purity, Cursor argv shape, and prompt wrapping with a PATH-stubbed `cursor` binary. This slice must not depend on a real `cursor-agent`.
- Optional local smoke gated on `CURSOR_PRESENT=true`: launches a real `cursor agent` against a tiny canned prompt. This is for local development only and is not wired into the Makefile.

**Makefile wiring**: `make test-cursor-implementer` runs the always-on offline slice. `make test-harnesses` includes that target.
