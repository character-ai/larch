### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: MainAgent re-tally scope-anchor refresh is prose-only, not script-enforced
- **Reviewer(s)**: dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: Re-tally `SCOPE_ANCHOR_FILE` refresh (`_RETALLY_SCOPE_ANCHOR_IN` / `_RETALLY_PARSED_SCOPE_ANCHOR_FILE`, omit on `tally-error`, dual env rewrite) is enforced only through orchestrator prose and `test-step3-orchestrator-fence.sh` grep pins, unlike loop and `run-step3-review.sh` paths with script-level terminal gating. A prompt-side miss can leave a stale anchor in result env files despite stated stale-leak mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-handoff-output.txt: Extract re-tally scope-anchor parse/persist into a small helper (parallel to `_scope_anchor_handoff_value()` / `scope_anchor_relay_allowed()`) invoked from the re-tally Bash fence, or add a behavioral harness that simulates re-tally stdout/env refresh rather than only checking documentation strings.
  - From dyn-ship-driver-output.txt: Extract re-tally parse/persist into a small sourced helper (parallel to `_scope_anchor_handoff_value`) invoked from a thin SKILL.md Bash fence, and add an offline harness that seeds stale exported `SCOPE_ANCHOR_FILE`, omits the KV on `tally-error`, and asserts both refreshed env files stay clean.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: `_scope_anchor_handoff_value()` reads global tally status, not `emit_loop_kvs` parameter
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: `emit_loop_kvs()` accepts `tally_status` as a parameter but `_scope_anchor_handoff_value()` reads global `TALLY_PLAN_REVIEW_STATUS` instead of `$tally_status`. A future refactor passing a different `tally_status` while leaving the global stale could emit mismatched tally KV and `SCOPE_ANCHOR_FILE` lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Pass `tally_status` into `_scope_anchor_handoff_value` (or read only the parameter inside `emit_loop_kvs`) so the relay gate and emitted tally KV share one value.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `_PARSED_SCOPE_ANCHOR_FILE` not cleared on tally failure
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: On tally failure the script forces `TALLY_PLAN_REVIEW_STATUS=tally-error` but leaves `_PARSED_SCOPE_ANCHOR_FILE` populated from the raw tally stream; safety depends entirely on `_scope_anchor_handoff_value()` re-checking tally status, which is fragile if a later edit writes from the parsed variable before the gate runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Unset `_PARSED_SCOPE_ANCHOR_FILE` (or clear it in the `tally-error` branch) when `_tally_rc -ne 0`, matching the input/output separation the plan describes.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Pre-parse reset omits `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: The pre-parse reset in `run-step3-review.sh` clears `TALLY_PLAN_REVIEW_STATUS`, `VOTING_TALLY_FILE`, etc., but not `SCOPE_ANCHOR_FILE`, relying on line-146 initialization. Any future early path setting `SCOPE_ANCHOR_FILE` before loop invocation could leak into parse/fallback because stdout fallback only fills empty keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Add `SCOPE_ANCHOR_FILE=""` to the same reset block as the other handoff fields.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: `render-assessor-prompt.sh` duplicates escape pipeline locally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Local `emit_untrusted_feature_block` duplicates existing redact/escape helpers; a fifth copy of the escape pipeline increases drift risk versus voter/revise renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse shared emit_untrusted_file_block helper with feature_file tag


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: `launch-claude-subprocess.sh` inlines escape/redact instead of shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Context hardening inlines escape/redact instead of a shared block helper; subprocess context contract can drift from plan-review untrusted block emitters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor or source shared untrusted block and attribute escape helpers


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

