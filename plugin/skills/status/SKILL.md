---
name: status
description: "Use when checking larch plugin health: reports the current larch version and checks availability of external vendor tools (Codex and Cursor) using the same probe machinery as /implement."
allowed-tools: Bash
---

# status

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Print the current larch version and health status of external vendor tools (Codex and Cursor). Uses the same probe machinery as `/implement` Step 0: `agent check-reviewers` for binary/runtime probes, then `agent degraded-tools-gate` to classify each vendor as `ok`, `binary-missing`, or `probe-failed`. When a vendor probe is `ok`, also resolves that vendor's pinned model ids from `config.py` against the vendor's live model list (Cursor via `cursor agent models`; Codex reports `unverifiable` because it has no model-list surface).

<!-- step:1 — Run status check -->

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" status check
```

Parse all KV pairs from stdout without `eval`/`source`. Extract at minimum:
`LARCH_PLUGIN_VERSION`, `CODEX_STATE`, `CURSOR_STATE`, `CODEX_BINARY_FOUND`,
`CURSOR_BINARY_FOUND`, `CODEX_PRESENT`, `CURSOR_PRESENT`, `DEGRADED`, the
optional `CODEX_PROBE_DETAIL`, plus model-pin keys `CURSOR_MODEL_PINS`,
`CODEX_MODEL_PINS`, and optional `CURSOR_MODEL_PIN_DETAIL` /
`CODEX_MODEL_PIN_DETAIL`.

<!-- step:2 — Render and report -->

Render a human-readable status report using the parsed values:

- **Version**: `LARCH_PLUGIN_VERSION`
- **Codex**: translate `CODEX_STATE` — `ok` → `ok`; `binary-missing` → `binary not found on PATH`; `probe-failed` with `CODEX_PROBE_DETAIL` → render that detail; other `probe-failed` → `binary found but runtime probe failed`; `unknown` → `probe did not run`
- **Cursor**: same translation using `CURSOR_STATE`
- **Cursor model pins** (when `CURSOR_MODEL_PINS` is present): `ok` → `model pins: ok`; `unknown-id` → `model pin unknown: <CURSOR_MODEL_PIN_DETAIL>` (names the id and owning config constant); `list-failed` → `model list failed: <CURSOR_MODEL_PIN_DETAIL>`; `unparseable` → `model list unparseable`; `skipped` → omit (vendor probe was not `ok`)
- **Codex model pins** (when `CODEX_MODEL_PINS` is present): `unverifiable` → `model pins: unverifiable (no model-list surface)`; `skipped` → omit; never treat silence as success

Model-pin non-ok states are soft health lines only: do not abort `/status` for them, and do not treat them as vendor `DEGRADED` by themselves.

When `DEGRADED=true`, append a brief note based on vendor availability: if exactly one vendor is unavailable, `/implement` requires explicit operator confirmation and then continues with that external dropped from the reduced panel; if both vendors are unavailable, `/implement` hard-fails until at least one vendor is fixed.

If the script exits non-zero, surface the error message and do not invent status values.
