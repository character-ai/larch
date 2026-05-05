# launch-gemini-implement.sh

**Purpose**: Spawn the Gemini implementer subprocess for `/implement` Step 2 with a tight, machine-parseable stdout contract. Wraps `run-external-agent.sh` + `gemini --prompt ... --approval-mode yolo --skip-trust --model "$GEMINI_MODEL"` and redirects the wrapper's human-readable progress lines to a sidecar log file so the dispatcher (`skills/implement/scripts/step2-implement.sh`) only sees deterministic `KEY=VALUE` lines.

**Invariants**:
- Stdout contract is `KEY=VALUE` lines only: `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`. The dispatcher relies on this; progress text leaking to stdout would corrupt parsing.
- `run-external-agent.sh`'s stdout AND stderr are redirected (`>"$SIDECAR_LOG" 2>&1`) inside the wrapper. Operators inspecting a failed run read the sidecar log to see wrapper-level progress and diagnostics.
- Gemini stdout/stderr is captured to `--transcript-path` via `run-external-agent.sh --capture-stdout`. The dispatcher consumes the on-disk manifest, not Gemini stdout.
- Wrapper always exits 0 unless flag validation fails (exit 2). The Gemini subprocess exit code is reported via `LAUNCHER_EXIT=<int>` on stdout.
- `--timeout` rejects empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...), while preserving valid leading-zero positive values such as `010`.
- Composes Gemini's prompt by concatenating `--agent-prompt` (`agents/gemini-implementer.md`) with this-invocation parameters and an optional resume block. Composition is in shell, not agent-side prose.
- Resolves `GEMINI_MODEL` inline from `LARCH_GEMINI_MODEL` / `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` / hardcoded `gemini-2.5-pro` — does NOT delegate to `agent-model-args.sh`. The precedence chain is intentionally duplicated from the gemini arm of `agent-model-args.sh` (without `--default-model`, which this call site never used) and mirrors the same pattern in `scripts/launch-gemini-review.sh` and `scripts/check-reviewers.sh` (Gemini health probe). All three inline Gemini resolvers and the helper's gemini arm must stay in lockstep if env names, plugin fallbacks, or the hardcoded default ever change. Gemini CLI has no separate reasoning-effort flag; the max-reasoning posture is model-based.
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

**Call sites**:
- `skills/implement/scripts/step2-implement.sh` (dispatcher) — the only authorized caller.

**Edit-in-sync**: `scripts/run-external-agent.sh`, `scripts/agent-model-args.sh` (Gemini env-precedence chain must stay in lockstep — see Invariants), `agents/gemini-implementer.md`, `agents/cursor-implementer.md`, `scripts/launch-cursor-implement.md`, `scripts/launch-gemini-review.sh` (sibling Gemini launcher using the same inline-resolve pattern), `scripts/check-reviewers.sh` (Gemini health probe inlining the same precedence chain), `skills/implement/references/codex-manifest-schema.md`, `skills/implement/scripts/test-gemini-implementer.sh`.

**Test harness**: `skills/implement/scripts/test-gemini-implementer.sh`.

Coverage is an always-on offline launcher contract harness: validates flag errors, missing input handling, stdout KV purity, Gemini argv shape, inline model resolution (`--model "$GEMINI_MODEL"` as a single quoted token), absence of `--output-format json`, sidecar redirection, manifest detection, and resume-block prompt composition with a PATH-stubbed `gemini` binary.

**Makefile wiring**: `make test-gemini-implementer` runs the offline harness. `make test-harnesses-2` includes that target alongside `test-cursor-implementer`.
