# test-gemini-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-gemini-implement.sh`. It verifies the Gemini implementer launcher without depending on a real Gemini installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Missing input files exit 2.
- PATH-stubbed `gemini` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- `run-external-agent.sh --capture-stdout` captures Gemini stdout/stderr to the transcript path.
- Gemini argv shape includes `--prompt`, `--approval-mode yolo`, `--skip-trust`, and `--model "$GEMINI_MODEL"` (resolved inline by `launch-gemini-implement.sh` from `LARCH_GEMINI_MODEL` / `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` / hardcoded `gemini-2.5-pro`; the launcher does NOT shell out to `agent-model-args.sh`).
- The launcher does not pass `--output-format json`; the dispatcher consumes the on-disk manifest, not Gemini stdout JSON.
- Passing `--answers-file` adds the `## Resume invocation` block to the composed prompt.

**Invariants**:
- The always-on path must stay offline and must not call the real `gemini` binary.
- The stub records argv one argument per line so ordering and token assertions preserve argument boundaries.
- The test sets `LARCH_GEMINI_MODEL=stub-gemini-model` to avoid environment-specific model drift and to pin model forwarding.
- The stub writes the manifest atomically (`.tmp` then `mv`) so launcher detection mirrors production.

**Call sites**:
- `make test-gemini-implementer`.
- `make test-harnesses-2`.

**Edit-in-sync**:
- `scripts/launch-gemini-implement.sh` — launcher behavior under test.
- `scripts/launch-gemini-implement.md` — sibling launcher contract.
- `agents/gemini-implementer.md` — prompt body path and resume block wording.
- `scripts/run-external-agent.sh` — stdout capture semantics.
- `scripts/agent-model-args.sh` — owns the canonical Gemini env-precedence chain that `launch-gemini-implement.sh` duplicates inline; keep the two in lockstep when env names, plugin fallbacks, or the hardcoded default change.
- `scripts/launch-gemini-review.sh` — sibling Gemini launcher using the same inline-resolve pattern.
