# test-implement-preflight.sh

Offline harness for `scripts/implement-preflight.sh`. The primary contract lives in `scripts/implement-preflight.md`.

## Coverage

The harness stubs `gh` and `python3` and does not hit the network. It covers:

- Emergency admission `missing-designed-prefix`.
- Admission stdout parsed before rc branching.
- Admission refusal first-line templates.
- Parsed context echoes: `BLOCKERS=<value>` for `has-blockers`; `TITLE=<value>` for managed-prefix, report-title, and non-emergency missing-designed-prefix when parsed.
- Exact malformed-plan non-emergency refusal with the parsed `MALFORMED=` reason.
- Exact emergency warning strings through runtime stdout assertions.
- JSON extraction through Python stdlib `json`.
- `--repo` forwarding to admission, `gh`, and plan-block read.
- Titles containing `=`.
- `RESUME=false` default when admission omits `RESUME=`.
- `RESUME=true` forwarding when admission emits it.
- One `KEY=value` record per line.
- Success-envelope only behavior.
- Quiet-mode key output via `LARCH_QUIET_DISABLE=1`.
- Malformed emergency `BLOCK_PRESENT=true`.
