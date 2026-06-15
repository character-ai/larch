## Goal
Implement issue #4367: [IMPLEMENTING] [OOS] rebase-checkpoint-probe: auto-resolve trivial larch-log conflicts during early_rebase so orchestrator intervention is not needed.

## Implementation Plan
## Plan

## Approach

Implement the fix in `scripts/rebase-checkpoint-probe.sh`, not `scripts/rebase-push.sh`.

- Keeps behavior scoped to `/implement` early rebase checkpoints.
- Avoids changing generic `rebase-push.sh --keep-on-conflict` semantics (used in other callers).
- Matches the wrapper role: classify rebase outcomes before the orchestrator sees them.

On `rebase-push.sh` rc `1`:

1. Parse `CONFLICT_FILES` as today.
2. **Empty-list guard**: if the parsed path list is empty (rc=1 with no `CONFLICT_FILES=` line and `git diff --name-only --diff-filter=U` is also empty), skip the trivial-resolve loop entirely and emit the existing conflict envelope unchanged (exit 1 as today). An empty list is not "all trivial."
3. Split the non-empty comma-list into individual paths.
4. Treat only `larch-logs/*` paths as auto-resolvable trivial files.
5. For each trivial file, under `set +e` with explicit rc capture (same discipline as the existing `rebase-push.sh` invocation block):
   - Take the rebase `--ours` version (upstream/base during rebase) via `git checkout --ours -- <path>`.
   - If checkout fails (upstream deleted the file), use `git rm -f -- <path>` to stage the deletion.
   - Stage the path with `git add -- <path>`.
   - If any resolve step fails for this path, stop the batch immediately. Re-derive `CONFLICT_FILES` from `git diff --name-only --diff-filter=U` (not the stale pre-resolve list) and exit 1.
6. If any non-trivial conflicts remain, emit only those paths as `CONFLICT_FILES` and exit `1` (normal conflict path).
7. If all current conflicts were trivial and resolved: call `scripts/rebase-push.sh --continue --no-push --keep-on-conflict` internally, under `set +e` with explicit rc capture.
8. Repeat the same conflict-handling loop for consecutive larch-log-only rebase hops.
9. On eventual rc `0`: emit the existing success KVs and run the phantom probe as today.
10. On eventual rc `1` with non-trivial conflicts: emit `REBASE_OUTCOME=conflict`, `CONFLICT_FILES=<remaining>`, `ROUTE=conflict`, and skip the phantom probe.
11. On rc `3` or unexpected rc: preserve the existing failure handling.

A conservative iteration cap (50) guards against an unexpected infinite loop, falling through to the normal conflict exit if exceeded.

Do not add new KV keys: `CONFLICT_FILES` on exit 1 now carries only non-trivial conflicts; no other orchestrator surface changes.

## Files to modify/create

### UPDATED: scripts/rebase-checkpoint-probe.sh

Add trivial-conflict helpers:

- `_is_trivial_conflict_file <path>`: returns true only for `larch-logs/*` paths. Implemented with `case` for Bash 3.2 compatibility.
- `_resolve_trivial_conflict_file <path>`: runs `git checkout --ours -- <path>`; if that fails (upstream deleted the file), runs `git rm -f -- <path>`. On any error, emits a warning via `larch_err` and returns 1 (caller surfaces conflict list unchanged).

Refactor the single-invocation structure:

- Extract the `rebase-push.sh` call into a small internal runner that records the exit code and captures stdout/stderr.
- Keep `LARCH_QUIET_DISABLE=1` on each invocation.
- Keep the existing temp-file trap; reuse the same temp files across loop iterations (truncate before each invocation).

Add the conflict-loop around rc `1` (Bash 3.2 compatible, no associative arrays, no `mapfile`):

- Iterate up to 50 times.
- **Empty-list guard at loop entry**: re-parse `CONFLICT_FILES` from the latest stdout; if the parsed path list is empty, exit the loop and emit the existing conflict envelope unchanged (exit 1 as today).
- On each iteration: parse `CONFLICT_FILES` from the latest `rebase-push.sh` stdout, split on commas using a `while IFS= read -r` + `tr ',' '\n'` pipeline.
- Classify each path via `_is_trivial_conflict_file`.
- **All git operations inside the loop run under `set +e` with explicit rc capture**, matching the existing `rebase-push.sh` invocation block — never rely on `set -e` to catch git errors here.
- Resolve trivial paths via `_resolve_trivial_conflict_file` one at a time; if any resolve fails mid-batch, stop immediately, re-derive `CONFLICT_FILES` from `git diff --name-only --diff-filter=U` (not the stale pre-resolve list), and break to exit 1.
- If non-trivial paths remain: set `CONFLICT_FILES` to only those paths and break to the existing exit-1 block.
- If all paths were trivial and resolved: invoke `rebase-push.sh --continue --no-push --keep-on-conflict` under `set +e`, capture to the same temp files, update the exit code, and loop.
- On rc `0` after a continue: exit the loop and proceed to the existing success block (skip and outcome KVs, phantom probe).
- On rc `3` after a continue: break to existing failure handling.
- After 50 iterations: emit `larch_err` warning and fall through to exit 1 with current `CONFLICT_FILES`.

Preserve existing behavior unchanged:

- rc `0` skip precedence: `SKIPPED_ALREADY_PUSHED` before `SKIPPED_ALREADY_FRESH`.
- rc `3` `REBASE_ERROR` parsing (stdout before stderr).
- unexpected rc wrapping.
- breadcrumb format.
- forked-target argv handling.

