# parse-plan-commands.sh

Deterministic markdown parser for `/design` plan bodies: extracts fenced `bash` / `sh` commands and NEW/UPDATED allow-list rows into a single TSV (see normative schema in `skills/design/SKILL.md`).

## CLI

```text
parse-plan-commands.sh --plan-file FILE --output FILE [--repo-root DIR]
```

- Exits **0** on success (including empty fenced blocks → header-only TSV).
- `--repo-root` defaults to `git rev-parse --show-toplevel` from the script’s repo.

## Output

TSV columns: `row_type`, `source_line`, `script_path`, `flag`, `flag_value`, `note`, `cmd_uid`.

- **`source_line`**: physical markdown line number (1-based) of the shell line the command segment came from inside the opening fence (the fence’s own ` ```bash ` line is not counted as a command line).
- **`note`**: human or downstream notes for non-invocation rows; **empty** for `invocation` and `invocation_no_flags` rows.
- **`cmd_uid`**: monotonic per-run identifier grouping multiple `invocation` rows that belong to the same parsed command (same argv); empty for `new_script`, `updated_flag`, and `parse_note` rows.

Primary consumer: `validate-plan-commands.sh` via `validate-plan.sh`.

## Fenced `bash` / `sh` blocks

- Backslash line continuations are joined before further processing.
- **Heredocs**: bodies between `<<DELIM` / `<<'DELIM'` / `<<"DELIM"` and a closing line containing only `DELIM` are removed from the physical line stream so later commands in the same fence are still parsed. Unterminated `<<"…` openers emit a `parse_note` and leave the line intact (no silent fast-forward to EOF).
- Command lines are split on `|`, `&&`, `||`, and `;` outside quotes and outside balanced `(...)`.
- Interpreter prefixes (`bash`, `sh`, `env`, …), leading `VAR=value`, and `${CLAUDE_PLUGIN_ROOT}` / repo-root absolute prefixes are stripped when resolving `script_path`.
- **Rejected / noted constructs**: subshells `$()`, process substitution `<(`, `eval`, inline `-c`, absolute script paths, and paths containing `..` after normalization → `parse_note` rows (validator ignores them as invocations).

## Allow-list sections

Parser recognizes `### Files to create` / `### Files to update` (and compatible `##` headings), `### NEW:` / `### UPDATED:` headings, bullet `**NEW**` / `**UPDATED**` paths, and `- Adds flag: --name` bullets under an UPDATED path.

## Charset

Tab, newline, or carriage return inside allow-listed paths, flags, or flag values produce `parse_note` / charset failures instead of malformed TSV fields.
