# Run-log batch registry

Run-log batches are registered in `python/larch/report/run_logs.py`.

Each batch declares:

- **extension**: the on-disk suffix.
- **mode**: `replace` or `append`.
- **sanitizer**: `none`, `json-object`, `json-lines`, or a specialized
  sanitizer.

The Python CLI validates the batch name before writing.
Append-mode batches must use `run-log append`.
Replace-mode batches must use `run-log write`.

The registry includes the durable implement, review, design, token, timing,
execution-issue, transcript, vendor-diagnostic, and checks-digest telemetry carriers.

`architectural-invariant-outcome` is a replace-mode `.json` batch with the
`json-object` sanitizer. It writes
`larch-logs/implement/<RUN_ID>/architectural-invariant-outcome.json` when an
implement run reaches Step 8 invariant-note composition. Schema version `1`
uses `outcome` values `clean`, `violation`, or `dropped`; `violation` is
blocking and feeds remediation, while `assessment_kind` is `clean` or
`violation` when a note exists. Reason `deterministic-clean` requires `clean`
with `assessment_kind=clean`. Reason `unavailable` requires the existing
`dropped` non-violation fallback with an empty assessment kind. A valid
violation remains blocking and is not downgraded by a later unavailable input.

`architectural-guideline-outcome` is a replace-mode `.json` batch with the
`json-object` sanitizer. It writes
`larch-logs/implement/<RUN_ID>/architectural-guideline-outcome.json` when an
implement run reaches Step 8 guideline-note composition.

Schema version `1` uses:

- `schema_version`: `1`.
- `phase`: `implement`.
- `step`: `8`.
- `outcome`: `pinned`, `clean`, or `dropped`.
- `reason`: stable token from `ship_guidelines.py`.
- `detail`: redacted bounded diagnostic.
- `guidelines_status`: `present`, `absent`, or `invalid`.
- `head_sha`, `base_ref`, and `assessment_kind`.

Schema version `1` remains unchanged. Historical records stay valid. For
guidelines, reason `deterministic-clean` requires `outcome=clean` and
`assessment_kind=clean`; reason `unavailable` requires `outcome=dropped` and an
empty assessment kind. The same combinations apply to invariant outcomes, with
`violation` reserved for an authored `violation-note`.

New schema-version `1` writers may add optional boolean `operator_waived`.
`true` is valid only with `outcome=dropped`, `reason=unavailable`, and an empty
assessment kind. Missing and `false` remain valid for historical records and
non-waived outcomes.

Runs below `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION`, or runs that did not
reach the Step 8 condition, are pre-feature-era for this batch. At or above the
cutover, Step 8-eligible runs without the artifact fail the audit scan.

`checks-digest-sizes` is an append-mode `.tsv` batch with `none` sanitizer.
It is content-free: rows contain counts and safe identifiers only.
