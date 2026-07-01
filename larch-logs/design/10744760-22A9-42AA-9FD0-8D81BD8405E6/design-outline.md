## Proposed Design Outline

### Goals
- Record Read-tool calls on `skills/**/references/*.md` and `skills/shared/*.md` to `larch-tokens-*.jsonl` as `{"type":"read"}` events.
- Make `measure-references-heatmap` emit non-zero `reads_observed` rows from committed run-logs.
- Make `measure-realized-cost` include average reference-read token cost per invocation.

### Non-goals
- No edits to any reference `.md` file.
- No changes to `/design` or `/implement` step flow.
- No new timing-report or manifest artifacts.

### Approach sketch
- Add `TokenLedger.record_read(path, bytes)` emitting `{"type":"read","path":"...","bytes":N,"ts":"..."}`.
- Add `python/cli.py token record-ref-read --file-path <path>` CLI verb; resolves ledger via env or CC-session pointer.
- During design `step0-session`, write `~/.cache/larch/sessions/ledger-for-cc-{CC_SESSION_ID}.path` so the hook can find the active ledger; clean up at Step 6.
- Add PostToolUse hook `scripts/hook-ref-read-logger.sh` → calls `token record-ref-read`; exits 0 always.
- Update `measure_references_heatmap` to walk `larch-logs/*/*/larch-tokens-*.jsonl` and parse `type==read` events.
- Update `measure_realized_cost` to add `ref_tokens_per_invocation` (avg reference tokens per run) and `ref_tokens_realized` columns.

### Surfaces in scope
- `python/larch/report/tokens.py`
- `python/larch/cli.py`
- `python/larch/state/session_env.py` (CC ledger pointer write + cleanup)
- `hooks/hooks.json`
- `scripts/hook-ref-read-logger.sh` + `scripts/hook-ref-read-logger.md`
- `python/tests/report/test_tokens.py`

### Open questions
- None.
