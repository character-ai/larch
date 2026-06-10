### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/oos.py:38-70
- **Concern**: [SCOPE-REDUCTION] In-memory serialize buffer diverges from bash on mid-scan classifier failure. Scenario: The retired `oos-serialize.sh` truncates then appends accepted blocks per `flush_block`; if a later block hits classifier exit 2, earlier accepted blocks remain in `OUTPUT_FILE` (`skills/shared/scripts/oos-serialize.sh:76-94`). The plan requires buffering and leaving the sink empty on any classifier failure, which changes emit-tally rebuild behavior when failure happens after at least one accepted block.
- **Proposed resolution**: Either drop the in-memory buffer and match bash incremental writes for parity, or keep fail-closed empty sink but add an explicit mid-scan classifier-failure parity test and document the intentional bash divergence in the plan acceptance section.
