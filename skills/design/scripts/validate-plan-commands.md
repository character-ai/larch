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

## Tier 3

Disabled when `--source-kind composed` (pre-redaction `composed-plan.md`). Otherwise requires a row in `scripts/dry-runnable-scripts.tsv`.
