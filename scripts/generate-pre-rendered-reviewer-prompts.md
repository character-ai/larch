# scripts/generate-pre-rendered-reviewer-prompts.sh - contract

`scripts/generate-pre-rendered-reviewer-prompts.sh` generates committed static
body files under `agents/pre-rendered/` for every `agents/reviewer-*.md` file.
Each body file contains only the agent body after YAML frontmatter; the runtime
renderer uses these files to avoid repeatedly extracting identical reviewer
profiles during review fan-out.

## Modes

- Default write mode rewrites `agents/pre-rendered/reviewer-*-body.txt` and
  `agents/pre-rendered/.manifest`.
- `--check` mode regenerates the expected directory in a temp location and
  exits non-zero if the committed directory differs.

## Invariants

- Runs with `set -euo pipefail` and `LC_ALL=C`.
- Discovers `agents/reviewer-*.md` from the repo root, sorted by path.
- Fails if no reviewer agents are found or if any extracted body is empty.
- The manifest records SHA-256 checksums for the generated body files.
- The generator is registered in `scripts/generators.tsv`; CI reaches it via
  `scripts/check-generators.sh --check` dispatch.

## Edit In Sync

Update `scripts/render-specialist-prompt.sh`,
`scripts/test-render-specialist-prompt.sh`, `scripts/generators.tsv`, and
`scripts/test-check-generators.sh` when changing the pre-rendered body contract.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
