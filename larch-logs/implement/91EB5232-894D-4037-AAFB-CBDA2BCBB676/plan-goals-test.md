## Goal
Implement issue #4011: [IMPLEMENTING] /implement: collapse Bash-fence rehydration preludes via a session launcher script\n\n**Problem.** Every post-Step-0 Bash fence in `skills/implement/SKILL.md` repeats the multi-line `CLAUDE_PLUGIN_ROOT` rehydration prelude (source guard plus, at some sites, the `LARCH_CLAUDE_PLUGIN_ROOT` awk fallback). The repetition bloats the always-loaded skill body and invites copy drift between fences..

## Implementation Plan
## Plan

## Context

- `approach-synthesis.txt` is `NO_SKETCHES_CLASSIFIED_SIMPLE`.
- Draft from direct code and doc inspection. Do not claim sketch agreement.
- Binding scope comes from the approved outline and accepted reviewer findings.
- Keep pre-bootstrap fences unchanged:
  - structured-invocation pin
  - both Preflight `plan-block read` fences
  - Step 0 initial bootstrap
  - dirty-tree recovery resume

## Approach

Add a Step 0 emitted launcher, then make post-Step-0 prompt fences call it.

The launcher owns only rehydration and dispatch:

1. Set `IMPLEMENT_TMPDIR` from the environment, or from the launcher directory if unset.
2. Source `$IMPLEMENT_TMPDIR/plugin-root.env` when `CLAUDE_PLUGIN_ROOT` is unset.
3. Fall back to the existing `LARCH_CLAUDE_PLUGIN_ROOT=` awk extract from `$IMPLEMENT_TMPDIR/session-env.sh`.
4. Export `IMPLEMENT_TMPDIR` and `CLAUDE_PLUGIN_ROOT`.
5. Validate that one repo-relative `.sh` or `.py` script path was passed.
6. Reject absolute paths and paths containing `..`.
7. Dispatch `.sh` targets by direct exec.
8. Dispatch `.py` targets with `python3`, not bare exec.
9. Preserve all remaining argv exactly.

Keep it Bash 3.2 portable. Do not use associative arrays, namerefs, or Bash 4 features.

## Files to modify/create

### UPDATED: scripts/implement-bootstrap.sh

Add `emit_larch_run_sh()` near the existing Step 0 artifact helpers.

Implementation details:

- Write `$IMPLEMENT_TMPDIR/larch-run.sh` through a temp file in the same directory.
- `chmod +x` the temp file before `mv -f` into place.
- Return non-zero on write, chmod, or rename failure.
- Use `larch_err` for diagnostics, not raw stderr writes.
- Do not read or rewrite `session-env.sh` beyond the existing sanctioned paths.
- Do not change `plugin-root.env` write semantics.

Call sites:

- Fresh Step 0 path: call after `python3 "$PY_CLI" session write-env ...` succeeds and before post-Step-0 callers can run.
- `--resume-plan-tail` path: keep the legacy `plugin-root.env` sync block unchanged.
- `--resume-plan-tail` path: call `emit_larch_run_sh` unconditionally after that sync block, even when `plugin-root.env` already existed.
- Fail fast with `STEP_FAILED=larch-run` and exit 2 if the launcher cannot be emitted.

Launcher content requirements:

- Source `plugin-root.env` only when `CLAUDE_PLUGIN_ROOT` is empty.
- Use the same one-line awk fallback currently embedded in eligible pre-bootstrap fences.
- Print a short error and exit 2 when `CLAUDE_PLUGIN_ROOT` remains empty.
- Print a short error and exit 2 when no script path is passed.
- Reject absolute script paths and paths containing `..`.
- Accept only `.sh` and `.py` targets.
- Dispatch `.py` targets with `python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@"`.
- Dispatch `.sh` targets with `exec "$CLAUDE_PLUGIN_ROOT/$script" "$@"`.
- Preserve all remaining argv exactly.

### NEW: $IMPLEMENT_TMPDIR/larch-run.sh

Runtime artifact emitted by `scripts/implement-bootstrap.sh`.

This file is not committed.

Expected generated shape:

