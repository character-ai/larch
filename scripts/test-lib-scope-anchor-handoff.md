# test-lib-scope-anchor-handoff.sh

Regression harness stub for `scripts/lib-scope-anchor-handoff.sh` — the
primary contract lives in `scripts/lib-scope-anchor-handoff.md`.

Covers relay terminal gating (`ok` / `main-agent-vote-required` admit;
`tally-error` / `panel-failed` / non-terminal reject), CR/LF path
rejection, and tmpdir containment validation. Wired into `make lint` via
the `test-lib-scope-anchor-handoff` Makefile target.
