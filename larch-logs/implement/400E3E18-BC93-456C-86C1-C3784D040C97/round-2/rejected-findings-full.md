### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Ledger isolation:** `design-publish.sh` and `render-final-summary.sh` bind `LARCH_TIMING_LEDGER` explicitly and `env -u IMPLEMENT_TMPDIR`, closing cross-skill ledger resolution bleed into published design timing JSON.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ledger isolation:** `design-publish.sh` and `render-final-summary.sh` bind `LARCH_TIMING_LEDGER` explicitly and `env -u IMPLEMENT_TMPDIR`, closing cross-skill ledger resolution bleed into published design timing JSON.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **TSV / JSON safety:** `record-round` validates skill enum and uint fields, clamps durations, and `sanitize_field`s step labels; `emit_round_array` emits only numeric round fields (plus numeric `oos` for design).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **TSV / JSON safety:** `record-round` validates skill enum and uint fields, clamps durations, and `sanitize_field`s step labels; `emit_round_array` emits only numeric round fields (plus numeric `oos` for design).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-119
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] skills/review-and-fix/scripts/record-implement-review-round-timing.sh:51-95 Implement uses two parallel record-round paths with different count sources (IRF_LAST_* in-loop vs artifact greps in deferred helper). Future tally or MAV changes update artifacts but in-loop timing still uses stale IRF_LAST counts, or record-round flags diverge between paths. Consolidate through one wrapper with optional accepted/rejected overrides; keep artifact counting for deferred paths only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Path hygiene:** Deferred helpers reject symlink tmpdirs, canonicalize with `pwd -P`, and bind ledger to `$TMPDIR/timing-ledger.tsv` under validated roots via `timing-ledger.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path hygiene:** Deferred helpers reject symlink tmpdirs, canonicalize with `pwd -P`, and bind ledger to `$TMPDIR/timing-ledger.tsv` under validated roots via `timing-ledger.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Publish surface:** `design-log-publish.sh` excludes `timing-report-final.stderr.log` / `.failure.log`; `design-publish.sh` renders to a private `mktemp` dir, validates with `jq`, and atomically moves only JSON into `$DESIGN_TMPDIR`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Publish surface:** `design-log-publish.sh` excludes `timing-report-final.stderr.log` / `.failure.log`; `design-publish.sh` renders to a private `mktemp` dir, validates with `jq`, and atomically moves only JSON into `$DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **Failure logging:** Render failures go through `append-tool-failure.sh --redact`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Failure logging:** Render failures go through `append-tool-failure.sh --redact`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **Untrusted reviewer data:** Counting uses fixed `grep`/`awk` patterns on session artifacts; numeric outputs are re-validated before ledger write. SKILL.md handoff prose preserves the existing untrusted-data treatment for MAV ballots.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Untrusted reviewer data:** Counting uses fixed `grep`/`awk` patterns on session artifacts; numeric outputs are re-validated before ledger write. SKILL.md handoff prose preserves the existing untrusted-data treatment for MAV ballots. No command injection, path traversal, secret leakage, authz bypass, or unsafe deserialization was introduced. Committed `larch-logs/` timing enrichment is operational metadata (durations and finding counts), not a new secrets channel.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: risk-integration: skills/design/scripts/design-publish.sh:228-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Publish skips timing JSON when jq absent. Design run log publish ships without per-round timing-report batch content. Require jq for publish or degrade with explicit operator warning in run summary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_49

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_49: **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:92-98` and `skills/design/scripts/plan-review-loop.sh:414-420` — `step5_persist_round_start` and `_persist_plan_round_start` write `round-start-s` with no-clobber semantics but never validate that `start_s` is numeric before persisting, unlike `_emit_*` helpers which bail when `start_s`/`end_s` fail `^[0-9]+$`. A blank or corrupted value is persisted and later deferred emit fails validation in the helper (`exit 2`, swallowed by `|| true`), dropping MAV/handoff round timing silently. **Suggested fix:** Reuse the same uint guard before `printf` (skip persist and optionally warn when invalid), or read back and reject empty/non-numeric files before writing.
- **Reviewer**: dyn-bash32-output.txt
- **Concern**: - **code-quality** `skills/review-and-fix/scripts/review-implement-step5-loop.sh:92-98` and `skills/design/scripts/plan-review-loop.sh:414-420` — `step5_persist_round_start` and `_persist_plan_round_start` write `round-start-s` with no-clobber semantics but never validate that `start_s` is numeric before persisting, unlike `_emit_*` helpers which bail when `start_s`/`end_s` fail `^[0-9]+$`. A blank or corrupted value is persisted and later deferred emit fails validation in the helper (`exit 2`, swallowed by `|| true`), dropping MAV/handoff round timing silently. **Suggested fix:** Reuse the same uint guard before `printf` (skip persist and optionally warn when invalid), or read back and reject empty/non-numeric files before writing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/scripts/plan-review-loop.sh:1469-1486
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] panel-failed terminal path hand-rolls timing emit instead of using _snapshot_terminal_exit_preserving_status. A future terminal branch may omit timing emission while other statuses use the unified hook. Route panel-failed through the shared terminal snapshot+timing helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: scripts/timing-report.sh:381-388
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] emit_round_array uses bubble sort for round ordering. Fine at n<=5 but harder to extend if round caps increase. Use a simpler linearithmic awk sort if round volume grows.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

