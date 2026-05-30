## Decision 1: Launcher / lane scope
- **Question**: How wide should the failed-stderr-tail change reach across the launcher family?
- **Resolution**: Centralize at the shared choke points. In scope: codex/cursor failure paths via `run-external-agent.sh` (observes the exit) + `collect-agent-results.sh` (orchestrator-facing surface), and claude via `launch-claude-review.sh` (bypasses the runner). This covers review/CI/implement codex+cursor lanes plus claude. Out of scope: bespoke per-launcher edits to each `launch-*-*.sh`.
- **Source**: user

## Decision 2: Emit cadence
- **Question**: When should the redacted stderr tail be surfaced — every failed subprocess exit, or only when a waterfall slot fully exhausts?
- **Resolution**: Surface on every non-zero subprocess exit (matches the issue's literal "On any FAILED (non-zero exit) subprocess invocation"). Capture at the per-subprocess layer; each attempt is independently diagnostic. A fully-failing slot may print up to 3 tails.
- **Source**: user

## Decision 3: Size guard parameters
- **Question**: What bounds the surfaced output?
- **Resolution**: Default 30 tail lines, tunable via `LARCH_FAILED_AGENT_STDERR_TAIL_LINES`; PLUS an absolute 5 KB byte ceiling applied after redaction so one pathological long line cannot flood chat. `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` disables surfacing (escape hatch).
- **Source**: user

## Decision 4: Redaction (hard constraint)
- **Question**: Must the tail be redacted before surfacing?
- **Resolution**: Yes. Pipe the tail through `scripts/redact-secrets.sh` before it reaches chat — stderr can carry tokens/secrets.
- **Source**: issue body

## Decision 5: Failure-only / quiet-on-success (hard constraint, non-goal)
- **Question**: Which exit conditions trigger surfacing?
- **Resolution**: Surface on non-zero exit only (includes the timeout case, exit 124). Preserve quiet-by-default on success (exit 0), including the exit-0-but-empty-output case. Do NOT surface stderr on success.
- **Source**: issue body / codebase (`run-external-agent.sh` exit handling)

## Decision 6: Backward compatibility (hard constraint)
- **Question**: What existing behavior must not break?
- **Resolution**: Keep the existing one-line verdict (`Failed with exit code ... Output size: ... bytes.`), the `.diag` file, and the `collect-agent-results.sh` `FAILURE_REASON` single-line contract unchanged. The new tail is ADDITIVE — a separate surface alongside the verdict, not a replacement. Multi-line tail must not corrupt the `KEY=value` / pipe-delimited collector parser. Emit the tail on FD 2 (stderr / `larch_err`), NOT into the stdout KV plane the orchestrator parses.
- **Source**: codebase (`collect-agent-results.sh` parser; `.claude/rules/external-tool-launcher-parity.md`)

## Decision 7: Suppress identical (same-root-cause) failures
- **Question**: When many slots fail with the same cause (the #3119 flood: 12 slots, same codex exit-1), should each emit a full tail?
- **Resolution**: No. Within one `collect-agent-results.sh` batch, the FIRST occurrence of a given failure prints the full tail; each later slot with the SAME root cause prints ONE line ("identical failure to <first slot>; tail suppressed"). "Identical" is a best-effort root-cause fingerprint, NOT byte-identical: normalize volatile tokens (digit runs, hex, tmpdir/session paths, durations, byte sizes, per-slot output basename) then hash via `cksum`. Documented explicitly as heuristic, not semantic understanding. Cross-invocation / foreground (CI, lint-fix-loop) dedup is a non-goal for this change.
- **Source**: user
