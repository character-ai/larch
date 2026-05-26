# test-review-and-fix.sh Contract

Regression harness for `skills/review-and-fix/scripts/review-and-fix.sh`.

It verifies standalone accepted-findings mode no-op behavior and Codex coder dispatch.

It also verifies `/implement` orchestrator mode selected by `--implement-tmpdir`: Codex success, Cursor fallback success, empty ambient `LARCH_DYNAMIC_ARCHETYPES_MAX` falling through to the session-env cap, no Claude-subagent fallback, all-coder failure, scrub failure fail-closed behavior, scrubbed-out `in-scope-filtered-out` status, post-dispatch tracked and untracked submodule revert failure, no-finding exit `0`, summary JSON schema `2`, coder/submodule fields, OOS accumulation, and `review-scout-manifest` batch flush: committed when `SCOUT_STATUS != na`, absent when `SCOUT_STATUS=na`.

Run with `bash skills/review-and-fix/scripts/test-review-and-fix.sh` or `make test-review-and-fix`.

Supports `--section dispatch|convergence|parsers|step5-starting-round` for CI shard packing. `dispatch` covers coder dispatch, scrubber, scout-manifest, and per-invocation tests up to the `convergence` section marker. `convergence` covers convergence and degraded-round loop tests. `parsers` exercises `review-implement-step5-loop.sh` capture-file KV parsing under `set -e` (including malformed-check fail-closed and lint stderr-only paths). `step5-starting-round` covers entry-time cap resume, prior-artifact probe and sync-retry handling, and `starting-round-invalid` / `env-write-failed` envelopes in `review-implement-step5-loop.sh`. Without `--section`, all tests run sequentially (local-dev backward compat).