### UPDATED: scripts/rebase-checkpoint-probe.md

Document the new larch-log conflict pre-pass:

- Add a section "Trivial-conflict pre-pass" explaining: `larch-logs/*` paths are auto-generated run-log artifacts; the wrapper resolves them by taking the upstream/base side; consecutive larch-log-only conflicts are handled internally; mixed conflict sets surface only remaining non-trivial paths; phantom probe runs only after a fully successful rebase.
- Note the iteration cap (50) and fallback.
- Update the `CONFLICT_FILES` grammar note: on exit 1, may contain only the non-trivial subset when trivial conflicts were auto-resolved.
- No new required KV is introduced.

### UPDATED: scripts/test-rebase-checkpoint-probe.sh

Extend the existing offline harness with new cases using stub repos:

1. **larch-log-only conflict resolves and exits 0**: initial call produces `CONFLICT_FILES=larch-logs/implement/run-1/manifest.json`; after internal resolve and continue, the wrapper exits 0 with `REBASE_OUTCOME=ok` and `ROUTE=continue`.

2. **consecutive larch-log-only conflicts loop internally**: initial call conflicts on one `larch-logs/*` file; first continue conflicts on a second `larch-logs/*` file; second continue exits 0; wrapper exits 0 and runs phantom probe.

3. **mixed conflict resolves trivial subset only**: `CONFLICT_FILES=larch-logs/implement/run-1/manifest.json,python/stall_recovery.py`; wrapper stages the larch-log file, emits `CONFLICT_FILES=python/stall_recovery.py`, exits 1; phantom probe does not run.

4. **trivial conflict followed by non-trivial continue conflict**: initial call conflicts only on `larch-logs/*`; continue exits 1 with `CONFLICT_FILES=agent-lint.toml`; wrapper exits 1 with `CONFLICT_FILES=agent-lint.toml`.

5. **trivial conflict with continue failure (rc 3)**: initial call conflicts only on `larch-logs/*`; continue exits 3 with `REBASE_ERROR=continue-failed`; wrapper exits 3 with `REBASE_OUTCOME=failed` and `ROUTE=bail`.

6. **resolve command failure re-derives CONFLICT_FILES**: stub `git checkout --ours` to exit non-zero on the second of two trivial paths; wrapper re-derives `CONFLICT_FILES` via `git diff --name-only --diff-filter=U` (not the stale comma list), exits 1 with the current conflict state.

7. **empty CONFLICT_FILES on rc=1 skips loop**: stub `rebase-push.sh` to exit 1 with no `CONFLICT_FILES=` output and a clean working tree; wrapper emits existing conflict envelope unchanged and exits 1 without calling `--continue`.

All new cases use real temporary git repositories with stub scripts or `PATH`-injected fakes for Bash 3.2 compatibility — no `declare -A`, no `mapfile`.

### UPDATED: scripts/test-rebase-checkpoint-probe.md

Update the case description to cover the new larch-log auto-resolution scenarios. No structural change to the harness contract; add a note that the harness covers larch-log-only, consecutive, mixed, trivial-with-continue-failure, and resolve-failure paths.

### UPDATED: docs/linting.md

Update the `make test-rebase-checkpoint-probe` row to mention larch-log conflict auto-resolution coverage. Existing target name and shard reference unchanged.

## Edge cases

- **Empty conflict list**: no change from today; existing conflict path fires.
- **Mixed conflict set**: trivial paths staged, non-trivial paths surfaced as `CONFLICT_FILES`, no internal `--continue` attempt.
- **Consecutive larch-log conflicts (multi-hop)**: loop resolves all hops; orchestrator sees `ROUTE=continue` after the final successful continue.
- **Upstream deleted the larch-log file**: `git checkout --ours` fails for deleted-upstream paths; `git rm -f` stages the deletion.
- **Resolve command failure mid-batch**: stop the batch; re-derive `CONFLICT_FILES` from `git diff --name-only --diff-filter=U` (not stale pre-resolve list); exit 1 with accurate current conflict state.
- **Continue rc 3**: existing failure-handling path fires.
- **Loop cap (50 iterations)**: emits `larch_err` warning; falls through to exit 1 with the current `CONFLICT_FILES`.

## Failure modes

1. **Wrong `--ours` assumption**: during rebase, `--ours` is the upstream/base side (not the feature branch). A comment in the code documents this. If the assumption were wrong, larch-logs would get the wrong version. Risk is low: larch-logs are regenerated by the run and the upstream version is always authoritative.

2. **Loop cap hit**: 50 iterations is far above any realistic multi-hop count. If somehow hit, the fallback surfaces the remaining conflict for manual resolution rather than hanging.

3. **Mixed-conflict false negative**: if `_is_trivial_conflict_file` has a wrong pattern, a file could be misclassified as trivial. Risk is low: the pattern is a simple `larch-logs/*` prefix match.

## Testing strategy

Primary:
- `bash scripts/test-rebase-checkpoint-probe.sh` — covers all new cases directly.
- `make test-rebase-checkpoint-probe` — same harness through the Makefile target.

Secondary:
- `bash scripts/relevant-checks.sh` — lint + full harness suite.

## Acceptance

Plan reviewed by Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements (Codex unavailable). Applied findings: empty-list guard, set +e discipline in loop, re-derive CONFLICT_FILES on partial batch failure.

diff_lines: 145

## Test plan
(no test plan section in plan-file)
