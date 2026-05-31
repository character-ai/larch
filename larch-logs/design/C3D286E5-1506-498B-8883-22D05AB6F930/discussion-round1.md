## Decision 1: Part 1 (#3257 — resolve-conflict CI stderr surfacing)
- **Question**: The issue's Part 1 claims resolve-conflict CI launches omit `_surface_ci_stderr_tail`. Is this still a real gap?
- **Resolution**: Already fixed by #3270 (commit 12677a01e). Both the direct vendor resolve-conflict launch (`ship-pr.sh:3401`) and the recovery waterfall (`ship-pr.sh:2835`) already call `_surface_ci_stderr_tail`. The CI fix-loop (2096/2107/2159) also surfaces. The issue's cited line range (3278-3290) is stale. **Drop Part 1 entirely** — no fix, no test (relies on existing #3227/#3270 tests).
- **Source**: codebase + user

## Decision 2: FINDING_6 scope (cursor implement/ci launcher round-trip)
- **Question**: `launch-cursor-implement.sh:339` and `launch-cursor-ci.sh:227` call `cursor_launcher_append_outer_meta` with only 4 args. Minimal placeholder fix or full `--stderr-sink` wiring?
- **Resolution**: **Positional placeholders only.** Pass empty 5th (risk) + 6th (stderr_sink) args so the call shape documents both optional slots and prevents future arg-position drift. No new `--stderr-sink`/`--risk` flag acceptance in those launchers (they have none today). No behavioral change today; defensive against future adoption.
- **Source**: user

## Decision 3: FINDING_1/2 test-conversion breadth
- **Question**: Convert all static source-grep assertions to runtime, or only the finding-named ones?
- **Resolution**: **Finding-named greps only.** Convert (a) the collector retry-forwarding static greps in `test-collect-agent-retry.sh` (`_outer_sink_args`/`RETRY_ARGS` literals) and (b) the `launch-review.sh` threading static grep in `test-launch-review.sh` (`_RUN_EXTERNAL_SINK_ARGS` literal) to runtime argv/`.meta` captures. Keep existing behavioral tests (the `.meta` recording checks, fail-closed `..` guard). Additionally add a FINDING_12 risk round-trip test.
- **Source**: user

## Decision 4: FINDING_12 (launch-review.sh --risk wiring) — confirmed in-scope, no ambiguity
- **Question**: Is FINDING_12 a real gap and what is the fix surface?
- **Resolution**: Real. `launch-review.sh` parses `--risk` at lines 131 (codex lane) and 672 (cursor lane) but discards the value (`shift 2`, no capture), then passes `""` as the 5th arg to `*_launcher_append_outer_meta` at lines 604 (codex) and 1028 (cursor). `""` triggers the `${5:-${RISK:-high}}` default → `OUTER_LAUNCHER_RISK=high` on every collector retry regardless of caller intent. Fix: capture the `--risk` value into a `RISK` variable in both lanes and pass it as the 5th arg, symmetric to the existing `STDERR_SINK` 6th arg.
- **Source**: codebase

## Hard constraints (codebase-derived, not user decisions)
- Must not break existing tests; `bash scripts/relevant-checks.sh` / `make lint` must stay green. Converted runtime tests must pass against the actual (fixed) code.
- Bash 3.2 portability (BASH_AUTHORING.md §3): no associative arrays, namerefs, `mapfile`, `${var^^}`, `&>>`.
- Preserve the `external_launcher_append_outer_meta` contract: `<meta_path> <outer_launcher_path> <prompt_file_sidecar> <workdir> [risk] [stderr_sink]`. Empty 5th keeps `${RISK:-high}` default; empty 6th omits the `STDERR_SINK=` line. Update `scripts/lib-external-launcher-common.md` only if behavior/contract wording changes (it likely does not).
- Update `.md` siblings for any `.sh` whose behavior changes (script-md-siblings rule): `scripts/launch-review.md`, `scripts/launch-cursor-implement.md`, `scripts/launch-cursor-ci.md`.
- `--stderr-sink` / `--risk` argv validation in launch-review.sh must remain (charset guard via `validate_meta_scalar_path`).

## Out of scope
- Part 1 (#3257) — already fixed.
- Wiring `--stderr-sink` flag acceptance into the cursor implement/ci launchers (deferred per Decision 2).
- Any broader static-grep → runtime sweep beyond the finding-named assertions (per Decision 3).
