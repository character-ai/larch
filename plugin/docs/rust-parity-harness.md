# Rust Parity Harness

The black-box parity harness lives in
`crates/larch-cli/tests/support/parity.rs`. It runs a Python command and its
Rust replacement in separate temporary roots. Both roots start with the same
seed files. The harness compares:

- exit code, stdout, and stderr;
- every regular file, including binary files and non-UTF-8 output streams;
- declared UTF-8 side-effect records, such as fake service call logs.

The sole structural exception is the private
`.home/.cache/larch/sessions/.larch-session-activity.lock` inode. It is an
advisory `flock` coordination primitive added after the frozen session-writer
cutover, not a wire artifact or command payload. The harness still rejects a
symlink at that location.

A mismatch reports only the differing channels and truncates large values.
It reports mismatched file paths as whole units and names how many paths it
omitted when the bounded diagnostic fills. Each child has a 30-second default
timeout. A case may select a shorter or longer explicit timeout.
The harness rejects symlinks, special files, absolute fixture paths, and path
traversal.

## Service isolation

Children start with a cleared environment. The harness supplies isolated
home, temporary, cloud-config, and executable directories. It removes inherited
credentials and points standard GitHub and proxy variables at a closed
loopback endpoint. A case cannot override credential, service-host, or proxy
variables. Commands that need GitHub or cloud behavior must use a fixture
executable or local fixture service and record each permitted call.

This boundary prevents accidental live access through normal clients. It is
not a security sandbox for hostile test code that opens a hard-coded socket.
Parity cases must not use direct network APIs.

## Normalization

Normalization is opt-in per case. The harness supports only these rules:

- `SandboxRoot` replaces that command's temporary root with `<SANDBOX>`.
- `Rfc3339Utc` replaces complete UTC timestamps such as
  `2026-07-18T20:00:00.123Z` with `<TIMESTAMP>`.

Rules apply to stdout, stderr, text files, and side-effect records. Binary
files remain byte-exact. Add a new rule only for documented nondeterminism and
cover its exact match boundary with a test. Do not normalize semantic values.

## Add a parity case

Add a `ParityCase` to a `larch-cli` integration test. Supply absolute Python
and Rust executable paths, arguments, environment values, seed files, declared
side-effect record paths, and the smallest needed normalization rule set. Use
`{sandbox}` in an argument or environment value when the command needs its
isolated root. Call `assert_case` with a checked-in golden path.

`fixtures/rust-parity/` demonstrates clean, usage-error, malformed-input,
environmental-failure, and service-isolation cases. The clean case also covers
text and binary files, side-effect records, temporary paths, and timestamps.

Review a contract change before updating its golden. After Python and Rust
match, refresh goldens with:

```bash
LARCH_UPDATE_PARITY_GOLDENS=1 cargo test --locked --package larch-cli --test parity
```

Inspect and commit the resulting `*.golden.json` diff. CI never sets the
update variable, so an unreviewed contract change fails.
