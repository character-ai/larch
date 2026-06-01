## Proposed Design Outline

### Goals
- Add one helper that reads the three ledger keys from `session-env.sh` and emits both `token-ledger.sh mark` + `timing-ledger.sh mark`.
- Collapse the repeated read+export+mark telemetry trio at eligible `/implement` step-entry sites to a single helper call.
- Cut per-step context cost while keeping telemetry behavior byte-for-byte identical.

### Non-goals
- Do not move or fold the Step 18 closing `Step 18 — done` cap (stays orchestrator-emitted/inline).
- Do not change ledger semantics, mark labels, or `token-report.sh` vendor-table slicing.
- Do not generalize the helper beyond `/implement` (no speculative `--session-env` interface).

### Approach sketch
- New `scripts/step-telemetry-mark.sh --implement-tmpdir <dir> --label <label>` + sibling `scripts/step-telemetry-mark.md` contract.
- Helper reads `LARCH_TOKEN_SESSION_ID` / `LARCH_CLAUDE_SOURCE_FILE` / `LARCH_TIMING_LEDGER` from `$IMPLEMENT_TMPDIR/session-env.sh`, exports them, runs both marks best-effort (`|| true`, always exit 0).
- Convert only adjacent, unconditional step-entry mark pairs; leave the branchy Step 2 `case` marks and the Step 18 closing cap inline (audit each site).
- Keep the `CLAUDE_PLUGIN_ROOT` rehydration one-liner; replace only the trio+2-marks block with the helper call.

### Surfaces in scope
- `scripts/step-telemetry-mark.sh` + `scripts/step-telemetry-mark.md`
- `skills/implement/SKILL.md` (eligible step-entry preambles + any stale prose counts)
- `scripts/test-implement-timing-rehydration.sh` (update pinned mark form) + new helper unit test
- `Makefile` (register the new test target)

### Open questions
- None.
