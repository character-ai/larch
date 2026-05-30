## Proposed Design Outline

### Goals
- Make `${output}.stderr-tail` carry the real agent stderr (not `.diag` wrapper boilerplate) for default-mode codex lanes that capture wrapper stderr to a custom sink.
- Teach `run-external-agent.sh` the custom sink path so `select_failed_agent_stderr_source` can prefer it in default mode.
- Close the gap for all 3 affected lanes (implement, lint-fix, review-and-fix).

### Non-goals
- No new `.stderr-tail` consumer wiring — step2-implement.sh keeps reading `SIDECAR_LOG` directly; this is a latent-correctness fix to the shared artifact.
- No change to `--capture-stdout` / `--capture-stdout-only` lanes or any Cursor lane (their child stderr is already routed correctly).
- No change to lanes that already use the `${output}.sidecar` convention (launch-codex-ci.sh, launch-review.sh).

### Approach sketch
- Add an optional `--stderr-sink PATH` flag to `run-external-agent.sh`; validate it via the existing `validate_meta_scalar_path`.
- Extend `select_failed_agent_stderr_source` with an optional explicit-sink argument; in the default (non-capture) branch prefer the explicit sink first, then the existing `${output}.sidecar` → output → `.diag` order. Capture-mode branches ignore it.
- Forward the lane's existing sink path via `--stderr-sink` from the 3 broken codex invocations.

### Surfaces in scope
- `scripts/run-external-agent.sh` (+ `.md`), `scripts/lib-failed-agent-stderr-tail.sh` (+ `.md`)
- `scripts/launch-codex-implement.sh`, `scripts/lint-fix-loop.sh`, `skills/review-and-fix/scripts/review-and-fix.sh` (+ `.md` siblings)
- Tests: `scripts/test-lib-failed-agent-stderr-tail.sh`, `scripts/test-run-external-agent.sh`

### Open questions
- None.
