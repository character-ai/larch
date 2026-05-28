# lib-design-tmpdir.sh

## Purpose

Source-only library exposing `larch_design_tmpdir_validate <dir>`. Canonicalizes a caller-supplied `--design-tmpdir` path and rejects locations outside an operator-session allowlist. The validator never creates directories; callers run `mkdir -p` only after validation succeeds.

## Allowlist

Built once per shell at first validation from:

- `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions/`
- `${TMPDIR}/` when `TMPDIR` is set
- `/tmp/`

Each prefix is canonicalized with `cd && pwd -P` when the path exists (macOS `/tmp` → `/private/tmp`), then normalized with a trailing `/` for prefix matching.

## Sourced From

- `scripts/dispatch-plan-voters.sh`
- `skills/design/scripts/tally-plan-review.sh`

## Function Reference

### `larch_design_tmpdir_validate <dir>`

Returns 0 when the resolved path is under the allowlist; returns 2 with `larch_err` on empty input, newline/carriage-return bytes, any `.`/`..` path segment, parent resolution failure, non-directory existing leaves (including symlink-to-file), or disallowed prefix.

## Harness

`scripts/test-lib-design-tmpdir.sh` covers allowed prefixes, unresolved dot-segment rejection, regular-file leaves, control-byte rejection, symlink cases, and quoted-prefix `case` behavior. Consumer wiring is pinned by `scripts/test-dispatch-plan-voters.sh` and `skills/design/scripts/test-tally-plan-review.sh`. Wired through `make test-lib-design-tmpdir`.
