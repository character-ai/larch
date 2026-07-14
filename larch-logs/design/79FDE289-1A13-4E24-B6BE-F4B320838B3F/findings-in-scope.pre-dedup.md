### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py (planned)
- **Concern**: NDJSON builders must emit compact single-line rows matching existing fixtures (G-Wire-1). Scenario: Migrated plan-review and fake_cli paths pin byte-stable NDJSON like `{"slot":"cursor-plan-arch","tool":"cursor",...}` in python/test_support.py:203-209 and python/tests/review/test_plan_review.py:1174-1179; default `json.dumps` inserts spaces after `:` and `,` and breaks those exact-shape assertions
- **Proposed resolution**: Specify `slot_manifest_ndjson` / shared panel NDJSON helpers use `json.dumps(row, separators=(',', ':'))`, terminal `\n` per row, and `str(path)` for path fields before serialization



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py (planned)
- **Concern**: `make_finding_block` must cover all tally ballot heading grammars the firm migration targets (G-Wire-1). Scenario: python/tests/review/test_review_tally.py firm-updates require replacing `_mk_ballot` (`### FINDING_3: [OUT_OF_SCOPE] ...`, python/tests/review/test_review_tally.py:96-112) and `_write_classification_ballot` (`### OOS_1: ...`, lines 36-47); a single FINDING-only template cannot emit both shapes and the migration cannot complete without weakening classification coverage
- **Proposed resolution**: Document `make_finding_block` parameters for block kind (`finding` vs `oos`), id prefix (`FINDING_N` vs `OOS_N`), optional `[OUT_OF_SCOPE]` in the title, and `Reviewer` vs `Reviewer(s)` labels; keep non-canonical variants inline per plan



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py (planned)
- **Concern**: `make_rejected_block` must preserve rejected-findings spacing contract (G-Wire-1). Scenario: python/tests/review/test_plan_review.py compares `emit-rejected` stdout with `==` to helper output (e.g. 3919, 3931, 4057); `_make_rejected_block` uses a blank line after the optional `[Plan Review]` wrapper and a trailing `\n\n` (3880-3887)
- **Proposed resolution**: Specify `make_rejected_block(..., *, plan_review_framing: bool)` reproduces the wrapper blank line and terminal `\n\n`; add one migrated assertion or a small builder self-check so framing-off blocks stay byte-identical ## Findings 1. **correctness** — `python/tests/support/review_wire.py` (planned): NDJSON builders must emit compact single-line rows matching existing fixtures (**G-Wire-1**). Migrated plan-review and fake_cli paths pin byte-stable NDJSON. Default `json.dumps` inserts spaces and breaks exact-shape assertions. Specify compact separators, terminal newline per row, and `str(path)` coercion before serialization. 2. **correctness** — `python/tests/support/review_wire.py` (planned): `make_finding_block` must cover all tally ballot heading grammars the firm migration targets (**G-Wire-1**). Firm updates require replacing `_mk_ballot` and `_write_classification_ballot`, which use different OOS heading shapes. Document block kind, id prefix, optional `[OUT_OF_SCOPE]`, and reviewer label variants. 3. **correctness** — `python/tests/support/review_wire.py` (planned): `make_rejected_block` must preserve rejected-findings spacing (**G-Wire-1**). Several plan-review tests assert stdout equality against the current helper shape, including wrapper blank line and trailing `\n\n`. Specify framing parameter behavior and pin with at least one representative assertion.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py
- **Concern**: NDJSON builders omit the production compact-json contract. Scenario: Plan requires deterministic compact NDJSON and no production grammar drift, but never pins json.dumps options. Existing fixtures use manual {"slot":"..."} strings or json.dumps(row, separators=(",", ":")); production writers such as python/larch/review/plan_review_panel.py _write_manifest use separators=(",", ":") per row. Default json.dumps emits spaces after colons and can change migrated manifest bytes and diverge from the wire grammar this module is meant to centralize.
- **Proposed resolution**: In ### NEW: python/tests/support/review_wire.py, require slot_manifest_ndjson / panel-manifest helpers to emit each row as json.dumps(row, separators=(",", ":"), sort_keys=False) + "\n", preserve caller dict insertion order, and return "" for zero rows; add one migrated assertion that pins a representative row string.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py
- **Concern**: NDJSON builders omit compact json.dumps separators. Scenario: Production writers and compact hand literals use json.dumps(..., separators=(",", ":")); default json.dumps adds spaces after colons so slot_manifest_ndjson / plan_review_slot_line output will not match plan-review-slots.ndjson or panel-manifest.ndjson bytes and can desync migrated golden assertions
- **Proposed resolution**: In NEW review_wire.py specify every NDJSON emitter uses json.dumps(row, separators=(",", ":")) plus terminal newline; document that contract beside slot_manifest_ndjson



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/support/review_wire.py
- **Concern**: make_finding_block API not pinned to optional field omission. Scenario: Migrated families differ today: _mk_ballot omits Severity; aggregation fixtures include Severity and Reviewer(s); OOS uses OOS_ headings vs [OUT_OF_SCOPE] tags. A single baked template would change bytes and dedup/preview assertions even if parsers still pass
- **Proposed resolution**: Define make_finding_block kwargs for optional severity location focus_area reviewer vs reviewer(s) suggested_revision and OOS heading style; default omitted fields absent from output; keep marker-drift and noncanonical shapes as explicit literals per plan



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/review_wire.py
- **Concern**: plan_review_slot_line vs slot_manifest_ndjson roles underspecified. Scenario: test_plan_review_panel.py uses minimal rows with only tool and slot; plan-voter rows carry nested prompt_files. Typed plan_review_slot_line must not require output/agent or reject extra keys
- **Proposed resolution**: Document slot_manifest_ndjson as pass-through ordered dict rows (any keys nested dicts Path values) and plan_review_slot_line as optional-field convenience for flat plan-review slots only; tests with partial or nested rows call slot_manifest_ndjson



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/tests/review/test_review_aggregate.py:1, python/tests/review/test_plan_review_panel.py:1, python/tests/review/test_plan_review_round.py:1, python/tests/report/test_review_phase_detail.py:1
- **Concern**: Named review-cluster migrations remain optional. Scenario: The four files explicitly named for migration can retain canonical wire literals, so one grammar edit still requires updating those fixtures and the stated centralization feature is incomplete.
- **Proposed resolution**: Change these `### MAY_UPDATE:` entries to firm `### UPDATED:` entries and perform the canonical-fixture migrations already described.



