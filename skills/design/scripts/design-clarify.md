# design-clarify.sh

Two-phase `/design` Step 0b clarify helper.

## Purpose

Moves the prompt-side clarify shell sequence behind the design launcher while
leaving the LLM-owned `AskUserQuestion` and artifact composition in
`skills/design/SKILL.md`.

## Phases

- `--phase fetch --issue N`: verifies `clarify state` is `awaiting-response`,
  fetches the matching request comment with `python/cli.py clarify
  comment-fetch`, writes `$DESIGN_TMPDIR/clarify-request.md`, and emits
  `CLARIFY_FETCH_STATUS=ok` plus durable file paths.
- `--phase publish --issue N`: reads `$DESIGN_TMPDIR/clarify-plan.md` and
  `$DESIGN_TMPDIR/clarify-response.md`, redacts and writes the plan block,
  runs design-log publish fail-closed, posts the clarify response, removes the
  clarification label, and renames to `[DESIGNING]` only when `SESSION_ID` is
  non-empty and `PUBLISH_OK=true`.

## Invariants

- Invoked through `design-run-$PPID.sh`, which supplies `--session-env-path`
  and `--claude-pid`.
- Accepts the current issue explicitly through `--issue`.
- Falls back to `.design-step0-route-state.env` for `REPO` when the session env
  lacks it.
- Never prints request or response bodies on stdout. Bodies move through files.
- Does not emit `--state designed`; clarify-only updates are not terminal
  design completion.

## Harness

Covered by `skills/design/scripts/test-design-clarify.sh` and structural pins in
`scripts/test-design-structure.sh`.
