## Proposed Design Outline

### Goals
- Fix the 4 accepted latent defects (FINDING_17, _11, _25, _4) in the `/design` Step 5c publish tail, each at its true site.
- Make the empty-`SESSION_ID` terminal summary honest: add a `publish-skipped` outcome and drop the fake `larch-logs/design/unknown/` Run-logs path.
- Keep every fix surgical and independent — no shared refactor.

### Non-goals
- No change to the normal full-`SESSION_ID` publish / CI-gate / squash-merge flow.
- No rework of `design-log-publish.sh`'s worktree / PR / merge machinery beyond `--repo` validation.
- No new `/design` features; defect repair only.

### Approach sketch
- FINDING_17: broaden `design-publish.sh`'s first publish-result branch to force `PUBLISH_OK=false` on **any** non-zero `design-log-publish.sh` exit (fail-closed).
- FINDING_11: add a fail-closed `validate_repo` (`exit 1`) at `design-log-publish.sh` entry, run only when `REPO` is non-empty.
- FINDING_25: gate the `.completed/step-5c` sentinel in `SKILL.md` (the real writer) on publish success; update its pinned `test-design-structure.sh` assertion.
- FINDING_4: add a `publish-skipped` `SUMMARY_OUTCOME` in `design-publish.sh` + `render-final-summary.sh`; fix the `unknown` run-id Run-logs leak in shared `render-run-summary.sh`.

### Surfaces in scope
- `skills/design/scripts/design-publish.sh`, `scripts/design-log-publish.sh`, `skills/design/scripts/render-final-summary.sh`, `scripts/render-run-summary.sh`, `skills/design/SKILL.md`.
- Their regression tests + each changed script's `.md` sibling contract.

### Open questions
- None. (Exit-code convention and summary-outcome shape were resolved in Round 1.)
