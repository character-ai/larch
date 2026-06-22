## Acceptance

- One `Finding` type and one `parse_findings(path, *, boundary=...)` parser live in `python/review_types.py`; `review_and_fix` and `review_aggregate` adopt them, and the duplicate `### FINDING_N:` regex re-scans on the same finding-file format are retired (kept only where no same-format scan remains).
- `Manifest.from_json` / `Manifest.to_json` is the sole manifest representation; `_dict_to_manifest`, `_manifest_to_dict`, and `_manifest_v2_merge` are deleted; the duplicated v2 exclude-set literal collapses to one role-classified key registry.
- The named internal sets are `StrEnum` (`ReviewCoreStatus`, `ReviewVote`, `JudgeSeverity`), each member `.value` equal to today's literal; `JudgeSeverity` has a single definition in `review_types`, imported by `voting.py`.
- Byte-stable on the wire and on disk: committed `manifest.json` bytes (`sort_keys=True`, `indent=2`, trailing newline), every `KEY=value` format, and the `### FINDING_N:` markdown layout are unchanged.
- `make py-lint`, `make py-test`, and `make lint` pass (parity and unit tests green).

diff_added: 780
diff_deleted: 330
mechanical_churn: false
diff_lines: 1110
