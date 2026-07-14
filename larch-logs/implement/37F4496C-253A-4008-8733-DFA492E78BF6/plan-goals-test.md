## Goal
Implement issue #7209: [IMPLEMENTING] bug-treadmill [FEATURE] 6968.1: /learn-from-bugs host, size-budget, and cheaper-alternative proposal contract plus G-Prevent-1.

## Implementation Plan
## Plan

## Approach

Extend the `/learn-from-bugs` proposal and filing contracts with enforceable host, cost, and cheaper-mechanism semantics, pin them in the existing structure harness, and record the operating principle as an architectural guideline. This piece changes prose contracts and their pins only; the mechanical manifest lint is the independent sibling piece.

## Files to modify/create

### UPDATED: skills/learn-from-bugs/SKILL.md

- Require **Host**, **Size budget**, and **Cheaper alternative** for Step 4 sections 4 and 7, and section 5 proposals whose `best-home` is `lint` or `hook`.
- Define **Host** as an existing lint rule, module, hook, or harness being extended. Permit `Host: New module` only when the proposal also names the closest existing host and gives one sentence explaining why it cannot absorb the rule.
- Define **Size budget** as estimated new non-test lines; require an explicit justification above 150 lines.
- Define **Cheaper alternative** as the nearest cheaper mechanism, such as extending an existing rule, a manifest/table entry, invariant test, or hook line, plus one sentence explaining why it is insufficient.
- Require the three fields and their conditional explanations in Lint, Hook-contract, and Regression test filing body contracts.
- Make the pre-filing completeness pass fail closed for missing, blank, or semantically incomplete applicable fields, including missing over-150-line justification.
- Require default-mode Step 5 operator approval for every proposal whose Size budget exceeds 400 lines.
- Require filing mode to split every proposal whose Size budget exceeds 400 lines before filing; do not allow filing to proceed with the oversized proposal intact.

### UPDATED: python/tests/skills/_structure_learn_from_bugs_specialized.py

- Pin the exact field names `Host`, `Size budget`, and `Cheaper alternative`.
- Pin the Host exception requirement naming the closest existing host and why it cannot absorb the rule.
- Pin the Cheaper alternative requirement naming the nearest cheaper mechanism and why it is insufficient.
- Pin the fields and semantics in the applicable report and Lint, Hook-contract, and Regression test filing contracts.
- Pin fail-closed completeness behavior, the over-150-line justification threshold, the default-mode Step 5 approval gate above 400 lines, and filing-mode split-before-filing behavior above 400 lines.

### UPDATED: ARCHITECTURAL_GUIDELINES.md

- Append a `## Prevention discipline` section matching the repository's heading and bullet style.
- Add a `G-Prevent-1: Prevention machinery names its host before it is commissioned` guideline heading at the file's standard guideline heading level.
- State the host-first rule, expected size disclosure, preference for extending existing mechanisms, the 2026-07 evidence including #6873, #6881, and #6955, and the narrow new-surface deviation.

## Edge cases

- Proposals whose `best-home` is neither `lint` nor `hook` in section 5 are not subject to the three fields.
- `Host: New module` without the closest-existing-host sentence is incomplete, not merely unjustified.
- A Size budget exactly at 150 or 400 lines does not trip the respective over-threshold requirement.

## Failure modes

- Keep proposal filing blocked until every applicable field, conditional explanation, threshold justification, and oversized-proposal action is complete.
- The completeness pass treats a lint, hook, or regression-test proposal missing these fields as incomplete, consistent with the existing fail-closed completeness check.
- The guideline must not restrict what `/learn-from-bugs` may propose; it changes only what a proposal must state.

## Testing strategy

- Run `make test-learn-from-bugs-structure`.
- Run focused pytest for the changed structure test module.
- Run `make lint` for acceptance coverage of the guideline and skill edits.

## Acceptance

- Run `make test-learn-from-bugs-structure`.
- Run focused pytest for the changed structure test module.
- Run `make lint` for acceptance coverage.
- The guideline lands in `ARCHITECTURAL_GUIDELINES.md` with correct numbering and style, so the `/learn-from-bugs` coverage indexer sees it as existing coverage on future runs.

diff_added: 245
diff_deleted: 5
mechanical_churn: false
diff_lines: 250

## Test plan
(no test plan section in plan-file)
