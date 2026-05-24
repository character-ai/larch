# validate-plan.sh

`ACTION=VALIDATE_PLAN_COMMANDS` driver invoked by `design-driver.sh`.

## CLI

```text
validate-plan.sh --plan-file FILE [--repo-root DIR]
```

- Runs `parse-plan-commands.sh` then `validate-plan-commands.sh`.
- Infers `--source-kind` from basename (`plan.txt` → `plan`, `composed-plan.md` → `composed`).
- Emits `VALIDATE_STATUS`, `VALIDATE_DEFECT_COUNT`, `VALIDATE_SKIPPED_COUNT`, `VALIDATE_UNSAFE_TOKEN_COUNT`, and `VALIDATE_LOG_FILE` via `emit_kv` on FD 3.
- Copies the validator log to `$DESIGN_TMPDIR/validate-plan-commands.log` when `DESIGN_TMPDIR` is set.
- Exits **0** on successful pipeline (including `defects-found`).
