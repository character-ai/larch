# test-gemini-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-gemini-implement.sh`. It verifies the Gemini implementer launcher without depending on a real Gemini installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Positive leading-zero timeouts (e.g. `010`) are accepted: launcher exits 0 with the standard five-line stdout envelope. Pins acceptance of the leading-zero positive form so a future refactor tightening the digit-only `case` validation (e.g. to `^[1-9][0-9]*$`) breaks CI. Note: the stub exits immediately, so this does NOT prove that downstream treats `010` as decimal 10 vs. octal 8 — only contract stability at the launcher boundary.
- Missing input files exit 2 with the launcher's literal validation messages — specifically: missing `--plan-file` (`plan file not found`), missing `--feature-file` (`feature file not found`), missing `--agent-prompt` (`agent prompt not found`), and `--answers-file` pointing at a non-existent path (`--answers-file given but path does not exist`).
- PATH-stubbed `gemini` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- `run-external-agent.sh --capture-stdout` captures Gemini stdout/stderr to the transcript path.
- Gemini argv shape includes `--prompt`, `--approval-mode yolo`, `--skip-trust`, and `--model "$GEMINI_MODEL"`. The launcher resolves the model by sourcing `scripts/lib-gemini-model-resolver.sh` and calling `resolve_gemini_model`, which walks `LARCH_GEMINI_MODEL` / `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` / hardcoded `gemini-2.5-pro` with set-aware semantics (`${VAR+x}` checks, not `${VAR:-…}`). The launcher does NOT shell out to `agent-model-args.sh`.
- Verifies model-rejection paths via `lib-gemini-model-resolver.sh`: blank `LARCH_GEMINI_MODEL`, whitespace-only, and control-byte values are rejected before the stub `gemini` runs. The launcher converts model-resolution failure into the standard five-line KV envelope on stdout — `LAUNCHER_EXIT=<resolver-rc>` (typically `1`), `MANIFEST_WRITTEN=false`, `QA_PENDING_WRITTEN=false`, plus `TRANSCRIPT=` / `SIDECAR_LOG=` — and exits the wrapper process with `0` (the dispatcher consumes `LAUNCHER_EXIT` from stdout, not the wrapper's process exit code). The resolver's stderr diagnostic identifying the rejected source is appended to `SIDECAR_LOG`.
- Pre-existing non-empty manifest / Q&A files do not affect model-rejection classification: resolver failure still emits `MANIFEST_WRITTEN=false` and `QA_PENDING_WRITTEN=false`, matching the Cursor preflight-failure contract.
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
- `scripts/lib-gemini-model-resolver.sh` — sourced by all three Gemini consumers (`launch-gemini-implement.sh`, `launch-gemini-review.sh`, `check-reviewers.sh` Gemini probe). Owns the runtime env-precedence chain (`LARCH_GEMINI_MODEL` → `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL` → `gemini-2.5-pro`) plus blank/whitespace/cntrl rejection. Update this helper and `scripts/lib-gemini-model-resolver.md` together.
- `scripts/agent-model-args.sh` — owns the canonical Gemini env-precedence chain documented in `scripts/agent-model-args.md`. Edit-in-sync with `lib-gemini-model-resolver.sh` when env names, plugin fallbacks, or the hardcoded default change (the helper and the agent-model-args.sh Gemini arm both implement the same chain).
- `scripts/launch-gemini-review.sh` — sibling Gemini launcher; sources the same helper. One of the three call sites that must stay in lockstep with the resolver.
- `scripts/check-reviewers.sh` — Gemini health probe; sources the same helper. One of the three call sites that must stay in lockstep with the resolver.
