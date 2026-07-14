## Goal
Implement issue #7250: [IMPLEMENTING] [BUG] /design --skip-approve skips Gate C architectural-invariant present-note +….

## Implementation Plan
## Summary

During a `/design -s 7137` run (run AB77BCA2-66DF-4F90-8217-9EB05D98DE11), the orchestrator skipped the mandatory Gate C Presentation steps — `architectural-invariants present-note` → `persist-design-assessment` and `architectural-guidelines present-note` → `persist-design-assessment` — on the `--skip-approve` path. Instead it called `architectural-invariants read` (the plan-drafting verb from Step 2b) and made no `persist-design-assessment` call, leaving both `architectural-invariant-assessment.md` and `architectural-guideline-assessment.md` absent when Step 5c ran. This caused two sequential publish refusals and a multi-step manual recovery before the design completed.

## Original report

root cause of why architectural assessment was NOT written the first time around

## Reproduction scenario

1. Run `/design -s <issue>` against any repo where `ARCHITECTURAL_INVARIANTS.md` is `present` with parsed non-empty content and `ARCHITECTURAL_GUIDELINES.md` is also `present`.
2. The orchestrator reaches Step 4b with `SKIP_APPROVE_REQUESTED_GATEC=true`.
3. Orchestrator reads the Gate C preview plan, then checks invariants using `architectural-invariants read` (the wrong verb for Gate C).
4. Orchestrator runs the accepted-findings audit and auto-approves with no `present-note` or `persist-design-assessment` calls.
5. Step 5c fails: `PUBLISH_REFUSE_REASON=missing-invariant-assessment`, then after manual recovery: `PUBLISH_REFUSE_REASON=missing-guideline-assessment`.

## Expected behavior

When `--skip-approve` is active, Gate C Presentation must still execute the full architectural assessment sequence before the auto-approve breadcrumb:

1. Source `REPO_ROOT` from the Step 0 source env.
2. `python/cli.py architectural-invariants present-note --repo-root "$REPO_ROOT"`
3. Assess against `plan.txt`; persist via `python/cli.py architectural-invariants persist-design-assessment ...`
4. `python/cli.py architectural-guidelines present-note --repo-root "$REPO_ROOT"`
5. Assess and persist via `python/cli.py architectural-guidelines persist-design-assessment ...`
6. Run the accepted-findings audit.
7. Auto-approve only after all persistence steps succeed.

Both `architectural-invariant-assessment.md` and `architectural-guideline-assessment.md` must exist in the design tmpdir before Step 5c is called.

## Observed behavior

The orchestrator:
- Called `architectural-invariants read` (Step 2b plan-drafting verb) during Step 4b instead of `architectural-invariants present-note` (Gate C verb).
- Made no `persist-design-assessment` call for either invariants or guidelines.
- Printed `⏩ 4b: Gate C: auto-approved final plan (--skip-approve)` and advanced to Step 5.
- Step 5c attempt 1 returned `PUBLISH_RC=4` / `PUBLISH_REFUSE_REASON=missing-invariant-assessment`.
- After manual recovery (ran `persist-design-assessment --assessment clean` for invariants), Step 5c attempt 2 returned `PUBLISH_RC=4` / `PUBLISH_REFUSE_REASON=missing-guideline-assessment`.
- After a second manual recovery (guidelines), Step 5c attempt 3 succeeded.

## Root cause analysis

Two interacting gaps:

**Gap 1 — wrong verb at Gate C**: The orchestrator used `architectural-invariants read` (the Step 2b plan-drafting verb, which only reads and returns content for consultation) at Step 4b instead of `architectural-invariants present-note` (the Gate C verb, which also emits `INVARIANTS_VIOLATION_ASSESSMENT_REQUIRED=true` and is required before `persist-design-assessment`). The two verbs are superficially similar; the plan-drafting check at Step 2b leaves an association in the session context that primes the wrong verb at Gate C.

