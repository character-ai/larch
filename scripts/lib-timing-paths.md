# lib-timing-paths.sh — contract

Sourced-only shell library shared by `scripts/timing-ledger.sh` and `scripts/timing-report.sh`. Owns the path-validation primitives both scripts need so the set of allowed ledger roots stays in sync.

## Interface

- `tmp_root` — print canonicalized `${TMPDIR:-/tmp}`; return 1 on failure.
- `canonical_parent_path <raw>` — canonicalize the parent of `<raw>`; print `<canonical-parent>/<basename>`. Rejects `..` segments and unresolvable parents.
- `canonical_dir <raw>` — canonicalize an existing directory; return 1 if missing.
- `path_under_root <path> <root>` — succeed iff `<path>` equals `<root>` or is beneath it.
- `validate_under_roots <raw> <root>...` — canonicalize `<raw>` and succeed iff its canonical form lies under any provided root. Print the canonical path on success.
- `timing_allowed_roots` — print every canonicalized root the timing helpers accept (`${TMPDIR:-/tmp}`, `IMPLEMENT_TMPDIR`, `DESIGN_TMPDIR`, `REVIEW_TMPDIR`, `dirname("$SESSION_ENV_PATH")`), one per line. Unset / unresolvable roots are silently omitted.

## Conventions

- **Not a standalone script**: no shebang, no `set -euo pipefail`, no `main`. Consumers `source` this file under their own `set -euo pipefail` context.
- **Bash 3.2 compatible**: indexed arrays only.
- **Read-only contract**: consumers MUST NOT mutate the helper definitions after sourcing.

## Edit-in-sync pointers

| File | Relationship |
|---|---|
| `scripts/timing-ledger.sh` | Sources this file for path canonicalization, env-root lookup, and `--ledger` test override validation. |
| `scripts/timing-report.sh` | Sources this file for `--ledger` validation; mirrors timing-ledger's allowed-root set so a path valid for writes is also valid for reads. |
| `scripts/timing-ledger.md` | Documents the resolver chain that depends on this library. |
| `scripts/timing-report.md` | Documents the renderer's `--ledger` semantics that depend on this library. |

## Test harness

Covered indirectly by:
- `scripts/test-timing-ledger.sh` — exercises `--ledger` containment, env-root acceptance, fallback chain.
- `scripts/test-timing-report.sh` — exercises `--ledger` acceptance under a non-TMPDIR root (regression coverage for review FINDING_1).

No direct harness — the file exposes only sourced functions consumed by the two primary scripts.

## Makefile wiring

No direct target. Both consumers are already wired into `make lint` via `test-timing-ledger` / `test-timing-report` (shard `test-harnesses-4`).
