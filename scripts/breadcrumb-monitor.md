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

Six env vars are allocated by paired callers before launching the monitor (the
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
- `LARCH_PAIRED_PID_FILE` — optional paired-process PID file. When the monitor
  is invoked with `--paired-pid-file PATH`, the top-level Family B script writes
  its own `$$` here via `larch_quiet_write_paired_pid_file`; no flag means no
  timeout signaling and preserves the previous behavior.

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
- **Paired PID ownership is top-level only.** `ship-pr.sh`,
  `run-step5-review.sh`, `run-step2-dispatch.sh`, `collect-agent-results.sh`,
  and `dispatch-plan-voters.sh` write `LARCH_PAIRED_PID_FILE`. Nested children
  (`ci-wait.sh`, `review-and-fix.sh`, `step2-implement.sh`, and
  `dispatch-with-waterfall.sh`) do not write it; parents unset the env var
  before invoking them.
- **Timeout signaling is best-effort.** On timeout with `--paired-pid-file`,
  the monitor reads at most 33 bytes, strips one final newline only, then
  rejects any remaining CR/LF, non-digit, empty, zero, or post-strip overlong
  value and warns with `WARN paired-pid-file-missing` before continuing to
  `exit 4`. A valid PID gets `SIGTERM`, up to five one-second `kill -0` polls,
  then `SIGKILL`; every `kill` is guarded so stale or inaccessible PIDs cannot
  prevent `exit 4`.
- **Paired PID reads re-validate the path.** Timeout handling does not trust the
  startup argv check alone: immediately before reading `LARCH_PAIRED_PID_FILE`,
  the monitor re-runs the same absolute/no-`..`/non-symlink/regular-file/
  session-tmpdir validation and treats anything that no longer passes as missing.
- **PID reuse caveat.** The monitor does not prove the PID is still the child
  originally launched by the shell. A long-departed PID could theoretically be
  reused; the 1800-second timeout and same-UID operator model keep this a known
  limitation rather than a process-identity guarantee.

## Caller Contract

Callers paired with a top-level Family B writer must keep the wrapper shell
alive until the writer process exits. The canonical same-fence pattern is:
launch the writer with shell `&`, capture `$!`, run this monitor in the
foreground, then `wait` on the captured PID after the monitor returns.

Callers must preserve both exit-code channels. Capture `monitor_rc` with
`monitor_rc=0` plus `breadcrumb-monitor.sh ... || monitor_rc=$?`. When
`monitor_rc=0`, wait for the writer and exit with `writer_rc`; orchestrators
then read the writer's `EXIT_CODE` from `LARCH_STATUS_FILE` for routing.
**Monitor exit 0 does not mean writer success** — it only means the done
sentinel was detected. Writer success is determined by `writer_rc` (the `wait`
exit code) and `EXIT_CODE` from `LARCH_STATUS_FILE`. When
`monitor_rc` is non-zero, perform the bounded reap and exit with `monitor_rc`
so infrastructure failures remain visible.

The monitor's timeout path is the bounded hang-stop: after 1800 seconds it calls
`larch_bm_signal_paired_pid`, which sends SIGTERM, waits briefly, then sends
SIGKILL. The caller's post-monitor `wait` reaps that process and does not extend
the hang window beyond the monitor timeout discipline.

See `BASH_AUTHORING.md` §4 for the copyable canonical wrapper.

## Exit codes

- `0` — done sentinel became non-empty within timeout; or the surfaced
  sentinel was already non-empty at startup (resume).
- `2` — argv / path-validation failure.
- `4` — timed out (default 1800s) waiting for the done sentinel. Tests may set
  `LARCH_BM_TEST_MODE=1` plus a positive `LARCH_BM_TEST_TIMEOUT_SECONDS` to
  shorten this branch.

The monitor surfaces a "Failure tail (status=N)" block from
`LARCH_QUIET_LOG_FILE` when `EXIT_CODE` is non-zero, but the monitor's own
exit is `0` for any non-timeout outcome (the orchestrator reads the status
file for the real exit code).

## Caller-side path allocation

See `BASH_AUTHORING.md` §4 ("Pre-launch path allocation"). The six env
vars must live under the calling skill's session tmpdir
(`$IMPLEMENT_TMPDIR` / `$DESIGN_TMPDIR` / `$REVIEW_TMPDIR` /
`$RESEARCH_TMPDIR`); `larch_bm_validate_path` rejects anything outside
that surface. Paths must be absolute, contain no `..`, and not be symlinks.
When `LARCH_LOG_ROOT` is set, the helper deliberately disables the fallback
acceptance for repo-root `larch-logs/...` paths and requires an explicit
session tmpdir env instead.

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
- timeout signaling through `--paired-pid-file`, TERM-to-KILL escalation,
  missing/empty/malformed PID fallback warnings, stale PID kill failures, the
  `LARCH_BM_TEST_MODE=1` / `LARCH_BM_TEST_TIMEOUT_SECONDS` hook, and the
  nested-overwrite regression

## Edit-in-sync

- Changing the monitor's sentinel-check semantics requires updating the
  Family B caller fences (they may pre-create files via `mktemp`) and
  `lib-quiet.sh:larch_quiet__exit_write_done` /
  `lib-quiet.sh:larch_quiet_init` to keep the signalling contract aligned.
- Adding a new Family B script to `scripts/lint-foreground-markers.sh`'s
  denylist requires that script to also `source lib-quiet.sh` and call
  `larch_quiet_append_done_trap` (`larch_quiet_init` is optional and
  changes stdout/stderr semantics). Only top-level Family B entrypoints should
  call `larch_quiet_write_paired_pid_file`; nested children must stay excluded.
