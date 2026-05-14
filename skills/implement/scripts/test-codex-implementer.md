# test-codex-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-codex-implement.sh`. It verifies the Codex implementer launcher without depending on a real Codex installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Positive leading-zero timeouts (e.g. `010`) are accepted: launcher exits 0 with the standard five-line stdout envelope. Pins acceptance of the leading-zero positive form so a future refactor tightening the digit-only `case` validation (e.g. to `^[1-9][0-9]*$`) breaks CI. Note: the stub exits immediately, so this does NOT prove that downstream treats `010` as decimal 10 vs. octal 8 — only contract stability at the launcher boundary.
- Missing input files exit 2 with the launcher's literal validation messages — specifically: missing `--plan-file` (`plan file not found`), missing `--feature-file` (`feature file not found`), missing `--agent-prompt` (`agent prompt not found`), and `--answers-file` pointing at a non-existent path (`--answers-file given but path does not exist`).
- PATH-stubbed `codex` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- Env-derived `LARCH_TIMING_TASK_KIND=--prompt` falls back to `codex-implement` in the timing TSV instead of leaking the flag-shaped value.
- Invalid `LARCH_CODEX_MODEL` values fail during model-args resolution with wrapper exit 0, a non-zero `LAUNCHER_EXIT`, forced-false manifest flags, and a freshly truncated diagnostic sidecar. The dispatcher path retries that clean preflight failure once and then classifies it as `codex-runtime-failure`.
- Codex's `--output-last-message` transcript path receives the stubbed output payload.
- Codex argv shape includes `exec`, `--full-auto`, `-C "$PWD"`, canonical `--add-dir "$(cd "$(dirname "$MANIFEST")" && pwd -P)"` immediately after `-C "$REPO_ROOT"`, `--output-last-message`, and model/effort args from `scripts/agent-model-args.sh --tool codex --with-effort`.
- The composed prompt is passed after a `--` end-of-options separator and is the last positional argv argument.
- Passing `--answers-file` adds the `## Resume invocation` block to the composed prompt.
- The launcher exits 2 with a "must share the same parent directory" error when `--manifest-path` and `--qa-pending-path` resolve to different parents.
- The launcher exits 2 with a "session tmpdir does not exist" error when the manifest parent directory is absent.

**Invariants**:
- The always-on path must stay offline and must not call the real `codex` binary.
- The stub records argv one argument per line so ordering assertions preserve argument boundaries.
- The test sets `LARCH_CODEX_MODEL=stub-codex-model` to avoid environment-specific model drift and to pin model forwarding.
- The test relies on the default Codex effort (`high`) emitted by `agent-model-args.sh --with-effort`.
- The stub writes the manifest atomically (`.tmp` then `mv`) so launcher detection mirrors production.
- The harness unsets inherited session tempdir variables and points `LARCH_EXECUTION_ISSUES_LOG` at its scratch dir so failures cannot append to a parent `/implement` run's log.

**Call sites**:
- `make test-codex-implementer`.
- `make test-harnesses-3`.

**Edit-in-sync**:
- `scripts/launch-codex-implement.sh` — launcher behavior under test.
- `scripts/launch-codex-implement.md` — sibling launcher contract.
- `agents/codex-implementer.md` — prompt body path and resume block expectations.
- `scripts/run-external-agent.sh` — transcript and sidecar capture semantics.
- `scripts/agent-model-args.sh` — Codex model and effort argv generation.
