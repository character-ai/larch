# lib-phase-driver.sh

Shared **Bash** foundation for `/design` phase drivers (umbrella #3133). Sourced-only library; not executed directly.

## Shape

- **Driver** (`run-step3-review.sh`, future steps): owns deterministic setup, inner script invocation, result normalization, and atomic result `.env` writes.
- **Orchestrator** (`skills/design/SKILL.md`): owns LLM-boundary work (semantic dedup, gates, `AskUserQuestion`, adjudication).

## Gate hand-back

Driver emits normalized status KVs (and writes `$DESIGN_TMPDIR/.step3-review-result.env`) → orchestrator runs the gate / branch matrix → orchestrator may re-invoke the driver on a later Step 3 entry. No `--resume-from` in drivers; idempotency uses caller-owned sentinels (for example `.completed/step-3`) plus session files such as `review-round-count.txt`.

## File-based handoff

- Inputs: `$DESIGN_TMPDIR` artifacts, argv flags, session env (`CODEX_PRESENT`, `CURSOR_PRESENT`, optional `IMPLEMENT_TMPDIR`).
- Outputs: normalized result `.env` under `$DESIGN_TMPDIR`; contract breadcrumbs via `emit_kv` after `larch_quiet_init`.

## Primitives

| Function | Role |
|----------|------|
| `phase_driver_session_get` | Awk KV read from `KEY=VAL` lines |
| `phase_driver_resolve_plugin_root` | `CLAUDE_PLUGIN_ROOT` → session-env `LARCH_CLAUDE_PLUGIN_ROOT` → tree-walk from `skills/design/scripts` |
| `phase_driver_write_result_env` | Atomic `mktemp` + `mv` write; refuses symlink target |
| `phase_driver_read_result_env` | Allowlisted KV parse; refuses symlink source |

Diagnostics use `larch_err` / `emit_kv` from `scripts/lib-quiet.sh`.

## Language note

Implemented in Bash 3.2 now; may re-home when Python phase-driver infra lands. Keep the I/O surface small and language-neutral.

## First consumer

`run-step3-review.sh` — see `run-step3-review.md`.

## Harness

`skills/design/scripts/test-lib-phase-driver.sh` (contract stub: `test-lib-phase-driver.md`).
