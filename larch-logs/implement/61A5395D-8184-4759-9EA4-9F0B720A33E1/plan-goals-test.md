## Goal
Implement issue #6383: [IMPLEMENTING] [BUG] /design (and likely /implement) explicitly ask for confirmation to file [OOS] item, but should not ask for confirmation, and should just do it.

## Implementation Plan
## Plan

## Approach

Make the smallest prompt-contract change that fixes the bug.

- Treat accepted non-security OOS filing as already authorized by the review and approval flow.
- Do not change OOS acceptance, security routing, dedup, dependency analysis, priority labeling, retry behavior, or the `/implement` Python path.
- Add explicit `AskUserQuestion` / confirmation bans at every prompt surface in `finalize-step5.md` that can invoke `/larch:issue`, including the manual recovery path.

## Files to modify/create

### UPDATED: skills/design/references/finalize-step5.md

In `NEXT_ACTION=file-issues`, add a short directive before the `/larch:issue` invocation details:

- Do not ask the operator for confirmation before filing.
- Do not use `AskUserQuestion` on this branch.
- The accepted non-security OOS set plus Gate C approval is the authorization to file.
- Apply the same rule to the once-only retry path.

In the **Manual OOS recovery** subsection (steps 1-4), extend the same scoped directive:

- Do not ask for confirmation before invoking `/larch:issue` on the manual recovery path.
- Accepted non-security OOS only; security-routed OOS is never filed here.

Add a matching `contains` assertion in `scripts/test-design-structure.sh` for a stable literal in the manual recovery subsection.

Keep all existing dependency-file, stdout-capture, annotate, label-failure, and partial-failure rules unchanged.

### UPDATED: skills/design/SKILL.md

In Step 5b, reinforce the `file-issues` dispatch bullet:

- Invoke `/larch:issue` and annotate per `finalize-step5.md`.
- Do not ask for confirmation before that invocation.

Keep this as routing reinforcement only. Do not duplicate the detailed body from `finalize-step5.md`.

### UPDATED: skills/implement/references/oos-pipeline.md

In step 4, `Run the /issue batch`, add the same explicit rule for the legacy bash path:

- Do not ask the operator for confirmation before the batch call.
- Accepted non-security OOS disposition is automatic for this checkpoint.
- Preserve existing carve-outs: security-routed OOS, `forked_target=true`, `repo_unavailable=true`, failed cap/pre-pass behavior, and failed `/issue` handling.

Do not modify `skills/implement/SKILL.md` routing. Current normal filing stays in `python/cli.py oos file`; this reference remains bash-path procedure text.

### UPDATED: scripts/test-design-structure.sh

Add assertions that pin the new design prompt contract:

- `finalize-step5.md` contains the no-confirmation / no-`AskUserQuestion` instruction in the Step 5b file-issues body.
- `finalize-step5.md` contains the same scoped directive in the manual recovery subsection.
- `skills/design/SKILL.md` contains the Step 5b dispatch reinforcement.

Use stable literal snippets. Avoid brittle full-paragraph matching.

### UPDATED: scripts/test-implement-structure.sh

Add an assertion that `skills/implement/references/oos-pipeline.md` step 4 contains the no-confirmation / no-`AskUserQuestion` instruction.

Keep existing assertions that the active security-sidecar route does not load or run `oos-pipeline.md`.

## Edge cases

- Degraded design dependency pre-pass still files automatically, with the existing warning.
- Design retry after empty `/larch:issue` stdout still retries automatically once.
- Label-only and skip-pipeline branches still do not call `/larch:issue`.
- Security OOS remains private and must not be public-filed.
- `/issue` dedup and dependency behavior remain unchanged.
- Manual recovery path (annotate-before-issue) also fires without confirmation.

## Failure modes

- If the manual recovery section is missed, that path remains promptable even after the main fix. Covered by FINDING_1.
- If only `finalize-step5.md` changes, the Step 5b skeleton may still look promptable. Reinforce `skills/design/SKILL.md`.
- If wording is too broad, it could appear to skip security disposition. Keep the rule scoped to accepted non-security OOS filing.
- If tests pin overly long prose, small readability edits will churn harnesses. Pin short contract literals.

## Testing strategy

Run changed-file harnesses:

```bash
make test-design-structure test-implement-structure
```

If markdown lint runs locally for changed `.md` files, run the scoped relevant checks path or the repo's changed-file lint flow.

confidence: high

## Acceptance

Run changed-file harnesses:

```bash
make test-design-structure test-implement-structure
```

If markdown lint runs locally for changed `.md` files, run the scoped relevant checks path or the repo's changed-file lint flow.

confidence: high

diff_lines: 48

## Test plan
(no test plan section in plan-file)
