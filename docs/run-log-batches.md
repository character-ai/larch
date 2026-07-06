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
`violation` when a note exists.

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

Runs below `GUIDELINE_SHIP_OUTCOME_MIN_LARCH_VERSION`, or runs that did not
reach the Step 8 condition, are pre-feature-era for this batch. At or above the
cutover, Step 8-eligible runs without the artifact fail the audit scan.

`checks-digest-sizes` is an append-mode `.tsv` batch with `none` sanitizer.
It is content-free: rows contain counts and safe identifiers only.
