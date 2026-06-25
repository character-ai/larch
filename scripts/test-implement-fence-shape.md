# test-implement-fence-shape.sh

Structural harness for `/implement` prompt Bash fences. It parses `skills/implement/SKILL.md` and fails when a Bash fence drifts away from an intentional launcher shape.

## Invariants

- Exactly four pre-bootstrap call sites keep the old plugin-root guard shape:
  - the structured invocation pin for `python/cli.py pr closes-issue`;
  - the single Preflight `python/cli.py implement preflight` helper fence;
  - Step 0 initial bootstrap;
  - dirty-tree recovery resume.
- The Preflight helper replaces the two prior direct `plan-block read` anchors.
- The `preflight-helper` fence may use Bash 3.2 indexed-array argv construction.
- The `preflight-helper` fence is exempt from the one-logical-command check but must contain exactly one helper invocation.
- The helper is invoked through `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement preflight`.
- Direct Preflight `python/cli.py plan-block read` and `gh issue view` Bash fences are forbidden.
- Old-shape pre-bootstrap fences other than `preflight-helper` must contain exactly one logical command after the guard, allowed awk fallback, exports, comments, and blank lines are removed.
- Every post-Step-0 fence is exactly one nonblank, noncomment physical line.
- The harness expects exactly four old-shape fences and thirty-two new-shape launcher fences (Step 1.r is represented by the Step 0 bootstrap fence instead of its own prompt-side fence; legacy `step-0-degraded-gate.sh` is not an active Step 0 fence).
- Post-Step-0 fences call `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative .sh|.py target> ...`, except the terminal Step 16-17 direct Python CLI fence.
- Launcher targets must be repo-relative and must not contain `..`.
- Telemetry-only fences (`python3 python/cli.py timing telemetry-mark`, token/timing ledgers, token/timing reports) are banned; wrappers own telemetry internally.
- Inline `session read-key` calls are banned from SKILL.md fences.
- If any post-Step-0 fence targets `python/cli.py`, the harness also pins that the emitted launcher dispatches `.py` targets through `python3`.
- A generated `larch-run.sh` sandbox pins `.sh` and `.py` argv passthrough, invalid-target rejection, awk fallback parity with `step-0-bootstrap.sh`, and resume partial-upgrade emission when `plugin-root.env` exists but `larch-run.sh` is absent.

## Caller

`make test-implement-fence-shape` and the `test-harnesses-N` shard in `Makefile`.
