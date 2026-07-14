## G-Cfg-1 deviation — new cross-module wire literals not routed through config.py

**Identifier:** G-Cfg-1

**Policy:** "Define every exit code, env-var name, tunable, and wire literal once in config.py as a Final; build token sets from prior sets rather than re-listing."

**Triggering plan text:** The plan introduces `gate-c-return` (SETTLE_NEXT_ACTION token), new Step 5c refusal-reason tokens for invariant-violation and invalid-guideline-deviation publish refusals, and new Gate C exit codes in `design_session.py` — all cross-module wire literals consumed by `settle-rc-dispatch.md`, `design-step35-settle.md`, `design-step35-settle.sh`, and the SKILL.md orchestrator. `python/larch/core/config.py` is absent from the plan's file list.

**Existing baseline:** The pattern `gate-b-continue` / `gate-a-return` carries the same deviation in the current codebase. This plan extends it with genuinely new cross-module literals.

**Suggested resolution:** Add `python/larch/core/config.py` to the file list; define the new Gate C settle action, Step 5c refusal-reason tokens, and any new Gate C exit codes as `Final` constants there.
