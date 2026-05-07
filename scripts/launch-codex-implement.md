# launch-codex-implement.sh

**Purpose**: Spawn the Codex implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `codex exec --full-auto` (parallel to `launch-codex-review.sh`) but redirects the wrapper's human-readable progress lines (⏳, ✓, ❌) to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only — `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; any progress text leaking to stdout would be parsed as garbage.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see what went wrong.
- After manifest / Q&A detection, the wrapper silently scrapes the sidecar for the last `tokens used` block and records a best-effort `codex_implement` vendor total via `scripts/token-ledger.sh`. Scrape failure never changes launcher stdout or exit behavior.
- After manifest / Q&A detection, the wrapper also emits one best-effort `scripts/timing-ledger.sh record-vendor-task` row. `TIMING_START_S` is captured at wrapper entry after argv validation. `--timing-task-kind <kind>` defaults to `codex-implement`; timing failures are silent and never affect the KEY=VALUE stdout envelope or wrapper exit behavior.
- Codex's full transcript (the `--output-last-message` payload) lands at `--transcript-path`. This file may grow large; it is intentionally NOT echoed to stdout.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Codex subprocess's exit code is reported via `LAUNCHER_EXIT=<int>` on stdout; the dispatcher decides whether that constitutes failure.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Codex receives `--add-dir "$SESSION_TMPDIR"` so its sandbox can atomic-write `manifest.json` and `qa-pending.json` to the dispatcher-owned session tmpdir. The launcher canonicalizes both `dirname "$MANIFEST_PATH"` and `dirname "$QA_PENDING_PATH"` with `cd "$dir" && pwd -P`, compares those canonical bytes, and embeds the canonical parent in Codex's prompt. It exits 2 if the canonical parents differ or the session tmpdir does not exist. The granted directory is the ENTIRE session tmpdir as constructed by `step2-implement.sh`, not just the two JSON files — operators should treat any other artifact placed in that tmpdir (transcripts, sidecars, dispatcher baseline / spawn / resume-count sentinels) as Codex-writable.
- Composes Codex's prompt by concatenating `--agent-prompt` (system-prompt body, `agents/codex-implementer.md`) with this-invocation parameters and an optional resume block. Composition is in shell, not in agent-side prose, so the contract is mechanically inspectable.
- Reuses `agent-model-args.sh --tool codex --with-effort` exactly as `launch-codex-review.sh` does — this implementer benefits from max reasoning effort. The helper's line-token stdout is read into a Bash array and consumed with `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}`.
- Codex argv shape places `--add-dir "$SESSION_TMPDIR"` after `-C "$PWD"` and before the model-args array, then passes the composed prompt as a positional argument after a `--` end-of-options separator. The separator is load-bearing: `agents/codex-implementer.md` begins with YAML frontmatter (`---`), and codex-cli (observed on 0.125.0) interprets a leading `---` as a flag delimiter and aborts. `launch-codex-review.sh` does not need this separator because `render-specialist-prompt.sh` strips frontmatter from reviewer prompts.

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

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Edit-in-sync**: `scripts/run-external-agent.sh`, `scripts/agent-model-args.sh`, `agents/codex-implementer.md`, `skills/implement/references/codex-manifest-schema.md`. Differs from `launch-codex-review.sh` in: (a) progress chatter redirected to sidecar log; (b) prompt composition in shell (review launcher passes prompt as a single argv string).

**Test harness**: `skills/implement/scripts/test-codex-implementer.sh` PATH-stubs `codex` and exercises flag validation, timeout validation, missing input files, manifest/qa-pending parent validation, missing-session-tmpdir validation, the five-line `KEY=VALUE` stdout envelope, transcript detection via `--output-last-message`, Codex argv shape/model forwarding including `--add-dir`, and resume prompt composition. `skills/implement/scripts/test-step2-dispatch.sh` remains the dispatcher harness for Step 2 branches that do not call this launcher (claude_fallback, argument validation, resume-cap bail).

**Makefile wiring**: directly exercised by `make test-codex-implementer` and included in `make test-harnesses-3`; dispatcher-only paths remain covered by `make test-step2-dispatch`.
