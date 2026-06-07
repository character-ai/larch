## Goal
Implement issue #3640: [IMPLEMENTING] [OOS] auto-fix-plan-commands.sh live-path coverage gaps (from #3628)\n\n## Out-of-Scope Observation.

## Implementation Plan
## Out-of-Scope Observation

**Surfaced by**: `/implement` code-review panel (round 3), issue #3628
**Phase**: implement
**Vote tally**: accepted

> **Trimmed 2026-06-07**: this issue originally combined **four** follow-ups from #3628. Items 1, 3, and 4 concerned the Step 3.6 assessor→Revert path (e2e orchestration coverage, partial-failure rollback semantics, failed-Revert contract) and are **superseded by #3648**, which removes the assessor, the Step 3.6 WORSE-majority Continue/Revert/Stop branch, and the `snapshot-plan-round.sh revert-round` subcommand entirely — there will be no Revert path left to test or to tighten. Only the validator auto-fix item below survives. The original 4-item body is preserved in this issue's edit history.

## auto-fix-plan-commands.sh offline coverage excludes live behavior

`test-auto-fix-plan-commands.sh` covers the loop / vendor-alternation / re-validation / KV contract through the `LARCH_AUTOFIX_DISPATCH_SH` seam, but not: (a) live Codex/Cursor launcher exit parsing (`launch-codex-exec.sh` `LAUNCHER_EXIT`, cursor `run-external-agent.sh` capture), (b) repo-root parity between the auto-fix re-validation and the shared validator caller sites, and (c) orchestrator cycle/attempt limits when the shared handler re-enters after an `AUTOFIX_STATUS=ok`. Add coverage (CI-gated where live vendors are available) so the production dispatch path is exercised, not only the seam.

### Scope notes

- This is independent of the 3-PR review overhaul (#3647 EXONERATE removal, #3648 assessor removal, #3649 necessity rubric): `auto-fix-plan-commands.*` is Component D of #3628 (plan-command validation auto-fix) and is explicitly out of scope for #3648.
- No ordering constraint against those PRs; worst-case overlap is line-level adjacency in `Makefile` / `scripts/relevant-checks.sh` test wiring.

---
*Auto-surfaced as an out-of-scope observation by the larch `/implement` workflow for #3628; originally combined from review findings OOS_2/3/5/6, trimmed to the surviving item after #3648 superseded the assessor-Revert items.*


## Test plan
(no test plan section in plan-file)
