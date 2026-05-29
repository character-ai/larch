## Acceptance

- Every Step 3 `LOOP_STATUS` exit in `skills/design/SKILL.md` names its Step 3.6 disposition: `complete` / `converged` / `cap-hit` / `revision-failed` / `emit-plan-failed` / `zero-findings-degraded-panel` / `main-agent-vote-required` route THROUGH Step 3.6 (via Gate B); `tally-error` / `panel-failed` / `cap-reached` / `degraded-empty-collector` / `plan-size-trigger` / `plan-validator-defects` SKIP Step 3.6 with a status-specific `⏩ 3.6: assessor — skipped (Step 3 <status> short-circuit)` breadcrumb.
- `skills/design/references/approval-gates.md` bypass lists include `panel-failed` and stay aligned with SKILL.md (Gate C "When", Gate B multi-round outcomes, Step 3.5 entry); the same six Step 3.6 skip-breadcrumb literals appear byte-for-byte in both files.
- `main-agent-vote-required` is NOT in any skip list: after successful inline adjudication + re-tally (passing `--findings-classification-out` for the active round), the Step 3 result state (`.step3-plan-review-result.env`, `TALLY_PLAN_REVIEW_STATUS=ok`, `LOOP_STATUS=complete`) is refreshed before Gate B; a re-tally `tally-error` uses the `tally-error` short-circuit.
- `zero-findings-degraded-panel` continues to route THROUGH Step 3.6 (absent from every skip list).
- All existing `scripts/test-design-structure.sh` pinned substrings are preserved (edits are append-only where the substring is pinned); the cap breadcrumb pin `skipping panel and returning to Gate C.` stays literal or is updated in the same change.
- `scripts/test-design-structure.sh` gains a passive-summary Continue → Step 3.6 assertion and a Step 3.5 Gate-B-bypass coverage assertion.
- `skills/design/scripts/test-assess-plan-round.sh` gains an isolated two-entry integration case (case-local tmpdir + mocks): Entry 1 asserts the assessor skips on round 1; the cursor advances to 2; Entry 2 asserts the assessor fires (`ASSESSOR_STATUS=ok`, `ASSESSOR_VERDICT=worse-majority`, `EFFECTIVE_ASSESSORS=3`).
- `skills/design/scripts/test-assess-plan-round.md` documents the new integration case.
- `assess-plan-round.sh` / `snapshot-plan-round.sh` behavior is unchanged.
- Verification passes: `bash skills/design/scripts/test-assess-plan-round.sh`, `bash scripts/test-design-structure.sh`, and `make lint`.
