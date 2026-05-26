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
- Tier 2 `--help` capture merges **stdout and stderr** (quiet-aware scripts may route usage to stderr) and treats help as available when the capture is **non-empty** and the probe exits **0**, or exits **1** or **2** with a non-empty capture (usage-style non-zero exits). Flag documentation checks use the same capture with **long-option boundary** matching (not naive substring grep) so `--file` cannot false-match against `--files` in help text.

## Time bounds

`--help` and Tier 3 dry-run probes require a wall-clock cap: use GNU `timeout` / `gtimeout` when present, otherwise **`perl` with `alarm`** (same exit code **124** semantics as GNU timeout when the alarm fires). The Perl fallback sets `PERL_BADLANG=0` so locale warnings cannot contaminate merged `--help` captures. If none of these are available, the script exits **2** during startup instead of running unbounded children.

## Tier 3

Disabled when `--source-kind composed` (pre-redaction `composed-plan.md`). Otherwise requires a row in `scripts/dry-runnable-scripts.tsv`. Dry-run subprocesses run under `env -i` with a small explicit allowlist, with `cwd` pinned to the repo root.

**Argv contract (narrow)**: Tier 3 builds the child **argv** as the resolved script path plus **only** long options from the plan (`--name` / `--name=value` tokens). **Short** single-dash flags and **non-flag positional** tokens from the fenced command are **not** replayed. Dry-runnable scripts must not rely on omitted tokens for safety-critical behavior under `LARCH_DRY_RUN=1`; use long-flag-only contracts, `--validate-only`, or extend the parser/TSV if a script truly needs literal positionals replayed.

The registry **`hook`** column must be exactly `LARCH_DRY_RUN=1` or `--validate-only`; any other value is a **defect** (`kind=unknown-registry-hook`), not a silent alias.

Validator log lines record Tier 3 child output only as a **bounded, redacted excerpt** (first 64 KiB through `scripts/redact-secrets.sh` when executable), not unlimited verbatim capture.
