# parse-plan-commands.sh

Deterministic markdown parser for `/design` plan bodies: extracts fenced `bash` / `sh` commands and NEW/UPDATED allow-list rows into a single TSV (see normative schema in the implementation plan / `skills/design/SKILL.md`).

## CLI

```text
parse-plan-commands.sh --plan-file FILE --output FILE [--repo-root DIR]
```

- Exits **0** on success (including empty fenced blocks → header-only TSV).
- `--repo-root` defaults to `git rev-parse --show-toplevel` from the script’s repo.

## Output

TSV columns: `row_type`, `source_line`, `script_path`, `flag`, `flag_value`, `note`.

Primary consumer: `validate-plan-commands.sh` via `validate-plan.sh`.
