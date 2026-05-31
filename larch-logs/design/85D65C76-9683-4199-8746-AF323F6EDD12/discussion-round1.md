## Decision 1: Fix completeness (STDERR_SINK plumbing depth)
- **Question**: How complete should the STDERR_SINK plumbing be, given launch-review.sh rejects unknown flags and never sets a sink today?
- **Resolution**: Complete & safe. Record STDERR_SINK in the outer-meta; parse + validate + forward it in BOTH outer-launcher retry sites (the launch_outer_retry_or_mark() function and the inline empty-output/transient retry loop); add `--stderr-sink` passthrough to launch-review.sh and thread it to run-external-agent.sh so the forwarded flag is accepted. Forward only when non-empty.
- **Source**: user

## Decision 2: CMD_JSON retry path coverage
- **Question**: Should the fix also cover the CMD_JSON retry path used by default-mode --stderr-sink lanes?
- **Resolution**: Yes. Record STDERR_SINK in run-external-agent.sh's base `.meta`, and forward `--stderr-sink` in both CMD_JSON retry sites (launch_cmd_json_retry_or_mark() and the inline empty-output CMD_JSON path).
- **Source**: user

## Decision 3: Existing `.meta` byte-stability (hard constraint)
- **Question**: Must the new STDERR_SINK field avoid disturbing existing `.meta` files / fixtures for the common no-sink lanes?
- **Resolution**: Yes. Write the `STDERR_SINK=` line only when the sink value is non-empty, in both the run-external-agent.sh base-meta writer and external_launcher_append_outer_meta. No-sink lanes keep their current `.meta` grammar byte-for-byte.
- **Source**: codebase

## Decision 4: Codex/Cursor parity (hard constraint)
- **Question**: Does the launch-review.sh change need to cover both tool lanes?
- **Resolution**: Yes. launch-review.sh has two argv-parse blocks (codex + cursor) and two outer-meta append call sites (lines 594, 1010). Apply `--stderr-sink` parsing, run-external threading, and outer-meta recording symmetrically to both, per .claude/rules/external-tool-launcher-parity.md.
- **Source**: codebase

## Decision 5: Preserve retry-path security guards (hard constraint)
- **Question**: Must the existing canonical-launcher validation and test-hook env scrub in the outer-retry exec be preserved?
- **Resolution**: Yes. STDERR_SINK forwarding is additive. Validate it symmetrically to OUTER_LAUNCHER (reject `..` traversal) before forwarding; run-external-agent.sh re-validates via validate_meta_scalar_path. Do not weaken the env -u scrub or canonical launch-review.sh pinning.
- **Source**: codebase
