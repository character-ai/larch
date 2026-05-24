# dry-runnable-scripts.tsv

Opt-in registry for `/design` plan-command **Tier 3** dry-run validation (`validate-plan-commands.sh`).

## Schema

TSV with header row:

- `script_path` — repo-relative path to the shell script.
- `hook` — either `LARCH_DRY_RUN=1` (execute via `env LARCH_DRY_RUN=1 …`) or `--validate-only` (append that flag after the plan-derived argv).
- `doc_anchor` — short pointer to the script’s sibling `.md` section that documents the hook.

## Conventions

- **`LARCH_DRY_RUN=1`**: the script must treat this environment variable as a no-side-effects validation mode (documented in its sibling `.md`).
- **`--validate-only`**: the script must accept this long flag and exit without mutating production state.

## Opt-in workflow

1. Declare the dry-run contract in the script’s sibling `.md`.
2. Add a row to `dry-runnable-scripts.tsv`.
3. Keep Tier 3 behavior safe: argv-array execution only, cwd pinned to repo root, 10s timeout, metacharacter rejection (see `SECURITY.md`).
