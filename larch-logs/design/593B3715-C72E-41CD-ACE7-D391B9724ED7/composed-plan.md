## Plan

## Approach

- Update only `ARCHITECTURAL_GUIDELINES.md`.
- Insert the requested `## Migration discipline` section immediately before `## Enforcement philosophy`.
- Keep the inserted block byte-identical to the feature description.
- Do not edit existing guideline entries or lint infrastructure.

## Files to modify/create

### UPDATED: ARCHITECTURAL_GUIDELINES.md

Insert this block before `## Enforcement philosophy`:

```markdown
## Migration discipline

### G-Mig-1: Inventory environmental assumptions before a platform migration
- Why: two platform migrations broke distant features that depended on properties the migration changed rather than on any code it edited; the Python flush port moved rendered files into the system `$TMPDIR` and corrupted every subsequent transcript capture (#6263), and the bgjob transport removed the idle prompt that the typed `p`/`progress` surface required to fire at all (#6624), and neither victim surface appeared in the migration diffs, so review could not catch them.
- Guidance: before landing a migration that changes an execution-environment property, such as temp-file location, process lifetime, turn or idle structure, working directory, or notification timing, enumerate the features keyed on that property by searching for its consumers (env-var reads, hook trigger channels, path derivations), and verify or migrate each consumer in the same change or a linked tracking issue.
- Deviate when: the changed property provably has no consumer outside the migration's edit surface; say so in the PR description and name the search you ran.
```

## Edge cases

- Preserve the blank line before `## Enforcement philosophy`.
- Do not normalize quotes, issue numbers, `$TMPDIR`, or `p`/`progress`.
- Keep the change insert-only.

## Failure modes

- Wrong insertion point would weaken the intended section order.
- Non-byte-identical prose would fail the acceptance criteria.
- Editing nearby entries could create avoidable review churn.

## Testing strategy

- Inspect the diff and confirm only `ARCHITECTURAL_GUIDELINES.md` changed.
- Verify the inserted block matches the requested block exactly.
- Run changed-file relevant checks with `python3 python/cli.py checks run-relevant`.
- Rely on CI for the full sweep unless the operator asks for local `make lint`.

## Acceptance

- Inspect the diff and confirm only `ARCHITECTURAL_GUIDELINES.md` changed.
- Verify the inserted block matches the requested block exactly.
- Run changed-file relevant checks with `python3 python/cli.py checks run-relevant`.
- Rely on CI for the full sweep unless the operator asks for local `make lint`.

review_status: ok
rounds_completed: 1
difficulty: TRIVIAL
diff_added: 7
diff_deleted: 0
mechanical_churn: false
diff_lines: 7
