### [Plan Review] FINDING_3

### FINDING_3: Router plan presence must use a non-`None` check
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Marker Contract Auditor
- **Severity**: minor
- **Concern**: After switching `design_router.py` to `parse_named_block`, the router must distinguish an empty valid plan block from an absent or malformed block. Since parsing returns an empty string for a valid empty block, checking `plan_inner` for truthiness would incorrectly route the request as unplanned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one routing test with an empty-inner valid plan block asserting ROUTE=already-planned. In design_router.py use plan_inner is not None (or malformed == "" and plan_inner is not None).
  - From Cursor-Requirements: In the `design_router.py` UPDATED bullets, require `inner, _malformed = issue_wire.parse_named_block(body=body, marker="plan"); has_plan = inner is not None`
  - From Cursor-dyn-Marker Contract Auditor: In the `design_router.py` plan bullet, require `has_plan = plan_inner is not None` explicitly.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/decompose.py:336-339
- **Concern**: [SCOPE-REDUCTION] Partition stub cannot be both byte-identical and naively wrapped with compose_named_block. Scenario: compose_named_block rstrip-trailing-newlines then emits exactly one newline before the end marker; decompose.py currently has a blank line before <!-- larch:plan:end --> inside the fence. A direct swap changes partition-input.txt bytes and can fail a pin-old-bytes test
- **Proposed resolution**: In decompose.py, call compose_named_block for the fenced placeholder and drop the byte-compatible claim. Pin the normalized fence block in test_decompose.py (spy plus golden substring). Do not change compose_named_block for this stub.

