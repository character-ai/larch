### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `TITLE_FILTER_MARKER` interpolated into `larch_err` may be unsafe if format-string semantics differ
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: At `skills/design/scripts/design-route.sh:261`, `TITLE_FILTER_MARKER` (derived from external GitHub issue title) is interpolated into the double-quoted first argument of `larch_err`. If `larch_err` treated that argument as a `printf` format string (unlike the safe `larch_errf` pattern used for reentry-guard at line 269), a `%` in the title could cause format-string injection. The reentry-guard path already uses positional `%s` args correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: verify `larch_err` uses `printf '%s'` (or equivalent) internally; if not, convert the title-filter banner to `larch_errf '...lifecycle marker %s — ...' "${TITLE_FILTER_MARKER:-<token>}"` to match the pattern already used for the reentry-guard case.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Re-entry guard KV parsing uses unsafe word-splitting
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/design-route.sh:401-407`, `for _rkv in $_reentry_out` word-splits unquoted output. Embedded whitespace or newlines in a future KV value (e.g., `MARKER_PATH=...`) would split/truncate silently; the pause-load sibling uses safe `while read`. Current `MARKER_HIT` / `MARKER_AGE` / `MARKER_TTL` are single-token, but the idiom is inconsistent and fragile for extension.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Embedded whitespace: if `_reentry_out` ever contains a value with spaces (e.g., a path in a future `MARKER_PATH=...` KV), the `for` loop splits it into two tokens and the case match fails silently, leaving the variable at its default.
  - From cursor-specialist-edge-cases-output.txt: Newline-embedded values: word splitting on unquoted `$var` collapses embedded newlines to IFS whitespace. If `design_reentry_marker_hit` emits multi-word values, the parser silently truncates them. In this change the three parsed KVs (`MARKER_HIT`, `MARKER_AGE`, `MARKER_TTL`) are all numeric or boolean single-words, so the current behavior is correct. But the inconsistency with the safe `while read` idiom used everywhere else in the file is a maintenance risk: if a future KV is added to `design_reentry_marker_hit`'s output with a string value (e.g., `MARKER_PATH=...`), it would silently fail to parse.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Empty `DESIGN_REENTRY_MARKER_PATH` yields blank path in reentry-guard banner
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `DESIGN_REENTRY_MARKER_PATH="$(design_reentry_marker_path ... 2>/dev/null || true)"` (`design-route.sh:410`) can leave the variable empty; `larch_errf` at lines 269-270 then prints "…delete  to override." with a blank where the path should be. Pre-existing behavior, not introduced by this refactor, but moving the banner into the driver makes the gap less visible to editors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: a non-empty guard or fallback literal (e.g., `${DESIGN_REENTRY_MARKER_PATH:-<unknown-path>}`) would eliminate the blank.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Missing ordering pin for `larch_err` before `render_cancel_summary` inside cancel side effects
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` verifies `route_write_result_env` precedes `route_emit_cancel_side_effects` in `emit_cancel_route_result`, but there is no intra-function ordering check that `larch_err` / `larch_errf` precedes `render_cancel_summary` within `route_emit_cancel_side_effects`. Swapping those lines would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add an awk-based ordering check (similar to the existing `cancel_write_line`/`cancel_side_effects_line` check) that scans inside `route_emit_cancel_side_effects` for `larch_err` before `render_cancel_summary`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Cancel-path test pins wrapper `route_write_result_env` but not underlying `phase_driver_write_result_env` on that path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan called for a `$DESIGN_ROUTE_SH` pin for `phase_driver_write_result_env` before reject/render on cancel paths. The harness pins `route_write_result_env` (wrapper) for cancel ordering but not the exact underlying writer symbol on the cancel-specific path, slightly weakening contract coverage if the wrapper were replaced with a non-conforming writer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add `grep -Fq 'phase_driver_write_result_env' "$DESIGN_ROUTE_SH"` alongside the existing `route_write_result_env` check, matching the plan's stated pin list.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `route_emit_stdout_and_exit` has no guard that `ROUTE_KVS` was built
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `ROUTE_KVS` is a script-global array populated only by `route_build_kvs` inside `route_write_result_env`. `emit_route_result` and `emit_cancel_route_result` call `route_write_result_env` first, but `route_emit_stdout_and_exit` itself has no precondition check. A direct or mistaken call would silently emit zero KVs and `exit 0`, yielding an empty-looking success that downstream parses as `ROUTE=""` and fails later with an opaque "missing or invalid ROUTE" error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a brief comment on `ROUTE_KVS` noting it is always populated by `route_write_result_env` before use, or assert `[[ ${#ROUTE_KVS[@]} -gt 0 ]]` at the top of `route_emit_stdout_and_exit` to make the precondition explicit.
  - From cursor-specialist-correctness-output.txt: Add a guard: `[[ ${#ROUTE_KVS[@]} -gt 0 ]] || { larch_err 'route_emit_stdout_and_exit: ROUTE_KVS not built'; exit 2; }` at the top of `route_emit_stdout_and_exit`, or make `ROUTE_KVS` local by inlining `route_build_kvs` into `route_write_result_env`.
  - From cursor-specialist-edge-cases-output.txt: Assert `[[ ${#ROUTE_KVS[@]} -gt 0 ]]` at the top of `route_emit_stdout_and_exit` to make the precondition explicit.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `route_emit_cancel_side_effects` silently no-ops on unknown cancel routes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `route_emit_cancel_side_effects` (`skills/design/scripts/design-route.sh:257-278`) handles only `cancel-title-filter` and `cancel-reentry-guard`. Any other `ROUTE` value falls through with no reject banner and no `render-final-summary.sh` invocation. A future cancel route wired through `emit_cancel_route_result` would fail silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a `*) fail "route_emit_cancel_side_effects: unexpected ROUTE=${ROUTE}"` arm to the `case` to fail loudly if called with an unhandled cancel route.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `write-design-current-env.sh` stdout suppression lacks documented protocol assumption
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: In `design-init-runparams.sh` (resume env-refresh path), child stdout is redirected to `/dev/null` in both quiet and non-quiet branches. This is correct only if `write-design-current-env.sh` never emits parsed `WARN=` / other KVs to stdout on failure; any such stdout is now discarded with no test or comment anchoring the assumption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add an inline comment at the `>/dev/null` line stating "write-design-current-env.sh must not emit KVs to stdout; only stderr diagnostics are expected" to document the protocol assumption and make a future violation detectable.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `test-step0b-router-flag-recovery.sh` assumption that it never calls `design-route.sh` is unpinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `design-route.sh` now requires `--session-id` (exit 2 when missing). The plan asserts `test-step0b-router-flag-recovery.sh` only exercises `design-init-runparams.sh`, but the diff adds no structural pin confirming the harness never invokes `design-route.sh`. If it did, cases would exit 2 before exercising router-flag recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Read `scripts/test-step0b-router-flag-recovery.sh` to confirm no `design-route.sh` invocation; add a `! grep -q 'design-route.sh' "$HARNESS"` structural assertion or a code comment if the assumption is load-bearing.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

