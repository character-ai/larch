### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/timing-report.sh:381-406
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] emit_round_array uses undeclared global match_idx in awk. Future awk edits could leak match_idx between emit_round_array calls. Declare match_idx in the function local list.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `489429700` — Add per-review-round timing reports  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `489429700` — Add per-review-round timing reports
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: `2a09054e2` — chore(larch-logs): flush implement run 400E3E18-…  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `2a09054e2` — chore(larch-logs): flush implement run 400E3E18-…
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: `2d230050d` — Apply relevant-checks fixes (Step 3)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `2d230050d` — Apply relevant-checks fixes (Step 3) ## Review summary This branch adds additive `round` rows to the timing ledger, aggregates them into `timing-report.json` under matching `per_step` intervals, instruments `/implement` Step 5 and `/design` Step 3 loops (including MAV/coder handoff deferral), refreshes design publish timing before log copy, and extends tests/docs. From a **security / trust-boundary** lens, the change stays inside existing session-tmpdir telemetry patterns and does not introduce new shell execution surfaces, network calls, or auth paths. **Controls that look sound**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **Ledger writes**: `record-round` validates skill enum and uint fields, sanitizes `--step` via `sanitize_field` (tabs/newlines), clamps negative durations, and reuses `append_tsv_line` + symlink refusal on the ledger file (`timing-ledger.sh`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ledger writes**: `record-round` validates skill enum and uint fields, sanitizes `--step` via `sanitize_field` (tabs/newlines), clamps negative durations, and reuses `append_tsv_line` + symlink refusal on the ledger file (`timing-ledger.sh`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Path binding**: Deferred helpers canonicalize `--implement-tmpdir` / `--design-tmpdir` with `cd … && pwd -P`, reject symlink tmpdir roots, and pin `LARCH_TIMING_LEDGER` to `$tmpdir/timing-ledger.tsv` instead of inheriting caller env.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Path binding**: Deferred helpers canonicalize `--implement-tmpdir` / `--design-tmpdir` with `cd … && pwd -P`, reject symlink tmpdir roots, and pin `LARCH_TIMING_LEDGER` to `$tmpdir/timing-ledger.tsv` instead of inheriting caller env.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Untrusted artifact parsing**: `review-tally.env` is read with `awk` (not `source`); counts are re-validated with `^[0-9]+$` before `record-round`. `voting-tally.md` OOS parsing is static `awk` over pipe fields.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Untrusted artifact parsing**: `review-tally.env` is read with `awk` (not `source`); counts are re-validated with `^[0-9]+$` before `record-round`. `voting-tally.md` OOS parsing is static `awk` over pipe fields.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **JSON emission**: `emit_round_array` prints only numeric `round` / `duration_seconds` / `accepted` / `rejected` / optional `oos`; step labels are not taken from round rows into JSON objects.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **JSON emission**: `emit_round_array` prints only numeric `round` / `duration_seconds` / `accepted` / `rejected` / optional `oos`; step labels are not taken from round rows into JSON objects.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Publish hygiene**: `design-publish.sh` renders timing JSON under a private `mktemp` dir, validates with `jq` when available, moves only `timing-report-final.json`, and on failure removes `timing-report-final.*` before logging via `append-tool-failure.sh --redact` — reducing risk of publishing stale stderr/sidecars that might contain paths or tool output.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Publish hygiene**: `design-publish.sh` renders timing JSON under a private `mktemp` dir, validates with `jq` when available, moves only `timing-report-final.json`, and on failure removes `timing-report-final.*` before logging via `append-tool-failure.sh --redact` — reducing risk of publishing stale stderr/sidecars that might contain paths or tool output. **Non-issues for this lens**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: Committed `larch-logs/` churn from the chore flush (out of scope per run-log policy).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Committed `larch-logs/` churn from the chore flush (out of scope per run-log policy).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: Per-round `accepted`/`rejected`/`oos` in published run logs are intentional operational metrics, not secret-bearing fields.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Per-round `accepted`/`rejected`/`oos` in published run logs are intentional operational metrics, not secret-bearing fields.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: Orchestrator SKILL prose references `$round_start_s` without a fenced read; the helper still enforces uint validation on `--start-s` / `--end-s`, so there is no injection path there.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Orchestrator SKILL prose references `$round_start_s` without a fenced read; the helper still enforces uint validation on `--start-s` / `--end-s`, so there is no injection path there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/review-and-fix/scripts/review-implement-step5-loop.sh:101-167
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] In-loop implement timing duplicates record-round inline instead of delegating to record-implement-review-round-timing.sh like design does. Future count or step-label changes require editing two parallel code paths. Delegate in-loop emits to the helper (optional count overrides) for parity with plan-review-loop.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_52

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_52: **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:51-78` — When `round-N/review-tally.env` exists, `ACCEPTED_COUNT` / `REJECTED_COUNT` (or `ACCEPTED` / `REJECTED` aliases) are taken as authoritative whenever they are numeric, including `0`, so artifact fallbacks never run. If the env file is stale (e.g. pre–main-agent-vote tally with zeros) but `accepted-findings.md` / `rejected-findings.md` / `review-summary.json` reflect post-adjudication counts, the deferred helper records zeros. `REJECTED_COUNT=0` does trigger the `review-summary.json` fallback, but `ACCEPTED_COUNT=0` does not. **Suggested fix:** Prefer tallies when `review-tally.env` is missing or keys are non-numeric; when numeric env counts are zero, reconcile against artifacts/JSON (max or explicit post-MAV refresh) so deferred emission after MAV re-tally failure cannot silently under-report accepted findings.
- **Reviewer**: dyn-tally-parsers-output.txt
- **Concern**: - **correctness** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh:51-78` — When `round-N/review-tally.env` exists, `ACCEPTED_COUNT` / `REJECTED_COUNT` (or `ACCEPTED` / `REJECTED` aliases) are taken as authoritative whenever they are numeric, including `0`, so artifact fallbacks never run. If the env file is stale (e.g. pre–main-agent-vote tally with zeros) but `accepted-findings.md` / `rejected-findings.md` / `review-summary.json` reflect post-adjudication counts, the deferred helper records zeros. `REJECTED_COUNT=0` does trigger the `review-summary.json` fallback, but `ACCEPTED_COUNT=0` does not. **Suggested fix:** Prefer tallies when `review-tally.env` is missing or keys are non-numeric; when numeric env counts are zero, reconcile against artifacts/JSON (max or explicit post-MAV refresh) so deferred emission after MAV re-tally failure cannot silently under-report accepted findings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_64

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_64: **code-quality** `scripts/timing-ledger.sh:261-265` — New `cmd_record_round` duration math uses `(( end_s < start_s ))` and `$((end_s - start_s))` without `10#` coercion, while callers elsewhere use `$((10#$ROUND_NUM))` to avoid Bash 3.2 leading-zero/octal pitfalls. Epoch seconds are unlikely to be zero-padded today, but persisted `round-start-s` or hand-edited fixtures could still trip `set -e` or wrong durations. **Suggested fix:** Coerce with `local s=$((10#start_s)) e=$((10#end_s))` (and similarly for `--round` if passed as a bare string) before comparisons and subtraction, consistent with `run-step5-review.sh` and the deferred helpers.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/timing-ledger.sh:261-265` — New `cmd_record_round` duration math uses `(( end_s < start_s ))` and `$((end_s - start_s))` without `10#` coercion, while callers elsewhere use `$((10#$ROUND_NUM))` to avoid Bash 3.2 leading-zero/octal pitfalls. Epoch seconds are unlikely to be zero-padded today, but persisted `round-start-s` or hand-edited fixtures could still trip `set -e` or wrong durations. **Suggested fix:** Coerce with `local s=$((10#start_s)) e=$((10#end_s))` (and similarly for `--round` if passed as a bare string) before comparisons and subtraction, consistent with `run-step5-review.sh` and the deferred helpers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

