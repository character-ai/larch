# test-lib-quiet.sh

Regression harness for `scripts/lib-quiet.sh`. It creates temporary helper
scripts that source the library and verifies the public quieting contract:
contract output remains caller-visible through `emit` / `emit_kv`, incidental
stdout/stderr is redirected to the quiet log, disable mode preserves legacy
stdout, nested initialization is idempotent, `larch_err` stays operator-visible
on stderr while being mirrored into the quiet log through
`redact-secrets.sh --streaming`, and pure filters can opt out with
`LARCH_QUIET_DISABLE=1`. It also covers Stage 3 compatibility shim no-ops,
`emit_kv` newline rejection (embedded LF/CR), literal backslash-n pass-through,
and long single-line values.

Wired into `make test-lib-quiet`. Keep this harness in sync with
`scripts/lib-quiet.md` and any change to `larch_quiet_init`, `emit`,
`emit_kv`, or `larch_err`.
