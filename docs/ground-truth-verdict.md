# Ground-truth Verdict for Token Allocation

## Scope

This artifact records the token-allocation capstone verdict for #4771.

- **Validation era:** incentivized-era runs only.
- **Blocked until:** calibration-incentive #5461 is shipped.
- **Since date:** `2026-06-26` at midnight UTC.
- **Started-at source:** strict manifest `started_at`; `updated_at` does not qualify.
- **Minimum larch version:** `52.1.0`.
- **Minimum corpus:** `150` unique qualifying `run_dir` values.

## Command

```bash
python3 python/cli.py analyze-issues run --ground-truth-verdict --since-date 2026-06-26 --min-larch-version 52.1.0 --min-runs 150
```

## Preconditions

- **Calibration incentive:** #5461 must be closed and shipped with a non-empty `closedByPullRequestsReferences` list. Bare `CLOSED` and `NOT_PLANNED` do not satisfy the gate.
- **Enrichment:** GitHub issue enrichment must not be degraded.
- **Targeted filed-OOS fetches:** no targeted `gh issue view` calls for filed-OOS details may fail.
- **Corpus:** the filtered run corpus must satisfy the unique-`run_dir` gate.

## Corpus Gate Result

- **Observed qualifying runs:** `5`.
- **Since date:** `2026-06-26`.
- **Minimum larch version:** `52.1.0`.
- **Required runs:** `150`.
- **Incentive-era shipped:** `no`.
- **Enrichment degraded:** `bulk_fetch_failed`.
- **Targeted-fetch degraded:** `targeted_fetch_degraded`.
- **Gate result:** `FAIL`.
- **Gate reason:** `calibration_incentive_check_unavailable`.
- **Command exit status:** `1`.

## Verdict

**NO-GO.**

## Decision

Do not ship token allocation #4771 until the verdict command produces a passing eligible corpus report and this artifact is updated with a human GO decision.

## Evidence Summary

The local smoke run could not prove the shipped-incentive precondition because GitHub issue enrichment failed. The generated verdict corpus block reported 5 qualifying runs, 150 required runs, `bulk_fetch_failed`, `targeted_fetch_degraded`, `Gate result: FAIL`, and `Gate reason: calibration_incentive_check_unavailable`. Before changing this artifact to GO, paste or summarize a generated report including:

- **Filtered verdict corpus block.**
- **Outcome buckets.**
- **Acceptance alignment.**
- **Severity slice.**
- **Missing-severity coverage.**

## Notes

- **No numeric alignment threshold** is encoded in the CLI.
- **Conservative matching** can undercount realized outcomes.
- **Pre-incentive and pre-`52.1.0` runs** are excluded by design.
- **Same basename runs** under `design/` and `implement/` are distinct qualifying runs.
- **Filed-OOS joins and accepted-evidence matching** use log-root-relative keys such as `implement/run-1`, not `code-review/run-1`.
