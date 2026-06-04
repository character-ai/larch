### FINDING_1: Implement admission docs still tie [DESIGNED] to successful publish
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-admission-contract, Codex-dyn-admission-contract, Codex-dyn-harness-parity, Codex-dyn-operator-recovery
- **Severity**: important
- **Concern**: `scripts/implement-admission.md` remains stale after the planned reorder: it still implies `[DESIGNED]` means a completed `/design` run and successful log publish, even though the new behavior can make `/implement` admissible after plan write/diagram upsert/rename while log publish fails separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the purpose and Exit 5 recovery prose to say [DESIGNED] means Step 5c has written larch:plan and performed the admission rename; log publish recovery is separate and is not an /implement prerequisite when the plan block is present
  - From Codex-Pragmatic: Update the missing-designed-prefix recovery sentence to say Step 5c renames after plan and diagram upsert, and log-publish recovery is separate from /implement admission
  - From Codex-Requirements: Add scripts/implement-admission.md to the doc-only updates and change the recovery sentence to say Step 5c renames after the larch:plan write/diagram upsert; log-publish recovery is separate from admission
  - From Cursor-dyn-admission-contract: Add ### UPDATED: scripts/implement-admission.md — rewrite missing-designed-prefix recovery to Step 5c rename after larch:plan + diagram upsert, not gated on PUBLISH_OK; note log recovery is separate
  - From Codex-dyn-admission-contract: Update this doc-only contract in the plan: describe [DESIGNED] as the admission marker after Gate C plus larch:plan write and diagram-upsert attempt; remove the successful-publish/completed-run implication; note log recovery is separate and /implement still separately reads larch:plan.
  - From Codex-dyn-harness-parity: Update the single recovery sentence to say /design renames to [DESIGNED] after Gate C plan write/diagram upsert, and log-publish recovery is separate from admission
  - From Codex-dyn-operator-recovery: Add a small docs-only update to scripts/implement-admission.md line 17: say Step 5c renames to [DESIGNED] after the plan/diagram write and before log publish when SESSION_ID is present; log publish success is not required for /implement admission, while a rename failure still requires re-running /design or manually renaming before retrying /implement.

### FINDING_2: Edge-case prose misstates /design re-entry behavior on [DESIGNED] issues
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan says re-invoking `/design` on an already-`[DESIGNED]` issue after log-publish failure routes to already-planned, but the current route order rejects lifecycle titles before plan-block verdict, so recovery guidance is wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Revise the Edge cases bullet to state lifecycle title-filter refuse (or manual title edit) instead of already-planned routing; keep the reentry-marker note separate

### FINDING_3: Failed-publish operator copy ignores rename failure
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-operator-recovery
- **Severity**: important
- **Concern**: The planned failed-publish messaging is keyed only on `PUBLISH_OK=false`, so if the early `[DESIGNED]` rename also failed, operators may be told `/implement` is unblocked even though Preflight still requires the `[DESIGNED]` title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Qualify the new Step 5d note and Continue block: /implement is admissible only when RENAMED=true (or the issue title is already [DESIGNED]); when rename failed, say fix/retry rename first and do not imply log-publish failure alone blocks admission
  - From Cursor-dyn-operator-recovery: Qualify Step 5d blockquote and the new failed-publish bullet on RENAMED=true (or title already [DESIGNED]); when RENAMED=false, point to the rename WARN and manual rename / re-invoke /design instead of implying admission is ready

### FINDING_4: Early rename may bypass fail-closed secret scrub gate
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Moving the `[DESIGNED]` rename before `design-log-publish` can allow `/implement` to proceed even when the log-publish path refused due to the fail-closed secret scrub gate, weakening the security gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Do not blanket-drop the PUBLISH_OK gate; keep rename publish-gated for scrub/security failures, or add a minimal result signal so design-publish admits only after the scrub gate has passed while still allowing ordinary log-publish failures to avoid blocking implement

### FINDING_5: No-architecture publish test does not prove rename still runs
- **Reviewer(s)**: Cursor-dyn-harness-parity
- **Severity**: important
- **Concern**: The no-diagram/no-architecture test only checks that upsert is skipped, so an implementation could accidentally put the `[DESIGNED]` rename inside the upsert block and block `/implement` for no-architecture designs without tests failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-parity: In `test-design-publish.sh` no-arch case, after the upsert-skip pass, assert `tracking-issue-write` appears in `RENAME_LOG`/`CALL_LOG` and `RENAMED=true` in `.design-publish-result.env` (and optionally `rename_pos < publish_pos` when upsert line is absent)

### FINDING_6: Harness does not prevent duplicate designed rename calls
- **Reviewer(s)**: Codex-dyn-harness-parity
- **Severity**: important
- **Concern**: The proposed ordering assertions use the first rename occurrence, so a copy-not-move implementation could leave an extra old publish-gated rename in place while tests still pass, causing duplicate GitHub rename attempts and confusing `RENAMED` semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-parity: Add one minimum assertion that exactly one designed rename runs, e.g. count tracking-issue-write in CALL_LOG/RENAME_LOG on happy path and/or count one tracking-issue-write.sh rename --state designed structural occurrence
