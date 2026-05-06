# scripts/check-generators.sh - contract

`scripts/check-generators.sh` is the CI and local walker for `scripts/generators.tsv`. It validates every registry row, runs each generator in `--check` mode, then checks the registered generated artifacts for post-run working-tree drift.

## Purpose And Callers

Primary callers are the `agent-sync` job in `.github/workflows/ci.yaml`, the offline harness `scripts/test-check-generators.sh`, and manual local runs via `bash scripts/check-generators.sh`.

## Invariants

- Runs with `set -euo pipefail` and `LC_ALL=C`.
- Resolves `REPO_ROOT` from `${BASH_SOURCE[0]}`, then `cd`s there so caller cwd does not affect registry paths.
- Requires a git work tree.
- Processes rows sequentially in registry order and fails fast on the first validation or generator error.
- Requires each registered generator path and output path to exist as regular files.
- Requires registered output paths to be tracked by git.
- After all generators pass, runs `git diff HEAD --exit-code` over the registered output paths only. The `HEAD` comparison catches both unstaged and staged drift; a plain `git diff --exit-code` would miss staged-only changes (worktree==index but both differ from HEAD). This is **scoped, not whole-tree**: a generator that mutates an unregistered tracked file in `--check` mode would leave that file dirty and the walker would still exit 0. The trust model is "repo-local generators are reviewed code"; widening the post-run check to `git diff-index --quiet HEAD --` is a future-work option if the registry opens up to less-trusted contributors.

## TSV Parsing

The walker reads raw lines with `IFS= read -r line`. Lines whose raw first byte is `#` are comments, and strictly empty lines are skipped. CRLF line endings are rejected. Data rows are parsed with `awk -F '\t'`, requiring `NF == 2 && $1 != "" && $2 != ""`; the walker does not use `IFS=$'\t' read` because Bash collapses adjacent IFS whitespace and would miss empty columns.

## Registry Contract

Path grammar, one-row-per-generator-script, symlink-hardening scope, and the column 2 to generator-`--check` alignment rule are owned by `scripts/generators.md`. `scripts/generate-code-reviewer-agent.md` is the exemplar generator contract.

The script is Bash 3.2-compatible: duplicate detection uses plain arrays and linear scans, not associative arrays.

## Makefile Wiring

Target: `make test-check-generators`. A `make lint` prerequisite via `test-harnesses-5`; `test-harness-shards-coverage` must remain the first prerequisite of that shard. See `scripts/test-harness-shards-coverage.md` for the shard invariant.

## Edit In Sync

Changes to walker validation grammar or execution semantics must update `scripts/generators.md` and `scripts/test-check-generators.sh` fixtures in the same PR. Changes to Makefile shard wiring must update `docs/linting.md`.
