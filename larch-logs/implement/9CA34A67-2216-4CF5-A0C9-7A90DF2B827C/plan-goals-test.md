## Goal
Implement issue #4747: [IMPLEMENTING] [BUG] plan-review panel always fails: dispatch passes unsupported --mode to waterfall.

## Implementation Plan
## Summary

The `/design` Step 3 plan-review panel fails on **every** run with `panel-failed`, applying zero reviewers. `python/plan_review_panel.py::dispatch_panel()` invokes `agent dispatch-waterfall` with `--mode plan-review`, but the waterfall only accepts `--mode` in `{diff, description}` and raises a `ValidationError` (exit 2) before launching any reviewer. `dispatch_panel` discards the subprocess stderr, so the failure is silent: the loop maps the non-zero exit to `panel-failed` with `exit_code=unknown` and an empty `failure_detail_log`. This is a deterministic regression introduced by PR #4729 ("Fixes #4632"); it was not caught because the offline harness stubs the waterfall. Fix is one token (`description`), plus two hardening changes so this class of failure can never be silent again.

## Original report

Discovered while running `/design` for issue #4725. The Step 3 plan-review panel returned `STEP3_REVIEW_LOOP_STATUS=panel-failed` with `DEGRADED_PANEL=1`, `AGGREGATOR_STATUS=skipped`, `ACCEPTED_COUNT=0`. No reviewer output, no `reviewer-status.tsv`, no `execution-issues.md`, only a `round-start-s` timing mark. The panel died ~1 second after launch (far too fast for a reviewer timeout). Root-causing the silent failure revealed a `--mode` mismatch between the panel dispatcher and `agent dispatch-waterfall`. File one issue covering the mode fix plus the stderr-surfacing and test hardening.

## Reproduction scenario

1. Run `/design <issue>` on larch 51.1.4 (any issue) and let it reach Step 3 (plan review). The panel fails immediately with `panel-failed`.

Direct reproduction of the failing dispatch (mode is validated before any reviewer launches, so this is fast and side-effect-free):

```bash
python3 python/cli.py agent dispatch-waterfall \
  --slots-file "$DESIGN_TMPDIR/plan-review-slots.ndjson" \
  --plan-file "$DESIGN_TMPDIR/plan.txt" \
  --feature-file "$DESIGN_TMPDIR/plan-review-scope-anchor.txt" \
  --codex-present true --cursor-present true \
  --mode plan-review --timeout 600 2>&1; echo "EXIT=$?"
```

Observed:

```text
dispatch-with-waterfall.sh: --mode must be diff or description
EXIT=2
```

## Expected behavior

The Step 3 plan-review panel dispatches its static (and any dynamic) reviewer slots through `agent dispatch-waterfall` and collects their findings. When the waterfall fails, the error detail is surfaced (logged to `execution-issues.md` / `failure_detail_log`) rather than discarded.

## Observed behavior

`dispatch_panel` calls `agent dispatch-waterfall --mode plan-review`. The waterfall rejects the mode (`--mode must be diff or description`) and exits 2 before launching any reviewer. `dispatch_panel` runs the subprocess with `capture_output=True`, prints only `proc.stdout`, and returns `proc.returncode`; `proc.stderr` (the actual error) is thrown away. The plan-review loop then maps the non-zero `body_rc` to `panel-failed`, and the escalation ledger records `exit_code=unknown` with an empty `failure_detail_log`. Every `/design` review is silently degraded.

## Root cause analysis

Two defects, one primary and one that makes it silent:

1. **Mode mismatch (primary).** `python/plan_review_panel.py::dispatch_panel()` passes `--mode plan-review` to `agent dispatch-waterfall`. The waterfall's argument validation (`python/agent_waterfall.py`) accepts `--mode` only in `{diff, description}` and raises `ValidationError` otherwise. The voter-dispatch path in the **same** file (`dispatch_voters`) correctly passes `--mode description` and works, which confirms `description` is the intended/working value for plan review. `mode` is also forwarded to each per-reviewer launch, so `description` (not a new `plan-review` mode) is the value that works end to end.

