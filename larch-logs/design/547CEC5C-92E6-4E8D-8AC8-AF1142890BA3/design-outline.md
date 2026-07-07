## Proposed Design Outline

### Goals
- Convert every remaining larch `run_in_background` launch to `bgjob start` plus chunked `bgjob wait` per `skills/shared/bgjob-wait.md`.
- Shrink `python/larch/lint/bg_wait_allowlist.txt` to at most the `skills/shared/orchestrator-never.md` compatibility entry.
- Add `scripts/test-bgjob.sh`, a real-process harness for owner death, budget expiry, dead daemon, and identity-checked reap.

### Non-goals
- Deleting the defense stack, its hooks, lints, sidecar tokens, or `python/larch/implement/bg_wait.py` (#6516 owns deletion).
- Waiter-subagent mode (rejected in the #6514 design round).
- Retiring terminal sentinels or changing any routing contract.

### Approach sketch
- Migrate in small mechanical passes, one surface group per commit: /design, /implement, /review, /research, state classifiers, shared docs, then lints and harnesses.
- Wrappers keep their names and `exec` under `bgjob start`; harness-visible stdout is the one `BGJOB_STATUS=STARTED` line; `$TMPDIR/bgjob/<step>.result.env` becomes the completion source of truth.
- Orchestrator prose swaps every task-notification wait for a foreground `bgjob wait --max-wait-s 270` loop gated on `BGJOB_RC=0` plus required step KVs.
- Terminal sentinels keep being written; legacy hooks stay functional and inert.
- Update prompt-shape harnesses and Python tests in the same PR as their surfaces.

### Surfaces in scope
- `skills/design/` (Step 3 review, Step 4 tail, Step 5c, final summary, brainstorm) plus `python/larch/design/`.
- `skills/implement/` (Steps 3, 5, 6, 7a, 8) plus `python/larch/implement/`.
- `python/larch/review/`, `skills/research/references/`, `python/larch/state/`, `skills/shared/`, `docs/`, `python/larch/lint/`, root and skill harnesses.

### Open questions
- None.
