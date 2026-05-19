## Goal
Add scout-round*-manifest.json.raw to larch-log round_artifact_included allow-list so Claude's raw scout output is committed to round-N logs

## Implementation Plan

Phase 1 of issue #2373: commit scout raw-output sidecar to larch-logs round-N.

### Background
`scripts/scout-dynamic-archetypes.sh` already captures Claude's raw output to `${OUTPUT}.raw`
(e.g. `scout-roundN-manifest.json.raw`) via `launch-claude-subprocess.sh --output-file "$raw_output"`.
The file is preserved on all Claude-invoked outcomes (ok, empty, parse-failed). It is NOT deleted anywhere.
However, `larch-log.sh::round_artifact_included()` does NOT include `scout-round*-manifest.json.raw`
in its allow-list, so it's never committed to round-N logs.

### Changes

1. **`scripts/larch-log.sh`** — In `round_artifact_included()` (line ~92), add
   `scout-round*-manifest.json.raw` to the pattern block that returns 0 (alongside
   `scout-round*-manifest.json`). The `.raw` files fall through to the `cp` branch in
   `stage_round_artifact` — no special trimming needed.

2. **`scripts/larch-log.md`** — In the `write-round` bullet, extend the
   "allow-list includes scout artifacts" sentence to also mention
   `scout-round*-manifest.json.raw`.

3. **`scripts/test-scout-dynamic-archetypes.sh`** — After the existing `run_case valid4`
   (ok), `run_case empty`, and `run_case malformed` (parse-failed) invocations, assert:
   - `$out_dir/scout-manifest.json.raw` exists
   - its content matches the fixture byte-for-byte
   The `run_case` helper sets `output="$out_dir/scout-manifest.json"` so the raw sidecar
   is `$out_dir/scout-manifest.json.raw`. The fixture content is written by the stub claude.
   Do NOT add raw-file assertions for `claude-failed` or `timeout` cases.

4. **`scripts/scout-dynamic-archetypes.md`** — Document that `${OUTPUT}.raw` (the raw
   sidecar) is preserved verbatim for every Claude invocation outcome and is committed
   to round-N via `larch-log.sh write-round`.


## Test plan
- Run `scripts/test-scout-dynamic-archetypes.sh` — all existing assertions plus new raw-file assertions pass.
- Run `make lint` to verify larch-log.sh changes pass lint checks.
