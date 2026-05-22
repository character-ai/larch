## Plan

### Goal

Eliminate the machine-wide `~/.cache/larch/sessions/current-design-env.sh` singleton that causes concurrent `/design` runs (across working-tree clones on the same machine, including nested-under-`/implement` runs) to silently clobber each other's session env. Key the stable symlink name on the Claude Code parent process id so each Claude session owns its own slot.

### Approach

The Claude Code Bash tool spawns a fresh `bash` subshell per Bash-tool call. Inside any such subshell, `$PPID` resolves to the Claude Code process itself, and is **stable for the entire Claude session**. Different Claude sessions, including concurrent ones in different working-tree clones, have **different** PPIDs.

**Empirically verified on Claude Code (Opus 4.7) during this design's quick-mode self-review**: from inside a Bash-tool subshell, `$PPID` resolves directly to Claude's PID (parent process name = `claude`), and is identical across separate Bash tool calls in the same Claude session (two consecutive Bash tool calls in this `/design 2599` run both reported `PPID=870`). The PID-keying mechanism is grounded in observed runtime behavior.

**Cross-skill audit** (grep + `ls scripts/write-*-current-env.sh`): only `/design` uses a machine-wide env symlink. `/implement`, `/research`, `/review` use other handoff patterns (`SESSION_ENV_PATH` env var, explicit per-session paths) and are unaffected by this bug. The fix is scoped to `/design` and its writer.

