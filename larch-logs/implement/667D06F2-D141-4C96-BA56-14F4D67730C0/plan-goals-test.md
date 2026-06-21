## Goal
Implement issue #4954: [IMPLEMENTING] [BUG] Progress report during review does not work.

## Implementation Plan
It is supposed to show detailed progress of review process, including Gantt graph of already completed rounds, and stats.
Instead:
```
  Step 5 — Code Review (scripted loop, self_review=false). Launching the review wrapper in immediate-background mode (timeout: 21600000); it prints the banner, runs the 3-judge panel loop, post-round checks, lint-fix, and substantiality gates internally. Waiting for
  <task-notification>.

  ▎ 🔶 /implement 5: code review

⏺ Bash(export IMPLEMENT_TMPDIR=<TMPDIR>
      bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/st…)
  ⎿  Running in the background (↓ to manage)

⏺ Step 5 review loop running in background (3-judge panel, multi-round). Waiting for <task-notification> — not polling.

  ⏳ 5: code review — review panel running.

✻ Baked for 56s · 1 shell still running

※ recap: Implementing issue #4776 (fate-adjusted OOS scoring) via /implement --merge. Codex finished the code and Step 3 checks passed; the Step 5 code-review panel is now running in the background. Next: parse its results when the completion notification fires. (disable recaps in
  /config)

⏺ UserPromptSubmit operation blocked by hook:
  implement: Step 0 — preflight — started 4m ago
  last artifact: 2026-06-21 04:04:47 copy-plan.stderr.log

  Original prompt: p
```

## Test plan
(no test plan section in plan-file)
