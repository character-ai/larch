## Goal
Implement issue #5710: [IMPLEMENTING] [BUG] remove escalation-success issue-filing from /implement Step 18a.5 — main-agent intervention is a feature, not a defect.

## Implementation Plan
## Summary

When a `/implement` run succeeds and the PR merges, but the run included a main-agent intervention (e.g., the lint-fix loop escalated a PLR0915 complexity fix to main agent), Step 18a.5 attempts to file a GitHub issue titled as an escalation-success report. This is wrong: main-agent intervention is an intentional, expected feature of the `/implement` workflow, not a defect signal. The filing adds noise, wastes tokens, and — as observed — gets stuck in validation loops (sensitive-corpus blocking, root-cause format errors) that burn time after a successful merge. The entire escalation-success filing path should be removed.

## Original report

main-agent intervention is not a bug, it's a feature we use to resolve difficult-for-subagents-to-resolve-issues like CI failures. Therefore, we should not be filing issues about it. Remove this functionality, i.e., main agent intervention should NOT induce an attempt to file an issue at the end.

## Reproduction scenario

1. Run `/implement <issue>` on a plan that causes the Step 3 lint-fix loop to require main-agent edit (e.g., a `PLR0915 too-many-statements` baseline violation that automated lint-fix cannot repair).
2. Main agent makes the fix; checks pass; review runs; PR is created and merges.
3. At Step 18, `step-18-gate-finalize` detects the non-empty `stall-recovery-escalation-ledger.tsv` and emits `NEXT_ACTION=escalation-filing` instead of `NEXT_ACTION=finalize-done`.
4. The orchestrator enters the Step 18a.5 procedure, spending turns trying to compose and file a GitHub issue about the escalation before teardown.

## Expected behavior

A successful merged run with main-agent intervention should proceed directly to `NEXT_ACTION=finalize-done` (or equivalent teardown). No GitHub issue should be filed about the intervention. Escalation to main agent is a normal, designed fallback — not a reportable defect.

## Observed behavior

`step-18-gate-finalize` emits `NEXT_ACTION=escalation-filing` whenever `stall-recovery-escalation-ledger.tsv` is non-empty and the run succeeded. The orchestrator then:
- Calls `stall-recovery compose-report --report-kind escalation-success` (which has its own complex validation: root-cause file KV format, sensitive-corpus checks, bounded-root-cause checks).
- On validation failures, retries with reformatted inputs, consuming extra turns.
- Even on success, invokes `/issue` to create a public GitHub issue describing the escalation.
- Writes `stall-recovery-escalation-success.env` as a sentinel.

All of this happens after a successful merge, adding latency and failure modes to an otherwise clean run.

## Root cause analysis

`_step18_escalation_filing_eligible` in `python/larch/implement/implement_dispatch.py` treats a non-empty escalation ledger as a signal that something went wrong and should be reported. The implicit assumption is that escalation = larch defect. That assumption is incorrect: the lint-fix loop deliberately escalates classes of failures it cannot auto-repair (complexity violations, semantic refactors) to main agent, which is the intended behavior, not a bug.

## Evidence

- `python/larch/implement/implement_dispatch.py:2252–2266` — `_step18_escalation_filing_eligible` returns `True` whenever `stall-recovery-escalation-ledger.tsv` is non-empty AND the run succeeded AND no stall is active.
- `python/larch/implement/implement_dispatch.py:2293–2295` — `step_18_gate_finalize_main` routes to `NEXT_ACTION=escalation-filing` on that condition, bypassing the green-path finalize entirely.
- `python/test_implement_dispatch.py:651–669` — `test_step18_gate_finalize_escalation_evidence_breaks_out` asserts this breakout behavior (test must be removed or updated).
- `skills/implement/references/step18a5-filing.md` — the full filing procedure reference, entirely devoted to filing a public GitHub issue about the escalation.
- `skills/implement/references/step18-cleanup.md:23–48` — "Step 18a.5 escalation-success report gate" section describes the skip predicates and filing trigger.
- `skills/implement/SKILL.md` — `NEXT_ACTION=escalation-filing` branch in the Step 18a composite routing.

## Affected files

- `python/larch/implement/implement_dispatch.py` — delete `_step18_escalation_filing_eligible` and `_escalation_evidence_present`; remove the escalation-filing branch from `step_18_gate_finalize_main`.
- `python/test_implement_dispatch.py` — remove `test_step18_gate_finalize_escalation_evidence_breaks_out` and any other tests that assert `NEXT_ACTION=escalation-filing`.
- `skills/implement/references/step18a5-filing.md` — retire or delete entire file.
- `skills/implement/references/step18-cleanup.md` — remove "Step 18a.5 escalation-success report gate" section.
- `skills/implement/SKILL.md` — remove `NEXT_ACTION=escalation-filing` branch from Step 18a routing.
- `python/larch/state/stall_recovery.py` — consider whether `compose-report --report-kind escalation-success` and related helpers (`_validate_root_cause_artifact`, bounded-root-cause path, `escalation-success` branch in `_compose_report_body`) should be removed or kept for the `/design` skill which may have its own escalation reporting path. If only `/implement` used this, remove. If `/design` still needs it, keep but scope narrowly.
- `docs/` — update any workflow lifecycle or stall-recovery docs that reference the escalation-success filing path.

## Suggested fix(es)

**Minimal fix** (recommended):
1. In `implement_dispatch.py`: delete `_step18_escalation_filing_eligible` and `_escalation_evidence_present`; remove the `if _step18_escalation_filing_eligible(...)` block from `step_18_gate_finalize_main`. The function then always proceeds to `NEXT_ACTION=finalize-done` on the no-stall path.
2. In `test_implement_dispatch.py`: delete `test_step18_gate_finalize_escalation_evidence_breaks_out`.
3. In `SKILL.md`: remove the `escalation-filing` NEXT_ACTION branch from Step 18a.
4. In `step18-cleanup.md`: remove the Step 18a.5 section.
5. Retire `step18a5-filing.md` (move to `docs/` graveyard or delete if no other consumer).
6. Audit `stall_recovery.py` `escalation-success` path for consumers outside `/implement`; remove if unused.

The `stall-recovery-escalation-ledger.tsv` and `record-escalation` mechanism can remain for diagnostic/observability purposes (they appear in run logs), just without triggering a filing flow.

## Open questions

- Does `/design` use `compose-report --report-kind escalation-success`? If so, that path in `stall_recovery.py` should be retained and scoped to `/design` only.
- Should the escalation ledger still be committed to `larch-logs/` for observability, even if no issue is filed? (Likely yes — keep the ledger, remove only the filing step.)

## Test plan
(no test plan section in plan-file)
