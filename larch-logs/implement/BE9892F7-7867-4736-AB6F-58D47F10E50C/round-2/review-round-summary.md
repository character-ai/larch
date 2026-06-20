# Review Round 2

- Mode: `diff`
- 4 accepted, 3 rejected (2 neutral)

## Accepted Findings

### FINDING_9: risk-integration: malformed data rows silently dropped without counter
- **Reviewer(s)**: dyn-legacy-tsv-schemas-output.txt
- **Severity**: important
- **Concern**: The plan calls for a **malformed-row warning counter** with fail-soft behavior, but the analyzer only increments `skipped_files` for whole files with unsupported/missing headers (`classification_tsv_schema_supported` / empty first line). Supported TSVs with bad data rows (empty votes, short rows, invalid `voting_result`, etc.) are silently dropped by `voter_agreement_row_from_panel` with no row-level counter or report note, so operators cannot tell “no qualifying panels” from “data was discarded.”
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-legacy-tsv-schemas-output.txt: Track `malformed_rows` (and optionally `ineligible_rows`) inside `voter_agreement_rows_from_tsv` or the analyzer loop, surface them in the Corpus section, and add harness coverage for a supported-header file with corrupt rows.


### FINDING_10: risk-integration: legacy compact `--voter-files` path lacks live-vs-TSV parity test
- **Reviewer(s)**: dyn-legacy-tsv-schemas-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires live-vs-committed parity for **legacy compact** `--voter-files` runs, but only the three-slot `--voter-tools` path is parity-tested against re-ingested TSV. `test_tally_excludes_narrative_only_voter_parse_rate_check` only asserts `v1`/`v2` scoreboard rows exist; it never compares `voting-tally.md` agreement output to `compute_voter_agreement(voter_agreement_rows_from_tsv(...))` on the emitted 18-column classification file. A compact-path label or vote wiring regression would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-legacy-tsv-schemas-output.txt: Add a compact `--voter-files` fixture mirroring `_CLASSIFICATION_HEADER`, assert live tally rows match TSV-reingested rows, and cover single-voter exclusion.


### FINDING_15: architecture: shipped harness does not assert 21-column fixture vote mapping
- **Reviewer(s)**: dyn-skill-harness-contract-output.txt
- **Severity**: important
- **Concern**: The offline harness builds a 21-column design fixture without `body_severity`, but never asserts that `v3_tool` / Cursor votes from that file appear correctly in the report; the `grep -Fq '| design | Cursor |'` check (`test-voter-calibration.sh:51`) is satisfied by the 22-column fixture alone. The plan and `test-voter-calibration.md:8` call out this case specifically as protection against header-driven mis-mapping (treating `v3_tool` as `body_severity`). That regression guard exists only in `python/test_voting.py:310-318`, not in the public skill harness that `make test-voter-calibration` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-harness-contract-output.txt: Add harness assertions tied to the 21-column fixture only (for example `grep -Fq '| design | Codex |'` on `FINDING_3`’s rejected row, or a dedicated `--log-root` scoped to `run-b`) so the shipped harness enforces the schema contract the docs describe.


### FINDING_16: architecture: code-review schema selection diverges from fluff-analysis
- **Reviewer(s)**: dyn-skill-harness-contract-output.txt
- **Severity**: important
- **Concern**: Code-review schema selection requires both `vN_severity` and `vN_tool` in the header before using the 21-column `DictReader` path, while the plan and `fluff-analysis.py:295` use severity columns alone to choose the named-rating path. Any committed 21-column TSV with severities but without `vN_tool` columns would be parsed by `_legacy_compact_rows_from_tsv` here but by `csv.DictReader` in `/fluff-analysis`, splitting the cross-tool ingestion contract the plan says should mirror fluff-analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-harness-contract-output.txt: Align compact detection with fluff-analysis (`all(f"v{pos}_severity" in header_set for pos in (1, 2, 3))`), keep tool-based voter labels optional via `_voter_label()`, and add a fixture for a severity-only 21-column header if that shape exists in historical logs.


