# test-persist-retally-step3-env.sh

Regression harness stub for
`skills/design/scripts/persist-retally-step3-env.sh` — the primary contract
lives in `skills/design/scripts/persist-retally-step3-env.md`.

Covers dual env refresh on `ok` (stdout-parsed anchor preferred,
input-anchor fallback when stdout omits the KV), stale-anchor omission on
`tally-error`, cumulative in-scope and accepted-OOS merges after successful
MainAgent re-tally, and CR/LF / containment rejection. Wired into `make lint`
via the `test-persist-retally-step3-env` Makefile target.
