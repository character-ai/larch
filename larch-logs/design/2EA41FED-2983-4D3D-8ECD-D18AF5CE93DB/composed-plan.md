## Plan

## Approach

Make the minimum doc-only change. The approach synthesis is `NO_SKETCHES`, so this plan comes from direct repo inspection.

## Files to modify/create

### UPDATED: docs/workflow-lifecycle.md

Add a new Standalone Usage bullet immediately after the existing **Step 3 external-stop recovery** bullet.

Content intent:
- Title it **Step 5 external-stop recovery**.
- Mirror the Step 3 bullet structure.
- State that a signal-induced Step 5 wrapper stop leaves `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`, keeps the review worker alive, and withholds `.completed/step-5-terminal`.
- State that the next Step 5 entry reattaches to the recorded identity, normalizes the captured stdout, performs tmpdir-scoped cleanup, and writes `.completed/step-5-terminal`.
- State that normal completion and explicit abort cleanup still own full teardown.

Keep it operator-facing. Do not add new mechanics or imply `/review` standalone behavior changed.

### UPDATED: skills/implement/references/step5-review-branches.md

In the `stall` section, add `orphan-timeout` to the `Tool Failures` token list.

Keep it in the Tool Failures list only:
- Do not add it to `Coder Issues`.
- Do not add it to the lint-fix stall token list.
- Do not change durable bail computation.
- Do not change Step 18 state persistence prose.

## Edge cases

- Preserve the distinction between Step 5 signal detach and Step 5 orphan timeout. The lifecycle bullet should describe external-stop recovery, while the branch reference should only classify the `orphan-timeout` stall reason.
- Keep the existing `relevant-checks-*`, `round-failed-*`, and default stall wording intact.
- Do not touch files outside the two scoped targets.

## Failure modes

- If `orphan-timeout` is added to the lint-fix token list, Step 18 may treat a tool timeout as a lint-fix bail. Avoid this.
- If the lifecycle bullet says Step 5 completes on detach, operators may skip the required reentry. Say completion waits for reattach normalization and `.completed/step-5-terminal`.

## Testing strategy

- Run `make markdownlint` for the two Markdown edits.
- Optionally run `python3 python/cli.py checks run-relevant` if the branch has only these Markdown changes and local dependencies are available.
- No Python or shell harness changes are expected.

## Acceptance

- Run `make markdownlint` for the two Markdown edits.
- Optionally run `python3 python/cli.py checks run-relevant` if the branch has only these Markdown changes and local dependencies are available.
- No Python or shell harness changes are expected.

review_status: complete
rounds_completed: 1
difficulty: TRIVIAL
diff_lines: 4
