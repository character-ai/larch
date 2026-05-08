# launch-codex-review.sh

**Purpose**: Wrap the Codex agent launch pattern (agent-model-args + optional render-specialist-prompt + run-external-agent) into a single script invocation. Eliminates `$(...)` command substitution from SKILL.md Bash blocks that triggered "Contains command_substitution" permission prompts.

**Invariants**:
- Prompt passed only as argv; no `eval`; no unsafe expansion
- Validates `--output` via `lib-validate-meta-path.sh::validate_meta_scalar_path` BEFORE installing traps, sidecars, or any other side effects (parity with `scripts/launch-cursor-review.sh:60-62`); the same byte-exact `.meta`-sidecar contract enforced for Cursor review applies on the Codex path so retry substitution stays byte-identical with the recorded `CMD_JSON` element.
- No additional stdout beyond what `run-external-agent.sh` produces
- Runs `run-external-agent.sh` without `exec` so the launcher can perform a best-effort post-call token scrape, then exits with `run-external-agent.sh`'s exit code
- Sources `scripts/lib-codex-launcher-common.sh` for inner-sentinel promotion and outer-launcher retry metadata (canonical bodies live in `scripts/lib-external-launcher-common.sh`), and `scripts/lib-dirty-tree-sidecar.sh` for the shared `_write_dirty_tree_sidecar` helper used in the EXIT trap.
- Redirects wrapper stderr to `${OUTPUT}.sidecar` when possible and silently scrapes the last `tokens used` block into `token-ledger.sh` as `codex_review`; if the sidecar cannot be opened, stderr falls back to `/dev/null`
- Before token-ledger scraping or spawning Codex, the wrapper rehydrates token context from `IMPLEMENT_TMPDIR` when present: `$IMPLEMENT_TMPDIR/session-id` overwrites any stale `LARCH_TOKEN_SESSION_ID`, and `$IMPLEMENT_TMPDIR/claude-source.env` becomes `LARCH_CLAUDE_SOURCE_FILE`.
- Captures `TIMING_START_S` after argv validation and emits one best-effort `timing-ledger.sh record-vendor-task` row on EXIT. `--timing-task-kind <kind>` defaults to `codex-review`; timing failures are silent and never affect stdout or exit code. **Validation**: when `--timing-task-kind` is supplied via the CLI, the value must be non-empty and must not begin with `--`; otherwise the launcher exits 2 with `--timing-task-kind requires a non-empty, non-flag-like value` on stderr (issue #1480 defense-in-depth against argv-shape collapse from a broken env-var-prefix expansion in the caller). Env-derived `LARCH_TIMING_TASK_KIND` that is empty or starts with `--` silently falls back to the per-launcher default (for example, `codex-review`). The CLI `--timing-task-kind` flag still hard-rejects empty / flag-shaped values with exit 2.
- Uses `--output-last-message` for Codex output (no `--capture-stdout`)
- Invokes `run-external-agent.sh` with `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done`; the wrapper writes `${OUTPUT}.inner.done`, and the launcher publishes `${OUTPUT}.done` only after token scraping and dirty-tree sidecar publication complete.
- Before launching, removes stale `${OUTPUT}.dirty-tree` / `${OUTPUT}.untracked-baseline` sidecars and captures a NUL-delimited untracked baseline. On exit, writes `${OUTPUT}.dirty-tree` via `check-mid-run-dirty-tree.sh --mode baseline` before promoting `${OUTPUT}.inner.done` to `${OUTPUT}.done`.
- Stores the original prompt in `${OUTPUT}.prompt`, accepts `--prompt-file`, and appends `OUTER_LAUNCHER`, `OUTER_LAUNCHER_PROMPT_FILE`, and `OUTER_LAUNCHER_WORKDIR` to `${OUTPUT}.meta` so empty-output retry re-enters this launcher and re-runs the dirty-tree guard.
- **Read-only sandbox at spawn time (issue #1529)**: invokes `codex exec --sandbox read-only` (replacing the prior `--full-auto` workspace-write mode) so model-issued shell commands cannot mutate the working tree. Pairs with the `CODEX_REVIEW_HARDENING_PREAMBLE` heredoc that prepends a HARD CONSTRAINTS block to every prompt (specialist or generic, `--prompt` / `--prompt-file` / `--agent-file`) so the model also reasons about its read-only role. The dirty-tree-sidecar machinery (`snapshot-untracked.sh` baseline + `_write_dirty_tree_sidecar` on EXIT) remains as the after-the-fact detector consumed by `/review` Step 3a recovery and `/implement` Step 5's mid-run scan.
- Grants Codex write access to the canonical parent directory of `--output` via `--add-dir "$CANON_OUTPUT_DIR"` immediately after `-C "$PWD"`. Under the read-only sandbox introduced in issue #1529, `--add-dir` is benign (the sandbox blocks writes regardless); the flag is preserved for consistency with the implementer-lane argv.
- Reads `agent-model-args.sh` line-token stdout into a Bash array and expands it with `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}` so model values containing spaces remain one argv token and producer-side validation failures abort before Codex is launched.
- Specialist mode calls `render-specialist-prompt.sh` internally, supporting all flags

**Stdout contract**: Same stdout as `run-external-agent.sh`; no `LAUNCHER_EXIT=` line. Exit code is `run-external-agent.sh`'s exit code after the best-effort post-call token scrape.

**Flags**: Same as `launch-cursor-review.sh` (see `scripts/launch-cursor-review.md`), including optional `--timing-task-kind <kind>`.

**Call sites**:
- `skills/implement/SKILL.md` Step 5 (quick-mode specialists + generic reviewers)
- `skills/design/SKILL.md` Step 3 (Codex generic reviewer + archetype fallbacks)
- `skills/design/references/sketch-launch.md` (2 regular + 1 quick Codex sketch slots)
- `skills/design/references/dialectic-execution.md` (Codex debater launches)
- `skills/review/SKILL.md` (Codex specialist + generic reviewer)
- `scripts/collect-agent-results.sh` empty-output retry path, when valid Codex `OUTER_LAUNCHER*` metadata is present

**Edit-in-sync**: `scripts/lib-codex-launcher-common.sh`, `scripts/lib-external-launcher-common.sh`, `scripts/lib-dirty-tree-sidecar.sh`, `scripts/check-mid-run-dirty-tree.sh`, `scripts/snapshot-untracked.sh`, `scripts/agent-model-args.sh`, `scripts/render-specialist-prompt.sh`, `scripts/run-external-agent.sh`, `scripts/collect-agent-results.sh`, `scripts/test-launch-codex-review.sh`, and `scripts/test-collect-agent-retry.sh`. Differs from `launch-cursor-review.sh` in: no `cursor-wrap-prompt.sh` call, no `--capture-stdout`, uses `--output-last-message`.
