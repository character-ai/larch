### FINDING_1: NDJSON builders must preserve compact wire formatting
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Shared NDJSON builders must preserve compact, deterministic, single-line serialization, terminal newlines, path coercion, and insertion order expected by existing fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify `slot_manifest_ndjson` / shared panel NDJSON helpers use `json.dumps(row, separators=(',', ':'))`, terminal `\n` per row, and `str(path)` for path fields before serialization
  - From Cursor-Innovation: In ### NEW: python/tests/support/review_wire.py, require slot_manifest_ndjson / panel-manifest helpers to emit each row as json.dumps(row, separators=(",", ":"), sort_keys=False) + "\n", preserve caller dict insertion order, and return "" for zero rows; add one migrated assertion that pins a representative row string.
  - From Cursor-Pragmatic: In NEW review_wire.py specify every NDJSON emitter uses `json.dumps(row, separators=(",", ":"))` plus terminal newline; document that contract beside slot_manifest_ndjson

### FINDING_2: Finding-block builder must support migrated heading and field variants
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `make_finding_block` must preserve the distinct finding and OOS heading grammars, reviewer-label variants, optional fields, and omission behavior used by migrated fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document `make_finding_block` parameters for block kind (`finding` vs `oos`), id prefix (`FINDING_N` vs `OOS_N`), optional `[OUT_OF_SCOPE]` in the title, and `Reviewer` vs `Reviewer(s)` labels; keep non-canonical variants inline per plan
  - From Cursor-Pragmatic: Define make_finding_block kwargs for optional severity location focus_area reviewer vs reviewer(s) suggested_revision and OOS heading style; default omitted fields absent from output; keep marker-drift and noncanonical shapes as explicit literals per plan

### FINDING_3: Rejected-block builder must preserve exact spacing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: `make_rejected_block` must preserve wrapper spacing and trailing-newline behavior relied on by byte-exact plan-review assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify `make_rejected_block(..., *, plan_review_framing: bool)` reproduces the wrapper blank line and terminal `\n\n`; add one migrated assertion or a small builder self-check so framing-off blocks stay byte-identical

### FINDING_4: NDJSON helper roles and accepted row shapes need explicit contracts
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: `slot_manifest_ndjson` and `plan_review_slot_line` need clearly separated responsibilities so partial, nested, extra-key, and path-valued rows remain supported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document slot_manifest_ndjson as pass-through ordered dict rows (any keys nested dicts Path values) and plan_review_slot_line as optional-field convenience for flat plan-review slots only; tests with partial or nested rows call slot_manifest_ndjson

### FINDING_5: Named review-cluster migrations must be firm
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Leaving the four named review-cluster migrations optional permits canonical wire literals to remain duplicated, undermining the stated centralization acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Change these `### MAY_UPDATE:` entries to firm `### UPDATED:` entries and perform the canonical-fixture migrations already described.