```bash
#!/usr/bin/env bash
set -uo pipefail

IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)}"
export IMPLEMENT_TMPDIR

[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT

[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || { printf '%s\n' 'larch-run.sh: CLAUDE_PLUGIN_ROOT could not be resolved' >&2; exit 2; }
[ "$#" -ge 1 ] || { printf '%s\n' 'larch-run.sh: missing relative script path' >&2; exit 2; }

script=$1
shift
case "$script" in
  /*|*..*) printf '%s\n' "larch-run.sh: invalid relative script path: $script" >&2; exit 2 ;;
esac

case "$script" in
  *.py) exec python3 "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;
  *.sh) exec "$CLAUDE_PLUGIN_ROOT/$script" "$@" ;;
  *) printf '%s\n' "larch-run.sh: unsupported script target: $script" >&2; exit 2 ;;
esac
```

### UPDATED: skills/implement/SKILL.md

Update `### Bash block prelude` prose.

New contract:

- Pre-bootstrap fences keep their current shapes.
- The structured-invocation pin, Step 0 initial bootstrap, and dirty-tree recovery resume may keep the current source guard plus awk fallback.
- Both Preflight `plan-block read` fences keep their current guard-only shape.
- Do not add an awk fallback to the Preflight fences.
- Post-Step-0 fences use `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative-script-path> ...`.
- Post-Step-0 fences should not source `plugin-root.env` inline.
- Wrappers still read other session keys internally.
- Post-Step-0 Python CLI fences use the launcher with `python/cli.py`; the launcher runs them via `python3`.

Collapse every post-Step-0 Bash fence body to exactly one physical command line.

Requirements for converted fences:

- The fence body has exactly one nonblank, noncomment physical line.
- That line is the launcher call.
- Do not use backslash continuations.
- Move `# Foreground required`, anti-halt reminders, or similar comments into prose outside the fence.
- Preserve all existing script arguments.

Convert post-Step-0 shell-script calls, for example:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-0-degraded-gate.sh
```

and:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" scripts/rebase-checkpoint-probe.sh 1.r 'plan materialization' --forked-target "${forked_target:-false}"
```

