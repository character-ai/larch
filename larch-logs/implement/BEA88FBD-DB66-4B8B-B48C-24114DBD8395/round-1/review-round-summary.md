# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_5: `stall` branch references post-driver exit matrix incompatible with pre-driver contract
- **Reviewer(s)**: dyn-dyn-step8-routing-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md:830` — The `stall` branch tells the orchestrator to route per `ship-pr-exit-matrix.md` and also continue to Step 18, but that matrix's Exit 4 path is written for `step-8-ship.sh` JSON failures and directs **Continue to Step 16**, not Step 18. Pre-driver guard failures only emit `NEXT_ACTION=stall` on stdout (STALLED JSON is on stderr), so an orchestrator that follows the matrix can enter the post-driver Step 16 flow without ever invoking the ship wrapper, or otherwise take the wrong continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step8-routing-output.txt: For `NEXT_ACTION=stall`, drop the `ship-pr-exit-matrix.md` reference and pin a pre-driver-only contract: set `STALL_TRACKING=true`, skip `step-8-ship.sh`, and go directly to Step 18 (stall recovery before final report).


### FINDING_6: Missing `IMPLEMENT_TMPDIR` emits no `NEXT_ACTION` routing token
- **Reviewer(s)**: dyn-dyn-step8-routing-output.txt
- **Severity**: important
- **Concern**: `python/implement_dispatch.py:587-597` — `ship_pre_driver_main` calls `_tmpdir_from_env()`, which raises `SystemExit(2)` when `IMPLEMENT_TMPDIR` is unset, before any `NEXT_ACTION=...` line is emitted. That breaks the branch's stated stdout contract (`NEXT_ACTION=stall|halt-seed|halt-oos|ship` on every path) and leaves the orchestrator with no machine routing token on a setup failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step8-routing-output.txt: Catch the missing-tmpdir case inside `ship_pre_driver_main`, emit `NEXT_ACTION=halt-seed` (or a dedicated `halt-setup` token), replay a stderr diagnostic, and return a stable non-zero exit code instead of propagating bare `SystemExit(2)`.


