# breadcrumb-monitor.sh contract

`scripts/breadcrumb-monitor.sh` is the foreground consumer paired with every
Family B background launch (see `BASH_AUTHORING.md` §4). It surfaces breadcrumbs
written to `LARCH_BREADCRUMB_STREAM` to its stdout and, crucially, blocks the
orchestrator's foreground Bash turn until the monitored script has actually
exited. The blocking semantic is what prevents step-jumping: while a Family B
script is still running, the next orchestrator step cannot start.

## Callers

Every Family B `# Background pair required` fence in:

- `skills/design/SKILL.md` (and `skills/design/references/*.md`)
- `skills/research/references/*.md`
- Any future Family B fence covered by `scripts/lint-foreground-markers.sh`'s
  denylist (`ship-pr.sh`, `ci-wait.sh`, `run-step5-review.sh`,
  `review-and-fix.sh`, `run-step2-dispatch.sh`, `step2-implement.sh`,
  `collect-agent-results.sh`, `dispatch-with-waterfall.sh`,
  `dispatch-plan-voters.sh`).

## Wire contract

Five env vars must be set by the caller before launching the monitor (the
launcher fences do this via `mktemp` under the calling skill's session
tmpdir):

- `LARCH_BREADCRUMB_STREAM` — append-only NDJSON-ish stream the monitored
  script writes via `emit_breadcrumb`.
- `LARCH_DONE_SENTINEL` — **signaled when non-empty.** The monitored
  script's `larch_quiet_append_done_trap` writes `EXIT_CODE=N` here on
  exit; the monitor's polling loop breaks when this file becomes
  non-empty. `mktemp` may pre-create the file empty — that is treated as
  "not yet signaled."
- `LARCH_STATUS_FILE` — receives `EXIT_CODE=N` written atomically by the
  same trap.
- `LARCH_QUIET_LOG_FILE` — receives stdout/stderr from the monitored
  script under quiet mode. The monitor tails this on failure.
- `LARCH_BREADCRUMBS_SURFACED_FILE` — **resume-safety check.** Treated as
  signaled when non-empty. `lib-quiet.sh:larch_quiet_init` writes
  `surfaced\n` here when FD-3 is visible (a subprocess that surfaces
  breadcrumbs to its parent via the inherited FD-3 pipe), at which point
  a freshly launched monitor exits 0 because the breadcrumbs are already
  being surfaced by the subprocess. `mktemp` may pre-create the file
  empty — that is treated as "not yet surfaced."

## Invariants

- **Non-empty content, not existence.** Both sentinels (`done`, `surfaced`)
  are checked with `[ -s ]`, not `[ -f ]`. This is mandatory because the
  caller fences pre-create the files via `mktemp`; an existence-only check
  fires immediately and decouples the monitor from the script (see #2826).
- **The done-trap installer must run.** Any Family B script (denylist
  above) that wants its completion to be coupled to the foreground Bash
  turn must call `larch_quiet_append_done_trap` after sourcing
  `lib-quiet.sh`. Without it, the EXIT-trap that writes the done sentinel
  is never installed and the monitor either hangs to its 30-minute
  timeout or breaks immediately on a content-less file (depending on the
  failure mode).
- **One physical process per launch.** Paths are unique per `mktemp`; the
  monitor does not coordinate across launches.

## Exit codes

- `0` — done sentinel became non-empty within timeout; or the surfaced
  sentinel was already non-empty at startup (resume).
- `2` — argv / path-validation failure.
- `4` — timed out (default 1800s) waiting for the done sentinel.

The monitor surfaces a "Failure tail (status=N)" block from
`LARCH_QUIET_LOG_FILE` when `EXIT_CODE` is non-zero, but the monitor's own
exit is `0` for any non-timeout outcome (the orchestrator reads the status
file for the real exit code).

## Caller-side path allocation

See `BASH_AUTHORING.md` §4 ("Pre-launch path allocation"). The five env
vars must live under the calling skill's session tmpdir
(`$IMPLEMENT_TMPDIR` / `$DESIGN_TMPDIR` / `$REVIEW_TMPDIR` /
`$RESEARCH_TMPDIR`); `larch_bm_validate_path` rejects anything outside
that surface.

## Harness

`scripts/test-breadcrumb-monitor.sh` is the offline regression harness:

- non-empty surfaced sentinel → exit 0 within ~1s
- empty sentinels, late `EXIT_CODE=N` write → monitor blocks until write
- end-to-end with a fake Family B script that calls
  `larch_quiet_append_done_trap` and exits after a delay → monitor
  blocks for the script's full duration (no step-jumping)
- non-zero `EXIT_CODE` propagation through status file and failure-tail
  surfacing
- `lib-quiet.sh:larch_quiet_init` writes content (not just a touch) to
  the surfaced sentinel when FD-3 is visible
- live stream growth, truncation/reset handling, PEM-redacted failure tails,
  path-scope rejection, `RESEARCH_TMPDIR` acceptance, symlink rejection, and
  invalid-category dropping

## Edit-in-sync

- Changing the monitor's sentinel-check semantics requires updating the
  Family B caller fences (they may pre-create files via `mktemp`) and
  `lib-quiet.sh:larch_quiet__exit_write_done` /
  `lib-quiet.sh:larch_quiet_init` to keep the signalling contract aligned.
- Adding a new Family B script to `scripts/lint-foreground-markers.sh`'s
  denylist requires that script to also `source lib-quiet.sh` and call
  `larch_quiet_append_done_trap` (`larch_quiet_init` is optional and
  changes stdout/stderr semantics).
