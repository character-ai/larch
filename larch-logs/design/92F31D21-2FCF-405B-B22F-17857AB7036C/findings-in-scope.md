### FINDING_1: Blocking todo count must cover the full manifest
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The blocking-todo count can undercount real deferred work if counting is limited to the display window or stops at the character budget, which can incorrectly clear `disposition_required` and `TODOS_LEFT_COUNT` while blocking items still exist later in the manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Split classify/count from display: validate every entry, classify blocking vs nonblocking across the entire array, set `todos_left_count` to the full blocking count, then build bounded `todos_left` text from blocking items only; add a unit test with a blocking todo at index 21 (and optionally one truncated only by char budget) still requiring disposition

### FINDING_2: Omission suffix should ignore filtered validation todos
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The omission marker can be emitted for filtered-out validation todos even when there are no omitted blocking items, which breaks the intended empty `todos_left` contract and pollutes downstream artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Compute omission counts from blocking items only (`len(blocking_items) > len(displayed_blocking_lines)`), never from raw-vs-filtered deltas; keep nonblocking ignores silent

### FINDING_3: Stale-fingerprint check should not block when no disposition is required
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: `validate_disposition_for_ship` appears to reject advisory cases on fingerprint staleness before confirming that no disposition is required, which can halt ship flow even when the recomputed state no longer needs operator choice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When disposition_required is false after recompute, return ok before stale enforcement, or unlink stale disposition records in that branch; add a unit test with a recorded proceed-partial plus a benign-only manifest under advisory coverage

### FINDING_4: Blocking classifier needs a fail-closed pre-check
- **Reviewer(s)**: Cursor-dyn-Scope Gate Reviewer
- **Severity**: minor
- **Concern**: The blocking/nonblocking classifier can miss compound todo text that includes both validation wording and real work items, which risks filtering out genuinely blocking items and suppressing disposition when work remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Scope Gate Reviewer: Define the helper as fail-closed: return blocking unless ALL hold: (1) no failure/action tokens (fail/failing/failed, fix, add, implement, missing, need, docs, write, etc.), (2) full-suite validation context, (3) make py-lint or make py-test mention. Add a unit test in python/tests/implement/test_scope_disposition.py for that compound string plus a mixed manifest case (benign validation todo + "finish docs" => todos_left_count==1)
