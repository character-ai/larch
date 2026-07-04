## Goal
Implement issue #6237: [IMPLEMENTING] [BUG] Survive external harness stops of /design Step 3 review loops: signal-aware….

## Implementation Plan
## Summary

Two live `/design` sessions (larch7 on #6160, larch8 on #6159) lost their Step 3 review-loop background tasks to external stops on 2026-07-03 evening. Both sessions run plugin v52.4.3, which contains the #6213 fix; that fix is present and working, and its new kill logging is what made attribution possible. Forensics attribute the stops to the Claude Code harness itself (v2.1.201): it killed the task process trees of idle sessions, twice, synchronized across two independent CLI processes. larch owns the amplification: the Step 3 wrapper's EXIT trap reacts to the external SIGTERM by killing the still-live detached review loop and sweeping in-flight detached Codex/Cursor reviewer dispatches. Each transient harness stop therefore destroys minutes of vendor work, burns a review round, and looks like the #6213 "another session killed my process" class.

## Original report

Operator report (2026-07-03, condensed): "Despite having just merged the fix for the 'another parallel session's (in a different clone) job kills my process' vicious bugs, 2 sessions currently running (larch7 and larch8, both /design) have just experienced this same symptom. Please confirm their version of larch has the fix, and that therefore the fix is not working, figure out the proper fix."

Session transcripts show:

- larch7 (`/larch:design -s 6160`): `Background command "Resume Step 3 review loop after Gate B apply (continuation phase)" was stopped`, then a retry also stopped about 7 minutes later. `finalize-kill.log.jsonl` showed a `session kill-background-processes` sweep with `reason: "tmpdir-scoped-background-cleanup"` killing Round-2 Codex reviewer dispatches mid-flight. A third retry, launched after the operator returned, completed normally.
- larch8 (`/larch:design -s 6159`): `Background command "Resume Step 3 review loop after Gate B apply (background)" was stopped`; the resumed loop received an explicit SIGTERM with no terminal sentinel written.

## Reproduction scenario

The harness-side trigger is not reproducible on demand: it fired only while the operator was away and both sessions were idle, and it stopped recurring once the operator interacted again. The larch-owned amplification is deterministic:

1. Start a `/design` run to Step 3 and let `design-step3-review.sh` reach `wait "$_loop_pid"` with the `plan-review run` loop live in its own process group and at least one detached `agent launch-review` dispatch in flight.
2. Send SIGTERM to the wrapper bash process only (simulating a harness task stop).
3. Observe: the EXIT trap tears down the live loop group (SIGTERM, 2 s, SIGKILL, logged as `step3-trap-cleanup`), then `_step3_review_kill_tmpdir_processes` sweeps and kills every process whose argv contains the session tmpdir, including the detached reviewer dispatches (logged as `tmpdir-scoped-background-cleanup`).
4. The next `--phase awaiting-continuation` entry re-dispatches the round from scratch.

## Expected behavior

An external stop of the harness task shell should not destroy the detached, file-backed review loop or its in-flight vendor dispatches. The loop should finish its round on its own; the next continuation entry should reattach to it (or to its persisted results) and no review round should be burned. Full teardown should remain reserved for normal end-of-pass exits and explicit abort paths.

## Observed behavior

- larch8's loop group 44554 was killed at 20:55:06 PDT; larch7's loop group 52010 at 20:55:07, 0.5 s later; larch7's relaunched loop group 67604 at 21:01:59.
- Each stop killed the wrapper, the loop, and then (via the trap sweep) the detached reviewer dispatches: larch7 codex pids 52045/52049/52051 and cursor 67675; larch8 cursor voter 57981.
- Rounds were re-dispatched from scratch on retry, spending vendor time and tokens and consuming round-cap headroom.
- The operator saw repeated unexplained "was stopped" failures and paused both runs to investigate.

## Root cause analysis

Two layers.

**Layer 1, the stopper (external to larch, high confidence on attribution, exact trigger unknown).** Claude Code v2.1.201 initiated the task stops. Evidence: the harness enqueued `<task-notification><status>killed</status>` at 03:55:06.296Z (larch8) and 03:55:06.798Z (larch7), 0.5 s apart in two unrelated CLI processes, and again at 04:01:59.008Z; each enqueue precedes the victim-side trap's first kill-log write by 170 to 240 ms, and the wrapper stayed alive about 2.5 s past enqueue running its trap, so the harness's own direct child was already gone at enqueue time. No TaskStop tool calls exist in either transcript. Both sessions were idle with the operator away; kills ceased once the operator interacted from about 21:14. The internal harness trigger (idle housekeeping, away-summary machinery, or similar) cannot be determined from disk artifacts; CLI versions 2.1.199 to 2.1.201 were installed over the prior two days, matching the operator's "only started the last 2 to 3 days".

**Layer 2, the amplifier (larch-owned).** `skills/design/scripts/design-step3-review.sh` installs `_step3_review_cleanup` as an EXIT trap. Bash runs the EXIT trap on an untrapped fatal SIGTERM. Because `_loop_pid` is still set while the wrapper waits, the trap kills the healthy detached loop group and then runs the tmpdir process sweep, killing detached reviewer dispatches the harness tree-signal missed. The wrapper cannot currently distinguish "harness stopped me" from "I finished a pass".

**Eliminated with evidence:** the #6213 `kill-active-leg` path (no `.active-leg-pgid` files, no `active-leg-kill.log.jsonl` anywhere); larch SessionStart hooks (no kill calls; hook firings every 20 to 60 s all evening with both kills inside firing gaps, 20:54:51 to 20:56:49 and 20:59:12 to 21:02:47); rogue `pkill` from another session (transcript sweep found none); system sleep (pmset shows the machine awake since 09:34); a fixed background-task timeout (task ages at kill were 129.7 s, 192.7 s, 287.5 s); stale pre-52.4.3 processes (none live).

## Evidence

- Victim kill logs: `~<TMPDIR>/design-step3-kill.log.jsonl` (trap SIGTERM loop pgid 52010 at ts 1783137307.037, SIGKILL 1783137309.056; pgid 67604 at 1783137719.19/1783137721.22) and `finalize-kill.log.jsonl` (sweep kills of codex/cursor dispatch pids at 1783137309.26 and 1783137721.49). Same pair under `claude-design-larch8-82g7nlug` (pgid 44554; cursor voter 57981 at 1783137308.75).
- Killed process argv embeds `plugins/cache/larch-local/larch/52.4.3/`, proving both sessions run v52.4.3; `git merge-base --is-ancestor 5eb733233 HEAD` in the marketplace checkout confirms the #6213 fix is included in that release.
- Session transcripts (larch7 `b3195881-...jsonl`, larch8 `fb90316c-...jsonl` under `~/.claude/projects/`): `queue-operation` entries with `<status>killed</status>` at 03:55:06.296Z, 03:55:06.798Z, 04:01:59.008Z; task launch timestamps giving kill ages 287.5 s, 129.7 s, 192.7 s; no TaskStop calls.
- Task output sidecars (391 bytes each) captured bash's job message `line 351: 52010 Terminated: 15` for the loop, showing the wrapper was alive and reaping when the loop died.
- `$TMPDIR/larch-cleanup-sessionstart-*.log` mtime series places larch SessionStart hook activity outside both kill instants.
- `pmset -g log`: no sleep entries after 09:34 on 2026-07-03.

## Affected files

- `skills/design/scripts/design-step3-review.sh`: the EXIT trap (`_step3_review_cleanup`), `_step3_review_kill_tmpdir_processes`, and the launch/wait block are the amplifier and the primary fix site.
- `skills/design/scripts/design-step3-review.md`: sibling contract doc; must describe the new signal-aware behavior.
- `skills/design/scripts/test-design-step3-review.sh`: asserts the kill helper argv today; needs same-PR assertions for the detach path per `.claude/rules/launcher-argv-test-coverage.md`.
- `python/larch/core/process_identity.py`: loop identity records and validation; the reattach path builds on `read_identity_record` / `validate_process_identity`.
- `python/larch/state/finalize.py`: `kill_session_background_processes` is the sweep the trap invokes; unchanged behavior but its call sites change.
- `skills/implement/scripts/step-5-review.sh`, `skills/implement/scripts/step-8-ship.sh`: same exposure class (EXIT traps under harness-stoppable background tasks); assess for the same treatment, though they lack the tmpdir sweep amplifier.
- `docs/` (likely `docs/workflow-lifecycle.md` or a new note): document the harness away-idle stop behavior and the recovery contract.

## Suggested fix(es)

1. **Signal-aware trap with detach-and-reattach (recommended).** Trap TERM/HUP/INT in `design-step3-review.sh` to set an `_external_signal` flag before the EXIT trap runs. In `_step3_review_cleanup`, when the flag is set and `_loop_pid` is live: skip `teardown-loop-identity`, skip `_step3_review_kill_tmpdir_processes`, write a `.step3-wrapper-detached` marker next to the existing `.step3-loop-identity.json`, guarantee sentinels as today, and exit fast. The setsid loop is file-backed and completes the round unattended. Teach the `--phase awaiting-continuation` entry to reattach when the marker plus a validated live loop identity exist: wait for the loop's persisted result sidecars instead of dispatching a fresh round; fall back to today's fresh dispatch when identity validation fails or the loop is gone. Keep full teardown for normal end-of-pass exits (the existing post-`wait` sweep) and for explicit abort paths.
2. **Alternative, smaller but lossier.** Keep teardown on external signal, but persist round state so the killed round is not burned against the round cap and re-dispatch is idempotent.
3. **Documentation.** Record the harness away-idle stop behavior, the forensic signature (`<status>killed</status>` notification with no TaskStop, victim-side `step3-trap-cleanup` entries), and the recovery contract, so future incidents are triaged against the harness first.
4. **Upstream.** Recommend the operator file a Claude Code issue for the v2.1.19x/2.1.20x behavior (spontaneous synchronized background-task kills in idle sessions); larch cannot fix the harness side but must stay robust to it.

## Open questions

- Operator aborts: a TaskStop-initiated SIGTERM is indistinguishable from the harness's spontaneous stop at signal level. Is "detach and let the loop finish" acceptable for deliberate aborts, given the explicit abort path (`design-step0-abort-cleanup`) still tears everything down? If not, the trap needs an abort marker protocol.
- Should the reattach path block waiting for the detached loop, or return an `awaiting-continuation` status immediately and rely on the existing sentinel probe protocol?
- Do `/implement` Step 5 and Step 8 wrappers need the same signal-aware trap in this issue, or a follow-up? Their kill paths are identity-validated already, but a harness stop still kills their drivers mid-run (the #6213 larch6 incident matches this signature).
- Should the detached loop self-terminate if no wrapper reattaches within a bound (orphan cap), to avoid unattended vendor spend after a genuine session death?

## Test plan
(no test plan section in plan-file)
