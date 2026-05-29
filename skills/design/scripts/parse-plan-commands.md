# parse-plan-commands.sh

Deterministic markdown parser for `/design` plan bodies: extracts fenced `bash` / `sh` commands and NEW/UPDATED allow-list rows into a single TSV (normative column contract in this file and `validate-plan-commands.md`; consumed by `validate-plan.sh`).

## CLI

```text
parse-plan-commands.sh --plan-file FILE --output FILE [--repo-root DIR]
```

- Exits **0** on success (including empty fenced blocks → header-only TSV).
- `--repo-root` defaults to `git rev-parse --show-toplevel` from the script’s repo.

## Output

TSV columns: `row_type`, `source_line`, `script_path`, `flag`, `flag_value`, `note`, `cmd_uid`.

**Field count**: seven tab-separated columns per data row (including `cmd_uid`); do not assume six columns when diffing parser output or issue-body plan tables.

- **`source_line`**: physical markdown line number (1-based) of the shell line the command segment came from inside the opening fence (the fence’s own ` ```bash ` line is not counted as a command line).
- **`note`**: human or downstream notes for non-invocation rows; **empty** for `invocation` and `invocation_no_flags` rows.
- **`cmd_uid`**: monotonic per-run identifier grouping multiple `invocation` rows that belong to the same parsed command (same argv); empty for `new_script`, `updated_flag`, and `parse_note` rows.

Primary consumer: `validate-plan-commands.sh` via `validate-plan.sh`.

## Fenced `bash` / `sh` blocks

This parser intentionally uses a simple `bash` / `sh` fence toggle, which differs from the plan-line dedup's two-pass balanced-pair model for heading/Constraints-state detection in [`dedup-plan-lines.md`](dedup-plan-lines.md). The two are not unified because they serve different concerns; plan-line dedup still collapses duplicate lines inside fences.

- Backslash line continuations are joined before further processing.
- **Heredocs**: bodies between `<<DELIM` / `<<'DELIM'` / `<<"DELIM"` and a closing line containing only `DELIM` are removed from the physical line stream so later commands in the same fence are still parsed. Unterminated `<<"…` openers emit a `parse_note` and leave the line intact (no silent fast-forward to EOF).
- Command lines are split on `|`, `&&`, `||`, and `;` outside quotes and outside balanced `(...)`.
- Interpreter prefixes (`bash`, `sh`, `env`, …), leading `VAR=value`, and `${CLAUDE_PLUGIN_ROOT}` / repo-root absolute prefixes are stripped when resolving `script_path`.
- **Rejected / noted constructs**: command substitution `$(` (but not arithmetic **`$((`…`))`**, which is left to the shell), process substitution `<(`, `eval`, inline `-c`, absolute script paths, and paths containing `..` after normalization → `parse_note` rows (validator ignores them as invocations).

## Allow-list sections

Parser recognizes `### Files to create` / `### Files to update` (and compatible `##` headings), `### NEW:` / `### UPDATED:` headings (and `##` forms), the bracket path variants `### NEW [path]:` / `### UPDATED [path]:` (and `##` forms), bullet `**NEW**` / `**UPDATED**` paths, and `- Adds flag: --name` bullets under an UPDATED path.

## Charset

Tab, newline, or carriage return inside allow-listed paths, flags, or flag values produce `parse_note` / charset failures instead of malformed TSV fields.
