# lib-timing-kinds.sh

`scripts/lib-timing-kinds.sh` exposes the canonical `TIMING_TASK_KINDS_ALLOWED` Bash array consumed by `scripts/timing-ledger.sh`.

The timing ledger accepts any kebab-case task kind matching its grammar, but emits a warning when the value is not listed here. That warning catches typo-class drift without dropping timing data. When adding a new `--timing-task-kind <kind>` call site under `skills/` or `scripts/launch-*`, update this allow-list in the same change; `scripts/test-implement-structure.sh` pins the invariant. The CI-fix launchers reserve `cursor-ci-fix` and `codex-ci-fix`.
