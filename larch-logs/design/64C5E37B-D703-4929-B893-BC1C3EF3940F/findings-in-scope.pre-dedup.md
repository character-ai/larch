### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/implement_dispatch.py:65
- **Concern**: [SCOPE-REDUCTION] Seed stage must use the same stdout-capture wrapper as guard, not a bare `step8_seed_initial_main` call. Scenario: The plan wraps `step8_python_guard_main` under stdout capture before emitting `NEXT_ACTION=stall`, but tells `ship_pre_driver_main` to call `step8_seed_initial_main([])` bare and only then replay output on failure. `step8_seed_initial_main` routes seeding through `_run_cli_forward` → `_forward_result`, which writes captured child stdout to process stdout during the call. Any seed-stage stdout would appear before `NEXT_ACTION=halt-seed` or `NEXT_ACTION=ship`, breaking the single-line stdout contract (same failure mode as guard/OOS).
- **Proposed resolution**: Mandate wrapping the in-process seed call in the same stdout-capture/replay-to-stderr pattern as guard (or route seed only through the capture-to-stderr subprocess helper). Emit `NEXT_ACTION=halt-seed` or `NEXT_ACTION=ship` only after capture completes.



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



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/implement_dispatch.py:599-622
- **Concern**: [SCOPE-REDUCTION] Approach still scopes `step8_oos_checkpoint_main` stderr replay outside the merge. Scenario: The Approach still says to mirror stderr-only OOS capture in `step8_oos_checkpoint_main`, a separate post-driver `implement step-8-oos-checkpoint` surface. Acceptance is only collapsing the three pre-driver fences into `ship pre-driver`. Prior rounds marked this out of scope; the bullet remains and can pull unrelated CLI stdout changes into the PR.
- **Proposed resolution**: Delete the `step8_oos_checkpoint_main` mirror sentence from Approach (and any implied work on that helper). Limit OOS stdout isolation to the new pre-driver capture-to-stderr path only; leave the checkpoint helper unchanged unless a follow-up issue scopes it.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:22
- **Concern**: [SCOPE-REDUCTION] Approach still mandates mirroring stderr-only replay in step8_oos_checkpoint_main outside the pre-driver merge surface. Scenario: Approach step 7 and line 22 tell implementers to change step8_oos_checkpoint_main, but Files to modify/create omits that helper. That helper serves the separate post-driver disposition-checkpoint path (python/cli.py implement step-8-oos-checkpoint), which today forwards disposition-checkpoint stdout to process stdout at python/implement_dispatch.py:610-611. Following Approach would alter unrelated CLI output and expand scope beyond collapsing the three pre-driver fences.
- **Proposed resolution**: Pdelete the step8_oos_checkpoint_main mirror bullet from Approach. Keep stderr-only capture/replay scoped to ship_pre_driver_main and the new OOS pre-driver stage only.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:844-845
- **Concern**: Standalone OOS disposition paragraph survives fence merge. Scenario: The plan replaces pre-driver items 1-3 with one `ship pre-driver` fence and NEXT_ACTION routing, but does not call out the post-fence OOS block at lines 844-845. That prose still says "Always invoke it", routes on standalone `oos file` exit codes, and tells the orchestrator to proceed to `step-8-ship.sh` on exit 0. After the merge, OOS runs inside the verb and routing must branch on `NEXT_ACTION=halt-oos` vs `NEXT_ACTION=ship`. Leaving this block unchanged revives three-fence semantics on recovery turns and can skip `ship pre-driver` or misroute before the ship driver.
- **Proposed resolution**: Add an explicit SKILL.md task to relocate or rewrite the ~844-845 OOS disposition/timing contract under the merged pre-driver model: state that disposition-checkpoint and `run-statistics` behavior is owned inside `ship pre-driver`/`oos file`, and replace exit-code orchestration with `NEXT_ACTION=halt-oos` (Step 18 + Tool Failures) and `NEXT_ACTION=ship` (proceed to `step-8-ship.sh` only).



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:599-622
- **Concern**: [SCOPE-REDUCTION] Approach still scopes `step8_oos_checkpoint_main` stderr replay. Scenario: The acceptance surface is collapsing the three pre-driver fences into `python/cli.py ship pre-driver`. Approach line 22 still asks to mirror stderr-only OOS capture in `step8_oos_checkpoint_main`, which serves the separate post-driver `implement step-8-oos-checkpoint` disposition path, not the new pre-driver verb. Implementing it adds unrelated CLI-output churn and was rejected as out of scope in prior rounds.
- **Proposed resolution**: Remove the `step8_oos_checkpoint_main` bullet from Approach and keep stderr-only replay limited to `ship_pre_driver_main` (guard + pre-driver `oos file`). Leave the post-driver disposition-checkpoint helper unchanged unless a separate issue targets it.



