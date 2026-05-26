### [Plan Review] FINDING_17

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-fixture-interface
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/decompose-file-issues.sh:83-85,158-160
- **Concern**: Proposed p2c fixture cannot verify partition-deps.tsv column semantics because raw piece numbers equal 1-based batch positions. Scenario: The script sorts by raw Piece N, then writes TSV columns as a+1 and b+1 batch positions; a future implementation that incorrectly writes raw piece numbers would still pass the proposed 1..5 fixture
- **Proposed resolution**: Use non-contiguous or out-of-order piece numbers in p2c, for example Pieces 10, 20, 30, 40, 50 with Piece 50 blocked by the first four, and keep expected rows 1 5 through 4 5 to pin position-based TSV semantics


