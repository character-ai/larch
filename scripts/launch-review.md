# launch-review.sh

**Purpose**: Unified external reviewer launcher. `--tool codex|cursor|gemini`
selects the vendor path while preserving the former review-launcher contracts:
Codex and Cursor support generic prompts plus specialist `--agent-file` modes;
Gemini remains generic-only and rejects specialist flags.

## Invariants

- `--tool` is required and must be one of `codex`, `cursor`, or `gemini`.
- `--output` is validated through `scripts/lib-validate-meta-path.sh` before
  launcher side effects.
- Codex and Cursor append `OUTER_LAUNCHER=<repo>/scripts/launch-review.sh`
  metadata and store `${OUTPUT}.prompt` so `collect-agent-results.sh` can replay
  retries through the same launcher with `--tool <tool>`.
- Gemini writes launcher-shaped `CMD_JSON` containing
  `launch-review.sh --tool gemini ...` so retries re-run JSON normalization,
  prompt hardening, model resolution, and snapshot-guard logic.
- Timing rows default to `<tool>-review`; CLI `--timing-task-kind` values must
  be non-empty and non-flag-like.
- Token budget cap handling is shared across all three tool paths via
  `--token-budget-cap` or `LARCH_TOKEN_BUDGET_CAP_REVIEW`.
- Codex receives a compact read-only hardening preamble through
  per-invocation `CODEX_HOME/config.toml`; Cursor receives the same compact
  prohibition in the wrapped prompt plus a `--mode plan` enforcement note.

## Primary Callers

- `skills/implement/SKILL.md` quick review fan-out.
- `skills/design/SKILL.md` and design references for plan/sketch reviewers.
- `skills/review/SKILL.md` specialist and generic review fan-out.
- `scripts/collect-agent-results.sh` empty-output retry replay.

## Harness

Run `make test-launch-review`. The harness ports the previous Codex, Cursor,
and Gemini launcher assertion sets and adds direct coverage for missing,
invalid, and Gemini-incompatible `--tool` forms.

## Edit In Sync

Update `scripts/test-launch-review.sh`, `scripts/collect-agent-results.sh`,
`scripts/test-collect-agent-retry.sh`, `docs/linting.md`, external-reviewer
docs, and the skill call sites whenever argv grammar, sidecar shape, retry
metadata, timing, budget-cap, or read-only hardening behavior changes.
