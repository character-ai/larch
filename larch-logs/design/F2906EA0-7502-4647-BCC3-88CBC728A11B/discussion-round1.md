## Decision 1: Rename scope
- **Question**: How far should the lock-helper rename go (open question #3)?
- **Resolution**: Full rename. Rename the functions `external_serial_lock_acquire` / `external_serial_lock_release_after` to `external_startup_lock_acquire` / `external_startup_lock_release_after` in both lanes, AND rename the operator env vars `LARCH_EXTERNAL_SERIAL_LOCK_{TTL,TRIES,DELAY,FORCE_UNAME}` to `LARCH_EXTERNAL_STARTUP_LOCK_{TTL,TRIES,DELAY,FORCE_UNAME}`.
- **Source**: user

## Decision 2: Lock-path token
- **Question**: Should the unified lock-path token be `external-serial` (issue's literal) or `external-startup` (consistent with the rename)?
- **Resolution**: `external-startup`. The unified path is `/tmp/larch-external-startup-$USER.lock`, used byte-identically by both the Python and Bash lanes.
- **Source**: user

## Decision 3: Lock scoping key
- **Question**: Scope the unified lock per-$USER only, or also per boot session (open question #2)?
- **Resolution**: Per-$USER only. Keep the current `$USER`-scoped path and the existing TTL-30s stale-recovery; do not add a boot-session component.
- **Source**: user

## Decision 4: Operator env-var backward compatibility
- **Question**: Provide a fallback that still reads the old `LARCH_EXTERNAL_SERIAL_LOCK_*` env vars?
- **Resolution**: No. Hard rename — the old env-var names are no longer read. This is an accepted breaking change for operators who set them (the rename-scope choice explicitly accepted breaking operator env-var compat). No compatibility shim.
- **Source**: user

## Decision 5: Keychain empirical investigation
- **Question**: Block the fix on empirically confirming the Codex binary touches the macOS login Keychain at startup (open question #1)?
- **Resolution**: No. Proceed with unification as a strictly-safer change regardless of the empirical result (the issue's own conclusion). No `sudo fs_usage` / dtrace tracing is in scope. The open empirical question may be noted in prose but does not gate the change.
- **Source**: issue

## Decision 6: `tool` argument retention
- **Question**: Remove the `tool` parameter from the lock functions since it leaves the path?
- **Resolution**: Keep it in both signatures. The `tool` arg still gates the early-return guard (`Darwin` AND `tool in {codex, cursor}`); only its use in the path literal is removed. Callers continue to pass it.
- **Source**: codebase (`python/agents.py:1685`, `scripts/lib-external-launcher-common.sh:376-384`)

## Decision 7: Cross-tool serialization regression test
- **Question**: What new test coverage is required?
- **Resolution**: Add a regression assertion that a Codex startup-lock acquire blocks a concurrent Cursor acquire (and vice versa) on Darwin — coverage that would have caught the original per-tool bug. Update all existing path/env-var literals in the harnesses in the same change.
- **Source**: issue + `.claude/rules/launcher-argv-test-coverage.md`

## Decision 8: Python/Bash byte-identical parity (hard constraint)
- **Question**: What must not break?
- **Resolution**: The Python and Bash lock-path literal must stay byte-identical so a Python-launched tool and a Bash-launched tool serialize cross-lane. This is the whole point of the fix. Covered by `.claude/rules/external-tool-launcher-parity.md` (serial-lock spawn site parity surface).
- **Source**: codebase / repo rule
