# render-debate-retry-prompt.sh

Primary script: `render-debate-retry-prompt.sh` (same directory).

## Purpose

Builds a **corrective** dialectic debater prompt for waterfall retries: failure summary at the top, a bounded excerpt of `--previous-output-file`, explicit re-emit instruction, then the original task body verbatim (from `--original-prompt-file`). For `--retry-tool claude`, appends a self-identification prohibition line.

## Contract

- **Stdout**: machine-parseable KV lines only — `RENDERED=true` and `OUTPUT_FILE=<path>` (no secrets).
- **Stderr**: human-readable errors (exit 2).
- **Atomic write**: caller path is written via `*.tmp` + `mv` internally.

## `--failure-reason`

Comma-separated **top-level** tokens. Each token head (text before `:` if present) must be one of: `missing_tag`, `bad_recommend`, `missing_citation`, `role_mismatch`, `substantive_empty`, `no_output`. Unknown heads are rejected (exit 2). Commas **inside** `missing_tag:…` detail lists are supported (the renderer splits only on commas that start a new known keyword such as `missing_citation,…`). Semicolon-separated lists (`a;b`) bypass comma splitting entirely.

## Callers

- `/design` Step 2a.5 per `skills/design/references/dialectic-execution.md` step **5** (per-side waterfall retry).

## Tests

- `scripts/test-render-debate-retry-prompt.sh` (harness-timer via Makefile).

## Edit-in-sync

Update this `.md` when changing CLI flags, stdout KV contract, or retry prompt shape.
