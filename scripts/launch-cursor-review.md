# launch-cursor-review.sh

**Purpose**: Wrap the Cursor agent launch pattern (agent-model-args + cursor-wrap-prompt + optional render-specialist-prompt + run-external-agent) into a single script invocation. Eliminates `$(...)` command substitution from SKILL.md Bash blocks that triggered "Contains command_substitution" permission prompts.

**Invariants**:
- Prompt passed only as argv; no `eval`; no unsafe expansion
- No additional stdout beyond what `run-external-agent.sh` produces
- Runs `run-external-agent.sh` without `exec` so the launcher can perform best-effort post-call token handling, then exits with `run-external-agent.sh`'s exit code
- Redirects wrapper stderr to `${OUTPUT}.sidecar` when possible; if the sidecar cannot be opened, stderr falls back to `/dev/null`
- Uses `--capture-stdout-only` and `--output-format json`, then moves raw Cursor JSON to `${OUTPUT}.json`, extracts `.result` back into `$OUTPUT` for existing collectors, and records `.usage` as `cursor_review` in `scripts/token-ledger.sh`
- Specialist mode calls `render-specialist-prompt.sh` internally, supporting all flags

**Stdout contract**: Same stdout as `run-external-agent.sh`; no `LAUNCHER_EXIT=` line. Exit code is `run-external-agent.sh`'s exit code after best-effort JSON-sidecar extraction and token scrape.

**Flags**:
- `--output FILE` — (required) output file path
- `--timeout SECS` — (required) timeout in seconds
- `--prompt TEXT` — generic mode prompt text (mutually exclusive with `--agent-file`)
- `--agent-file FILE` — specialist mode agent definition file
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

**Edit-in-sync**: `scripts/agent-model-args.sh`, `scripts/cursor-wrap-prompt.sh`, `scripts/render-specialist-prompt.sh`, `scripts/run-external-agent.sh`. Update `scripts/cursor-wrap-prompt.md` callers registry when adding/removing call sites.
