## Goal
Fix two suspension/network resilience gaps in /review's external-agent infrastructure.

## Implementation Plan
See plan.txt (suspend-resilient wait-for-reviewers.sh + transient-net retry in collect-agent-results.sh)

## Test plan
- make test-wait-for-reviewers (covers Part A + S1 suspend simulation)
- make test-collect-agent-results (covers Part B C_T1–C_T5)
- /relevant-checks clean
