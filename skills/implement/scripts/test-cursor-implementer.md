# test-cursor-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-cursor-implement.sh`. It verifies the Cursor implementer launcher without depending on a real Cursor installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Positive leading-zero timeouts (e.g. `010`) are accepted: launcher exits 0 with the standard five-line stdout envelope. Guards against a future refactor swapping the base-10 force-decimal expression `(( 10#$TIMEOUT < 1 ))` for plain `(( $TIMEOUT < 1 ))` and silently regressing to `010`-as-octal-eight (or stricter-shell errors).
- Missing input files exit 2 — specifically: missing `--plan-file`, missing `--feature-file`, missing `--agent-prompt`, and `--answers-file` pointing at a non-existent path.
- PATH-stubbed `cursor` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- `run-external-agent.sh --capture-stdout` captures Cursor stdout to the transcript path.
- Cursor argv shape matches `scripts/launch-cursor-review.sh`: `cursor agent -p --force --trust $MODEL_ARGS --workspace "$PWD" "$WRAPPED_PROMPT"`.
- No `--` end-of-options separator is inserted before the prompt.
- The prompt is wrapped by `scripts/cursor-wrap-prompt.sh`.

**Optional smoke**: `CURSOR_HEALTHY=true bash skills/implement/scripts/test-cursor-implementer.sh --real-smoke` launches a real `cursor agent` against a tiny prompt. This is a local development smoke only and is not wired into the Makefile.

**Invariants**:
- The always-on path must stay offline and must not call the real `cursor` binary.
- The stub records argv one argument per line so ordering assertions preserve argument boundaries.
- The test sets `LARCH_CURSOR_MODEL=stub-model` to avoid environment-specific model drift.

**Call sites**:
- `make test-cursor-implementer`.
- `make test-harnesses`.

**Edit-in-sync**:
- `scripts/launch-cursor-implement.sh` — launcher behavior under test.
- `scripts/launch-cursor-implement.md` — sibling launcher contract.
- `scripts/launch-cursor-review.sh` — argv parity source.
- `scripts/cursor-wrap-prompt.sh` and `scripts/cursor-wrap-prompt.md` — prompt wrapper contract and caller registry.
- `scripts/run-external-agent.sh` — stdout capture semantics.
- `scripts/agent-model-args.sh` — Cursor model argv generation.
