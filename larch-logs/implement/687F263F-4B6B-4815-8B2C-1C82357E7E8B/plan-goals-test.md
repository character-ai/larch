## Goal
Speed up CI by resharding test-harnesses to 10 jobs and splitting lint into two parallel halves

## Implementation Plan

Goal: Speed up CI by resharding test-harnesses from 8 to 10 jobs and splitting the lint job into two parallel halves.

Files to modify:
1. Makefile — reshard test harnesses
2. .github/workflows/ci.yaml — update matrix + split lint job

Makefile changes:
- Add test-harnesses-9 and test-harnesses-10 to .PHONY
- Update test-harnesses umbrella to include test-harnesses-9 test-harnesses-10
- Shard 3: remove test-validate-citations (move to shard 10)
- Shard 4: remove test-validate-citations-budget (move to shard 10)
- Shard 7: remove test-ci-rerun-failed test-ci-status test-ci-wait test-ship-pr test-refresh-run-logs test-launch-cursor-ci test-launch-codex-ci (move to shard 8)
- Shard 8: remove test-harness-shards-coverage and test-launch-review; add 7 tests from shard 7
- Add shard 9 (new, single line): test-launch-review (isolated ~66s dominant)
- Add shard 10 (new, last, single line): test-harness-shards-coverage test-validate-citations test-validate-citations-budget
- Update comment to reflect 10 shards
- INVARIANT: test-harness-shards-coverage must be FIRST prereq of shard 10 (the new last shard)
- INVARIANT: each shard on a single physical line (no backslash continuations)

ci.yaml changes:
- test-harnesses matrix: [1, 2, 3, 4, 5, 6, 7, 8] → [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
- lint job: remove Node.js steps (setup-node, cache node-modules, cache puppeteer, Install Mermaid CLI, Lint Mermaid fences, Pipe SIGPIPE safety lint); remove fetch-depth: 0 (only needed for mermaid fences)
- Add new lint-mermaid job: checkout (fetch-depth: 0), setup-node, cache node-modules, cache puppeteer, Install Mermaid CLI (same conditional: only when node-modules-cache OR puppeteer-cache misses), Lint Mermaid fences (changed only), Pipe SIGPIPE safety lint

Verification: make test-harness-shards-coverage validates partition invariants.

## Test plan
(no test plan section in plan-file)
