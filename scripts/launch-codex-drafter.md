# launch-codex-drafter.sh

## Purpose

Read-only Codex plan drafter launcher for `/design` Step 2b. Wraps
`launch-codex-exec.sh` with a read-only sandbox, passes the drafter prompt,
and parses the `LARCH_PLAN_BEGIN/END` + `LARCH_SUMMARY_BEGIN/END` sentinel
output into `plan.txt` and `plan-summary.md` under `$DESIGN_TMPDIR`.

Produces the same status KV contract as `launch-claude-drafter.sh` so the
caller (`skills/design/SKILL.md` Step 2b) can handle both launchers
identically.

## Primary callers

- `skills/design/SKILL.md` Step 2b drafter fence (when `_step2b_drafter_vendor=codex`).

## Flags

| Flag | Required | Description |
|------|----------|-------------|
| `--prompt-file FILE` | yes | Drafter prompt text file (must be under DESIGN_TMPDIR or REPO_ROOT) |
| `--output-file FILE` | yes | Status KV output path (must be under DESIGN_TMPDIR) |
| `--timeout SECONDS` | yes | Wall-clock cap forwarded to `launch-codex-exec.sh` (1–1800) |
| `--design-tmpdir DIR` | yes | Design session tmpdir |
| `--repo-root DIR` | yes | Repository root (grants Codex read access via `--add-dir`) |
| `--timing-task-kind KIND` | no | Timing ledger kind; default `codex-plan-draft` |
| `--baseline-porcelain FILE` | no | Pre-launch `git status --porcelain` snapshot for dirty-tree detection |

## Output contract (mirrors launch-claude-drafter.sh)

On **stdout** (via `emit_kv`):
- `STATUS=OK|ERROR`
- `OUTPUT_FILE=<path>` — the status KV file path

In `--output-file` (status KV file):
- `STATUS=OK|ERROR`
- `PLAN_WRITTEN=true|false`
- `PLAN_LINES=<N>`
- `DIFF_LINES=<N>`
- `SUMMARY_WRITTEN=true|false`
- `DRAFTER_LAUNCHED=true|false`
- `REASON=<token>` (on ERROR)

Side files written under `<output-file>.*`:
- `.dirty-tree` — baseline-delta or absolute dirty-tree sidecar (always written)
- `.done` — exit code
- `.token-record` — stable Codex usage sidecar copied from the raw inner launcher before raw-output cleanup when usage parsed
- `.stderr` — Codex stderr on failure (removed on success)
- `.failure-diag` — failure classification token (on ERROR)
- `.stderr-tail` — redacted stderr tail via `write_failed_agent_stderr_tail` (on exec failure)

Under `DESIGN_TMPDIR`:
- `plan.txt` — extracted plan body ending with `diff_lines: N`
- `plan-summary.md` — extracted summary (when present in output)

## Implementation

Calls `launch-codex-exec.sh --sandbox read-only --add-dir REPO_ROOT`, captures
`LAUNCHER_EXIT` from its stdout, then parses the `--output-last-message` file
for plan sentinels using the shared `scripts/parse-drafter-output.py` helper.
Timing recording is handled inside `launch-codex-exec.sh`. Token sidecar
creation is also handled there, but this wrapper copies the raw
`${_codex_raw}.token-record` to stable `<output-file>.token-record` immediately
after the exec launcher returns. Success and failure paths can expose usage.
Step 2b owns exactly-once ingestion into `$DESIGN_TMPDIR/token-report.ndjson`
and the active design token ledger.

## Edit-in-sync

- `scripts/launch-claude-drafter.sh` — claude-side equivalent; keep status KV
  contract identical so SKILL.md Step 2b can use either launcher
- `scripts/parse-drafter-output.py` — shared sentinel parser called by both launchers
- `python/cli.py agent launch-codex-exec` — inner launcher; argv changes affect this wrapper
- `skills/design/SKILL.md` — Step 2b drafter dispatch block
- `docs/configuration-and-permissions.md` — `LARCH_DESIGN_DRAFTER` env var docs
- `python/timing.py TIMING_TASK_KINDS_ALLOWED` — `codex-plan-draft` kind registration

## Harness

`scripts/test-launch-codex-drafter.sh` covers launcher wiring, trusted-instructions
override, sentinel parsing, dirty-tree handling, failure branches, and argv
propagation. `scripts/test-launch-claude-drafter.sh` covers the Claude path with
the same shared Python sentinel parser logic.
