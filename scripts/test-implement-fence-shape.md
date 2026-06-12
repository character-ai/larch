# test-implement-fence-shape.sh

Structural harness for `/implement` prompt Bash fences. It parses `skills/implement/SKILL.md` and fails when a Bash fence drifts away from one of the two intentional launcher shapes.

## Invariants

- Exactly five pre-bootstrap call sites keep the old plugin-root guard shape:
  - the structured invocation pin for `scripts/extract-closes-issue-from-pr.sh`;
  - the two Preflight `python/cli.py plan-block read` fences, which remain guard-only;
  - Step 0 initial bootstrap;
  - dirty-tree recovery resume.
- Every post-Step-0 fence is exactly one nonblank, noncomment physical line.
- Post-Step-0 fences call `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative .sh|.py target> ...`.
- Launcher targets must be repo-relative and must not contain `..`.
- Telemetry-only fences (`python3 python/cli.py timing telemetry-mark`, token/timing ledgers, token/timing reports) are banned; wrappers own telemetry internally.
- Inline `session read-key` calls are banned from SKILL.md fences.
- If any post-Step-0 fence targets `python/cli.py`, the harness also pins that the emitted launcher dispatches `.py` targets through `python3`.

## Caller

`make test-implement-fence-shape` and the `test-harnesses-N` shard in `Makefile`.
