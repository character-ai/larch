### OOS_1: [OUT_OF_SCOPE] `TIMING_VENDOR_MIN_COLS` still drifts in the live progress renderer
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `timing.py` now centralizes `TIMING_VENDOR_MIN_COLS` for the main report paths, but `_progress_report_live.py` still hardcodes its own `TIMING_VENDOR_MIN_COLS = 13`. That leaves a second source of truth, so future vendor-row column changes can diverge between live and non-live progress output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Import TIMING_VENDOR_MIN_COLS from larch.report.timing in _progress_report_live.py in a follow-up.`
  - From cursor-specialist-testing: `Import TIMING_VENDOR_MIN_COLS from larch.report.timing in _progress_report_live.py in a follow-up.`

### OOS_2: [OUT_OF_SCOPE] `gate-b-apply` reservation can interact badly with the Gantt row cap
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Adding `"gate-b-apply"` to `_CODER_APPLY_TASK_KINDS` makes the apply-row reservation path account for an additional reserved lane. In the same cap path, that can push the rendered Gantt past `PROGRESS_GANTT_ROW_CAP` when multiple apply lanes are present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Truncate apply rows by priority when len(apply_rows) > cap if observed in production.`

### OOS_3: [OUT_OF_SCOPE] `TimingLedger._append` can silently drop timing rows on flock timeout
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: When `TimingLedger._append` times out on the lock, it emits only a warning and skips the append. Under contention, gate-b-apply and other vendor timing rows can disappear with no visible bar in the chart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Retry or log to execution-issues in a follow-up.`
  - From cursor-specialist-edge-cases: `Surface append failures to execution-issues or add bounded retry; excluded from this plan intentionally.`
  - From cursor-specialist-testing: `Consider retry logic or surfacing append failures to execution-issues if contention is observed in production.`

### OOS_4: [OUT_OF_SCOPE] Design reruns can suppress fresh `gate-b-apply` timing rows
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Design round reruns reuse the same round and gate-b-apply idempotency keys, so a replayed Step 3 can fail to record a fresh apply window. That can hide post-Gate-B apply time in the Gantt on re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Version basenames per attempt if replay fidelity is required.`
  - From cursor-specialist-edge-cases: `Version output basenames per attempt or clear prior gate-b-apply rows on re-entry if replay fidelity is required.`
  - From cursor-specialist-testing: `Decide whether design re-entry needs per-attempt timing rows (as /implement stall recovery does) and version basenames or clear prior gate-b-apply rows on re-entry if so.`
