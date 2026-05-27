# test-cursor-implementer.sh

**Purpose**: Offline launcher-contract harness for `scripts/launch-cursor-implement.sh`. It verifies the Cursor implementer launcher without depending on a real Cursor installation, auth state, network, or model availability.

**Coverage**:
- Missing required flags exit 2.
- The generated Cursor prompt contains `## Manifest JSON template` and `## Self-validate before atomic rename`; the inline JSON template parses with `jq` and contains the canonical manifest field set.
- Asserts `agents/cursor-implementer.md` does NOT contain Hard guard #9 (Codex-only subprocess-tool prohibition) — guards against regression in `scripts/generate-cursor-implementer.sh`'s sed strip (issue #2991).
- Bad timeout exits 2.
- Zero-valued timeouts (`0`, `00`, `000`) exit 2 and report the positive-integer timeout contract.
- Positive leading-zero timeouts (e.g. `010`) are accepted: launcher exits 0 with the standard five-line stdout envelope. Pins acceptance of the leading-zero positive form so a future refactor tightening the digit-only `case` validation (e.g. to `^[1-9][0-9]*$`) breaks CI. Note: the stub exits immediately, so this does NOT prove that downstream treats `010` as decimal 10 vs. octal 8 — only contract stability at the launcher boundary.
- Missing input files exit 2 with the launcher's literal validation messages — specifically: missing `--plan-file` (`plan file not found`), missing `--feature-file` (`feature file not found`), missing `--agent-prompt` (`agent prompt not found`), and `--answers-file` pointing at a non-existent path (`--answers-file given but path does not exist`).
- PATH-stubbed `cursor` writes a minimal valid `manifest.json`; the launcher emits exactly five KV stdout lines and no progress chatter.
- Env-derived `LARCH_TIMING_TASK_KIND=--prompt` falls back to `cursor-implement` in the timing TSV instead of leaking the flag-shaped value.
- Invalid `LARCH_CURSOR_MODEL` values fail during model-args loading with wrapper exit 0, a non-zero `LAUNCHER_EXIT`, forced-false manifest flags, and a freshly truncated diagnostic sidecar. The dispatcher path retries that clean preflight failure once and then classifies it as `cursor-runtime-failure`.
- `run-external-agent.sh --capture-stdout-only` captures Cursor stdout to the transcript path while preserving JSON parseability.
- Cursor argv shape matches `scripts/launch-review.sh --tool cursor`: `cursor agent -p --force --trust --output-format json <model args> --workspace "$PWD" "$WRAPPED_PROMPT"`.
- The implementer launcher writes `${TRANSCRIPT_PATH}.prompt`, appends `OUTER_LAUNCHER*` keys to `${TRANSCRIPT_PATH}.meta`, and publishes `${TRANSCRIPT_PATH}.done` only after post-processing completes.
- No `--` end-of-options separator is inserted before the prompt.
- The prompt is wrapped by `scripts/cursor-wrap-prompt.sh`.
- Passing `--answers-file` adds the `## Resume invocation` block to the composed prompt.

**Optional smoke**: `CURSOR_PRESENT=true bash skills/implement/scripts/test-cursor-implementer.sh --real-smoke` launches a real `cursor agent` against a tiny prompt. This is a local development smoke only and is not wired into the Makefile.

**Invariants**:
- The always-on path must stay offline and must not call the real `cursor` binary.
- The stub records argv one argument per line so ordering assertions preserve argument boundaries.
- The test sets `LARCH_CURSOR_MODEL=stub-model` to avoid environment-specific model drift.
- The harness unsets inherited session tempdir variables and points `LARCH_EXECUTION_ISSUES_LOG` at its scratch dir so failures cannot append to a parent `/implement` run's log.

**Call sites**:
- `make test-cursor-implementer`.
- `make test-harnesses`.

**Edit-in-sync**:
- `scripts/launch-cursor-implement.sh` — launcher behavior under test.
- `scripts/launch-cursor-implement.md` — sibling launcher contract.
- `scripts/launch-review.sh --tool cursor` — argv parity source.
- `scripts/cursor-wrap-prompt.sh` and `scripts/cursor-wrap-prompt.md` — prompt wrapper contract and caller registry.
- `scripts/run-external-agent.sh` — stdout capture semantics.
- `scripts/agent-model-args.sh` — Cursor model argv generation.
