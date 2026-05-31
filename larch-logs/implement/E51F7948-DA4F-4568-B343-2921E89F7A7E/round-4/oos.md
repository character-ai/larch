### FINDING_17: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/dispatch-plan-review-panel.sh:183-210` — Dynamic scout slugs (`_slug` from `scout-plan-manifest.json`) are interpolated into filesystem paths without a slug charset guard (e.g. `/` or `..` in `name`). `larch_design_tmpdir_validate` rejects `..` on the tmpdir root, not on slug segments, so a hostile or malformed scout manifest could write outside the intended flat naming layout. **Pre-existing**; not introduced by availability gating. **Suggested fix:** sanitize slugs (same spirit as `plan-review-loop.sh`’s `_fail_slug` python one-liner) before use in paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **architecture** `scripts/dispatch-plan-voters.sh:139-144`, `skills/design/scripts/dispatch-plan-assessors.sh:95-100` — NDJSON rows are built with `printf '{"…":"%s",…}'` instead of `jq -nc`. Paths today live under an allowlisted `DESIGN_TMPDIR`, so practical risk is low, but `"` or `\` in a path would corrupt the manifest. **Pre-existing pattern** on this branch. **Suggested fix:** use `jq -nc` like `dispatch-plan-review-panel.sh` for defense in depth. --- **Summary:** From a security-and-trust-boundaries lens, this branch is **sound**: it removes misleading cross-slot output reuse, closes a resource-exhaustion stall, and keeps path/manifest validation. No injection, secret leakage, or auth-boundary regressions were identified in the changed code. Remaining notes are hardening opportunities outside the diff’s threat model.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] architecture: skills/design/scripts/decompose-aggregator.sh:82
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale eight-proposal header after availability-gated dispatch. Operator sees wrong slot-count expectation in merged prompt. Update header to reflect present-vendor slot count.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **Unquoted** `_wf_files=($all_output_files)` / `_wf_tools=($all_output_tools)` (`scripts/dispatch-plan-voters.sh:176-181`) follow the same space-delimited `emit_kv` contract as the rest of the waterfall stack; paths under `DESIGN_TMPDIR` are conventionally space-free, so this is consistent with repo practice rather than a new Bash 3.2 hazard.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **Unquoted** `_wf_files=($all_output_files)` / `_wf_tools=($all_output_tools)` (`scripts/dispatch-plan-voters.sh:176-181`) follow the same space-delimited `emit_kv` contract as the rest of the waterfall stack; paths under `DESIGN_TMPDIR` are conventionally space-free, so this is consistent with repo practice rather than a new Bash 3.2 hazard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] **`degraded-tools-gate.sh` stderr WARNINGs** (`scripts/degraded-tools-gate.sh:57-67`) go through `larch_err` on FD 2; canonical skill callers pass explicit `--codex-*` / `--cursor-*` flags (`skills/shared/external-reviewers.md:29-32`), so production KV parsing on stdout alone is unaffected. Harness cases 8–9 intentionally use `2>&1` to assert those warnings (`scripts/test-degraded-tools-gate.sh:104-125`); merged capture only becomes risky for ad-hoc callers that omit flags, rely on env, and parse stdout without ignoring non-`KEY=value` lines (case 11 documents that posture).
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - **`degraded-tools-gate.sh` stderr WARNINGs** (`scripts/degraded-tools-gate.sh:57-67`) go through `larch_err` on FD 2; canonical skill callers pass explicit `--codex-*` / `--cursor-*` flags (`skills/shared/external-reviewers.md:29-32`), so production KV parsing on stdout alone is unaffected. Harness cases 8–9 intentionally use `2>&1` to assert those warnings (`scripts/test-degraded-tools-gate.sh:104-125`); merged capture only becomes risky for ad-hoc callers that omit flags, rely on env, and parse stdout without ignoring non-`KEY=value` lines (case 11 documents that posture).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] `scripts/dispatch-plan-voters.md:16-22` still describes the legacy three-phase waterfall; the script now passes `--no-fallback` (`scripts/dispatch-plan-voters.sh:153`). Doc drift only, not a runtime defect in the current code path.
- **Reviewer**: dyn-bash-portability-output.txt
- **Concern**: - `scripts/dispatch-plan-voters.md:16-22` still describes the legacy three-phase waterfall; the script now passes `--no-fallback` (`scripts/dispatch-plan-voters.sh:153`). Doc drift only, not a runtime defect in the current code path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] **`scripts/dispatch-with-waterfall.sh:411-426` + `skills/design/scripts/assess-plan-round.sh:222-232`:** The new `--no-fallback` contract treats per-slot drops as non-fatal (`DISPATCH_OK=true` when any static slot survives), but `assess-plan-round.sh` still aborts tally whenever waterfall `DISPATCH_OK=false`, including the case where Claude succeeded and both external assessor rows were dropped (`ALL_SLOTS_DROPPED`). That is outside the four callers named in the scout prompt but is the same semantic asymmetry.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`scripts/dispatch-with-waterfall.sh:411-426` + `skills/design/scripts/assess-plan-round.sh:222-232`:** The new `--no-fallback` contract treats per-slot drops as non-fatal (`DISPATCH_OK=true` when any static slot survives), but `assess-plan-round.sh` still aborts tally whenever waterfall `DISPATCH_OK=false`, including the case where Claude succeeded and both external assessor rows were dropped (`ALL_SLOTS_DROPPED`). That is outside the four callers named in the scout prompt but is the same semantic asymmetry.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_35: [OUT_OF_SCOPE] **`scripts/dispatch-with-waterfall.sh:353-354` + `FALLBACK_COUNTER_FILE`:** Design panel/voter callers do not pass `--fallback-counter-file`; forcing `combined_fallback=0` under `--no-fallback` does not under-report in those paths. Only `/review`-style callers that opt into the counter file are affected, and none of the in-scope design dispatchers use it.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`scripts/dispatch-with-waterfall.sh:353-354` + `FALLBACK_COUNTER_FILE`:** Design panel/voter callers do not pass `--fallback-counter-file`; forcing `combined_fallback=0` under `--no-fallback` does not under-report in those paths. Only `/review`-style callers that opt into the counter file are affected, and none of the in-scope design dispatchers use it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] **`skills/design/scripts/plan-review-loop.sh:772-829`, `skills/design/scripts/dispatch-plan-review-panel.sh:265-280`, `skills/design/scripts/decompose-panel-dispatch.sh:299-313`:** Partial drop signaling is wired consistently via compact paths-file length vs manifest `slot_count`, `DEGRADED_ROUND` / `DEGRADED_PANEL`, `STATIC_DISPATCH_OK`, and `ALL_SLOTS_DROPPED`; `panel-failed` is gated on unreadable paths plus `DISPATCH_OK!=true`, which matches the intended degrade-vs-abort split for partial success.
- **Reviewer**: dyn-dispatch-ok-semantics-output.txt
- **Concern**: - **`skills/design/scripts/plan-review-loop.sh:772-829`, `skills/design/scripts/dispatch-plan-review-panel.sh:265-280`, `skills/design/scripts/decompose-panel-dispatch.sh:299-313`:** Partial drop signaling is wired consistently via compact paths-file length vs manifest `slot_count`, `DEGRADED_ROUND` / `DEGRADED_PANEL`, `STATIC_DISPATCH_OK`, and `ALL_SLOTS_DROPPED`; `panel-failed` is gated on unreadable paths plus `DISPATCH_OK!=true`, which matches the intended degrade-vs-abort split for partial success.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

