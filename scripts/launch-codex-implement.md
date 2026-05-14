# launch-codex-implement.sh

**Purpose**: Spawn the Codex implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `codex exec --full-auto` (parallel to `launch-review.sh --tool codex`) but redirects the wrapper's human-readable progress lines (⏳, ✓, ❌) to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines. The static implementer preamble is delivered through a per-invocation `CODEX_HOME/config.toml` top-level `instructions` key, while the positional prompt carries only dynamic task parameters.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only — `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; any progress text leaking to stdout would be parsed as garbage.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see what went wrong.
- After manifest / Q&A detection, the wrapper silently scrapes the sidecar for the last `tokens used` block and records a best-effort `codex_implement` vendor total via `scripts/token-ledger.sh`. Scrape failure never changes launcher stdout or exit behavior.
- Before token-ledger scraping or spawning Codex, the wrapper rehydrates token context from `IMPLEMENT_TMPDIR` when present: `$IMPLEMENT_TMPDIR/session-id` overwrites any stale `LARCH_TOKEN_SESSION_ID`, and `$IMPLEMENT_TMPDIR/claude-source.env` becomes `LARCH_CLAUDE_SOURCE_FILE`.
- After manifest / Q&A detection, the wrapper also emits one best-effort `scripts/timing-ledger.sh record-vendor-task` row. `TIMING_START_S` is captured at wrapper entry after argv validation. `--timing-task-kind <kind>` defaults to `codex-implement`; timing failures are silent and never affect the KEY=VALUE stdout envelope or wrapper exit behavior. **Validation**: when `--timing-task-kind` is supplied via the CLI, the value must be non-empty and must not begin with `--`; otherwise the launcher exits 2 with `--timing-task-kind requires a non-empty, non-flag-like value` on stderr (issue #1480 defense-in-depth against argv-shape collapse from a broken env-var-prefix expansion in the caller). Env-derived `LARCH_TIMING_TASK_KIND` that is empty or starts with `--` silently falls back to the per-launcher default (for example, `codex-implement`). The CLI `--timing-task-kind` flag still hard-rejects empty / flag-shaped values with exit 2.
- Codex's full transcript (the `--output-last-message` payload) lands at `--transcript-path`. This file may grow large; it is intentionally NOT echoed to stdout.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Codex subprocess's exit code is reported via `LAUNCHER_EXIT=<int>` on stdout; the dispatcher decides whether that constitutes failure.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Codex receives `--add-dir "$SESSION_TMPDIR"` so its sandbox can atomic-write `manifest.json` and `qa-pending.json` to the dispatcher-owned session tmpdir. The launcher canonicalizes both `dirname "$MANIFEST_PATH"` and `dirname "$QA_PENDING_PATH"` with `cd "$dir" && pwd -P`, compares those canonical bytes, and embeds the canonical parent in Codex's prompt. It exits 2 if the canonical parents differ or the session tmpdir does not exist. The granted directory is the ENTIRE session tmpdir as constructed by `step2-implement.sh`, not just the two JSON files — operators should treat any other artifact placed in that tmpdir (transcripts, sidecars, dispatcher baseline / spawn / resume-count sentinels) as Codex-writable. Codex also receives `--add-dir "$PWD"` to explicitly expand the `workspace-write` sandbox to cover the repo root; without this, repo-root files (`Makefile`, `AGENTS.md`, etc.) and paths under `.claude/` are denied writes, causing the implementer to bail with `sandbox-denied-required-root-files`.
- Creates a per-invocation `CODEX_HOME` under `/tmp/larch-codex-home-*`, outside both `$PWD` and `$SESSION_TMPDIR`, writes `config.toml` with the stripped `--agent-prompt` body as top-level `instructions`, then appends any existing `~/.codex/config.toml`. The launcher symlinks `~/.codex/auth.json` into the temporary home only when the file exists, so env-var auth users do not need a local auth file. The EXIT trap removes the temporary home.
- Composes Codex's positional prompt from this-invocation parameters and an optional resume block only. Composition is in shell, not in agent-side prose, so the contract is mechanically inspectable. The dynamic prompt is also written to `${TRANSCRIPT_PATH}.prompt` for retry/debug inspection; it intentionally does not contain the static implementer preamble.
- Reuses `agent-model-args.sh --tool codex --with-effort` exactly as `launch-review.sh --tool codex` does — this implementer benefits from max reasoning effort. The helper's line-token stdout is read into a Bash array and consumed with `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}`.
- If Codex model-args resolution fails, the launcher truncates `SIDECAR_LOG`, appends the `agent-model-args.sh` diagnostic, emits the same five-line KV envelope used by Gemini model resolution failures with `MANIFEST_WRITTEN=false` and `QA_PENDING_WRITTEN=false`, records timing best-effort, and exits wrapper-level 0. Argv validation errors still exit 2 before this preflight envelope exists.
- The actual Codex spawn is wrapped with `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and auth-startup outer retry loop. Retry classification reads `SIDECAR_LOG`, which captures `run-external-agent.sh` chatter and Codex startup stderr.
- When the auth-retry loop finishes with a non-zero `LAUNCHER_EXIT` and `IMPLEMENT_TMPDIR` is set, the launcher best-effort appends `SIDECAR_LOG` to `$IMPLEMENT_TMPDIR/execution-issues.md` through `scripts/append-tool-failure.sh --redact` under `Tool Failures`, including an auth verdict (`auth-retries-exhausted`, `non-auth`, or `unclassified`) and the final auth-loop attempt count.
- Codex argv shape sets `CODEX_HOME="$CODEX_HOME_DIR"`, places `--add-dir "$SESSION_TMPDIR"` and `--add-dir "$PWD"` (in that order) after `-C "$PWD"` and before the model-args array, passes trusted-project config for `$PWD` via `-c`, then passes the dynamic prompt as a positional argument after a `--` end-of-options separator. The separator remains a defense against future dynamic prompt changes that might begin with flag-like bytes.

**Stdout contract**:
```
LAUNCHER_EXIT=<int>            # exit code from run-external-agent.sh
MANIFEST_WRITTEN=<true|false>  # whether $MANIFEST_PATH exists and is non-empty
QA_PENDING_WRITTEN=<true|false># whether $QA_PENDING_PATH exists and is non-empty
TRANSCRIPT=<path>              # path to Codex's --output-last-message file
SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter
```

**Flags**:

| Flag | Required | Purpose |
|------|----------|---------|
| `--transcript-path PATH` | yes | Where Codex's `--output-last-message` is written |
| `--sidecar-log PATH` | yes | Where wrapper progress chatter is captured |
| `--manifest-path PATH` | yes | Where Codex MUST atomic-write `manifest.json` |
| `--qa-pending-path PATH` | yes | Where Codex atomic-writes `qa-pending.json` on `needs_qa` |
| `--plan-file PATH` | yes | Plan to implement (read by Codex) |
| `--feature-file PATH` | yes | Original feature description (read by Codex) |
| `--agent-prompt PATH` | yes | `agents/codex-implementer.md` system prompt body |
| `--timeout SECS` | yes | Wall-clock cap for Codex subprocess |
| `--answers-file PATH` | optional | Operator answers from a prior `needs_qa` cycle (resume) |
| `--timing-task-kind KIND` | optional | Timing attribution kind; defaults to `codex-implement` |
| `--token-budget-cap N` | optional | Combined vendor token cap; emits `LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit` on stdout and writes `STATUS=cap_hit` to `$TRANSCRIPT_PATH` when exceeded; `step2-implement.sh` detects `STATUS=cap_hit` and emits `STATUS=bailed REASON=cap_hit` without retrying. `LARCH_TOKEN_BUDGET_CAP_IMPLEMENT` env var sets the cap when the flag is absent. |

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Edit-in-sync**: `scripts/check-step-token-budget.sh` (budget-cap helper), `scripts/run-external-agent.sh`, `scripts/agent-model-args.sh`, `agents/codex-implementer.md`, `skills/implement/references/codex-manifest-schema.md`. Differs from `launch-review.sh --tool codex` in: (a) progress chatter redirected to sidecar log; (b) dynamic prompt composition in shell (review launcher receives prompt text from callers or `render-specialist-prompt.sh`).

**Test harness**: `skills/implement/scripts/test-codex-implementer.sh` PATH-stubs `codex` and exercises flag validation, timeout validation, missing input files, manifest/qa-pending parent validation, missing-session-tmpdir validation, env-derived timing fallback, model-args preflight envelopes and retry classification, the five-line `KEY=VALUE` stdout envelope, transcript detection via `--output-last-message`, Codex argv shape/model forwarding including `--add-dir`, per-invocation `CODEX_HOME` config, dynamic-only prompt sidecar, and resume prompt composition. `skills/implement/scripts/test-step2-dispatch.sh` remains the dispatcher harness for Step 2 branches that do not call this launcher (claude_fallback, argument validation, resume-cap bail).

**Makefile wiring**: directly exercised by `make test-codex-implementer` and included in `make test-harnesses-3`; dispatcher-only paths remain covered by `make test-step2-dispatch`.
