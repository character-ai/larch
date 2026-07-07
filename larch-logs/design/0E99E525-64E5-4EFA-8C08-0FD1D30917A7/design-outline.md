## Proposed Design Outline

### Goals
- On Step 8 `NEXT_ACTION=ci-fix`, spawn exactly one persistent CI-fix sub-agent (Agent tool) owning a ≤20-round fix loop; main agent idle (notification-only) and reads no CI logs on the success path.
- Add a stdlib-only `ci distill-log` verb producing a capped, redacted, all-failing-jobs failure digest, marked untrusted data.
- On fixer exhaustion/no-progress, write a bail artifact and hand back; main-agent inline fallback repairs with its own 10-attempt budget and never re-spawns the fixer for the same run-id.

### Non-goals
- No wholesale local test/lint suites in the fixer (pre-commit + targeted single-check reruns only).
- No static job allowlist, no auto-rollback of fixer edits (trust the push; CI judges).
- ship-pr's immediate-bail (#5182) and rebase paths stay unchanged.

### Approach sketch
- Router: `skills/implement/SKILL.md` Step 8 ci-fix branch spawns the fixer via the Agent tool with file-backed inputs (issue/PR URLs, branch-diff command, distilled-log path, doc pointers); gated by the `LARCH_CI_FIXER` kill switch (default on).
- Prompt basis: rework `ship-pr-ci-fix.md` into (a) the fixer sub-agent loop and (b) the bounded main-agent fallback; both share the per-run-id sentinel/counter surface.
- New `ci distill-log` verb in `python/larch/implement/ci.py` wrapping `gh run-logs` + `redact secrets`; new bail codes documented in `ship-pr-exit-matrix.md`.
- Kill switch + budget constants (20 / 10) in `python/larch/core/config.py`; fixer tokens/timing recorded through existing run-log plumbing so `/report-tokens` prices it separately.
- Remove the superseded `ci_agentic_fix.py`, its `agentic-fix` dispatch, the dead `ci_monitor.py` helpers, and `test_ci_agentic_fix.py`.

### Surfaces in scope
- `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-ci-fix.md`, `skills/implement/references/ship-pr-exit-matrix.md`
- `python/larch/implement/ci.py`, `python/larch/core/config.py`, `python/larch/implement/ci_monitor.py`
- Run-log / token plumbing + `python/tests/**` (new distill-log tests; remove agentic-fix test); `skill-closure-baseline.json` / `complexity-baseline.json`
- Bail artifact + shared attempt-sentinel surface under the per-run-id session dir

### Open questions
- None (scope resolved in Round 1).
