# launch-codex-review.sh

**Purpose**: Wrap the Codex agent launch pattern (agent-model-args + optional render-specialist-prompt + run-external-agent) into a single script invocation. Eliminates `$(...)` command substitution from SKILL.md Bash blocks that triggered "Contains command_substitution" permission prompts.

**Invariants**:
- Prompt passed only as argv; no `eval`; no unsafe expansion
- Validates `--output` via `lib-validate-meta-path.sh::validate_meta_scalar_path` BEFORE installing traps, sidecars, or any other side effects (parity with `scripts/launch-cursor-review.sh:60-62`); the same byte-exact `.meta`-sidecar contract enforced for Cursor review applies on the Codex path so retry substitution stays byte-identical with the recorded `CMD_JSON` element.
- No additional stdout beyond what `run-external-agent.sh` produces
- Runs `run-external-agent.sh` without `exec` so the launcher can perform a best-effort post-call token scrape, then exits with `run-external-agent.sh`'s exit code
- Redirects wrapper stderr to `${OUTPUT}.sidecar` when possible and silently scrapes the last `tokens used` block into `token-ledger.sh` as `codex_review`; if the sidecar cannot be opened, stderr falls back to `/dev/null`
- Uses `--output-last-message` for Codex output (no `--capture-stdout`)
- Grants Codex write access to the canonical parent directory of `--output` via `--add-dir "$CANON_OUTPUT_DIR"` immediately after `-C "$PWD"`, matching the implementer-lane sandbox posture.
- Reads `agent-model-args.sh` line-token stdout into a Bash array and expands it with `${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"}` so model values containing spaces remain one argv token and producer-side validation failures abort before Codex is launched.
- Specialist mode calls `render-specialist-prompt.sh` internally, supporting all flags

**Stdout contract**: Same stdout as `run-external-agent.sh`; no `LAUNCHER_EXIT=` line. Exit code is `run-external-agent.sh`'s exit code after the best-effort post-call token scrape.

**Flags**: Same as `launch-cursor-review.sh` (see `scripts/launch-cursor-review.md`).

**Call sites**:
- `skills/implement/SKILL.md` Step 5 (quick-mode specialists + generic reviewers)
- `skills/design/SKILL.md` Step 3 (Codex generic reviewer + archetype fallbacks)
- `skills/design/references/sketch-launch.md` (4 regular + 1 quick Codex sketch slots)
- `skills/design/references/dialectic-execution.md` (Codex debater launches)
- `skills/review/SKILL.md` (Codex specialist + generic reviewer)

**Edit-in-sync**: `scripts/agent-model-args.sh`, `scripts/render-specialist-prompt.sh`, `scripts/run-external-agent.sh`, `scripts/test-launch-codex-review.sh`. Differs from `launch-cursor-review.sh` in: no `cursor-wrap-prompt.sh` call, no `--capture-stdout`, uses `--output-last-message`.
