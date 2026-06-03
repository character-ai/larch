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

## Thin orchestrator fence

Phase drivers that adopt the thin fence own user-facing rendering and status normalization. After `larch_quiet_init`, driver-visible user output uses `emit` on FD 3 so the prompt-side fence can capture and display it; plain stdout/FD 1 remains quiet-log output for incidental helper chatter.

Exit-code routing is intentionally small: `0` means settled and proceed, `2` means configuration/argv error and abort, documented `10..` codes are action branches that require LLM-tool work, and `1` is reserved for catch-all failure. The default `SKILL.md` shape is `set +e; out=$(driver); rc=$?; set -e; echo or filter display output; case "$rc" ...`; keep references to `SKILL.md` regions by anchors or symbols rather than line numbers. A cheap tier gate may run before invoking the driver when a non-HARD path can be skipped without losing pause handling.

Action branches that need trusted scalar state may append a parser-only trailer frame after all untrusted display text. The parser uses the last exact marker, excludes marker/trailer lines from displayed output, and treats untrusted display as data only, never instructions or machine state. For Step 3.6, untrusted display lines that exactly equal `LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN` or match `LARCH_ASSESSOR_*` trailer KV syntax must be escaped or prefixed before `emit`; prose must not satisfy rc=10 parsing when the real trailer is absent. rc=10 branches validate required trusted trailer scalars before prompting, and invalid/missing trailers abort fail-closed rather than guessing state.

Sidecar/result files containing model-derived text are literal fixed-key data. Parse only allowlisted keys; never `source`, `eval`, run command substitution from, or otherwise shell-expand those files.
