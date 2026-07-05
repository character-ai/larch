## Decision 1: OOS_2 — timing mark wire labels in scope?

- **Question**: Should timing mark strings like "Step 0 — preflight", "Step 2 — implementation" be changed?
- **Resolution**: Skip. Timing marks are internal telemetry wire labels written to timing-ledger.tsv, not user-visible output. The issue description says "accept as wire-label passthrough per plan."
- **Source**: codebase (bootstrap.py lines 461/463; issue OOS_2 suggestion)

## Decision 2: OOS_7 — scan-all-lines fix in scope?

- **Question**: Is the `summary_heading_is_stalled` / `_summary_stalled_heading_index` all-lines scan fix in scope?
- **Resolution**: Yes. The issue explicitly requests this fix and the current first-non-empty-line behavior is fragile. Small, safe change.
- **Source**: codebase (final_report.py lines 612–625; issue OOS_7)

## Decision 3: redact.py test fixtures need to change?

- **Question**: Do `test_pr_body.py` / `test_gh.py` fixtures containing "[content truncated — safety]" need updating?
- **Resolution**: No. These are mock return values; the fail-closed check looks only for the prefix `[content truncated`. The em-dash in the mock is irrelevant to the assertion.
- **Source**: codebase (test_pr_body.py lines 208–234)

## Decision 4: test-write-final-report.sh top-reviewer assertion format

- **Question**: Does `cursor/correctness — 2` in test-write-final-report.sh line 849 need changing?
- **Resolution**: Yes. The `render_phase_detail` function (progress_report.py line 732) now emits `{label}: {count}` with a colon, so the assertion must change to `cursor/correctness: 2`.
- **Source**: codebase (progress_report.py line 732)

## Decision 5: bootstrap.py timing marks vs append-failure entry

- **Question**: Line 730 has em-dash in the append-failure fallback string (OOS_4). Lines 461/463 have em-dash in timing marks (OOS_2). Are these separate?
- **Resolution**: Yes. Line 730 `f"- **Step {site} — {tool} {status_label}..."` is user-facing (execution-issues.md entry), fix it. Lines 461/463 are wire-label timing marks, skip.
- **Source**: codebase (bootstrap.py lines 461, 463, 730)
