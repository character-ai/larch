# launch-cursor-implement.sh

**Purpose**: Spawn the Cursor implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `cursor agent -p --force --trust` (parallel to `launch-cursor-review.sh`) but redirects the wrapper's human-readable progress lines to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only: `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; any progress text leaking to stdout would be parsed as garbage.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see what went wrong.
- Cursor stdout is captured to `--transcript-path` via `run-external-agent.sh --capture-stdout-only`, with stderr routed to `<transcript>.diag` so Cursor JSON remains parseable. This file may grow large; it is intentionally NOT echoed to stdout.
- The Cursor command includes `--output-format json`; after the run, the wrapper best-effort parses `.usage` and records a `cursor_implement` vendor total via `scripts/token-ledger.sh`. Missing `jq`, malformed JSON, or absent usage is silent and non-fatal.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Cursor subprocess's exit code is reported via `LAUNCHER_EXIT=<int>` on stdout; the dispatcher decides whether that constitutes failure.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Composes Cursor's prompt by concatenating `--agent-prompt` (`agents/cursor-implementer.md`) with this-invocation parameters and an optional resume block. Composition is in shell, not in agent-side prose, so the contract is mechanically inspectable.
- Reuses `agent-model-args.sh --tool cursor --with-effort`, then wraps the composed prompt with `cursor-wrap-prompt.sh` so Cursor max-mode is enforced exactly like the review path.
- Cursor argv shape is pinned to `scripts/launch-cursor-review.sh`: `cursor agent -p --force --trust --output-format json $MODEL_ARGS --workspace "$PWD" "$WRAPPED_PROMPT"`. There is intentionally no `--` end-of-options separator before the prompt; the wrapped prompt is the positional argument after `--workspace`.

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

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Edit-in-sync**: `scripts/run-external-agent.sh`, `scripts/agent-model-args.sh`, `scripts/cursor-wrap-prompt.sh`, `scripts/cursor-wrap-prompt.md`, `agents/cursor-implementer.md`, `agents/gemini-implementer.md`, `skills/implement/references/codex-manifest-schema.md`, `scripts/launch-cursor-review.sh`, `scripts/launch-gemini-implement.md`, `skills/implement/scripts/test-cursor-implementer.sh`.

**Test harness**: `skills/implement/scripts/test-cursor-implementer.sh`.

Coverage is split into two slices:
- Always-on offline launcher contract harness: validates flag errors, missing input handling, stdout KV purity, Cursor argv shape, and prompt wrapping with a PATH-stubbed `cursor` binary. This slice must not depend on a real `cursor-agent`.
- Optional local smoke gated on `CURSOR_HEALTHY=true`: launches a real `cursor agent` against a tiny canned prompt. This is for local development only and is not wired into the Makefile.

**Makefile wiring**: `make test-cursor-implementer` runs the always-on offline slice. `make test-harnesses` includes that target.
