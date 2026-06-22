## Decision 1: StrEnum conversion scope
- **Question**: Which string sets should become StrEnum in this change?
- **Resolution**: Named sets only. Convert the review status / `core_status` set, the vote set, and the severity set. Do NOT sweep every internal status string tree-wide; other internal string sets stay as a follow-up item.
- **Source**: user

## Decision 2: Finding parser adoption reach
- **Question**: How far should the single `Finding` type + `parse_findings` replace the per-hop `### FINDING_N:` regex re-scans?
- **Resolution**: Adopt `Finding` / `parse_findings` in `review_and_fix` and `review_aggregate`, AND retire the duplicate `### FINDING_N:` regex re-scans on the same finding-file format (e.g. `python/review_pipeline.py:1245`, `python/review_tally.py:628`) so the duplication the issue cites is actually removed. Do NOT extend the parser to unrelated hops outside the review pipeline.
- **Source**: user

## Decision 3: Manifest serialization compatibility (hard constraint)
- **Question**: Must `Manifest.to_json` reproduce today's committed `manifest.json` byte-for-byte?
- **Resolution**: Yes. `to_json` must emit identical JSON (`sort_keys=True`, `indent=2`, trailing newline) so committed run-log manifests and the parity/unit tests stay green. Treat `manifest.json` as a frozen on-disk contract.
- **Source**: user

## Decision 4: Wire-format and layout freeze (hard constraint)
- **Question**: What must not change on the wire or on disk?
- **Resolution**: Keep the markdown `### FINDING_N:` finding-file layout and all `KEY=value` wire formats unchanged. Each new `StrEnum` keeps the existing string on the wire (its `.value` equals the current literal). Change in-memory representation only; serialize from the types. No behavior change to parity-checked artifacts.
- **Source**: codebase (issue "Out of scope / don't-touch")
