# scripts/test-scrub-log-secrets.sh — contract

Regression harness for `scripts/scrub-log-secrets.sh`; see
`scripts/scrub-log-secrets.md` for the full contract. Asserts the Cursor
incident class (`crsr_`/`key_`) and the base/extra family backstops are
scrubbed, clean files stay byte-identical, the `LARCH_SECRET_SCRUB_*` contract
and loud banner are emitted, scrubbing is idempotent, and argument validation
fails closed. Wired into `make lint` via the `test-scrub-log-secrets` target;
run directly with `bash scripts/test-scrub-log-secrets.sh`.
