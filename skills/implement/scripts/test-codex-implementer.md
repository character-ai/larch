# test-codex-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-codex-implement.sh`. It verifies the Codex implementer launcher without depending on a real Codex installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Missing input files exit 2.
- PATH-stubbed `codex` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- Codex's `--output-last-message` transcript path receives the stubbed output payload.
- Codex argv shape includes `exec`, `--full-auto`, `-C "$PWD"`, `--output-last-message`, and model/effort args from `scripts/agent-model-args.sh --tool codex --with-effort`.
- The composed prompt is passed after a `--` end-of-options separator and is the last positional argv argument.
- Passing `--answers-file` adds the `## Resume invocation` block to the composed prompt.

**Invariants**:
- The always-on path must stay offline and must not call the real `codex` binary.
- The stub records argv one argument per line so ordering assertions preserve argument boundaries.
- The test sets `LARCH_CODEX_MODEL=stub-codex-model` to avoid environment-specific model drift and to pin model forwarding.
- The test relies on the default Codex effort (`high`) emitted by `agent-model-args.sh --with-effort`.
- The stub writes the manifest atomically (`.tmp` then `mv`) so launcher detection mirrors production.

**Call sites**:
- `make test-codex-implementer`.
- `make test-harnesses-2`.

**Edit-in-sync**:
- `scripts/launch-codex-implement.sh` — launcher behavior under test.
- `scripts/launch-codex-implement.md` — sibling launcher contract.
- `agents/codex-implementer.md` — prompt body path and resume block expectations.
- `scripts/run-external-agent.sh` — transcript and sidecar capture semantics.
- `scripts/agent-model-args.sh` — Codex model and effort argv generation.
