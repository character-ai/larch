# launch-gemini-implement.sh

**Purpose**: Spawn the Gemini implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `gemini --prompt ... --approval-mode yolo --skip-trust --model "$GEMINI_MODEL"` and redirects the wrapper's human-readable progress lines to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only: `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; progress text leaking to stdout would corrupt parsing.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see wrapper-level progress and diagnostics.
- Gemini stdout/stderr is captured to `--transcript-path` via `run-external-agent.sh --capture-stdout`. The dispatcher consumes the on-disk manifest, not Gemini stdout.
- After manifest / Q&A detection, the wrapper emits one best-effort `scripts/timing-ledger.sh record-vendor-task` row. `TIMING_START_S` is captured at wrapper entry after argv validation. `--timing-task-kind <kind>` defaults to `gemini-implement`; timing failures are silent and never affect the KEY=VALUE stdout envelope or wrapper exit behavior. **Validation**: when `--timing-task-kind` is supplied via the CLI, the value must be non-empty and must not begin with `--`; otherwise the launcher exits 2 with `--timing-task-kind requires a non-empty, non-flag-like value` on stderr (issue #1480 defense-in-depth against argv-shape collapse from a broken env-var-prefix expansion in the caller). Env-derived `LARCH_TIMING_TASK_KIND` that is empty or starts with `--` silently falls back to the per-launcher default (for example, `gemini-implement`). The CLI `--timing-task-kind` flag still hard-rejects empty / flag-shaped values with exit 2.
- Before spawning Gemini, the wrapper rehydrates token context from `IMPLEMENT_TMPDIR` when present: `$IMPLEMENT_TMPDIR/session-id` overwrites any stale `LARCH_TOKEN_SESSION_ID`, and `$IMPLEMENT_TMPDIR/claude-source.env` becomes `LARCH_CLAUDE_SOURCE_FILE`. Gemini implementer does not record vendor tokens today; this keeps parity with Codex and Cursor launchers.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Gemini subprocess exit code is reported via `LAUNCHER_EXIT=<int>` on stdout.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Verified against Gemini CLI as of 2026-05: `--approval-mode yolo --skip-trust` permits writes to absolute paths passed via `--manifest-path` and `--qa-pending-path` (which today live under `--tmpdir`, typically rooted at `~/.cache/larch/sessions/...` per the `step2-implement.sh` convention). Gemini CLI also exposes `--include-directories` and `--sandbox`; if a future Gemini release tightens the trust posture and `yolo` no longer covers absolute writes, the launcher must add `--include-directories "$(dirname "$MANIFEST_PATH")"` and this contract revisited.
- Composes Gemini's prompt by concatenating `--agent-prompt` (`agents/gemini-implementer.md`) with this-invocation parameters and an optional resume block. Composition is in shell, not agent-side prose.
- Sources `scripts/lib-gemini-model-resolver.sh` to resolve `GEMINI_MODEL` from `LARCH_GEMINI_MODEL` / `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` / hardcoded `gemini-2.5-pro` with set-aware precedence — it does NOT delegate to `agent-model-args.sh`. Blank, whitespace-only, or POSIX `[[:cntrl:]]` values emit the standard five-line KV envelope with `LAUNCHER_EXIT=1`, route the resolver diagnostic to `SIDECAR_LOG`, and exit 0 per the implementer-launcher stdout contract. Internal spaces are allowed. Gemini CLI has no separate reasoning-effort flag; the max-reasoning posture is model-based.
- **`resolve_gemini_model` failure:** when the helper cannot resolve a Gemini model (e.g. `GEMINI_MODEL` env unset, blank, whitespace-only, or contains control bytes), the launcher truncates `SIDECAR_LOG`, appends the `resolve_gemini_model` diagnostic, then emits `LAUNCHER_EXIT=<rc>`, `MANIFEST_WRITTEN=false`, `QA_PENDING_WRITTEN=false` unconditionally — never inheriting `-s` byte-probe results from leftover artifacts, and never mixing stale chatter from a prior run into preflight diagnostics. This preserves the documented stdout KV contract, parity with `launch-cursor-implement.sh`'s and `launch-codex-implement.sh`'s preflight-failure blocks (which also `: > "$SIDECAR_LOG"` before appending diagnostics), and downstream retry / observability semantics in `step2-implement.sh`. Aligns with `.claude/rules/external-tool-launcher-parity.md`.
- The actual Gemini spawn is wrapped with `lib-external-launcher-common.sh`'s per-tool Darwin serial lock and auth-startup outer retry loop. Retry classification checks both `SIDECAR_LOG` and `TRANSCRIPT`, because `run-external-agent.sh --capture-stdout` routes Gemini stdout/stderr to the transcript file.
- Gemini argv shape is pinned to the non-interactive shell-tools path verified during design: `gemini --prompt "$PROMPT" --approval-mode yolo --skip-trust --model "$GEMINI_MODEL"`. Do not add `--output-format json`; the dispatcher reads `manifest.json`, not stdout JSON. The harness stubs Gemini CLI and asserts this shape. Verified against Gemini CLI 0.40.x; update this contract and `test-gemini-implementer.sh` together if a future CLI changes the headless flags.

**Stdout contract**:
```
LAUNCHER_EXIT=<int>            # exit code from run-external-agent.sh
MANIFEST_WRITTEN=<true|false>  # whether $MANIFEST_PATH exists and is non-empty
QA_PENDING_WRITTEN=<true|false># whether $QA_PENDING_PATH exists and is non-empty
TRANSCRIPT=<path>              # path to captured Gemini stdout/stderr
SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter
```

**Flags**:

| Flag | Required | Purpose |
|------|----------|---------|
| `--transcript-path PATH` | yes | Where captured Gemini stdout/stderr is written |
| `--sidecar-log PATH` | yes | Where wrapper progress chatter is captured |
| `--manifest-path PATH` | yes | Where Gemini MUST atomic-write `manifest.json` |
| `--qa-pending-path PATH` | yes | Where Gemini atomic-writes `qa-pending.json` on `needs_qa` |
| `--plan-file PATH` | yes | Plan to implement (read by Gemini through the composed prompt) |
| `--feature-file PATH` | yes | Original feature description (read by Gemini through the composed prompt) |
| `--agent-prompt PATH` | yes | `agents/gemini-implementer.md` system prompt body |
| `--timeout SECS` | yes | Wall-clock cap for Gemini subprocess |
| `--answers-file PATH` | optional | Operator answers from a prior `needs_qa` cycle (resume) |
| `--timing-task-kind KIND` | optional | Timing attribution kind; defaults to `gemini-implement` |
| `--token-budget-cap N` | optional | Combined vendor token cap; emits `LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit` on stdout and writes `STATUS=cap_hit` to `$TRANSCRIPT_PATH` when exceeded. `LARCH_TOKEN_BUDGET_CAP_IMPLEMENT` env var sets the cap when the flag is absent. |

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Edit-in-sync**: `scripts/check-step-token-budget.sh` (budget-cap helper), `scripts/lib-gemini-model-resolver.sh`, `scripts/run-external-agent.sh`, `scripts/agent-model-args.sh` (Gemini env-precedence chain must stay in lockstep — see Invariants), `agents/gemini-implementer.md`, `agents/cursor-implementer.md`, `scripts/launch-cursor-implement.md`, `scripts/launch-review.sh --tool gemini`, `scripts/check-reviewers.sh`, `skills/implement/references/codex-manifest-schema.md`, `skills/implement/scripts/test-gemini-implementer.sh`.

**Test harness**: `skills/implement/scripts/test-gemini-implementer.sh`.

Coverage is an always-on offline launcher contract harness: validates flag errors, missing input handling, stdout KV purity, Gemini argv shape, helper-backed model resolution and rejection (`--model "$GEMINI_MODEL"` as a single quoted token), absence of `--output-format json`, sidecar redirection, manifest detection, and resume-block prompt composition with a PATH-stubbed `gemini` binary.

**Makefile wiring**: `make test-gemini-implementer` runs the offline harness. `make test-harnesses-2` includes that target alongside `test-cursor-implementer`.
