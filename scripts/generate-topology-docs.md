# scripts/generate-topology-docs.sh - contract

`scripts/generate-topology-docs.sh` regenerates `docs/topology.md` from the consumer-doc projection in `skills/shared/topology.tsv`. The TSV is not a global source of truth: each row names a `runtime_authority` path that owns the actual runtime semantics, and the generator validates that the authority exists, is tracked by git, and contains the row's `value` literal.

## Purpose And Callers

Primary callers are the `agent-sync` registry walker (`scripts/check-generators.sh` via `scripts/generators.tsv`), `make test-generate-topology-docs`, and contributors changing topology-count projection rows.

## Invariants

- Runs with `set -euo pipefail` and `LC_ALL=C`.
- Supports default write mode and `--check` mode.
- Emits only `docs/topology.md`; consumer docs link to row anchors and are not generator-rewritten.
- Parses `skills/shared/topology.tsv` with `awk -F '\t'`; adjacent empty fields are preserved, and rows must have exactly four columns.
- Requires keys to match `[a-z0-9_.]+` and contain no colon.
- Allows an empty `composition` column, but requires non-empty `key`, `value`, and `runtime_authority`.
- Rejects display values containing tabs, newlines, Markdown-link delimiters, backticks, or HTML comment markers.
- Validates every `runtime_authority` path as repo-relative, tracked, and containing the row's `value` literal.
- Is deterministic: no timestamps and no locale-dependent output.

## Makefile And CI Wiring

Registered in `scripts/generators.tsv` as the row `scripts/generate-topology-docs.sh<TAB>docs/topology.md`, so `scripts/check-generators.sh` runs `--check` in CI's `agent-sync` job. The offline harness is `scripts/test-generate-topology-docs.sh`, exposed as `make test-generate-topology-docs` and assigned to a `test-harnesses-N` shard.

## Out Of Scope

Quick-mode `/implement` reviewer-loop phrases (`7 rounds`, `rounds 1-3`, `5 Cursor specialists`, `generic Codex`, and adjacent public-doc markers) are excluded from `skills/shared/topology.tsv`. They are owned by `scripts/test-quick-mode-docs-sync.sh` and its sibling contract.

## Edit In Sync

Changing the TSV schema, output table shape, charset rules, or runtime-authority validation must update this file and `scripts/test-generate-topology-docs.sh` in the same PR. Adding or changing a topology row requires regenerating `docs/topology.md`.
