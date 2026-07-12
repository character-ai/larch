### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/design/decompose.py:336-339
- **Concern**: [SCOPE-REDUCTION] Partition stub cannot be both byte-identical and naively wrapped with compose_named_block. Scenario: compose_named_block rstrip-trailing-newlines then emits exactly one newline before the end marker; decompose.py currently has a blank line before <!-- larch:plan:end --> inside the fence. A direct swap changes partition-input.txt bytes and can fail a pin-old-bytes test
- **Proposed resolution**: In decompose.py, call compose_named_block for the fenced placeholder and drop the byte-compatible claim. Pin the normalized fence block in test_decompose.py (spy plus golden substring). Do not change compose_named_block for this stub.
