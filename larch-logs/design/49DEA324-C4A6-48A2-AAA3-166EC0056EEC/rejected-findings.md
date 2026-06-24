### [Plan Review] FINDING_1

### FINDING_1: Split voter dispatch lacks combined completion wait before probes
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The planned split dispatch mirrors `plan_review_panel.dispatch_voters` (async voter-1 plus a voters 2–3 waterfall) but does not restate the post-waterfall completion contract the reference uses. Today’s unified path waits via `_wait_sentinels` over all three `.done` files; `plan_review_panel` also waits the voter-1 launch handle after the waterfall returns before reading outputs. If split dispatch launches voter-1 concurrently, binds waterfall stdout immediately, and probes `.done`/output before voter-1 (or voters 2–3) finish, it can mark voter-1 failed or trigger parse-rate retry early. This race applies on Cursor-present runs and on Codex-up/Cursor-down runs that Popen Claude voter-1 while launching the two-slot Codex waterfall. The plan must pin an explicit mirror: after the voters 2–3 waterfall returns, wait the voter-1 launch handle when started asynchronously, then call `_wait_sentinels` over every launched judge `.done` (voter-1 plus voters 2–3 resolved winning paths) before `.done`-rc probes, status assignment, and parse-rate retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `### UPDATED: python/agent_voters.py`, require one `_wait_sentinels(review_tmpdir, [v1.done, v2.done, v3.done])` (or the launched subset on Claude-only shrink) after both voter-1 launch and the voters 2-3 waterfall return, on Cursor-present and Codex-up/Cursor-down paths, before `_read_done_exit_code` and parse-rate retry. Add a test that voter-1 `.done` is still pending when the waiter starts.


### [Plan Review] FINDING_2

### FINDING_2: Voters 2–3 waterfall reuses `--no-fallback` helper and blocks required Codex→Cursor fallback
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Routing voters 2–3 through the existing `_dispatch_waterfall` helper silently disables the Codex-primary fallback the plan requires. `_dispatch_waterfall` always appends `--no-fallback` (line 214), but voters 2–3 must launch via `agent dispatch-waterfall` without global `--no-fallback` so Codex-down/Cursor-up runs can fall back to Cursor. Reusing the helper verbatim leaves pragmatism/plan-fidelity failed instead of running on Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Under `### UPDATED: python/agent_voters.py`, add an explicit step: parameterize `_dispatch_waterfall(..., no_fallback: bool)` or add `_dispatch_voter23_waterfall` that omits `--no-fallback`; route only voter-1 one-slot isolation through a `--no-fallback` launcher. State that the existing helper must not be reused verbatim for voters 2-3.