**Mechanism**:
1. Step 0 Bash block in `skills/design/SKILL.md` captures `$PPID` (= Claude's PID) and passes it to the writer via `--claude-pid "$PPID"`.
2. The writer scopes the symlink filename to that PID: `~/.cache/larch/sessions/current-design-env-${CLAUDE_PID}.sh`.
3. Every prelude line in SKILL.md becomes `[ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh`. Subshells inherit `$PPID`, so the same value resolves at every prelude.

The actual session env file still lives under `$DESIGN_TMPDIR/source-env.sh` (per-session, no change). Only the **symlink name** is keyed by Claude's PID. The conditional `[ -f ... ] &&` guard is preserved so missing/stale symlinks degrade to a silent no-op.

### Parallelism model — N concurrent `/implement` + `/design` sessions

- **Multiple `/design` across clones**: each is a separate Claude Code process with a unique PID → uniquely-named symlinks → no race. ✓
- **Multiple `/implement` across clones**: `/implement` does not use the machine-wide symlink (it threads `SESSION_ENV_PATH` explicitly). N concurrent `/implement` does not race on this symlink. ✓
- **`/implement` invoking nested `/design`**: nested `/design` runs in the same Claude session as its parent `/implement`, sees the same `$PPID`. Another concurrent `/implement` in a different Claude process has a different PID. ✓
- **One Claude session sequentially running multiple `/design`** (the pattern that produced this bug): both share the same `$PPID`, write the same symlink slot, but run sequentially — the second invocation correctly overwrites. ✓
- **PID reuse after Claude exit**: dangling symlinks are handled by the conditional guard; rare and detectable.

### Files to modify

1. **`scripts/write-design-current-env.sh`** (≈10 lines) — add `--claude-pid <pid>` flag (validate `^[1-9][0-9]*$`, max 7 digits). Symlink path becomes `${SYMLINK_DIR}/current-design-env-${CLAUDE_PID}.sh`. Transition shim: when `--claude-pid` is omitted, fall back to legacy unkeyed name and emit a stderr warning; remove the shim in a follow-up release.
2. **`scripts/write-design-current-env.md`** (≈20 lines) — replace `## Single-runner invariant` with `## Per-Claude-process symlink keying`. Document `--claude-pid`, the empirical verification, the legacy fallback, and an operator cleanup snippet for stale symlinks (`find ~/.cache/larch/sessions -name 'current-design-env-*.sh' -type l ! -exec test -e {} \; -delete`).
3. **`skills/design/SKILL.md`** (≈27 edits) — update `### Bash block prelude` prose and fenced canonical line to `current-design-env-$PPID.sh`; append `--claude-pid "$PPID"` in the Step 0a `_wdce_args=(...)` block; `replace_all` every remaining `current-design-env.sh` occurrence (25 prelude blocks + 1 explanatory paragraph) with `current-design-env-$PPID.sh`.
4. **`scripts/test-design-structure.sh`** (≈5 lines) — update check-11 `grep -Fq 'current-design-env.sh'` probes (line 256 comment + lines 279-280 assertions) to `'current-design-env-$PPID.sh'`. Add a new probe asserting `--claude-pid "$PPID"` appears literally in Step 0a (guards against future `bash -c` wrapping).
5. **`skills/design/scripts/test-write-design-current-env.sh`** (≈25 lines) — add four assertions: PID-keyed naming, two-PID independence (core concurrency invariant), invalid PID rejection (`0`, empty, non-integer), and transition shim (omitted flag → legacy name + stderr warning). Use fake high-numbered PIDs to avoid collision with real `/design` runs.
6. **`skills/design/scripts/test-write-design-current-env.md`** (≈5 lines) — describe new coverage.
7. **`AGENTS.md`** (≈3 lines) — rewrite the `Single-/design invariant` bullet: `/design` no longer relies on a machine-wide symlink; concurrent `/design` across clones (and concurrent `/implement` with nested `/design`) is safe by construction.
8. **`SECURITY.md`** (≈5 lines) — update the `/design` session-env paragraph; change path to `current-design-env-<PID>.sh`; drop the "concurrent /design runs must not overlap" sentence.

### Edge cases

`(...)` subshells inherit `$PPID` ✓ · `bash -c` wrappers would break it (guarded by structure probe) · PID reuse handled by conditional guard · pre-upgrade in-progress runs no-op gracefully · stale symlinks accumulate (operator cleanup snippet documented) · test isolation uses fake high PIDs.

### Failure modes

1. **Wrong PID captured** (future `bash -c` wrapping) → every Bash block fails with `DESIGN_TMPDIR: unbound variable`; mitigated by the new `test-design-structure.sh` probe.
2. **Invalid `--claude-pid`** (0, empty, non-integer) → writer rejects with explicit error before symlink update.
3. **Symlink race under filesystem stress** → `ln -sfn` is atomic at inode level; concurrent same-PID writes don't happen by construction; defense in depth.

### Testing strategy

- Extended `test-write-design-current-env.sh` with PID-keyed naming, two-PID independence, invalid PID rejection, transition shim.
- `test-design-structure.sh` check 11 updated; new probe for `--claude-pid "$PPID"` literal.
- Manual smoke: `/design <issue> --trivial`; verify `ls ~/.cache/larch/sessions/current-design-env-*.sh` shows symlink named with current Claude PID.
- Concurrent regression (deferred follow-up): scripted reproducer spawning two `/design` from two clones; not wired into `make lint`.
- `make lint` and `make test-harnesses` must pass.

## Acceptance

1. `scripts/write-design-current-env.sh` accepts `--claude-pid <pid>` and writes the symlink at `~/.cache/larch/sessions/current-design-env-${CLAUDE_PID}.sh` (validated PID grammar: `^[1-9][0-9]*$`). Omitting `--claude-pid` falls back to the legacy unkeyed name with a stderr warning (transition shim).
2. `skills/design/SKILL.md` Step 0a invokes the writer with `--claude-pid "$PPID"`. All 26 prelude occurrences source `current-design-env-$PPID.sh`. The `### Bash block prelude` section prose reflects the PID-keyed form.
3. Two concurrent `/design` invocations from different working trees on the same machine (e.g., `~/larch5` and `~/larch3`) each write their own tmpdir; neither's prelude resolves to the other's session. Verified by the new `test-write-design-current-env.sh` two-PID independence assertion.
4. `scripts/test-design-structure.sh` check 11 passes against the new prelude shape AND asserts `--claude-pid "$PPID"` appears literally in Step 0a.
5. `AGENTS.md` and `SECURITY.md` reflect the new symlink keying. The "concurrent /design must not overlap" guidance is removed from both.
6. `scripts/write-design-current-env.md` documents `--claude-pid`, the empirical PPID = Claude PID verification, the per-Claude-process keying model, and the operator stale-symlink cleanup snippet.
7. Cross-skill audit result is recorded in the writer doc: only `/design` is affected; `/implement`, `/research`, `/review` use other handoff mechanisms.
8. `make lint` and `make test-harnesses` pass.
9. Manual smoke test from one clone: after `/design <issue> --trivial`, `ls -la ~/.cache/larch/sessions/current-design-env-*.sh` shows a symlink named with the current Claude PID, pointing at the session's `source-env.sh`.

diff_lines: 150
