# validate-plan-commands.sh

Consumes the parser TSV; runs Tier 2 (existence + `--help` flag probe) and optional Tier 3 (registry-only dry-run).

## CLI

```text
validate-plan-commands.sh --tsv-file FILE --log-file FILE \
  [--dry-runnable-registry FILE] [--source-kind plan|composed] \
  [--help-timeout SEC] [--dry-run-timeout SEC]
```

- Emits human-readable log lines to `--log-file` and prints a single **tab-separated** summary line to stdout (last line of the log): `VALIDATE_STATUS=ok|defects-found`, `DEFECT_COUNT`, `SKIPPED_COUNT`, `UNSAFE_TOKEN_COUNT`.
- Exits **0** when the validator machinery completes (defects do **not** change the exit code).
- Tier 2 `--help` capture merges **stdout and stderr** (quiet-aware scripts may route usage to stderr) and treats help as available only when the capture is **non-empty** and the probe exits **0**. Flag documentation checks use the same capture with **long-option boundary** matching (not naive substring grep) so `--file` cannot false-match against `--files` in help text.

## Time bounds

`--help` and Tier 3 dry-run probes require a wall-clock cap: use GNU `timeout` / `gtimeout` when present, otherwise **`perl` with `alarm`** (same exit code **124** semantics as GNU timeout when the alarm fires). If none of these are available, the script exits **2** during startup instead of running unbounded children.

## Tier 3

Disabled when `--source-kind composed` (pre-redaction `composed-plan.md`). Otherwise requires a row in `scripts/dry-runnable-scripts.tsv`. Dry-run subprocesses run under `env -i` with a small explicit allowlist, with `cwd` pinned to the repo root.

Tier 3 argv is assembled from **long flags only** (`--name` / `--name=value` tokens). Non-flag positionals from the plan are not replayed in the dry-run argv (they may still appear in Tier 2 help coverage when folded into `--help` output); extend the parser/validator if a dry-runnable script requires literal positional arguments under `LARCH_DRY_RUN=1`.
