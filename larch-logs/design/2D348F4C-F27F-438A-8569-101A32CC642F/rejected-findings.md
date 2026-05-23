### [Plan Review] FINDING_12

### FINDING_12: `_max_fix` reduction not in the issue body's explicit ask
- **Concern**: The feature description (issue #2632 body) only asks to "extend run_ci_fix_vendor to include a Claude tier" or "document the asymmetry". It does not mention reducing `_max_fix` from 5 to 3. The plan adds that reduction as a Round 1 decision but the reviewer cannot see Round 1. The reviewer flagged it as scope creep. Raised by 1 reviewer: Cursor-Requirements.
- **Proposed resolution**: The reduction WAS the explicit Round 1 user decision (Decision 3 in discussion-round1.md): "Inner = 1 attempt × 3 tiers, outer = 3 retries." This finding should be EXONERATED — the change IS in scope per user direction, but the requirement-side reviewer was right that the issue body doesn't carry that direction. Optional follow-up: add a sentence to ship-pr.md noting that the budget change was confirmed during /design Round 1.


### [Plan Review] FINDING_16

### FINDING_16: Test cases 4 & 5 in plan are redundant (both exercise 9 launcher calls)
- **Concern**: Plan test case 4 (`ci_fix_vendor_all_tiers_fail_returns_to_outer_loop`) and case 5 (`ci_fix_vendor_outer_budget_capped_at_3`) both pin 9 total launcher calls (3 outer × 3 tiers). Raised by 1 reviewer: Codex-Requirements.
- **Proposed resolution**: Merge them, or specialize case 5: keep case 4 as the end-to-end "all fail" assertion, and rename case 5 to specifically assert `_max_fix=3` by checking the number of outer-loop attempts (e.g., count of detached-HEAD-guard calls or of jittered-backoff sleeps) rather than total launcher calls.


### [Plan Review] FINDING_21

### FINDING_21: Plan reverses #2395's "constraint C" (frozen CI-fix-loop risk surface)
- **Concern**: Older /design design artifacts under `larch-logs/design/CC79D945-CB91-4C84-BF50-45D8466D452D/` explicitly listed "do not restructure run_ci_fix_vendor's inner loop" as constraint C of #2395. This issue's plan deliberately reverses that. Future readers won't see the trade-off was conscious. Raised by 1 reviewer: Cursor-Innovation.
- **Proposed resolution**: Add one paragraph to `scripts/ship-pr.md` noting: "After #2632 landed, the CI-fix inner loop intentionally adopted the 3-tier waterfall shape originally introduced by #2395, reversing #2395's earlier constraint C. Telemetry to watch: stall-rate at `exit_stall 10-max-retries` / `12-max-retries`; Claude tier token consumption per phase in `larch-logs/implement/<RUN>/token-report.json`."