Convert post-Step-0 Python CLI calls, for example:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py run-log append --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --batch execution-issues --record-file "$IMPLEMENT_TMPDIR/execution-issue-record.ndjson"
```

Preserve these old-shape fences unchanged:

- structured-invocation pin for `scripts/extract-closes-issue-from-pr.sh`
- both Preflight `python/cli.py plan-block read` examples
- Step 0 initial bootstrap
- dirty-tree recovery resume

For long-running fences:

- Keep `run_in_background: true` metadata unchanged.
- Keep timeout values unchanged.
- Replace only the Bash fence body with the one-line launcher call.
- Keep `<task-notification>` wait prose unchanged.

### UPDATED: scripts/test-implement-fence-shape.sh

Update the structural parser to accept two intentional shapes.

Old pre-bootstrap shape:

- canonical guard
- optional awk fallback only for eligible old-shape fences
- one `${CLAUDE_PLUGIN_ROOT}/...` or `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ...` command

Preflight old-shape exception:

- Both `plan-block read` fences are guard-only today.
- The harness must not require an awk fallback for them.
- The harness must not encourage adding an awk fallback there.

New post-Step-0 shape:

- exactly one nonblank, noncomment physical line
- no trailing backslash
- exactly one `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative-script> ...` command
- no required guard

Pin the boundary by target, not category count.

Allow old shape only for these five fences:

- structured invocation pin: `scripts/extract-closes-issue-from-pr.sh`
- Preflight default `python/cli.py plan-block read`
- Preflight forked `python/cli.py plan-block read`
- Step 0 initial bootstrap: `step-0-bootstrap.sh --mode initial`
- dirty-tree recovery resume: `step-0-bootstrap.sh --mode resume`

Require new shape for all other Bash fences.

Keep existing checks:

- one logical command per fence
- no inline shell control logic
- no telemetry-only fences
- no inline `session read-key`
- no adjacent blank-only fence separation

Add checks for the new shape:

- Launcher path must be exactly `"$IMPLEMENT_TMPDIR/larch-run.sh"`.
- First launcher argument must be a relative `.sh` or `.py` path.
- Reject absolute paths and `..`.
- Reject comments or extra nonblank lines inside new-shape fences.
- Reject line continuations in new-shape fences.
- If any `.py` target appears, assert the emitted launcher template dispatches `.py` through `python3`, not bare `exec`.
- Count and report old-shape vs new-shape fences in the PASS line.
- Pin the expected converted count as `old=5 new=32` unless the actual fence count changes for a task-scoped reason.

### UPDATED: scripts/test-implement-structure.sh

Retarget structure anchors affected by the fence conversion.

Changes:

- Keep old-shape anchors for the five pre-bootstrap fences only.
- Treat both Preflight `plan-block read` fences as guard-only old-shape anchors.
- Require post-Step-0 wrapper call sites to appear as `bash "$IMPLEMENT_TMPDIR/larch-run.sh" <relative-script>`.
- Retarget Step 5 review, Step 7a, and Step 8 immediate-background anchors to the launcher form.
- Relax the Step 5 ready-to-commit background regex to match the one-line launcher call.
- Preserve existing timeout assertions.
- Preserve existing `<task-notification>` assertions.
- Preserve existing wrapper sibling and executable checks.
- Preserve existing anti-halt and site-count assertions.
- Do not use raw line-number pinning.
- Classify anchors by section or target script path.

### UPDATED: scripts/test-implement-structure.md

Document the updated structural invariant:

- Five pre-bootstrap call sites retain the old plugin-root guard shape.
- The two Preflight `plan-block read` fences remain guard-only.
- Post-Step-0 call sites use `larch-run.sh`.
- Background wrapper assertions match the launcher form.
- Timeout and `<task-notification>` checks remain load-bearing.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh

Update the relevant-checks anti-halt matcher.

Changes:

- Detect post-Step-0 relevant-checks sites through the launcher form:
  - `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/run-step-checks.sh ...`
  - any still-valid launcher form for `scripts/run-relevant-checks-captured.sh`
- Stop requiring `${CLAUDE_PLUGIN_ROOT}` in the invocation-line regex.
- Keep `EXPECTED_SITES=4` unless the SKILL conversion changes the actual number of load-bearing sites.
- Keep the five-line canonical opener window.
- Keep `REDACTED_LOG_FILE` and `NOT raw LOG_FILE` checks.
- Keep the legacy Skill-tool prose rejection.

### UPDATED: skills/implement/scripts/test-implement-relevant-checks-anti-halt.md

Update the contract text:

- The harness scans launcher-based post-Step-0 relevant-checks wrapper invocations.
- It still requires exactly four load-bearing sites.
- It still requires the local anti-halt blockquote and redacted-log guidance near each site.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

Update the Step 5 delegation literal if the SKILL prose changes with the fence shape.

New accepted literal should pin the launcher-based delegation, for example:

- `Step 5 invokes `bash "$IMPLEMENT_TMPDIR/larch-run.sh" scripts/run-step5-review.sh``

Keep the AGENTS.md anti-polling assertions unchanged.

### UPDATED: scripts/test-implement-anti-polling-rule.md

Update the Step 5 invariant to describe launcher-based delegation to `scripts/run-step5-review.sh`.

### UPDATED: scripts/implement-bootstrap.md

Document the launcher artifact.

Add to Outputs or Behavior mapping:

- Step 0 writes executable `$IMPLEMENT_TMPDIR/larch-run.sh`.
- Fresh sessions get it after `session write-env`.
- `--resume-plan-tail` emits it for legacy tmpdirs.
- `--resume-plan-tail` emits it unconditionally after any `plugin-root.env` sync work, including when `plugin-root.env` already exists.
- It sources `plugin-root.env`, falls back to `session-env.sh`, exports `IMPLEMENT_TMPDIR` and `CLAUDE_PLUGIN_ROOT`, then dispatches a repo-relative script.
- It runs `.py` targets through `python3`.
- It direct-execs `.sh` targets.

Update the resume-tail section:

- Legacy session-env-only tmpdirs now gain both `plugin-root.env` and `larch-run.sh`.
- Tmpdirs that already have `plugin-root.env` but lack `larch-run.sh` gain the launcher.
- Re-running resume-tail rewrites the launcher idempotently.
- `plugin-root.env` semantics stay unchanged.

### UPDATED: scripts/test-implement-fence-shape.md

Update invariants:

- Five pre-bootstrap fences use the old guard shape.
- Both Preflight `plan-block read` fences remain guard-only.
- Post-Step-0 fences use `bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...`.
- Post-Step-0 fence bodies have exactly one nonblank, noncomment physical line.
- Post-Step-0 fence bodies do not use backslash continuations.
- The harness accepts both shapes only at their intended boundary.
- The harness rejects post-Step-0 regressions to inline rehydration.
- Python launcher targets are valid only because `larch-run.sh` dispatches `.py` through `python3`.
- PASS output reports `old=5 new=32` unless the actual converted fence count changes intentionally.

### UPDATED: skills/implement/scripts/test-implement-bootstrap.sh

Add focused assertions for the new runtime artifact.

Required cases:

- Fresh infra path creates `$IMPLEMENT_TMPDIR/larch-run.sh`.
- The file is executable.
- The file contains the `plugin-root.env` source path.
- The file contains the `LARCH_CLAUDE_PLUGIN_ROOT=` awk fallback.
- The file contains a `.py` dispatch branch that execs `python3`.
- The file contains a `.sh` dispatch branch that direct-execs the target.
- The file rejects absolute targets.
- The file rejects parent-traversal targets.
- `--resume-plan-tail` creates `larch-run.sh` for a legacy tmpdir that already has `session-env.sh` but lacks `plugin-root.env`.
- `--resume-plan-tail` creates `larch-run.sh` for a tmpdir that already has both `session-env.sh` and `plugin-root.env` but lacks `larch-run.sh`.
- Re-running `--resume-plan-tail` leaves the launcher source stable.

Avoid executing a real repo script through the launcher unless the sandbox already has a safe stub script.

If adding execution assertions:

- Use a sandbox script under the fake plugin root.
- Add a safe stub `.py` target with no shebang and no executable bit.
- Assert the `.py` target succeeds through `python3`.
- Assert argv passthrough for both `.sh` and `.py`.

### UPDATED: skills/implement/scripts/test-implement-bootstrap.md

Add the new bootstrap harness coverage row:

- fresh Step 0 emits executable `larch-run.sh`
- launcher dispatches `.py` through `python3`
- launcher direct-execs `.sh`
- launcher rejects bad relative targets
- resume-tail legacy tmpdir emits `larch-run.sh`
- resume-tail emits `larch-run.sh` even when `plugin-root.env` already exists
- repeat resume-tail is idempotent

### UPDATED: docs/linting.md

Update the `make test-implement-fence-shape` row so it no longer says every fence must be a canonical plugin-root guard plus one repo script invocation.

New wording should state:

- five pre-bootstrap fences keep the canonical guard shape
- the two Preflight `plan-block read` fences remain guard-only
- post-Step-0 fences use `$IMPLEMENT_TMPDIR/larch-run.sh`
- post-Step-0 fences are exactly one nonblank, noncomment physical line
- the harness enforces the boundary
- `.py` launcher targets are dispatched with `python3`

Update rows for related harnesses if they mention old invocation literals:

- `make test-implement-structure`
- `make test-implement-relevant-checks-anti-halt`
- `make test-implement-anti-polling-rule`

## Edge cases

- **Python targets:** `python/cli.py` has no shebang and may not be executable. The launcher must run `.py` targets with `python3`.
- **Legacy resume tmpdir:** `session-env.sh` may exist without `plugin-root.env`. `--resume-plan-tail` must create both `plugin-root.env` and `larch-run.sh`.
- **Partial upgraded tmpdir:** `session-env.sh` and `plugin-root.env` may exist while `larch-run.sh` is missing. `--resume-plan-tail` must still create the launcher.
- **Fresh Step 0 write failure:** fail before Step 1.r. Later one-line fences depend on the launcher.
- **Unset `IMPLEMENT_TMPDIR`:** launcher derives it from its own directory, then exports it.
- **Unset `CLAUDE_PLUGIN_ROOT`:** launcher uses `plugin-root.env`, then awk fallback.
- **Bad launcher target:** reject empty, absolute, parent-traversal, and non-`.sh` / non-`.py` paths.
- **Preflight:** do not convert Preflight examples. `$IMPLEMENT_TMPDIR` may not exist yet.
- **Preflight awk fallback:** do not add it. The two plan-block read fences remain guard-only.
- **Dirty-tree recovery:** keep the old shape because it must recover on legacy tmpdirs before relying on post-Step-0 conventions.
- **Fence comments:** post-Step-0 fence comments belong in prose outside the fence, not inside the Bash block.

## Failure modes

- **Launcher missing:** post-Step-0 fences fail immediately. Bootstrap should catch this earlier with `STEP_FAILED=larch-run`.
- **Launcher missing on resume:** converted fences fail on upgraded tmpdirs. Avoid this by emitting the launcher unconditionally at the end of resume-tail.
- **Launcher not executable:** direct execution would fail, but fences call `bash "$IMPLEMENT_TMPDIR/larch-run.sh"`. Still set executable because acceptance requires it and it helps manual debugging.
- **Malformed `plugin-root.env`:** the launcher falls back only if `CLAUDE_PLUGIN_ROOT` remains empty. Preserve existing source behavior.
- **Bad `LARCH_CLAUDE_PLUGIN_ROOT`:** launcher may resolve a bad root and exec will fail. This matches the current awk fallback risk.
- **Missing `python3`:** `.py` targets fail like the prior explicit `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py"` fences would fail.
- **Harness false positives:** avoid line-number pinning where possible. Classify pre-bootstrap by command target or surrounding section, not raw line numbers.
- **Physical-line drift:** reject new-shape fences with comments, extra lines, or continuations even if they are one logical command.

