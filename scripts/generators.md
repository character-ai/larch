# scripts/generators.tsv - contract

`scripts/generators.tsv` is the registry consumed by `scripts/check-generators.sh`. Each non-comment row is a tab-separated `(generator-script, output-path)` pair: column 1 is the repo-relative generator script, and column 2 is the repo-relative committed artifact that the generator's `--check` mode validates.

## Format

- Rows use exactly two tab-separated columns. Empty first, middle, or last columns are invalid.
- Lines whose raw first byte is `#` are comments. Strictly empty lines are skipped. Comment and blank detection happens on the raw line read by `IFS= read -r line`, before field splitting.
- Line endings are LF only. CRLF is rejected.
- Paths are repo-relative and canonical: no leading `/`, no leading `./`, no leading `-`, no `.` or `..` segments, no duplicate `/`, and no embedded tabs or newlines.
- The registry has one row per `(generator-script, output-path)` pair and, in v1, at most one row per generator script. If a future generator emits multiple committed artifacts, add one thin wrapper script per output path or loosen the walker contract in a later PR.

## Invariants

- Every output path must exist and be tracked by git when `scripts/check-generators.sh` runs.
- Every registered generator's `--check` mode must validate the same artifact named in column 2. The walker enforces path existence and git tracking; the generator enforces drift detection for that artifact.
- The registry is contributor-controlled and human-reviewed. Symlink-escape hardening via realpath-prefix checks is intentionally deferred; the walker uses regular-file checks today.

## Edit In Sync

Adding a row requires a matching generator script with its sibling `.md` contract and a committed generated output path. Changes to registry grammar must update `scripts/check-generators.sh`, `scripts/check-generators.md`, and `scripts/test-check-generators.sh` fixtures in the same PR. See `scripts/generate-code-reviewer-agent.md` for the exemplar generator contract.
