# test-implement-fence-shape.sh

Structural harness for `/implement` prompt Bash fences. It parses `skills/implement/SKILL.md` and fails when a Bash fence drifts away from an intentional launcher shape.

## Invariants

- Exactly two pre-bootstrap call sites keep the old plugin-root guard shape:
  - the single Preflight `scripts/larch.sh implement preflight` helper fence;
  - Step 0 initial bootstrap.

The dirty-tree recovery resume fence moved to `skills/implement/references/bootstrap-recovery.md`. The `pr closes-issue` pin fence moved to `skills/implement/references/extracted-script-registry.md`.
- The Preflight helper replaces the two prior direct `plan-block read` anchors.
- The `preflight-helper` fence may use Bash 3.2 indexed-array argv construction.
- The `preflight-helper` fence is exempt from the one-logical-command check but must contain exactly one helper invocation.
- The helper is invoked through `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" implement preflight`.
- Direct Preflight `plan-block read` and `gh issue view` Bash fences are forbidden, whichever entrypoint spells the command.
- Old-shape pre-bootstrap fences other than `preflight-helper` must contain exactly one logical command after the guard, allowed `larch-run.sh --print-plugin-root` fallback, exports, comments, and blank lines are removed.
- Every post-Step-0 fence is exactly one nonblank, noncomment physical line.
- Step 0 initial and resume fences carry a `LARCH_CLAUDE_PID="$PPID"` environment-prefix assignment so the PID-keyed launcher matches later Bash-tool `$PPID` values.
- The harness expects exactly two old-shape fences and twenty-two new-shape launcher fences (Step 1.r is represented by the Step 0 bootstrap fence and Step 7.r by the Step 6 composite instead of their own prompt-side fences; legacy `step-0-degraded-gate.sh` is not an active Step 0 fence).
- Post-Step-0 fences call `"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" <repo-relative target> ...`; Step 16-17 reaches the Rust command through `scripts/larch.sh` in the same shape.
- Launcher targets must be repo-relative and must not contain `..`.
- Telemetry-only fences (`scripts/larch.sh timing telemetry-mark`, token/timing ledgers, token/timing reports) are banned; wrappers own telemetry internally.
- Inline `session read-key` calls are banned from SKILL.md fences.
- The `reship` and `ci-fix` Step 8+ branches must run `ship pre-fix-rebase` before stale-handoff clear or the ci-fixer subagent loop, except the documented phase14 continuation skip.
- The harness retains fail-closed launcher checks if a legacy `.py` target reappears; no active `/implement` fence uses one.
- Rust bootstrap coverage pins generated `larch-run.sh` `.sh` and `.py` argv passthrough, invalid-target rejection, and `--print-plugin-root` resolution through both `plugin-root.env` and `session-env.sh`.
- Session-lifecycle coverage separately owns the PID-keyed `implement-run-$PPID.sh` stable-runner contract.

## Caller

`make test-implement-fence-shape` and the `test-harnesses-N` shard in `Makefile`.
