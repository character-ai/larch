## Proposed Design Outline

### Goals
- Capture the `--risk` value in `launch-review.sh` and pass it as the 5th `*_launcher_append_outer_meta` arg so collector retries honor caller intent (FINDING_12).
- Add empty positional 5th/6th args to the cursor implement/CI launcher meta calls so both optional slots are documented and future-proof (FINDING_6).
- Replace the finding-named static source-grep test assertions with runtime argv/`.meta` captures, and add a risk round-trip test (FINDING_1/2 + FINDING_12 coverage).

### Non-goals
- Part 1 (#3257): already fixed by #3270 — no fix and no test.
- No `--stderr-sink`/`--risk` flag acceptance added to the cursor implement/CI launchers.
- No broader static-grep → runtime sweep beyond the finding-named assertions.

### Approach sketch
- `launch-review.sh`: capture `--risk` into a local `RISK` in both lanes (codex ~131, cursor ~672); pass `$RISK` as the 5th arg at lines 604/1028 in place of the literal `""` (empty preserves the existing `high` default).
- `launch-cursor-implement.sh:339` / `launch-cursor-ci.sh:227`: append empty 5th (risk) + 6th (stderr_sink) args to the existing `cursor_launcher_append_outer_meta` calls — no new flags.
- Tests: convert `_outer_sink_args`/`RETRY_ARGS` greps (test-collect-agent-retry.sh) and `_RUN_EXTERNAL_SINK_ARGS` grep (test-launch-review.sh) into runtime captures; add an `OUTER_LAUNCHER_RISK` round-trip assertion.

### Surfaces in scope
- `scripts/launch-review.sh`, `scripts/launch-cursor-implement.sh`, `scripts/launch-cursor-ci.sh`
- `scripts/test-collect-agent-retry.sh`, `scripts/test-launch-review.sh`
- `.md` siblings only if a behavior/contract line changes

### Open questions
- None.
