# test-lib-quiet.sh

Regression harness for `scripts/lib-quiet.sh`. It creates temporary helper
scripts that source the library and verifies the public quieting contract:
contract output remains caller-visible through `emit` / `emit_kv`, incidental
stdout/stderr is redirected to the quiet log, disable mode preserves legacy
stdout, nested initialization is idempotent, breadcrumbs are quiet unless
explicitly surfaced, and pure filters can opt out with `LARCH_QUIET_DISABLE=1`.
It also validates `larch_quiet_write_paired_pid_file`: unset no-op, atomic
write, fail-open warnings for invalid paths, containment checks, symlink and
`..` rejection, and concurrent writer behavior.

Wired into `make test-lib-quiet`. Keep this harness in sync with
`scripts/lib-quiet.md` and any change to `larch_quiet_init`, `emit`,
`emit_kv`, or `emit_breadcrumb`.
