### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:130-152
- **Concern**: Blocking-todo count must cover the full manifest list, not only the display window. Scenario: Today `todos_left_count` uses `len(raw_items)` while display iterates only `raw_items[:_MAX_TODO_ITEMS]` and may stop early on `_MAX_TODO_CHARS`. Refactoring `_read_manifest_todos()` to count blocking items only inside that loop can miss a real deferred todo after item 20 or past the char budget, so `disposition_required` and `TODOS_LEFT_COUNT` drop to zero while deferred work remains
- **Proposed resolution**: Split classify/count from display: validate every entry, classify blocking vs nonblocking across the entire array, set `todos_left_count` to the full blocking count, then build bounded `todos_left` text from blocking items only; add a unit test with a blocking todo at index 21 (and optionally one truncated only by char budget) still requiring disposition

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/scope_disposition.py:150-151
- **Concern**: Omission suffix must not treat filtered validation todos as truncated items. Scenario: The existing `len(raw_items) > len(lines)` branch adds `… N more todo item(s) omitted` whenever display lines are shorter than raw entries; after filtering benign validation todos, a single ignored entry produces a fake omission line, breaking the planned `todos_left == ()` contract and polluting fingerprint/deferred-inventory artifacts
- **Proposed resolution**: Compute omission counts from blocking items only (`len(blocking_items) > len(displayed_blocking_lines)`), never from raw-vs-filtered deltas; keep nonblocking ignores silent

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/implement/scope_disposition.py:768-778
- **Concern**: validate_disposition_for_ship checks fingerprint staleness before disposition_required=false. Scenario: After filtering benign validation todos, recomputed coverage can have disposition_required=false while a proceed-partial record from the pre-fix prompt still exists; fingerprint no longer matches, so ship pre-driver returns scope-disposition-stale and halts even though no operator choice is needed
- **Proposed resolution**: When disposition_required is false after recompute, return ok before stale enforcement, or unlink stale disposition records in that branch; add a unit test with a recorded proceed-partial plus a benign-only manifest under advisory coverage

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-Scope Gate Reviewer
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:130-153
- **Concern**: Classifier spec omits mandatory blocking-token pre-check before nonblocking validation match. Scenario: Edge cases forbid ignoring failing/missing/unimplemented/docs todos, but the Approach only defines a positive ignore pattern (unrun full-suite + make py-lint/py-test). A matcher that checks validation wording first can still ignore compound strings like "make py-test not completed; still need to add regression tests", hiding real deferred work and skipping disposition despite compute_coverage disposition_required=band == "high" or blocking_count > 0 at line 293
- **Proposed resolution**: Define the helper as fail-closed: return blocking unless ALL hold: (1) no failure/action tokens (fail/failing/failed, fix, add, implement, missing, need, docs, write, etc.), (2) full-suite validation context, (3) make py-lint or make py-test mention. Add a unit test in python/tests/implement/test_scope_disposition.py for that compound string plus a mixed manifest case (benign validation todo + "finish docs" => todos_left_count==1)
