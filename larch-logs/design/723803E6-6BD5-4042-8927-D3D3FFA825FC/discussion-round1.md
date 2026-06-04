## Decision 1: Move the [DESIGNING]→[DESIGNED] rename earlier
- **Question**: Where should the title rename to [DESIGNED] happen in design-publish.sh?
- **Resolution**: Move the `tracking-issue-write.sh rename --state designed` call to **right after the architecture-diagram upsert**, and **drop the `PUBLISH_OK == true` gate**. Keep the existing `[ -n "$SESSION_ID" ]` guard (preserves the documented SESSION_ID-empty skip behavior; SESSION_ID is always non-empty in real runs). The rename now runs **before** `design-log-publish.sh`.
- **Source**: issue #3482 + user

## Decision 2: Logs need not be published before /implement picks up
- **Question**: Is it acceptable that the design-log PR is not yet published/merged when an /implement run could pick up this issue?
- **Resolution**: Yes — this is the explicit intent/optimization. The earlier `[DESIGNED]` admission is the whole point.
- **Source**: user

## Decision 3: Log-flush failure must never affect /implement
- **Question**: Should a log-flush failure (or never-merged logs PR) be able to prevent or affect /implement's ability to proceed?
- **Resolution**: No, never. Because the rename now happens before publish and is no longer gated on PUBLISH_OK, a later `design-log-publish.sh` failure leaves the issue at `[DESIGNED]` and /implement is wholly unaffected. The rename must not be rolled back, re-gated, or reverted on publish failure.
- **Source**: user

## Decision 4: design_reentry_marker_write stays gated on publish success
- **Question**: The reentry marker (a `/design`-only 5-minute spurious-re-invocation guard, keyed on issue+pid) is currently bundled in the same `if SESSION_ID && PUBLISH_OK==true` block as the rename. Move only the rename, or move the marker too?
- **Resolution**: Move **only** the rename. Leave `design_reentry_marker_write` where it is — after publish, still gated on `SESSION_ID` non-empty AND `PUBLISH_OK==true`. The marker is irrelevant to /implement and to the logs decoupling; even on publish failure (no marker written) a spurious `/design` re-run is still caught by the already-planned route (title is `[DESIGNED]`, `larch:plan` present). Minimal change, least test churn. User delegated the call ("you know my goals").
- **Source**: user (delegated) + codebase

## Decision 5: Scope is design-publish.sh + its contract/tests/SKILL prose only
- **Question**: What is in-scope vs out-of-scope?
- **Resolution**: In scope: reorder the rename in `skills/design/scripts/design-publish.sh`; update its contract `design-publish.md` (ordering invariant + responsibilities), the harness `test-design-publish.sh`, the structural pin `scripts/test-design-structure.sh`, and the stale SKILL.md prose (Step 5c item 6 "rename gated on PUBLISH_OK"; Step 5c item 4 responsibilities order). Out of scope: any `/implement` change (it only keys on the title), the publish/security model (`gh pr merge --admin` unchanged → no SECURITY.md change), the clarify-path `--state designing` rename (different lifecycle token), and Step 6 cleanup gating (still correctly gated on PUBLISH_OK).
- **Source**: codebase + user
