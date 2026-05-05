# test-gemini-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-gemini-implement.sh`. It verifies the Gemini implementer launcher without depending on a real Gemini installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Positive leading-zero timeouts (e.g. `010`) are accepted: launcher exits 0 with the standard five-line stdout envelope. Pins acceptance of the leading-zero positive form so a future refactor tightening the digit-only `case` validation (e.g. to `^[1-9][0-9]*$`) breaks CI. Note: the stub exits immediately, so this does NOT prove that downstream treats `010` as decimal 10 vs. octal 8 — only contract stability at the launcher boundary.
- Missing input files exit 2 — specifically: missing `--plan-file`, missing `--feature-file`, missing `--agent-prompt`, and `--answers-file` pointing at a non-existent path.
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
- `scripts/agent-model-args.sh` — owns the canonical Gemini env-precedence chain that `launch-gemini-implement.sh`, `launch-gemini-review.sh`, and `check-reviewers.sh` (Gemini health probe) each duplicate inline. All four definitions (this helper's gemini arm + the three inline sites) must stay in lockstep when env names, plugin fallbacks, or the hardcoded default change.
- `scripts/launch-gemini-review.sh` — sibling Gemini launcher using the same inline-resolve pattern (one of the three inline sites in the four-way lockstep).
- `scripts/check-reviewers.sh` — Gemini health probe inlining the same precedence chain (one of the three inline sites in the four-way lockstep).
