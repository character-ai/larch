### FINDING_1: Bash harness calls startup lock with wrong arity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Bash harness spec calls `external_startup_lock_acquire` with only the tool name. The function signature is `external_startup_lock_acquire <out_var> <tool>`. A one-argument call treats `codex` as the output variable name, leaves `tool` empty, hits the non-codex/cursor early return, and never `mkdir`s the shared lock. The new cross-tool regression would not exercise acquisition or blocking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Call external_startup_lock_acquire _LOCK codex / external_startup_lock_acquire _LOCK2 cursor, assert [[ -n $_LOCK ]] and path /tmp/larch-external-startup-$USER.lock, then assert the second _LOCK2 is empty while the first lock dir exists. Mirror python/checks.py:1348-1349 in scripts/lib-external-launcher-common.md.




### FINDING_3: No cross-lane Python/Bash serialization regression test
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan lacks a cross-lane serialization regression test. The issue requires Python `agents.py` and Bash `lib-external-launcher-common.sh` to contend on one shared lock path (e.g. lint-fix Bash wrapper vs Python negotiation/review). Separate within-lane Codex-then-Cursor tests can pass even if path literals drift between lanes, so the original cross-implementation race can ship again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add one deterministic test: Python `external_startup_lock_acquire("codex")` holds the real lock dir, then Bash `external_startup_lock_acquire _LOCK cursor` with `TRIES=1` must return empty (and the reverse). Pin the shared `/tmp/larch-external-startup-$USER.lock` path in both steps.


### FINDING_4: `docs/configuration-and-permissions.md` path/rationale update is conditional, not required
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The shared startup-lock path and cross-tool rationale are not unconditionally required for `docs/configuration-and-permissions.md`. The issue and approved outline require updating that doc with the unified `/tmp/larch-external-startup-$USER.lock` path and Codex/Cursor shared-lock rationale (issue suggested fix #4). The plan only mandates env/function renames and adds path/rationale updates conditionally ("If nearby prose names the lock path…"). The current paragraph names neither a path nor per-tool behavior, so an implementer can satisfy the plan while leaving only renamed symbols and no shared-path explanation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Operators reading configuration docs would still lack the unified-path contract that SECURITY.md and `scripts/lib-external-launcher-common.md` are slated to carry; doc cleanup for this listed surface stays incomplete. Make the `docs/configuration-and-permissions.md` bullet unconditional: revise the Darwin startup-lock paragraph to name `/tmp/larch-external-startup-$USER.lock`, state that Codex and Cursor share one lock, and use the renamed `LARCH_EXTERNAL_STARTUP_LOCK_*` / `external_startup_lock_*` symbols.




### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:1687-1688; scripts/lib-external-launcher-common.sh:384
- **Concern**: Python empty-USER fallback can diverge from the Bash shared path. Scenario: With USER exported as empty, Python would build /tmp/larch-external-startup-.lock while Bash uses /tmp/larch-external-startup-larch.lock, so Python and Bash launchers still fail to serialize against one shared mutex
- **Proposed resolution**: Specify Python user resolution as os.environ.get("USER") or "larch" so it matches Bash ${USER:-larch}; cover unset and empty USER in the path-parity test



### FINDING_2: Planned Bash test USER may embed path slashes
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned Bash test sets `USER` under the test temp root. If `USER` is a path under `TMPDIR_ROOT`, the fixed `/tmp/larch-external-startup-$USER.lock` path contains slashes; `mkdir` without parents cannot acquire the lock, and the new regression test fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Use a path-safe unique username token, for example larch-test-$(basename "$TMPDIR_ROOT") or larch-test-$$, not a filesystem path



### FINDING_2: Plan omits `docs/linting.md` from startup-lock rename
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits `docs/linting.md` from the full startup-lock rename. After the helper and env-var rename, the linting docs may still describe the run-negotiation-round harness as covering Darwin serial-lock acquire/release, leaving stale user-facing documentation for the renamed startup-lock contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add docs/linting.md to the plan and update the row to say Darwin startup-lock acquire/release, matching the new helper and env terminology.



