## Goal
Implement issue #4068: [IMPLEMENTING] /design clarify loop: two-phase design-clarify.sh wrapper.

## Implementation Plan
## Plan

Implement the approved two-phase clarify wrapper with launcher-backed pause checks, explicit issue binding, resolved plugin-root binding, route-state repo fallback, durable request-id handoff, separate plan and response artifacts, byte-compatible cleanup semantics, explicit fetch-failure orchestration, stdin/stdout redaction, and fail-closed publish status handling.

- Add `clarify comment-fetch` as a narrow Python read helper.
- Add launcher-compatible `design-clarify.sh --phase fetch|publish`.
- Invoke clarify through exactly two `design-run-$PPID.sh` Bash fences plus the existing Final summary fence.
- Pass the current issue explicitly into both clarify launcher fences with `--issue "$ISSUE_NUMBER"`.
- Preserve repo targeting on `ROUTE=clarify` by loading `REPO` from route state when launcher/session env does not provide it.
- Keep `AskUserQuestion` and artifact composition in `skills/design/SKILL.md`.
- Write separate operator-produced artifacts:
  - `$DESIGN_TMPDIR/clarify-plan.md` for the revised plan block.
  - `$DESIGN_TMPDIR/clarify-response.md` for the clarify response comment.
- Preserve existing clarify branch semantics byte-for-byte (fetch requires `STATE=awaiting-response`; fail-closed on redact/plan-write failure; force `PUBLISH_OK=false` on non-zero publish exit; continue comment-post and label removal after publish failure; rename only when `SESSION_ID` non-empty and `PUBLISH_OK=true`; never emit `--state designed`).

## Acceptance

- Clarify branch: two Bash calls plus the existing Final summary fence; byte-compatible comment, label, and rename behavior and exit-0 semantics on success.
- Offline harness covers plan-write failure, publish failure, empty `SESSION_ID`, and the happy path.

diff_lines: 1090

## Test plan
(no test plan section in plan-file)
