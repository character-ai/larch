### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: empty manifest on both-absent leaves unknown-slot attribution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: With no manifest rows on both-absent, slot mapping may attribute findings to `unknown-slot` in ballots if sidecar parsing is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Recognize claude-plan-generic-output.txt in slot mapping or add synthetic manifest row


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: assessor harness lacks manifest row-count, --no-fallback argv, and fallback_group assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Availability cases cover status KVs but not manifest length (0 vs 1 vs 2), `--no-fallback` on waterfall argv, or `jq` “no fallback_group” on `plan-assessor-slots.ndjson`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: After each availability invocation, assert manifest length and `jq -s 'all(.[]; has("fallback_group") | not)'`, and capture/log argv from a thin wrapper or `PLAN_ASSESSOR_TRACE` hook for `--no-fallback`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: waterfall silently drops manifest rows for absent tools under --no-fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under `--no-fallback`, manifest rows whose `tool` is absent per `--codex-present` / `--cursor-present` are queued then dropped with empty `final_outputs` and no error. Caller gating is assumed; mismatch (e.g. Codex rows with `--codex-present false`) silently loses reviewers without loud failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After parsing the manifest, fail fast (exit 2) if any row’s `tool` is not `present_for_tool`, or emit an explicit `WARN=manifest-tool-absent` KV counted toward `DEGRADED_ROUND` in design dispatchers.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: degraded-tools-gate WARNINGs only on stderr; Step 0 may not persist them
- **Reviewer(s)**: dyn-env-var-gate-safety-output.txt
- **Severity**: latent
- **Concern**: WARNING diagnostics go through `larch_err` (stderr), not stdout KV contract. `/implement` Step 0 logging of `DEGRADED_EXPLANATION_*` to `execution-issues.md` may omit stale-env warnings when orchestrators use env-prefix invocation without flags. `*_SET` logic is sound; audit visibility is the gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-var-gate-safety-output.txt: Either extend the gate contract with optional stdout keys (e.g. `GATE_WARNINGS_BEGIN`…`END`) for autonomous logging, or update Step 0 procedures to require capturing gate stderr into `execution-issues.md` when `DEGRADED=true` or when any WARNING is present.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: floor_half hardcoded to 4 assumes eight-slot panel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `decompose-panel-dispatch.sh` uses `floor_half` hardcoded to 4 (8 slots). With one external tool present only four slots emit but degradation threshold still assumes an eight-slot panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Compute floor_half from manifest row count or remove obsolete fallback threshold


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

