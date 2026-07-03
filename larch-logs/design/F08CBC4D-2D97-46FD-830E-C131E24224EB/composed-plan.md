## Plan

## Approach

Implement the approved narrow fix.

- Scope Bash `tasks/*.output*` detection in `scripts/hook-bg-poll-guard.sh` to the same clone-correlation gate already used by the Read path.
- Add a Step 3/5 `/implement` foreground probe carve-out for:
  - `test -f "$IMPLEMENT_TMPDIR/.completed/step-3-terminal"`
  - `test -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal"`
  - braced forms and optional `IMPLEMENT_TMPDIR=<abs>;` prefix.
- Keep it narrow:
  - no `&&`, `||`, sleeps, loops, appended reads, task-output probes, or mutation commands.
  - bind probes only to matching live marker steps: `implement-step3-checks` and `implement-step5-review`.
  - reuse the existing per-sentinel clamp machinery.
- Update prose so a denied task-output read immediately after a genuine Step 3/5 completion notification has a bounded recovery path:
  - run one foreground terminal-sentinel probe for that same step.
  - if present, retry the just-denied output read once.
  - if absent after a genuine completion notification, do not wait for another notification. Treat it as a tool/hook inconsistency and route through the step's existing failure/stall handling.
- Do not add a defensive re-stat or sleep retry inside `marker_step_completed()`.

## Files to modify/create

### UPDATED: scripts/hook-bg-poll-guard.sh

- Update `bash_has_probe_target()` so the `*tasks/*.output*` Bash match requires `bash_probe_target_dir_plausible "$dir" "$cwd_canon"`.
- Fix the nearby comment that currently says task-output matches stay unconditional.
- Replace the stale "Race-free" wording above `marker_step_completed()` with conservative wording:
  - sentinel release is the intended fast path after notification.
  - callers must still handle transient mismatch through sanctioned bounded probes.
- Extend probe helpers for `/implement` Step 3/5:
  - make `probe_sentinel_name()` recognize `step-5-terminal`.
  - add an implement-specific live-dir resolver, similar to `probe_target_live_dir_step8`, that binds by `STEP=implement-step3-checks` or `STEP=implement-step5-review`.
  - add a narrow classifier for Step 3/5 implement terminal-sentinel probes.
  - call the existing clamp flow, or a small shared variant, before generic deny checks.
- Add `step-5-terminal` to `bash_attempts_terminal_sentinel_mutation()`'s sentinel-name case arm, alongside the already-covered `step-3-terminal`, so the new Step 5 probe target is protected against `touch`/truncate/redirect forgery the same way Step 3's sentinel already is. Leave other implement sentinels unchanged.
- Keep Step 8 behavior unchanged.
- Keep other implement steps denied for foreground terminal probes.

### UPDATED: scripts/test-hook-bg-poll-guard.sh

Add regression coverage for the hook changes.

- Add a Bash-path cross-clone test:
  - foreign clone live marker plus `cat tasks/foo.output` from this clone allows.
  - same-clone live marker plus `cat tasks/foo.output` still denies.
- Add Step 3 implement probe tests:
  - absent `.completed/step-3-terminal` probe allows up to clamp threshold.
  - repeated absent probe clamps.
  - present sentinel releases marker and clears counter.
  - probe bound to non-Step 3 marker denies.
- Add Step 5 implement probe tests with the same pattern for `.completed/step-5-terminal`.
- Add negative tests:
  - appended `&& cat ...` denies.
  - bracket forms remain denied unless intentionally supported.
  - Step 5 resume, self-review, Step 6, and Step 7a still do not gain a foreground terminal-probe carve-out.
- Add a focused negative test mirroring the existing Step 3 sentinel-forgery coverage: `touch`/truncate against `$IMPLEMENT_TMPDIR/.completed/step-5-terminal` denies while the `implement-step5-review` marker is live.
- Adjust existing assertions that currently state Step 3/5 implement probes must deny.

