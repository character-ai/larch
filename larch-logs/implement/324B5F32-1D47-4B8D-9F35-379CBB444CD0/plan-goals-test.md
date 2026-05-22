## Goal
Fix bailed /implement runs writing empty steps_ran={} so run-statistics.md absence does not false-positive in audit scans

## Implementation Plan
## Plan

### Files / globs to touch

1. `skills/implement/scripts/write-manifest.sh` (or the sibling that
   owns the bail-path manifest closure — search anchor:
   `manifest.json` + bail in `skills/implement/scripts/`).
2. `skills/implement/SKILL.md` Step 9a.1 / bail-path section
   (anchor: the `## Step 9a.1 — OOS …` heading; document that bailed
   paths explicitly mark `steps_ran.step9a1=false` and earlier-step
   skips).
3. `.claude/skills/audit-runs/scripts/audit-scan-run.sh` — defensive
   bail-aware fallback in `_rf_condition_met` (lines ~140–170).
4. `.claude/skills/audit-runs/scripts/test-audit-runs.sh` — new
   regression cases.
5. `scripts/verify-run-log-completeness.sh` — mirror the bail-aware
   fallback so the runtime contract enforcer agrees with the audit
   scan; **and** add an analogous regression case to
   `scripts/test-verify-run-log-completeness.sh`.

### Sequenced steps

1. **Locate the bail-path manifest closure.**
   Grep `skills/implement/scripts/` for files that write
   `manifest.json` on the bail path. Candidates include
   `write-manifest.sh`, `finalize-state.sh`, and `session-setup.sh`.
   Read each to find the bail-finalize call site. The owner is the
   script that handles `STALL_TRACKING=true` → bail → write final
   manifest before unmount/cleanup.

2. **Explicit `steps_ran.step9a1=false` on bail paths.**
   In the bail-finalize site, write
   `manifest.json::steps_ran.step9a1=false` whenever the bail occurred
   before Step 9a.1 executed (i.e., no `run-statistics.md` was
   written). Mirror the rule for `step7a`, `step8` when their owning
   steps did not execute. Use the existing `steps_ran` writer helper
   if one exists (search for `steps_ran` in
   `skills/implement/scripts/`); otherwise inline the jq edit:
   `jq '.steps_ran.step9a1 = false' manifest.json > tmp && mv tmp
   manifest.json`. Document the bail-time invariant in
   `skills/implement/SKILL.md` Step 9a.1.

3. **Audit-scan defensive bail-aware fallback.**
   In `.claude/skills/audit-runs/scripts/audit-scan-run.sh` function
   `_rf_condition_met`, before the existing `step9a1` default-true
   return, add a bail-signal probe: when both
   (a) `manifest.json::steps_ran` is empty (the `{}` shape) AND
   (b) `final-summary.md` first non-empty line matches a `bailed`
   suffix (regex `bailed$`), treat the step as not reached
   (`return 1`). Same fallback applies to `step8` and `step7a` chain
   nodes when their `steps_ran` field is absent and the bail signal
   is present.

4. **Mirror in `verify-run-log-completeness.sh`.**
   Apply the same fallback shape under `condition_reached step9a1`
   (line ~125) so the runtime enforcer and audit scan agree.

5. **Regression coverage.**
   - In `.claude/skills/audit-runs/scripts/test-audit-runs.sh`:
     stage a fixture with `manifest.json::steps_ran={}` +
     `final-summary.md` starting `## /implement run <id> - bailed`,
     assert `required-file-presence: pass` (not `fail`) for the
     `run-statistics.md` row. Stage a sibling fixture with the same
     `steps_ran={}` but `final-summary.md` starting `completed`,
     assert `fail` (preserves coverage of genuinely-incomplete runs).
   - In `scripts/test-verify-run-log-completeness.sh`: add the same
     two-case shape against the runtime enforcer.
   - Add a third positive fixture (the bail path on the
     `/implement`-side fix): manifest with explicit
     `steps_ran.step9a1=false`, assert `pass`.

6. **Run `/relevant-checks`** plus
   `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` and
   `bash scripts/test-verify-run-log-completeness.sh`.

### Breaking changes

None. The /implement-side change is additive (writing more
fields into `manifest.json::steps_ran`). The audit-scan-side fallback
softens an over-broad default-true into a conservative
default-with-bail-signal. External consumers reading the manifest's
`steps_ran` field gain more honest information (explicit `false` for
skipped steps); consumers that previously assumed empty means "may have
ran" must already handle the missing-field case (since today the field
is sometimes `{}`).

### Closed decisions

- **Audit-side fallback alone is insufficient**: leaving the manifest
  ambiguous (`steps_ran={}`) propagates the false-positive risk to
  every downstream consumer. The /implement-side change is the
  structurally correct fix.
- **Audit-side fallback alone is also insufficient**: not adding the
  audit-side bail-signal probe leaves stale-manifest historical runs
  (every run before this fix lands) misclassified. The audit-side
  probe gracefully handles backward-compatibility.
- **Do not modify `docs/run-logs-required-files.tsv` row**. The
  contract row (`run-statistics.md step9a1 run-statistics md`) is
  correct as-is; the bug is in the "is step9a1 reached?" inference,
  not in the file's required-when condition.

## Acceptance

1. `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` and
   `bash scripts/test-verify-run-log-completeness.sh` both PASS with
   the new cases.
2. A staged bail-path /implement run (force a Step 5 stall) produces a
   `manifest.json` whose `steps_ran` includes
   `step9a1: false` (and the other applicable skipped steps), and the
   audit-scan reports `required-file-presence: pass` for that run's
   `run-statistics.md` row.
3. `/relevant-checks` passes with no new warnings introduced.
4. After landing, a `/audit-runs since last audit` run that includes
   any bailed runs reports zero `required-file-presence: fail` rows
   whose only missing file is `run-statistics.md` (or
   `oos-issues.ndjson` on its bail-skip path).
5. Existing PASS cases in both test harnesses continue to PASS
   unchanged (no regression on the completed-run coverage).

## Test plan
(no test plan section in plan-file)
