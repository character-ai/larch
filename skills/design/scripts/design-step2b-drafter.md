# design-step2b-drafter.sh

## Purpose

Wrapper for the initial `/design` Step 2b Bash block.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- The wrapper owns the former `design-step2b-prelude.sh` checks for the active Step 2b entry path.
- Active entry order is: source environment, validate Step 2a exact sentinels, repair `.completed/step-2a`, run one pause-save check, mark timing, launch the drafter.
- Exact sentinel checks must preserve `step2b_exact_line_file` semantics: one exact line only, with multi-line files, trailing whitespace, and extra blank lines rejected.
- `design-step2b-drafter.sh` must not source `design-step2b-prelude.sh`. The helper must be copied into this wrapper or extracted into a non-executing include.
- Postplan runs internally only after drafter structural success and dirty-tree eligibility.
- Preview output is machine-row safe and cannot emit raw generated `KEY=value` rows.
- Wrapper-owned machine rows begin after `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1`.
- On drafter success the wrapper delegates with `design-step2b-postplan.sh --site step2b --snapshot-original --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" --plugin-root "$CLAUDE_PLUGIN_ROOT"`.
- The delegated exec line passes pinned launcher transport argv: `--session-env-path`, `--claude-pid`, and `--plugin-root`.
- The wrapper must not call `design-postplan-emit.sh` directly.
- Drafter failure and dirty-tree recovery do not run postplan.
- Drafter outcomes emit additive `DRAFTER_STATUS` and `DRAFTER_VENDOR` rows.
- The delegated postplan wrapper preserves rc 0, 10, 11, 12, 13, 1, 2, and unexpected rc handling.
- Missing postplan rows after drafter success are incomplete output, not success.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Removes `step2b-drafter-status.txt.token-record` before launch so retries cannot ingest stale Codex usage.
- Refuses to launch when `$DESIGN_TMPDIR/feature-description.txt` is missing or empty so the already-planned replacement path cannot proceed with a missing Step 0 input.
- The generated drafter prompt states that `mechanical_churn` accepts only `true` or `false`, never a numeric estimate.
- For the Codex drafter path only, best-effort appends the stable sidecar to `$DESIGN_TMPDIR/token-report.ndjson` and records it into the active design token ledger with `DESIGN_TMPDIR` exported. Missing, empty, or malformed sidecars are non-blocking no-ops.
- Active-ledger ingestion is required for live `/design` cost lines. NDJSON append is required for committed run-log accounting.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step2b-drafter.sh`, and relevant `/design` script checks.
