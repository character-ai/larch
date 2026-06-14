## Goal
Implement issue #4334: [IMPLEMENTING] Add dev-only /larch-size skill: repo line-count table + run-logs size report.

## Implementation Plan
## Plan

Add a dev-only `/larch-size` skill under `.claude/skills/larch-size/`. Do not modify `skills/`, `python/cli.py`, public docs, or plugin export metadata.

### NEW: .claude/skills/larch-size/SKILL.md

Create a dev-only skill prompt with frontmatter:

- `name: larch-size`
- `description:` includes a "Use when" trigger (agent-lint S017) noting it reports larch repo line counts and run-log sizes
- `allowed-tools: Bash`

Body instructs the agent to run:

```bash
python3 "$PWD/.claude/skills/larch-size/scripts/larch_size.py"
```

Pass the output through unchanged. No flags. Dev-only; not shipped by the plugin.

### NEW: .claude/skills/larch-size/scripts/larch_size.py

Stdlib-only Python script. Core functions:

- `git_ls_files(repo_root)` — runs `git ls-files -z`, splits on NUL, returns list of relative path strings.
- Categorize by extension + basename: Bash scripts (`*.sh`, basename not starting `test-`), Bash tests (`*.sh`, basename starting `test-`), Python code (`*.py`, basename not starting `test_`), Python tests (`*.py`, basename starting `test_`), Markdown (`*.md`). Exclude `larch-logs/` and `node_modules/` prefixes from line-count categories. Do not count `.inc.bash`.
- Count lines with `bytes.count(b"\n")` per file.
- Render the fixed box-drawing table (column widths: category 37, files 5, lines 6; thousands separators via `f"{n:,}"`).
- Sum `os.stat(...).st_size` for all tracked files (repo total), then for `larch-logs/`, `larch-logs/implement/`, `larch-logs/design/` prefixes. `rest = larch_logs_total - implement - design`. `repo_minus_logs = repo_total - larch_logs_total`.
- Print MB with two decimal places, percentages with one decimal place; zero-division guard when totals are zero.
- Do not add the optional `du -sh` line; keep output logical-byte only.
- Print output order: box table, blank line, size report.
- On `git` failure: print subprocess stderr to stderr and exit non-zero. On file-stat failure: print the repo-relative path to stderr and exit non-zero.

### Edge cases

- Paths with spaces or unusual characters: safe via `git ls-files -z` + Python path joining.
- Files without a trailing newline: final unterminated line not counted (`bytes.count(b"\n")` semantics).
- Empty `larch-logs/`: zero sizes and zero percentages.
- Future extra `larch-logs/` subdirs: absorbed into `rest`.
- Tracked `node_modules/` files: excluded from line counts; included in repo byte total.


## Test plan

Run from repo root:

```bash
python3 .claude/skills/larch-size/scripts/larch_size.py
```

Verify box table appears, live counts match categories, `larch-logs/` absent from line counts, `.inc.bash` absent from Bash counts, size report includes all six lines.

Check visibility:

```bash
git status --short .claude/skills/larch-size skills
```

Expected: new files only under `.claude/skills/larch-size/`; no changes under `skills/`.

Run the repo lint gate:

```bash
make lint
```

