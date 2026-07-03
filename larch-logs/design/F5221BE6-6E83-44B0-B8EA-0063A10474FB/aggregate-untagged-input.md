### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/state/bootstrap.py:449-466
- **Concern**: Missing LARCH_CLAUDE_PID still skips stable launcher creation silently. Scenario: Phase_infra only calls session write-implement-env when pid is non-empty. If Step 0 or resume omits the planned LARCH_CLAUDE_PID="$PPID" prefix, bootstrap can still reach BOOTSTRAP_NEXT=step2 with only tmpdir-local larch-run.sh and no implement-run-$PPID.sh, so the first post-Step-0 fence fails at launcher lookup.
- **Proposed resolution**: Treat empty LARCH_CLAUDE_PID as fatal in _phase_infra once implement-run is required: emit_step_failed("write-implement-env") when pid is missing, not only when the write call returns non-zero.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:631-655
- **Concern**: Step 8 foreground probe and stale-handoff clear stay outside implement-run. Scenario: Post-notification probe test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" and the separate rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" ... call are explicit non-launcher Bash fences. They still expand IMPLEMENT_TMPDIR in a fresh shell, so the probe always sees a root path and Step 8 can never advance past a genuine notification.
- **Proposed resolution**: Route both operations through implement-run-$PPID.sh via a tiny wrapper script, or document and test a one-line pointer-based probe that does not require exported IMPLEMENT_TMPDIR.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_recovery.py:121-147
- **Concern**: recovery-paths hardens only --tmpdir, not other tmpdir-derived argv paths. Scenario: The Step 2.4 fence passes --prelaunch-porcelain, --postlaunch-porcelain, --prelaunch-digests, and --out-file under $IMPLEMENT_TMPDIR/.... In a fresh shell those expand to /step2-*.nul and similar root paths while --tmpdir is env-recovered, so Claude-fallback commit path capture fails after the launcher fix.
- **Proposed resolution**: Resolve each tmpdir-derived path from os.environ IMPLEMENT_TMPDIR plus basename when the argv path is empty or not under the resolved tmpdir, mirroring the --tmpdir fallback.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:310
- **Concern**: Post-Step-0 dispatch still passes coder through caller-shell expansion. Scenario: The new stable launcher can export IMPLEMENT_TMPDIR, but the first Step 2 fence still expands --coder "$coder" in the fresh outer shell before the launcher runs. If coder is unset there, run-dispatch reaches step2-dispatch with an empty coder and fails instead of launching the selected implementer.
- **Proposed resolution**: Teach run_dispatch_main to recover an empty --coder from the resolved tmpdir's bootstrap-routing.env or another durable Step 0 source, validate it against the safe coder set, and add the empty --coder execution case to the planned test.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:389,397,634
- **Concern**: Tmpdir-derived path argv still becomes root-relative before launcher rehydration. Scenario: The plan only falls back for --implement-tmpdir and --tmpdir. Other argv built from "$IMPLEMENT_TMPDIR/..." still expands in the fresh caller shell first, so examples like --input /scout-coder-manifest.raw.json, recovery path sidecars under /, and --json-file /.step-8-ship-handoff.json can fail even though the launcher later exports the real tmpdir.
- **Proposed resolution**: For each prompt-side fence that passes a tmpdir-derived path argument, either omit redundant args and derive them from the resolved tmpdir inside the entrypoint, or reconstruct those specific path args after tmpdir fallback. Cover route-exit --json-file, normalize-coder-scout --input, recovery-paths sidecars/out-file, and the Step 2 redispatch --answers path if it remains prompt-side.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:310
- **Concern**: Accepted FINDING_1 is only partly fixed because the plan keeps non-tmpdir shell-expanded argv such as --coder "$coder" and "$IMPLEMENT_TMPDIR/..." file paths unchanged. Scenario: Fresh post-Step-0 shells can now reach implement-run-$PPID.sh, but the caller shell still expands --coder "$coder" to an empty value and "$IMPLEMENT_TMPDIR/foo" to /foo before the runner exports IMPLEMENT_TMPDIR, so Step 2 can still fail with --coder required or later helpers can read root-relative sidecars
- **Proposed resolution**: Do not keep the rest of each command unchanged; either make affected entrypoints reconstruct all session-derived argv from the exported IMPLEMENT_TMPDIR and durable routing files, or change prompt fences so session-derived args are literal or resolved inside the called wrapper before execution

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:631,655
- **Concern**: Step 8 handoff probe and stale-handoff clear still expand empty $IMPLEMENT_TMPDIR in fresh-shell Bash. Scenario: The plan retargets launcher fences but leaves NEVER #8 prose commands `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` and `rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" ...` as separate foreground calls. A new shell expands these to `/.step-8-ship-handoff.rc`, so a completed ship looks permanently premature and stale clears hit the wrong path.
- **Proposed resolution**: Resolve tmpdir from `current-implement-env-$PPID.sh` (same pointer the new runner uses) in those two commands, or route them through a one-line helper invoked via `implement-run-$PPID.sh`.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_ship.py:340-354
- **Concern**: ship route-exit still trusts a verbatim empty-expanded --json-file. Scenario: After the launcher exports `IMPLEMENT_TMPDIR`, the route-exit fence still passes `--json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"`, which becomes `/.step-8-ship-handoff.json`. `ship_route_exit_main` prefers that non-empty argv over the tmpdir default, so route-exit reads the wrong file even when `--implement-tmpdir` is env-recovered.
- **Proposed resolution**: After resolving tmpdir from argv or `IMPLEMENT_TMPDIR`, treat missing/unreadable `--json-file` (including root-only paths from empty expansion) as absent and default to `implement_tmpdir / ".step-8-ship-handoff.json"`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:727-729
- **Concern**: Step 16-17 direct Python fence stays on the broken fresh-shell contract. Scenario: The plan keeps the Step 16-17 exception as `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17 --implement-tmpdir "$IMPLEMENT_TMPDIR"` without launcher rehydration. In a fresh Bash call both variables expand empty; `closeout._resolve_tmpdir` only falls back to env when it is exported, so terminal report generation still fails after an otherwise successful run.
- **Proposed resolution**: Use the same `implement-run-$PPID.sh` prefix as other post-Step-0 fences for step-16-17, or add the same pointer-based tmpdir resolution used by the new runner.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:310,634; python/larch/implement/dispatch_step2.py:66-108; python/larch/implement/dispatch_ship.py:342-349
- **Concern**: Accepted FINDING_1 fix still leaves non-tmpdir argv expanded by the caller shell. Scenario: The plan keeps post-Step-0 arguments such as --coder "$coder" and --json-file "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json" unchanged while only adding env fallback for --implement-tmpdir/--tmpdir. In a fresh Bash tool shell, the new runner is found, but the outer shell has already passed --coder "" to Step 2 or "/.step-8-ship-handoff.json" to route-exit, so Step 2 can fail with missing coder and Step 8 can fail reading the wrong JSON.
- **Proposed resolution**: Audit prompt-side post-Step-0 fences for shell-expanded argv. For each required value, either derive it after runner rehydration inside the CLI or script, omit tmpdir-derived path args when the CLI can default from the resolved tmpdir, or change the prompt contract to substitute concrete literals instead of shell variables.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/bootstrap-recovery.md:31-38; python/larch/state/bootstrap.py:1788
- **Concern**: Resume bootstrap still relies on exported IMPLEMENT_TMPDIR. Scenario: The plan only adds LARCH_CLAUDE_PID="$PPID" to the --mode resume fence. That fence still calls step-0-bootstrap.sh directly from a fresh shell, and bootstrap invoke explicitly rejects resume when IMPLEMENT_TMPDIR is not exported, so degraded-prompt or dirty-tree recovery can fail before returning to Step 2.
- **Proposed resolution**: Route the resume fence through the new PID-keyed runner, for example with the same LARCH_CLAUDE_PID prefix before "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-0-bootstrap.sh --mode resume, or otherwise make the resume command recover IMPLEMENT_TMPDIR without caller shell state.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_step2.py:63-108
- **Concern**: Step 2 still passes an empty `--coder` after the launcher/tmpdir fix. Scenario: The live repro needed `export coder=codex` in the same fresh shell; the Step 2 fence still uses `"$coder"`, which expands empty across Bash tool calls. `run_dispatch_main` only hardens `--implement-tmpdir`, so dispatch can clear exit 127 yet fail at `step2-dispatch: --coder is required`.
- **Proposed resolution**: After resolving tmpdir from env, fall back to `coder` from `session-env.sh` (bootstrap already persists it) when argv `--coder` is empty; add a focused test mirroring empty-argv plus env/session-env.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_recovery.py:121-136; python/larch/implement/dispatch_manifest.py:241-252
- **Concern**: Only `--tmpdir`/`--implement-tmpdir` get env fallback; other `$IMPLEMENT_TMPDIR/...` argv slots stay broken. Scenario: Fresh shells still expand `"$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul"` and `"$IMPLEMENT_TMPDIR/scout-coder-manifest.raw.json"` to root paths like `/step2-prelaunch-porcelain.nul`. Step 2.4 `recovery-paths` and `normalize-coder-scout` fences keep those literals unchanged per the plan.
- **Proposed resolution**: For these hardened entrypoints, derive the conventional sidecar paths from the resolved tmpdir when explicit argv paths are empty or missing; cover with the same empty-argv-plus-env execution tests already planned for `--tmpdir`.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:310-341; python/larch/implement/dispatch_step2.py:66-67; python/larch/implement/dispatch_ship_seed.py:80-100
- **Concern**: Accepted FINDING_1 remains incomplete for non-tmpdir required argv. Scenario: The plan keeps `--coder "$coder"` and `--expected-branch "$BRANCH_NAME"` unchanged, so a fresh post-Step-0 shell still expands them to empty before the stable runner starts. Step 2 can then fail with missing coder, or an external-complete path can bail as `main-branch-post-dispatch` because expected branch is empty.
- **Proposed resolution**: Extend the plan with targeted durable fallbacks for these required values. Have `run_dispatch_main` recover empty coder from `$IMPLEMENT_TMPDIR/bootstrap-routing.env`, and have `step2_post_dispatch_main` recover empty expected branch from the same durable `BRANCH_NAME`. Add empty-argv tests for both paths.
