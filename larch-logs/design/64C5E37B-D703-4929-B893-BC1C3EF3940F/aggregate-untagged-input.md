### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:844-845
- **Concern**: SKILL merge must explicitly preserve the pre-driver OOS disposition contract block. Scenario: The plan replaces pre-driver items 1–3 and says to replace guard/seeder/OOS routing prose, but does not call out retaining the long `Always invoke it` paragraph (disposition-checkpoint inside `oos file`, `run-statistics` timing, NEVER #16 flush_logs_pre rationale, halt-before-ship semantics). That prose is not superseded by `NEXT_ACTION` tokens alone; dropping it during the item collapse risks losing load-bearing operator contract.
- **Proposed resolution**: Add an explicit SKILL edit bullet: after the merged `ship pre-driver` fence and `NEXT_ACTION` routing, preserve or relocate the existing `Always invoke it` / disposition-checkpoint / flush_logs_pre paragraph unchanged in substance (update only stale guard/seeder fence references).

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:844-845
- **Concern**: Orphan pre-driver OOS paragraph not explicitly slated for rewrite after items 1-3 collapse. Scenario: The plan replaces pre-driver items 1-3 with one `ship pre-driver` fence but only generically says to replace guard/seeder/OOS routing prose. The standalone block at lines 844-845 ("Always invoke it… disposition-checkpoint… NEVER #16 flush_logs_pre") sits after the retired item-3 fence. After the merge it has no referent, still describes a direct `oos file` hook, and carries load-bearing pre-ship OOS evidence / flush timing contract. A partial SKILL edit can leave dangling or conflicting prose beside `NEXT_ACTION=halt-oos` / `NEXT_ACTION=ship` routing.
- **Proposed resolution**: Add an explicit SKILL.md edit bullet: delete or rehome lines 844-845; fold only the still-valid pre-driver bits (OOS evidence before ship, halt-oos → Tool Failures + Step 18, ship → `step-8-ship.sh`, NEVER #16 flush timing) into the merged pre-driver / `NEXT_ACTION` section; keep post-driver `disposition-checkpoint` prose in the existing OOS checkpoint section only.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:844-845
- **Concern**: Standalone OOS disposition paragraph survives fence merge. Scenario: The plan replaces pre-driver items 1-3 with one `ship pre-driver` fence and NEXT_ACTION routing, but does not call out the post-fence OOS block at lines 844-845. That prose still says "Always invoke it", routes on standalone `oos file` exit codes, and tells the orchestrator to proceed to `step-8-ship.sh` on exit 0. After the merge, OOS runs inside the verb and routing must branch on `NEXT_ACTION=halt-oos` vs `NEXT_ACTION=ship`. Leaving this block unchanged revives three-fence semantics on recovery turns and can skip `ship pre-driver` or misroute before the ship driver.
- **Proposed resolution**: Add an explicit SKILL.md task to relocate or rewrite the ~844-845 OOS disposition/timing contract under the merged pre-driver model: state that disposition-checkpoint and `run-statistics` behavior is owned inside `ship pre-driver`/`oos file`, and replace exit-code orchestration with `NEXT_ACTION=halt-oos` (Step 18 + Tool Failures) and `NEXT_ACTION=ship` (proceed to `step-8-ship.sh` only).
