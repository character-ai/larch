# launch-cursor-review.sh

**Purpose**: Wrap the Cursor agent launch pattern (agent-model-args + cursor-wrap-prompt + optional render-specialist-prompt + run-external-agent) into a single script invocation. Eliminates `$(...)` command substitution from SKILL.md Bash blocks that triggered "Contains command_substitution" permission prompts.

**Invariants**:
- Prompt passed only as argv; no `eval`; no unsafe expansion. The post-wrapper test hook is gated behind two opt-in env vars and `source`s a regular non-symlink file (no env-var → arbitrary-shell channel; see "Test hook" below)
- No additional stdout beyond what `run-external-agent.sh` produces
- Validates `--output` through `scripts/lib-validate-meta-path.sh`, rejects empty / non-numeric `--timeout`, and rejects `--timeout` values that arithmetic-evaluate to less than `1` (catches both literal `0` and zero-padded `00` / `000` / `0000`) before creating launcher sidecars or sentinels. Also rejects missing or multiple prompt sources before any side effect.
- Runs `run-external-agent.sh` without `exec` so the launcher can perform best-effort post-call token handling, then exits with `run-external-agent.sh`'s exit code
- Redirects wrapper stderr to `${OUTPUT}.sidecar` when possible; if the sidecar cannot be opened, stderr falls back to `/dev/null`
- Invokes `run-external-agent.sh` with `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done`; the wrapper writes `${OUTPUT}.inner.done`, and this launcher publishes `${OUTPUT}.done` only after post-processing finishes on the normal success path
- Uses `--capture-stdout-only` and `--output-format json`. Before copying the wrapper's bytes, the launcher removes any stale `${OUTPUT}.json` from a prior run so a failed `cp` (full disk, transient I/O, permission) cannot leave the prior-run JSON in place to mislead the subsequent `jq` extraction or token scrape. On `cp` failure, the launcher leaves `$OUTPUT` as the wrapper-provided bytes (raw JSON or prose) and skips the post-processing block — collectors still see bounded content, just without launcher-extracted `.result` or token-ledger update for this run. On `cp` success, the launcher extracts `.result` back into `$OUTPUT` for existing collectors and records `.usage` as `cursor_review` in `scripts/token-ledger.sh`
- Appends `OUTER_LAUNCHER`, `OUTER_LAUNCHER_PROMPT_FILE`, and `OUTER_LAUNCHER_WORKDIR` to `${OUTPUT}.meta` after the wrapper exits so empty-output retry can replay through this launcher and inherit the same post-processing
- Stores the original unwrapped prompt in `${OUTPUT}.prompt`; outer retries use `--prompt-file` to replay those bytes without re-rendering or losing trailing newlines
- Installs an EXIT trap that promotes `${OUTPUT}.inner.done` to `${OUTPUT}.done`, or writes synthetic `99` if the wrapper failed before producing an inner sentinel. If the launcher exits abnormally during post-processing, `${OUTPUT}.done` can appear while `${OUTPUT}` still contains raw JSON envelope bytes; collectors must tolerate that abnormal-exit fallback.
- If the launcher is signaled while the wrapper child is still alive, the EXIT trap kills and reaps the child before publishing `${OUTPUT}.done`, avoiding a race between the wrapper's inner sentinel and the launcher's public sentinel
- **Test hook**: the post-wrapper deterministic seam is reached only when `LARCH_ALLOW_TEST_HOOKS=1` (exact string match) AND `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` points at a regular non-symlink file the harness wrote under its own tmpdir. The launcher then `source`s that file. Production callers must NOT set either env var. The legacy single-env-var name `LARCH_TEST_TRAP_AFTER_INNER_DONE` (without `_FILE`) is intentionally NOT honored — silent fallback would defeat the gating. This replaces an earlier `eval "$LARCH_TEST_TRAP_AFTER_INNER_DONE"` design that was an env-var → arbitrary-shell channel in shipped runtime code.
- Specialist mode calls `render-specialist-prompt.sh` internally, supporting all flags

**Stdout contract**: Same stdout as `run-external-agent.sh`; no `LAUNCHER_EXIT=` line. Exit code is `run-external-agent.sh`'s exit code after best-effort JSON-sidecar extraction and token scrape.

**Flags**:
- `--output FILE` — (required) output file path
- `--timeout SECS` — (required) timeout in seconds
- `--prompt TEXT` — generic mode prompt text (mutually exclusive with `--agent-file` and `--prompt-file`)
- `--prompt-file FILE` — generic mode prompt file, read with the sentinel-byte idiom so trailing newlines are preserved (mutually exclusive with `--prompt` and `--agent-file`)
- `--agent-file FILE` — specialist mode agent definition file (mutually exclusive with `--prompt` and `--prompt-file`)
- `--mode diff|description` — specialist review mode (requires `--agent-file`)
- `--description-text TEXT` — review target description (required when `--mode=description`)
- `--scope-files PATH` — canonical scope files list (required when `--mode=description`)
- `--competition-notice` — append competition notice to specialist prompt

**Call sites**:
- `skills/implement/SKILL.md` Step 5 (quick-mode specialists + generic reviewers)
- `skills/design/SKILL.md` Step 3 (4 Cursor archetype reviewers)
- `skills/design/references/sketch-launch.md` (4 regular + 1 quick Cursor sketch slots)
- `skills/design/references/dialectic-execution.md` (Cursor debater launches)
- `skills/review/SKILL.md` (Cursor specialist + generic reviewer)
- `scripts/collect-agent-results.sh` empty-output retry path, when `OUTER_LAUNCHER*` metadata is present and valid

**Edit-in-sync**: `scripts/agent-model-args.sh`, `scripts/cursor-wrap-prompt.sh`, `scripts/render-specialist-prompt.sh`, `scripts/run-external-agent.sh`, `scripts/collect-agent-results.sh`, `scripts/test-launch-cursor-review.sh`, and `scripts/test-collect-agent-retry.sh`. Update `scripts/cursor-wrap-prompt.md` callers registry when adding/removing call sites.
