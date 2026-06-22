## Proposed Design Outline

### Goals
- Add one typed `Finding` dataclass plus one `parse_findings(path) -> list[Finding]`, and adopt both in `review_and_fix` and `review_aggregate`.
- Make `Manifest.from_json` / `Manifest.to_json` the sole manifest representation; retire the `_dict_to_manifest` / `_manifest_to_dict` round-trips and the duplicated 18-key exclude-set.
- Convert the named internal sets (review status / `core_status`, votes, severities) to `StrEnum`.

### Non-goals
- No change to the `### FINDING_N:` markdown finding-file layout or any `KEY=value` wire format.
- No change to committed `manifest.json` bytes (`sort_keys=True`, `indent=2`, trailing newline preserved).
- No tree-wide enum sweep; no `Finding`/parser adoption outside the review pipeline.

### Approach sketch
- One `Finding` dataclass and one regex-based `parse_findings` replace the per-hop `### FINDING_N:` re-scans (`review_pipeline:1245`, `review_tally:628`).
- Route every manifest caller in `run_logs.py` through `from_json` / `to_json`; collapse the duplicate exclude-set to one constant.
- Define each `StrEnum` so its `.value` equals today's literal; serialize back to the existing string at every boundary.
- Keep `Finding` and the enums in-memory only; the wire and on-disk bytes stay identical.

### Surfaces in scope
- `python/run_logs.py` (Manifest, dict round-trips, exclude-set at `:734` / `:925`).
- `python/review_and_fix.py`, `python/review_aggregate.py`, `python/review_pipeline.py`, `python/review_tally.py`.
- A focused home for `Finding` + status `StrEnum`s, plus matching unit/parity tests.

### Open questions
- None.
