## Decision 1: Overall scope
- **Question**: Fix only the 4 accepted findings (17, 11, 25, 4), or also the entangled render-run-summary.sh `larch-logs/design/unknown/` leak that shares FINDING_4's empty-SESSION_ID root cause?
- **Resolution**: Full honest fix — the 4 accepted findings PLUS the shared `scripts/render-run-summary.sh` unknown-run-id guard. Each fix is surgical and independent; no shared refactor.
- **Source**: user

## Decision 2: FINDING_11 — malformed --repo failure convention
- **Question**: When `scripts/design-log-publish.sh` receives a malformed `--repo`, should the new `validate_repo` exit 1 (fail-closed) or `emit_publish_result false; exit 0` (match sibling value-validators)?
- **Resolution**: `exit 1` (fail-closed), honoring the finding's "match the strictness of its callers" intent and the script's structural argv-error convention (`usage; exit 1`). Validation runs only when `REPO` is non-empty (omitting `--repo` stays the hub-default path).
- **Source**: user

## Decision 3: FINDING_4 — empty-SESSION_ID summary outcome
- **Question**: How should `design-publish.sh` render the terminal summary when `SESSION_ID` is empty (publish skipped, not attempted)?
- **Resolution**: Introduce a new `publish-skipped` `SUMMARY_OUTCOME`, distinct from `approved` and `failed-publish`, with an honest "publish skipped — no SESSION_ID" note (NOT the `failed-publish` recovery-PR prose). Pair with the Decision 1 `render-run-summary.sh` guard so the Run-logs line reads `N/A`, not `larch-logs/design/unknown/`.
- **Source**: user

## Decision 4: FINDING_25 — sentinel-gate fix location
- **Question**: Where is `.completed/step-5c` actually written, and where should the publish-success gate be added?
- **Resolution**: The writer is the orchestrator (`skills/design/SKILL.md` Step 5c), NOT `design-publish.sh` — the finding misattributes it (verified: `design-publish.sh` contains no `step-5c` write). Gate the SKILL.md sentinel write on publish success (`SESSION_ID` empty **or** `PUBLISH_OK=true`) so a failed publish leaves Step 5c incomplete and pause/resume retries it. Update the pinned `test-design-structure.sh` assertion accordingly.
- **Source**: codebase

## Decision 5: FINDING_17 — fail-closed condition
- **Question**: How should `design-publish.sh` treat a non-zero `design-log-publish.sh` exit that still carries `PUBLISH_OK=true` on stdout?
- **Resolution**: Force `PUBLISH_OK=false` on ANY non-zero publish exit — broaden the first branch condition from `_publish_rc -ne 0 && stdout lacks PUBLISH_OK=` to just `_publish_rc -ne 0`. The exit-0 `elif` branches (`PUBLISH_OK==false` / unset) stay; the success path (exit 0 + `PUBLISH_OK=true`) is untouched.
- **Source**: codebase + finding

## Hard constraints (must not break)
- Preserve the exact byte substring the pinned `scripts/test-design-structure.sh` greps for in SKILL.md Step 5c (`: > "$DESIGN_TMPDIR/.completed/step-5c"` … `**only when**` … `PLAN_WRITE_OK=true`); **extend**, do not replace it.
- `scripts/render-run-summary.sh` is shared with `/implement` — the new guard must only trigger for `RUN_ID=unknown` (which `/implement` never passes); implement summaries must stay byte-identical.
- Every changed `.sh` gets its sibling `.md` updated (script-md-siblings rule); every finding gets a regression test.
- Keep the `design-publish.sh` success path (exit 0 + `PUBLISH_OK=true` → `approved` → `[DESIGNED]` rename + reentry marker) intact.
- No behavior change to the normal full-`SESSION_ID` publish flow; all four fixes target failure / edge paths only.
