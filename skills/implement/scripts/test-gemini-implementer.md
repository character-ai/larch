# test-gemini-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-gemini-implement.sh`. It verifies the Gemini implementer launcher without depending on a real Gemini installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Missing input files exit 2.
- PATH-stubbed `gemini` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- `run-external-agent.sh --capture-stdout` captures Gemini stdout to the transcript path.
- Gemini argv shape includes `--prompt`, `--approval-mode yolo`, `--skip-trust`, and model args from `agent-model-args.sh`.
- No `--output-format` dependency is introduced; the dispatcher consumes the on-disk manifest.
- The prompt includes the max-reasoning prefix and invocation parameters.

**Optional smoke**: `GEMINI_HEALTHY=true bash skills/implement/scripts/test-gemini-implementer.sh --real-smoke` launches a real Gemini CLI prompt. This is a local development smoke only and is not wired into the Makefile.

**Invariants**:
- The always-on path must stay offline and must not call the real `gemini` binary.
- The stub records argv one argument per line so ordering assertions preserve argument boundaries.
- The test sets `LARCH_GEMINI_MODEL=stub-model` to avoid environment-specific model drift.

**Call sites**:
- `make test-gemini-implementer`.
- `make test-harnesses`.

**Edit-in-sync**:
- `scripts/launch-gemini-implement.sh` — launcher behavior under test.
- `scripts/launch-gemini-implement.md` — sibling launcher contract.
- `scripts/run-external-agent.sh` — stdout capture semantics.
- `scripts/agent-model-args.sh` — Gemini model argv generation.
