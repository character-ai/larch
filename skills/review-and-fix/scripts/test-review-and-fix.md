# test-review-and-fix.sh Contract

Regression harness for `skills/review-and-fix/scripts/review-and-fix.sh`.

It verifies standalone accepted-findings mode no-op behavior and Codex coder dispatch.

It also verifies `/implement` orchestrator mode selected by `--implement-tmpdir`: Codex success, Cursor fallback success, empty ambient `LARCH_DYNAMIC_ARCHETYPES_MAX` falling through to the session-env cap, no Claude-subagent fallback, all-coder failure, scrub failure fail-closed behavior, scrubbed-out `in-scope-filtered-out` status, post-dispatch tracked and untracked submodule revert failure, no-finding exit `0`, summary JSON schema `2`, coder/submodule fields, OOS accumulation, and `review-scout-manifest` batch flush: committed when `SCOUT_STATUS != na`, absent when `SCOUT_STATUS=na`.

Run with `bash skills/review-and-fix/scripts/test-review-and-fix.sh` or `make test-review-and-fix`.

Supports `--section dispatch|convergence|parsers|step5-starting-round` for CI shard packing. `dispatch` covers coder dispatch, scrubber, scout-manifest, and per-invocation tests up to the `convergence` section marker. `convergence` covers convergence and degraded-round loop tests. `parsers` exercises `review-implement-step5-loop.sh` capture-file KV parsing under `set -e` (including malformed-check fail-closed and lint stderr-only paths). `step5-starting-round` covers entry-time cap resume, prior-artifact probe and sync-retry handling, and `starting-round-invalid` / `env-write-failed` envelopes in `review-implement-step5-loop.sh`. Without `--section`, all tests run sequentially (local-dev backward compat).

Manifest carryover guard cases `cd` into the fixture work repo before computing `pre_coder_snapshot_dir "$round_dir"`, recompute `_repo_root_*` from fixture `$PWD` (not the harness toplevel pre-`cd`), and assert `snap_dir` is outside fixture `$PWD`, outside `round_dir`, and outside the coder grant root. They stage `pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, and path-diff patches under the relocated snapshot dir (not under `round_dir`), and delete the worktree negative-control patch via `pre_coder_path_diff_file`.

In-repo relocation coverage builds a work repo, `cd`s into it, and asserts `pre_coder_snapshot_dir` resolves under normalized `${TMPDIR}/larch-pre-coder-snapshots/` and outside fixture `$PWD` and `round_dir`. `0444` perms and stale-`0444` rewrite cases use `mode_of` (`stat -c %a` then `stat -f %Lp`; not GNU `find -printf`). Post-coder-head `mode_of` assertions run on `run_orchestrator_case` and `carryover-orchestrator` only (not `mav-apply-relocated-pre-head`, which keeps `CODER_STATUS=no-changes`). The `step5-starting-round` shard `eval`s `clear_stale_pre_coder_snapshot_artifacts` beside `pre_coder_snapshot_dir`. Sandbox-confinement trust-boundary prose lives in `review-and-fix.md` and `SECURITY.md` (no CI probe).
