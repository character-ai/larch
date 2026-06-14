# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: skills/implement/scripts/stall-recovery-report.sh:695-698
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] submodule-restricted mirrors protected-path with RESUME_HINT=step2-impl and inline-recovery operator text but Main Claude is also blocked from submodule edits by block-submodule-edit.sh Plan requires editing files under a git submodule; external implementer bails with submodule-edit-required-out-of-scope; stall recovery dispatches step2-impl; Main Claude Edit/Write on submodule paths is denied by the hook; run stalls after misleading inline-recovery messaging Classify submodule-restricted as non-inline-recoverable (RESUME_HINT=none retry cap 0) with operator text that submodule work is manual, or add a dedicated recovery path that does not promise inline submodule edits
- **Suggested revision**: Address the concern above.


### FINDING_10: **correctness** `skills/implement/scripts/test-stall-recovery-report-1.sh:217-226` — Stale-evidence fixtures `case7k5`/`case7k6` mirror `case7k2`/`case7k3` for classification but omit `RESUME_HINT` assertions that the protected-path cases assert at lines 207-209. If resume routing is fixed to `none` for `submodule-restricted`, only `case7k4` would fail; the argv-only and stale-note paths could keep shipping `step2-impl` unnoticed. **Suggested fix:** Add `assert_eq none "$(kv RESUME_HINT ...)"` to `case7k5` and `case7k6` (or whatever the corrected hint is), matching the protected-path precedent.
- **Reviewer**: dyn-stall-recovery-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-stall-recovery-report-1.sh:217-226` — Stale-evidence fixtures `case7k5`/`case7k6` mirror `case7k2`/`case7k3` for classification but omit `RESUME_HINT` assertions that the protected-path cases assert at lines 207-209. If resume routing is fixed to `none` for `submodule-restricted`, only `case7k4` would fail; the argv-only and stale-note paths could keep shipping `step2-impl` unnoticed. **Suggested fix:** Add `assert_eq none "$(kv RESUME_HINT ...)"` to `case7k5` and `case7k6` (or whatever the corrected hint is), matching the protected-path precedent.
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: skills/implement/scripts/stall-recovery-report.sh:652-676
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] submodule-restricted uses RESUME_HINT=step2-impl like protected-path but submodule edits are blocked for Main Claude too Plan requires submodule edit; external coder bails; Step 18a dispatches step2-impl; block-submodule-edit.sh denies edits; run stalls after misleading inline-recovery warning Use RESUME_HINT=none, retry cap 0, and operator text that submodule work is operator-owned; do not mirror protected-path step2-impl
- **Suggested revision**: Address the concern above.


### FINDING_9: **correctness** `skills/implement/scripts/stall-recovery-report.sh:652-676` — `resume_hint_for()` takes `failure_class` but never branches on it for Step 2 stalls, so `submodule-restricted` always gets `RESUME_HINT=step2-impl` (same as `protected-path`). That is wrong for this bail: `submodule-edit-required-out-of-scope` is emitted when the plan requires submodule edits (`agents/_implementer-base.md:41`), and `hooks/hooks.json:5-21` runs `block-submodule-edit.sh` on Main Claude `Edit`/`Write` too, so inline Step 2 cannot satisfy the plan. Step 18a will promise recovery, burn an attempt, then stall again on the same hook block. **Suggested fix:** In `resume_hint_for()`, return `none` for `submodule-restricted` before the step-based `2) printf 'step2-impl'` arm (and mirror in phase fallthrough). Update `skills/implement/SKILL.md:398,838`, `skills/implement/scripts/stall-recovery-report.md:206`, and tests to expect `RESUME_HINT=none` plus a warning that submodule edits are blocked for Main Claude and no automatic inline recovery will run.
- **Reviewer**: dyn-stall-recovery-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/stall-recovery-report.sh:652-676` — `resume_hint_for()` takes `failure_class` but never branches on it for Step 2 stalls, so `submodule-restricted` always gets `RESUME_HINT=step2-impl` (same as `protected-path`). That is wrong for this bail: `submodule-edit-required-out-of-scope` is emitted when the plan requires submodule edits (`agents/_implementer-base.md:41`), and `hooks/hooks.json:5-21` runs `block-submodule-edit.sh` on Main Claude `Edit`/`Write` too, so inline Step 2 cannot satisfy the plan. Step 18a will promise recovery, burn an attempt, then stall again on the same hook block. **Suggested fix:** In `resume_hint_for()`, return `none` for `submodule-restricted` before the step-based `2) printf 'step2-impl'` arm (and mirror in phase fallthrough). Update `skills/implement/SKILL.md:398,838`, `skills/implement/scripts/stall-recovery-report.md:206`, and tests to expect `RESUME_HINT=none` plus a warning that submodule edits are blocked for Main Claude and no automatic inline recovery will run.
- **Suggested revision**: Address the concern above.


