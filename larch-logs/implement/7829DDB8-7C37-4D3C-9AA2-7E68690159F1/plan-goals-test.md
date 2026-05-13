## Goal
Consolidate duplicate is_transient_net_signature() into shared scripts/lib-net.sh.

## Implementation Plan
1. Create scripts/lib-net.sh — sourced-only library with consolidated function (all patterns from both copies)
2. Create scripts/lib-net.md — sibling documentation
3. Modify scripts/collect-agent-results.sh — add source, remove local definition
4. Modify scripts/ship-pr.sh — add source, remove local definition
5. Modify scripts/test-collect-agent-results.sh — add direct unit tests for is_transient_net_signature

## Test plan
Run: make test-collect-agent-results — verify all cases pass including new pattern assertions.
