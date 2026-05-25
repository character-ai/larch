# cursor-wrap-prompt.sh

**Purpose**: single source of truth for the Cursor max-mode prompt-level prefix. Wraps a prompt so that Cursor activates max-mode for that invocation regardless of user CLI config.

## Contract

- **Input**: exactly one positional argument — the raw prompt string.
- **Output (stdout)**: <code>&nbsp;/max-mode on. Prompt: &lt;prompt&gt;</code> (leading `U+0020` space intentional, no trailing newline).
- **Exit codes**: `0` on success; `1` if no argument supplied.
- **Implementation**: `printf ' /max-mode on. Prompt: %s'` (not `echo`) so the prompt content passes through literally without re-interpreting backslash escapes.

## Why

Cursor supports `~/.cursor/cli-config.json` for model pinning and max-mode. Each larch invocation uses a private per-invocation config directory (exported via `CURSOR_CONFIG_DIR` by `cursor_launcher_setup_private_config_dir` in `lib-cursor-launcher-common.sh`) seeded from the user's `cli-config.json` to avoid the rename race under parallel `cursor agent` processes (issue #2022). The prompt-level `/max-mode on.` slash command is the additional mechanism larch controls to request max-mode from its own invocations, independent of the config file. This wrapper owns the literal so every Cursor invocation goes through one file.

Cursor also has no way to configure a non-default model via config file that overrides the CLI's own fallback; larch passes `--model` on the command line via `scripts/agent-model-args.sh`. The two concerns are kept in separate single-source-of-truth files.

## Callers

- `scripts/launch-review.sh --tool cursor` — canonical Cursor launch wrapper; all SKILL.md Cursor reviewer/sketch/debater launches now route through this script.
- `scripts/launch-cursor-implement.sh` — Cursor implementer launcher for `/implement --coder=cursor`.
- `skills/research/references/validation-phase.md` — Cursor validation-reviewer launch (research lanes themselves are Codex-first; Cursor is not used for research lanes).
- `skills/shared/voting-protocol.md` — Cursor voter template.
- `skills/shared/dialectic-protocol.md` — Cursor judge template.
- `scripts/run-negotiation-round.sh` — Cursor negotiation-round branch.
- `scripts/lint-fix-loop.sh` — Cursor lint-fix coder branch (`run_cursor`).
- `scripts/check-reviewers.sh` — Cursor presence probe (`larch_run_one_cursor_probe`).
- `skills/review-and-fix/scripts/review-and-fix.sh` — Cursor coder fallback inside the review-fix coder dispatch.

**Migrated to `launch-review.sh --tool cursor`** (no longer direct callers):
- `skills/design/SKILL.md` (was 1 — plan-review Cursor reviewer)
- `skills/design/references/sketch-launch.md` (was 3 — sketch slots)
- `skills/design/references/dialectic-execution.md` (was 1 — debater launch)
- `skills/review/SKILL.md` (was 2 — diff/description Cursor reviewer blocks)
- `skills/implement/SKILL.md` (was 1 — quick-mode Cursor reviewer)

## Non-callers (intentional exclusions)

- `scripts/run-external-agent.sh` header example — illustrative of the wrapper's own tool interface, not a real invocation.

Note: `scripts/check-reviewers.sh` was previously listed as an intentional exclusion to keep the probe fast/cheap. As of the composer-2.5 + max-mode uniformity sweep it now wraps the probe prompt and passes `--model composer-2.5` so the probe matches what production Cursor invocations will see (auth/quota issues that are model-specific become visible at probe time).

## Edit-in-sync rules

- If the prefix literal changes, update `scripts/cursor-wrap-prompt.sh`, this file, and `scripts/agent-model-args.sh`'s `Cursor max-mode:` comment block in the same PR.
- When adding a new Cursor call site, append the file to the callers list above and route through this wrapper.
