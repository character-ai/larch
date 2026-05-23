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
- Rejects bare-numeric or otherwise too-short `value` strings (purely-numeric, or shorter than 3 chars). The substring grep against the runtime authority would otherwise be silently satisfied by an unrelated digit (e.g. `2` matching `Step 2a`); use a phrase like `2 sketch agents` that uniquely pins the topology fact.
- Rejects duplicate `key` rows and any future anchor-derivation regression that maps two distinct keys onto the same `<a id>` fragment. Anchor derivation is currently the verbatim key (HTML5 allows `.` and `_` in id attributes), so injectivity holds by construction; the duplicate-anchor check is defense-in-depth.
- Renders the post-validation rows via an ASCII record-separator (`\035`) intermediate so empty `composition` columns survive the read-back step. `IFS=$'\t'` would treat tab as IFS-whitespace and collapse adjacent tabs, which would shift `runtime_authority` into the `composition` cell on empty-composition rows.
- `LARCH_TOPOLOGY_TSV` and `LARCH_TOPOLOGY_DOC` are dev/CI overrides used only by `scripts/test-generate-topology-docs.sh`. They are trusted-only — operators must not pass untrusted values. The public surface is `--check` against the in-repo defaults.
- Is deterministic: no timestamps and no locale-dependent output.

## Makefile And CI Wiring

Registered in `scripts/generators.tsv` as the row `scripts/generate-topology-docs.sh<TAB>docs/topology.md`, so `scripts/check-generators.sh` runs `--check` in CI's `agent-sync` job. The offline harness is `scripts/test-generate-topology-docs.sh`, exposed as `make test-generate-topology-docs` and assigned to a `test-harnesses-N` shard.

## Out Of Scope

`/implement` Step 5 phrases pinned by `scripts/test-quick-mode-docs-sync.sh` (`5 rounds`, `--panel hard`, `3-judge panel on every round`, `6 Cursor specialists`, and adjacent public-doc markers) are excluded from `skills/shared/topology.tsv`. They are owned by `scripts/test-quick-mode-docs-sync.sh` and its sibling contract.

## Edit In Sync

Changing the TSV schema, output table shape, charset rules, or runtime-authority validation must update this file and `scripts/test-generate-topology-docs.sh` in the same PR. Adding or changing a topology row requires regenerating `docs/topology.md`.
