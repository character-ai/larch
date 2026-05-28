# dispatch-plan-assessors.sh

Launches the Step 3.6 plan-quality assessor panel: one direct Claude lane plus a two-slot Codex/Cursor waterfall manifest. The script is quiet-by-default and writes machine-readable KVs to stdout for `assess-plan-round.sh`; human progress belongs on the breadcrumb stream.

## Inputs

- `--design-tmpdir DIR`: validated design session tmpdir. Output files and the generated manifest live directly under this directory.
- `--round-num N`: positive integer round number. Used to name prompt/output artifacts.
- `--plan-original PATH`, `--plan-prev PATH`, `--plan-current PATH`, `--feature-file PATH`: required regular files used to render the shared assessor prompt.
- `--codex-present true|false`, `--cursor-present true|false`: availability flags forwarded to the waterfall dispatcher.
- `--timeout SECS`: optional launcher timeout, default `1860`.

## Outputs

Stdout emits a KV block consumed by `assess-plan-round.sh`:

- `DISPATCH_OK=true|false`
- `CLAUDE_ASSESSOR_PATH=...`
- `CODEX_ASSESSOR_PATH=...`
- `CURSOR_ASSESSOR_PATH=...`
- `CLAUDE_ASSESSOR_STATUS=launched|failed`
- `CODEX_ASSESSOR_STATUS=launched|fallback|failed`
- `CURSOR_ASSESSOR_STATUS=launched|fallback|failed`
- `DEGRADED_PANEL_WARNING=true|false`
- Zero or more passthrough `WARN=...` lines from the waterfall helper

The helper also writes:

- `assessor-prompt-round-<N>.txt`
- `plan-assessor-slots.ndjson`
- `claude-plan-assessor-round-<N>.txt`
- `codex-plan-assessor-round-<N>.txt`
- `cursor-plan-assessor-round-<N>.txt`

## Contracts

- `render-assessor-prompt.sh` must succeed before any launcher runs.
- The waterfall leg uses `--require-result-pattern` pinned to an `ASSESSMENT:` header so narration-only model replies fail closed.
- A failed Claude lane does not invalidate successful Codex/Cursor outputs; callers use the per-slot statuses plus tally results to decide whether the panel degraded.
- Breadcrumb coverage is mandatory: the script emits progress breadcrumbs for prompt render, Claude completion, and waterfall completion so the paired monitor has stream traffic to surface.
