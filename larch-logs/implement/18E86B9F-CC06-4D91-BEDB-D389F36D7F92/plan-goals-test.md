## Goal
Implement issue #7737: [IMPLEMENTING] [LEAF OF 7676] Port GitHub pull-request, review, and issue-dependency operations.

## Implementation Plan
## Program context — read first

This leaf belongs to #7676 and the #7687 chief Rust migration. Before implementation, read the full body of #7687, then the canonical service decision in #7672. Preserve observable contracts and track implementation parity, consumer cutover, and Python removal separately.

Port pull-request, review-state, and native issue-dependency operations through the authenticated GitHub client from #7724. This leaf owns their fixed REST and GraphQL documents; it does not own issue CRUD, Actions, checks, releases, assets, or workflow orchestration.

Implement typed pull-request get/list/create/edit and the merge/review fields current callers require. Prefer REST. Where REST does not expose required merge or review state, use fixed checked GraphQL documents compiled into the adapter. Reject any GraphQL response containing `errors`, including partial-data responses.

Port issue-dependency list, add, and remove operations to GitHub's REST API. Preserve live-mutation authorization, freshness checks, idempotency, exact relationship read-back, status and exit contracts, and bounded diagnostics.

Acceptance criteria:

- Core DTOs cover only the current PR, review, and dependency contracts and expose no arbitrary GraphQL or URL surface.
- GraphQL documents are fixed in code, variables are typed, and any `errors` member fails closed.
- Pull-request creation and merge mutations reconcile ambiguous outcomes before retry and never create duplicates silently.
- Dependency mutations preserve authorization, freshness, exact add/remove/read-back, and idempotent behavior.
- Black-box parity covers success, no-match, permissions, partial GraphQL data, stale targets, duplicate edges, rate limits, malformed responses, and ambiguous mutation outcomes.
- The ledger records implementation parity separately from each later workflow's consumer cutover and Python removal.
- `SECURITY.md` documents fixed GraphQL and dependency-mutation trust boundaries.
- The change stays near or below 1,500 new non-generated Rust lines, including tests.

Native blocker: #7724. Canonical decision: #7672. Parent umbrella: #7676. Chief umbrella: #7687.

## Test plan
(no test plan section in plan-file)