**Gap 2 — SKILL.md inline summary omits invariant persistence**: The SKILL.md Step 4b `--skip-approve` carve-out reads: "still run Gate C preview and full Presentation: guideline persistence, accepted-findings audit, and audit persistence." It lists `guideline persistence` but does not list `invariant persistence` explicitly. The orchestrator may interpret "full Presentation" as the plan-preview step only, with "guideline persistence" as the one named sub-step, omitting the invariant branch entirely.

`approval-gates-gate-c.md` §Gate C correctly states "Gate C still runs the final-plan preview, architectural invariant/guideline presentation and persistence, and the accepted plan-review findings audit." However, the inline SKILL.md summary is the live control text and its omission of the invariant persistence step creates the gap.

## Evidence

- **Run**: AB77BCA2-66DF-4F90-8217-9EB05D98DE11, issue #7137.
- **Wrong call at Gate C**: `python/cli.py architectural-invariants read` (observation from this session).
- **No persist-design-assessment call**: neither `architectural-invariant-assessment.md` nor `architectural-guideline-assessment.md` existed in the design tmpdir when Step 5c first ran.
- **Step 5c attempt 1 result env**: `PUBLISH_RC=4`, `PUBLISH_REFUSE_REASON=missing-invariant-assessment`, `ARCH_INVARIANT_ASSESSMENT_STATUS=missing`, `ARCH_INVARIANT_ASSESSMENT_ARTIFACT=architectural-invariant-assessment.md`.
- **Step 5c attempt 2 result env**: `PUBLISH_RC=4`, `PUBLISH_REFUSE_REASON=missing-guideline-assessment`, `ARCH_GUIDE_ASSESSMENT_STATUS=missing`.
- **Step 5c attempt 3**: `PUBLISH_RC=0`, `PLAN_WRITE_OK=true` after manual `persist-design-assessment --assessment clean` for both kinds.
- **`approval-gates-gate-c.md` §Presentation (line 37)**: "run `python/cli.py architectural-invariants present-note --repo-root "$REPO_ROOT"` before `python/cli.py architectural-guidelines present-note`" — this mandatory step was absent from orchestrator execution.
- **SKILL.md Step 4b inline bullet**: "still run Gate C preview and full Presentation: guideline persistence, accepted-findings audit, and audit persistence" — `invariant persistence` is absent from the inline enumeration.

## Affected files

- `skills/design/SKILL.md` — Step 4b `--skip-approve` carve-out description; inline enumeration omits invariant presentation and persistence.
- `skills/design/references/approval-gates-gate-c.md` — §Presentation; correct documentation, but not duplicated in the SKILL.md inline summary that the orchestrator reads as the live control text.

## Suggested fix(es)

1. **SKILL.md Step 4b** — Expand the `--skip-approve` inline bullet to enumerate both invariant and guideline presentation and persistence explicitly:
   > "still run Gate C preview and full Presentation: bind `REPO_ROOT`, run `architectural-invariants present-note` + `persist-design-assessment`, run `architectural-guidelines present-note` + `persist-design-assessment`, accepted-findings audit and audit persistence."
   Also explicitly name `present-note` (Gate C verb) to distinguish it from `read` (Step 2b verb).

2. **`approval-gates-gate-c.md` §Presentation** — Add a callout box or NOTE clarifying the verb distinction: "`architectural-invariants read` is for Step 2b plan drafting; Gate C requires `architectural-invariants present-note` followed by `persist-design-assessment`. Using `read` here is insufficient."

3. **Optional mechanical enforcement** — Add a defensive precheck in `design-step5b-prepare.sh` or a new Step 4b entry fence that verifies `architectural-invariant-assessment.md` and `architectural-guideline-assessment.md` exist before Step 5b/5c are allowed to start, surfacing the gap earlier than Step 5c publish.

## Open questions

- Should the Step 3b finalize boundary (`design-step3b-entry.sh --mode finalize`) or the Step 5 entry be updated to defensively check assessment artifact presence and warn before Step 5c?
- Is the `--skip-approve` path the only path that exhibits this gap, or does the explicit Gate C `AskUserQuestion` path also risk missing the `present-note` → `persist` sequence?

## Test plan
(no test plan section in plan-file)
