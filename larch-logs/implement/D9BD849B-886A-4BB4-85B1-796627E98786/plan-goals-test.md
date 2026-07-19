## Goal
Implement issue #7738: [IMPLEMENTING] [LEAF OF 7676] Port GitHub releases and bounded asset streaming.

## Implementation Plan
## Program context — read first

This leaf belongs to #7676 and the #7687 chief Rust migration. Before implementation, read the full body of #7687, then the canonical service decision in #7672. Preserve observable contracts and track implementation parity, consumer cutover, and Python removal separately.

Port GitHub release, tag-reference lookup needed by releases, release-asset metadata, upload, download, and bounded asset streaming through the authenticated client from #7724. This leaf provides service operations; #7674 retains ownership of the release state machine and installation workflow.

Preserve exact draft/published selection, immutable-release checks, asset allowlists, digest and size fields, upload conflict handling, and machine-readable outputs current release callers consume. Validate redirect chains with an operation-specific host policy, strip authorization across origins, and reject downgrade, loops, unexpected content types, oversized or truncated assets, and caller-supplied absolute URLs.

Acceptance criteria:

- Typed methods cover only current release and asset operations; release orchestration stays outside the adapter.
- Downloads and uploads enforce size, duration, content-type, redirect, origin, and cancellation limits.
- Ambiguous create, upload, edit, and publish outcomes are reconciled before retry.
- Black-box and loopback fixtures cover drafts, immutable releases, missing and duplicate assets, digest mismatch inputs, redirects, partial streams, rate limits, permissions, cancellation, and timeout.
- Implementation parity can land before #7674 cuts over; the ledger preserves separate consumer-cutover and Python-removal states.
- No operation shells out to `gh` or exposes an arbitrary API path.
- Release and security docs describe the service boundary without duplicating #7674's state machine.
- The change stays near or below 1,500 new non-generated Rust lines, including tests.

Native blocker: #7724. Canonical decision: #7672. Parent umbrella: #7676. Chief umbrella: #7687.

## Test plan
(no test plan section in plan-file)
