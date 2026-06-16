## Goal
Implement issue #4489: [IMPLEMENTING] [BUG] /design Step 3: .completed/step-3 absent after ELIGIBLE=0 zero-reviewer round; recovery-waiter pattern unmatchable, bails to main agent.

## Implementation Plan
## Summary

A zero-reviewer / `small-clean` `/design` Step 3 round can leave the anti-poll guard (`hook-bg-poll-guard.sh`) live because `$DESIGN_TMPDIR/.completed/step-3` is **not guaranteed on every terminal exit**, and the sanctioned recovery waiter the orchestrator would use to wait for that sentinel is **unmatchable** by the hook. Net effect: after the background Step 3 process finishes, the orchestrator stays blocked and falls back to a resume fence.

> **Verification note (rewritten after tracing live code @ `main` `ddb451592`).** The original framing — "the loop never writes `.completed/step-3` on the complete exit path" — is **inaccurate**: the terminal `complete` path already writes it (`review-design-step3-loop.sh:827`, `step3_loop_write_completed_step3`, before emitting `complete` at `:828`). The corrected root cause and fix are below. Originally gated on #4490 ("land that first"); operator dropped that dependency on 2026-06-15 to land #4489 independently while #4490 was in-flight. (#4487 was the misdiagnosed sibling, now closed stale.)

## Observed symptoms (forensic evidence — `/design 4464`, design log run `1F0A8524-694B-49BD-AE93-6A88DC200411`, PR #4483)

- One round ran with `ELIGIBLE=0` (zero reviewers dispatched), exited rc=0 with `LOOP_STATUS=complete`, `ACCEPTED_COUNT=0`, `PLAN_REVIEW_CONTINUE_REASON=small-clean`.
- `.step3-round-1.phase` = `awaiting-continuation`; `.completed/step-3` **absent** after the first SUCCESS notification, present only after a resume fence ran.
- `hook-bg-poll-guard.sh` kept blocking Read/Bash calls targeting the session dir because the sentinel was absent.
- The sanctioned recovery waiter (`until [ -f "$DESIGN_TMPDIR/.completed/step-3" ]; do sleep N; done`) was rejected by the hook.
- `review-round-count.txt` = 1, `ballot.txt` empty, no voter outputs (distinct fingerprint from #4487).

## Root cause (verified against `main` @ `ddb451592`)

**1. The sentinel is not guaranteed on every terminal exit (corrected).**
- The normal terminal `complete` path **does** write it: `review-design-step3-loop.sh:827` → `step3_loop_write_completed_step3`, before the `complete` envelope at `:828`.
- Paths that exit terminally **without** writing it: the continuation-failed branch (`review-design-step3-loop.sh:813-817`) emits `postplan-failed` and `exit 0` without the sentinel.
- The exact observed state (`rc=0, LOOP_STATUS=complete, phase=awaiting-continuation, sentinel absent`) is **not reproducible from any current `complete`-path** — it indicates the loop process was abandoned mid-continuation (after the hook blocked the orchestrator) or the run predates `:827`. Either way, there is no belt-and-suspenders guarantee that the sentinel exists once the outer entrypoint process exits.

**2. The guard cannot release early without the sentinel (narrow window).**
- `marker_step_completed` releases only when the sentinel exists (`hook-bg-poll-guard.sh:104`, `:83` maps `design-step3-review` → `$dir/.completed/step-3`).
- The dead-process fallback removes the marker only after `kill -0` observes the process dead on a **later** hook invocation (`:113`), leaving a window between the SUCCESS notification and that cleanup.

**3. The sanctioned recovery waiter is unmatchable (verified correct).**
- `bash_is_step3_recovery_waiter` (`hook-bg-poll-guard.sh:252`) anchors `^until` **and** requires the literal token `$DESIGN_TMPDIR` / `${DESIGN_TMPDIR}`. Normalization (`:243-244`) only collapses whitespace; it does not rewrite a resolved absolute path back to the token.
- Bash tool calls do not persist `$DESIGN_TMPDIR`, so the orchestrator must either prepend `DESIGN_TMPDIR=<abs>;` (breaks the `^until` anchor) or inline the resolved absolute path (fails the literal-token match). No compatible invocation exists.

## Fix

**Primary (on-disk; no asset re-embed) — guarantee the sentinel on terminal completion.**
In `design-step3-review.sh` (the immediate-background entrypoint; on-disk, **not** a gzipped `_LEGACY_ASSETS` copy), ensure `$DESIGN_TMPDIR/.completed/step-3` and `.completed/step-3.5` exist (mirroring `step3_loop_write_completed_step3`) whenever the inner `plan-review run` reaches a terminal `STEP3_REVIEW_LOOP_STATUS` — via an `EXIT` trap or a post-run check. This closes the window for every terminal path (including `postplan-failed` and the abandoned-mid-continuation case) regardless of which internal branch exited, and avoids editing the gzipped loop asset.

**Secondary (verified) — make the recovery waiter matchable.**
Relax `bash_is_step3_recovery_waiter` (`scripts/hook-bg-poll-guard.sh:252`) to accept an optional leading variable assignment, keeping the rest of the anchored shape intact:
```
^(DESIGN_TMPDIR=[^;]+;[[:space:]]*)?until[[:space:]]+\[[[:space:]]+-f[[:space:]]+"?(\$DESIGN_TMPDIR/\.completed/step-3|\$\{DESIGN_TMPDIR\}/\.completed/step-3)"?[[:space:]]+\];[[:space:]]+do[[:space:]]+sleep[[:space:]]+[0-9]+[[:space:]]*;[[:space:]]+done$
```
Preserve the existing guards (`.step3-review-result.env`, `&&`, `||`, probe-verb rejections at `:246-249`).

**Optional (only if a targeted in-loop write is preferred over the trap).**
Also write the sentinel on the continuation-failed exit (`review-design-step3-loop.sh:~816`). This requires **re-embedding** `_LEGACY_ASSETS["skills/design/scripts/review-design-step3-loop.sh"]` in `python/plan_review.py` in the same change — that file is in `_RETIRE_DESIGN_SKIPS`, so the executed copy is the gzipped asset, not the on-disk file. The Primary EXIT-trap already covers this path, so this is belt-and-suspenders.

## Acceptance criteria

- After any terminal Step 3 outcome (`complete`, `postplan-failed`, zero-reviewer/`small-clean`), `$DESIGN_TMPDIR/.completed/step-3` exists once the entrypoint process exits, so the bg-poll-guard releases on the first notification without a resume fence.
- The sanctioned recovery waiter prefixed with `DESIGN_TMPDIR=<abs>;` is accepted by `bash_is_step3_recovery_waiter`; the bare-`until` form still matches; compound-command (`&&`/`||`) and probe-verb rejections are unchanged.
- Regression tests: (a) the recovery-waiter matcher accepts the prefixed form and still rejects compound/probe variants; (b) the terminal-guarantee writes the sentinel on a simulated terminal exit where the inner loop did not.
- If the gzipped loop asset is edited (Optional fix), the re-embed is applied in the same change and the re-embed lint/test passes.

## Notes

- The `small-clean` continuation decision itself is normal behavior; the defect is the missing sentinel guarantee plus the unmatchable recovery waiter, not the continuation decision.
- Verified file:line anchors are against `main` @ `ddb451592` and may drift; re-confirm before editing.

## Test plan
(no test plan section in plan-file)