### UPDATED: scripts/hook-bg-poll-guard.md

- Document the Bash `tasks/*.output*` clone-scoping parity with the Read path.
- Replace the stale race-free completion claim with the weaker sentinel-release contract.
- Document the new `/implement` Step 3/5 foreground probe carve-out and clamp.
- Keep Step 8 documentation distinct because its sentinel lives at the tmpdir root.

### UPDATED: skills/implement/SKILL.md

- Update NEVER #8.
- Replace "Steps 3 and 5 remain notification-only" with the new split:
  - before notification: no progress probes.
  - premature notification while child is still running: still no Step 3/5 polling loop or Monitor fallback.
  - denied read immediately after a genuine completion notification: one foreground non-sleeping same-step sentinel probe is allowed.
- Add exact probe forms for Step 3 and Step 5.
- State the retry rule:
  - present sentinel: retry the just-denied output read once.
  - absent sentinel after genuine completion: do not wait for another notification. Route as the step's existing failure/stall path.
- Keep background recovery waiters forbidden.

### UPDATED: skills/shared/orchestrator-never.md

- Update NEVER #3 and #4 to match the new `/implement` Step 3/5 exception.
- Keep `/design` recovery wording unchanged.
- Keep Step 8 wording unchanged except for noting that Step 3/5 now have their own narrower post-denial recovery path.
- Preserve the ban on result-file sleep loops, Monitor, TaskOutput polling, and background recovery waiters.

### UPDATED: scripts/test-implement-anti-polling-rule.sh

- Update pinned literals for the new Step 3/5 recovery contract.
- Keep pins that still matter:
  - no Monitor.
  - no Bash polling loops.
  - no background recovery waiter.
  - Step 8 rc probe stays separate.
- Add pins for the new exact Step 3/5 probe forms and retry-on-present guidance.

### UPDATED: scripts/test-design-structure.sh

- Update any shared `orchestrator-never.md` literal checks that still assert Step 3/5 are purely notification-only.
- Keep `/design` assertions unchanged.

### MAY_UPDATE: scripts/test-implement-structure.sh

- Only update if its NEVER #8 literal checks become too weak or stale after the prose edit.
- Prefer minimal literal changes.

## Edge cases

- A foreign clone's live marker must not block this clone's task-output read through the Bash path.
- A same-clone live marker must still block real progress probes.
- Empty or uncorrelatable `cwd` should fail open for bare task-output shape, consistent with the current clone-correlation posture.
- Step 3 probe must not satisfy Step 5, and Step 5 probe must not satisfy Step 3.
- Symlink sentinels must still deny.
- Repeated absent probes must clamp.
- Appended reads must deny so the carve-out cannot become general polling.
- The new `step-5-terminal` sentinel must be covered by the mutation-deny path so it cannot be forged while the `implement-step5-review` marker is live, matching Step 3's existing coverage.

## Failure modes

- Over-broad probe matching could reintroduce progress polling.
- Over-narrow probe matching could keep the original stall path.
- Updating prose without updating harness literals could leave stale CI failures.
- Treating absent sentinel after a genuine notification as "wait again" would preserve the indefinite-stall bug.

## Testing strategy

Run focused harnesses only.

- `make test-hook-bg-poll-guard`
- `make test-implement-anti-polling-rule`
- `make test-design-structure`
- `make test-implement-structure` if touched or if NEVER #8 edits affect its pins.
- If shell syntax changes are nontrivial, also run the repo's relevant shellcheck path for the changed shell files.

## Acceptance

Run focused harnesses only.

- `make test-hook-bg-poll-guard`
- `make test-implement-anti-polling-rule`
- `make test-design-structure`
- `make test-implement-structure` if touched or if NEVER #8 edits affect its pins.
- If shell syntax changes are nontrivial, also run the repo's relevant shellcheck path for the changed shell files.

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 190
