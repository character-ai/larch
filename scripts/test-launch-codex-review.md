# scripts/test-launch-codex-review.sh

Offline regression harness for `scripts/launch-codex-review.sh`.

It PATH-stubs `codex` and verifies launcher validation, canonical `--add-dir` placement for the output directory, outer-launcher retry metadata (including preserved `OUTER_LAUNCHER_RISK`), `--prompt-file` prompt preservation, `--agent-file` specialist prompt rendering and replay idempotency, dirty-tree sidecar publication, env-derived timing fallback to `codex-review`, Codex review token-ledger scraping from stderr-sidecar output, risk-gated Codex effort args, conservative risk derivation from specialist `--diff-file`, and array-safe model argument consumption. The injection cases assert that a model value containing spaces remains a single argv token and that a control-character model value fails before Codex is invoked or a `.done` sentinel is produced, while emitting the five-line preflight KV envelope and truncating stale sidecar bytes.

**Primary**: `scripts/launch-codex-review.sh`

**Makefile wiring**: `make test-launch-codex-review`, included in `test-harnesses-2`.