2. **Discarded stderr (observability).** `dispatch_panel` captures the waterfall's stderr but never prints, logs, or returns it. That is why the panel-failed escalation has `exit_code=unknown` and an empty `failure_detail_log`, leaving operators with no diagnostic.

The mismatch was introduced by PR #4729 (commit `afbdbd488`, "Fixes #4632", 2026-06-18), which ported the panel dispatch from Bash to Python. The waterfall's `{diff, description}` validation predates that commit (2026-06-16) and was not updated. CI stayed green because the offline harness substitutes the waterfall binary via the `DISPATCH_PLAN_REVIEW_WATERFALL_SH` override (see `plan-review.md` "Harness overrides"), so the real `{diff, description}` validation is never exercised by the unit test.

## Evidence

- Reproduced the exact failing argv: `dispatch-with-waterfall.sh: --mode must be diff or description` / `EXIT=2` (mode is validated before any reviewer launch).
- Failure timing: the `.bg-wait-active` marker `START_EPOCH` and the `panel-failed` escalation timestamp are ~1 second apart; no per-slot reviewer output, `.output-files` paths-file, or vendor timing row was ever written.
- `dispatch_panel` source: runs `agent dispatch-waterfall ... --mode plan-review`, then `print(proc.stdout, end="")` and `return proc.returncode` with no handling of `proc.stderr`.
- `agent_waterfall.py` argument validation: `if mode not in {"diff", "description"}: raise ValidationError("...--mode must be diff or description")`.
- Voter parity: `dispatch_voters` in the same file passes `--mode description` (and `--launch-mode description`) and is not affected.
- Escalation ledger from the failing run: `trigger=panel-failed`, `exit_code=unknown`, `failure_detail_log=` (empty).
- Regression provenance: `git blame` attributes the `--mode plan-review` literal to commit `afbdbd488` (PR #4729, "Fixes #4632", 2026-06-18); the validation set is older.

## Affected files

- `python/plan_review_panel.py` — `dispatch_panel()` passes the wrong `--mode` value and discards the waterfall's stderr. Primary fix site.
- `python/agent_waterfall.py` — owns the `{diff, description}` mode validation; reference for the accepted contract (no change needed if the dispatcher is corrected to `description`).
- `python/test_plan_review_panel.py` — offline harness stubs the waterfall via `DISPATCH_PLAN_REVIEW_WATERFALL_SH`, so it did not catch the mismatch; needs a non-stubbed (or contract-asserting) regression case.
- `skills/design/scripts/design-step3-review.sh` / `python/plan_review.py` — map the non-zero dispatch exit to `panel-failed`; relevant to surfacing the real reason.

## Suggested fix(es)

1. **Correct the mode (one token).** In `dispatch_panel()`, change `--mode plan-review` to `--mode description`, matching the voter-dispatch path and the waterfall's accepted set.
2. **Stop swallowing the error.** When `agent dispatch-waterfall` exits non-zero, have `dispatch_panel` surface `proc.stderr` (append it to `execution-issues.md` / populate `failure_detail_log`, and include the real exit code) so `panel-failed` is never diagnostic-free again.
3. **Close the test gap.** Add a regression test that exercises the real `{diff, description}` validation (do not stub the waterfall for this case), or at minimum assert `dispatch_panel` passes a mode in `{diff, description}` and assert parity between the panel and voter mode values.

## Open questions

- Confirm `description` (not a new `plan-review` mode) is the intended end-to-end value. Voter parity and the waterfall contract both indicate yes; flagging in case PR #4632 intended a distinct `plan-review` mode with different downstream behavior.
- Should this also have a smoke/integration check that a real `/design` Step 3 panel launches at least one reviewer, so a future dispatch-contract drift fails CI rather than silently degrading every review?

## Test plan
(no test plan section in plan-file)
