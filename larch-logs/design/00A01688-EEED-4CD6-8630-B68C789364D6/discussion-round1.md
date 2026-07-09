## Decision 1: Bug is real and in-scope to fix
- **Question**: Is the reported "#6610 fix incomplete" gap real, or already fixed / non-material?
- **Resolution**: Real and material. `_postmerge_main_health_gate` returns `Outcome.TRANSIENT` (ship.py:779-788) after writing `phase="postmerge-push-watch"`; `dispatch_ship.py` converts transient→reship (802-815) and unconditionally sets `PRE_FIX_REBASE_REQUIRED=true` (375-378); `_ship_pre_fix_validate_checkout` (601-610) does not check `PR_CLOSED`, and post-merge the checkout stays on `BRANCH_NAME`, so the merged/closed-PR branch gets rebased + force-pushed. No existing carve-out. Prior review FINDING_2 (0/3) relied on a checkout guard that does not actually check `PR_CLOSED`.
- **Source**: codebase

## Decision 2: Fix blast radius — scope to merged/closed PR only
- **Question**: Should the fix change the proactive-retry `Outcome.TRANSIENT` emission, or narrowly prevent the erroneous rebase?
- **Resolution**: Narrowly prevent the pre-fix rebase when `PR_CLOSED=true`. Keep the `Outcome.TRANSIENT` emission and the reship "resume at postmerge-push-watch and re-check main health" behavior unchanged — that is #6610's intended proactive recovery. `PR_CLOSED=true` is reliably persisted to `ship-pr-state.sh` at the postmerge phase (ship.py:1817-1824 first entry; `run_ship` resume branches use `.with_(pr_closed=True)`), and `_ship_pre_fix_read_state` already reads `PR_CLOSED`.
- **Source**: codebase

## Decision 3: Do not touch the manual-recovery path
- **Question**: Does `_emergency_repair_transient_recovery_result` need changes?
- **Resolution**: No. It already bypasses pre-fix rebase by calling `run_postmerge_phase()` directly (ship.py:1172). The finding confirms this reactive path is solid. Out of scope.
- **Source**: codebase
