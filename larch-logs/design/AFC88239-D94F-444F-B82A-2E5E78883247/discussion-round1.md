## Decision 1: Fix location for source-env.sh rehydration
- **Question**: Should the fix go in `_finish_step0_route()` (design_step0.py) or in `route_main()` (design_router.py)?
- **Resolution**: Fix goes in `_finish_step0_route()` in `design_step0.py`. That function already has `plugin_root`, `design_tmpdir`, `claude_pid`, `env` (with `ISSUE_NUMBER`, `REPO`, `SESSION_ID`), and `route`. It can call `session write-design-env` directly as a subprocess when `route.startswith("resume@")`.
- **Source**: codebase