## Invariants

- No behavior change to wrapped scripts.
- No change to `session-env.sh` or `plugin-root.env` writer semantics.
- No raw prompt-side writes to `session-env.sh`.
- No Bash 4 features.
- One post-Step-0 Bash fence equals one physical launcher command line.
- Post-Step-0 prompt code no longer repeats plugin-root rehydration.
- `.py` targets are never bare-execed by the launcher.
- Background metadata and notification waits stay unchanged.
- Exactly five old-shape fences remain unless the SKILL structure changes for a task-scoped reason.
- Both Preflight `plan-block read` fences remain guard-only.

## Downstream consumers

- `make test-implement-fence-shape` must reflect the new fence contract.
- `make test-implement-structure` must reflect launcher-based post-Step-0 anchors.
- `make test-implement-relevant-checks-anti-halt` must still prove the relevant-checks continuation callouts.
- `make test-implement-anti-polling-rule` must still prove Step 5 delegates to `run-step5-review.sh`.
- `make test-implement-bootstrap` must prove fresh and resume-tail launcher emission, including the `plugin-root.env`-already-present case.
- `make test-implement-timing-rehydration` should still pass because eligible pre-bootstrap awk fallbacks remain and wrappers still self-rehydrate timing keys.
- `scripts/implement-bootstrap.md` remains the Step 0 behavior contract.
- `docs/linting.md` remains accurate for the harnesses.

## Testing strategy

Run focused tests first:

```bash
make test-implement-fence-shape
make test-implement-structure
make test-implement-relevant-checks-anti-halt
make test-implement-anti-polling-rule
make test-implement-bootstrap
make test-implement-timing-rehydration
```

Then run broader validation:

```bash
bash scripts/relevant-checks.sh
```

If time allows, also run:

```bash
make lint
```


## Acceptance

- `make test-implement-fence-shape` passes with all post-Step-0 fences in the new one-line launcher form and the five pre-bootstrap fences in the old guard form (`old=5 new=32`).
- `make test-implement-bootstrap` passes with assertions for fresh and resume-tail `larch-run.sh` emission.
- `make test-implement-structure` passes with retargeted post-Step-0 anchors.
- `make test-implement-timing-rehydration` still passes (pre-bootstrap awk fallbacks remain).
- `bash scripts/relevant-checks.sh` clean.
- Bash 3.2 portable: no Bash 4+ constructs in `larch-run.sh` or `implement-bootstrap.sh`.
- No behavior change to any wrapped script.

diff_lines: 485

## Test plan
(no test plan section in plan-file)
