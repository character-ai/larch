# scripts/launch-gemini-implement.sh — contract

## Purpose

Launches the Gemini CLI implementer for `/implement` Step 2 and returns only deterministic `KEY=VALUE` lines to the dispatcher. Gemini writes `manifest.json` and, on `needs_qa`, `qa-pending.json` at the exact paths passed by `skills/implement/scripts/step2-implement.sh`.

## Invariants

- Stdout is KV-only: `LAUNCHER_EXIT`, `MANIFEST_WRITTEN`, `QA_PENDING_WRITTEN`, `TRANSCRIPT`, `SIDECAR_LOG`.
- `run-external-agent.sh` stdout/stderr is redirected to `--sidecar-log`; Gemini stdout is captured to `--transcript-path` via `--capture-stdout`.
- Prompt composition happens in this shell script by concatenating `agents/gemini-implementer.md`, invocation paths, working directory, and the optional resume block.
- The Gemini invocation is `gemini --prompt "$PROMPT" --approval-mode yolo --skip-trust $MODEL_ARGS`.
- Model args come from `scripts/agent-model-args.sh --tool gemini --with-effort`.
- Max reasoning posture is prompt-prefix based: the launcher prepends `Work at your maximum reasoning effort level.`. `agent-model-args.sh --tool gemini --with-effort` is intentionally a no-op for effort flags.
- Minimum Gemini CLI expectation: support for `--prompt`, `--approval-mode yolo`, `--skip-trust`, and `--model`.
- The launcher never commits, stages, pushes, or interprets the manifest content.

## Flags

| Flag | Purpose |
|------|---------|
| `--transcript-path PATH` | Captured Gemini stdout. |
| `--sidecar-log PATH` | Wrapper progress and stderr log. |
| `--manifest-path PATH` | Required manifest destination for Gemini. |
| `--qa-pending-path PATH` | Required Q/A destination when Gemini emits `needs_qa`. |
| `--plan-file PATH` | Implementation plan. |
| `--feature-file PATH` | Original feature/operator prompt. |
| `--agent-prompt PATH` | `agents/gemini-implementer.md`. |
| `--timeout SECS` | Wall-clock cap passed to `run-external-agent.sh`. |
| `--answers-file PATH` | Optional resume answers file. |

## Call Sites

- `skills/implement/scripts/step2-implement.sh` (`--coder gemini` external implementer arm).

## Test Harness

- `skills/implement/scripts/test-gemini-implementer.sh`.

## Edit-in-sync

- `scripts/launch-gemini-implement.sh`
- `scripts/run-external-agent.sh`
- `scripts/agent-model-args.sh`
- `agents/gemini-implementer.md`
- `skills/implement/references/codex-manifest-schema.md`
- `skills/implement/scripts/test-gemini-implementer.sh`
