## Decision 1: Conversion breadth and depth
- **Question**: How much should this first PR convert to the typed Ctx, given hotspots agents.py (127 env reads), design_lifecycle.py (65), plan_quality.py (50)?
- **Resolution**: Introduce the typed Ctx and adopt it at the `_core` entrypoint boundary of all 3 named hotspots. Build Ctx once at each boundary; thread `ctx` into new and refactored paths. Reads-only at the boundary: leave deep legacy `os.environ` reads working untouched. No full per-file read sweep.
- **Source**: user

## Decision 2: Env-write-as-IPC is in scope
- **Question**: The issue flags ~21 `os.environ[...] =` writes in design_lifecycle.py used as cross-step IPC. Address them here or defer?
- **Resolution**: In scope. Replace the cross-step-IPC env writes with explicit passing (via Ctx fields and/or return values) so data flow is local, not ambient.
- **Source**: user

## Decision 3: Which env writes get replaced vs. preserved
- **Question**: Do all `os.environ[...] =` writes in design_lifecycle.py get replaced?
- **Resolution**: No. Replace only pure in-process IPC writes, where a later Python function in the same process reads the value back via `os.environ.get`. PRESERVE writes that configure a spawned child process's environment (e.g. `CLAUDE_PID`, launcher-inherited vars) and the entrypoint `os.environ` save/restore in `*_core` (issue out-of-scope). A child process reads the real process env, not a Python Ctx, so those writes cannot become parameter passing. Where a subprocess needs a computed value, prefer `subprocess(env=...)` over a global `os.environ` mutation when low-risk; otherwise leave as-is.
- **Source**: codebase

## Decision 4: Build on existing config.ENV_* constants
- **Question**: Is there an existing env-name surface to build on?
- **Resolution**: Yes. config.py already defines `ENV_*` name constants (e.g. `ENV_DESIGN_TMPDIR`, `ENV_LARCH_RUN_ID`, `ENV_LARCH_QUIET_*`). Ctx fields read env via these constants. No central typed accessor exists today; Ctx is the new one.
- **Source**: codebase

## Decision 5: Hard constraints preserved (out-of-scope / don't-touch)
- **Question**: What must not change?
- **Resolution**: Keep per-entrypoint `os.environ` save/restore in `*_core` (required because cli.py runs multiple commands in one process). Keep the `.sh` env-file wire format unchanged. Adoption is incremental: legacy paths keep working; no big-bang rewrite.
- **Source**: feature description

## Decision 6: Tests
- **Question**: What does "units green" require?
- **Resolution**: Existing unit tests stay green. Tests that drive converted boundaries via process env may construct a Ctx (or keep setting process env, since the boundary still reads env once). Add focused unit coverage for the new Ctx constructor/parsing. No broad test rewrite.
- **Source**: feature description
