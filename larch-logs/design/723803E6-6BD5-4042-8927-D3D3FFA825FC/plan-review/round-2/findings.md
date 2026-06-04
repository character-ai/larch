### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:3-17
- **Concern**: /implement admission contract still equates [DESIGNED] with a completed /design run and successful publish. Scenario: After the proposed early rename, operators can see [DESIGNED] while design-log-publish is still running or failed; this contract would still tell them to wait for successful publish/design completion, contradicting the new admission behavior
- **Proposed resolution**: Update the purpose and Exit 5 recovery prose to say [DESIGNED] means Step 5c has written larch:plan and performed the admission rename; log publish recovery is separate and is not an /implement prerequisite when the plan block is present

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:86-90
- **Concern**: Edge-case prose claims a post-failure /design re-invoke on an already-[DESIGNED] title routes to already-planned. Scenario: design-route.sh runs title lifecycle reject before the plan-block verdict (scripts/lib-title-eligibility.sh:12 includes DESIGNED; design-route.sh:263-267 emits cancel-title-filter). Re-invoking /design on a [DESIGNED] issue after log-publish failure is refused, not routed to already-planned — the “no protection gap” rationale is wrong and can mislead recovery (manual rename or log retry, not another /design pass)
- **Proposed resolution**: Revise the Edge cases bullet to state lifecycle title-filter refuse (or manual title edit) instead of already-planned routing; keep the reentry-marker note separate

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1550-1554
- **Concern**: Step 5d failed-publish footer extension is keyed only on PUBLISH_OK=false, not on rename success. Scenario: After the reorder, rename runs before publish. On publish failure with a failed [DESIGNED] rename (driver WARN, RENAMED unset/false), the planned footer still tells operators /implement is unblocked once design-publish.sh has renamed — Preflight still requires [DESIGNED] and will exit 5
- **Proposed resolution**: Qualify the new Step 5d note and Continue block: /implement is admissible only when RENAMED=true (or the issue title is already [DESIGNED]); when rename failed, say fix/retry rename first and do not imply log-publish failure alone blocks admission

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-publish.sh:257-334; scripts/design-log-publish.sh:602-619
- **Concern**: Plan moves the [DESIGNED] rename before design-log-publish, but design-log-publish currently includes the fail-closed secret scrub gate. Scenario: A missing or failing scrub helper makes design-log-publish emit PUBLISH_OK=false, yet the issue has already become [DESIGNED], so /implement can proceed after a security gate refused to flush logs
- **Proposed resolution**: Do not blanket-drop the PUBLISH_OK gate; keep rename publish-gated for scrub/security failures, or add a minimal result signal so design-publish admits only after the scrub gate has passed while still allowing ordinary log-publish failures to avoid blocking implement

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:17
- **Concern**: Missing admission-doc sync leaves recovery text saying [DESIGNED] appears only on successful publish. Scenario: After this PR, a failed design-log publish can still leave the issue [DESIGNED] and admissible, but operators reading this contract may wait or rerun /design unnecessarily
- **Proposed resolution**: Update the missing-designed-prefix recovery sentence to say Step 5c renames after plan and diagram upsert, and log-publish recovery is separate from /implement admission

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:15-18
- **Concern**: Plan leaves stale admission recovery prose saying /design renames to [DESIGNED] on successful publish. Scenario: After this change a failed log publish no longer blocks /implement once the title is [DESIGNED], but this admission doc would still tell operators the rename depends on successful publish
- **Proposed resolution**: Add scripts/implement-admission.md to the doc-only updates and change the recovery sentence to say Step 5c renames after the larch:plan write/diagram upsert; log-publish recovery is separate from admission

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-admission-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-admission.md:17
- **Concern**: Plan syncs /design admission prose but omits implement Preflight admission contract doc. Scenario: After a failed design-log publish, operators following Exit 5 recovery still read that /design renames to [DESIGNED] only on successful publish and may delay /implement despite an early rename
- **Proposed resolution**: Add ### UPDATED: scripts/implement-admission.md — rewrite missing-designed-prefix recovery to Step 5c rename after larch:plan + diagram upsert, not gated on PUBLISH_OK; note log recovery is separate

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-admission-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:3-17
- **Concern**: The plan omits the admission contract doc that still equates [DESIGNED] with a completed /design run and says /design renames only on successful publish. Scenario: After the proposed reorder, a log-publish failure can leave the issue [DESIGNED] with larch:plan present, but this Preflight contract still tells operators that missing [DESIGNED] means no completed design and that rename happens on successful publish
- **Proposed resolution**: Update this doc-only contract in the plan: describe [DESIGNED] as the admission marker after Gate C plus larch:plan write and diagram-upsert attempt; remove the successful-publish/completed-run implication; note log recovery is separate and /implement still separately reads larch:plan.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-harness-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:524-540
- **Concern**: The no-diagram case only asserts upsert is skipped; it never asserts `[DESIGNED]` rename runs when `SESSION_ID` is set. Scenario: An implementer can nest `tracking-issue-write.sh rename --state designed` inside the `_run_upsert` block; happy-path and `PUBLISH_OK=false` ordering tests still pass while no-architecture designs never get `[DESIGNED]` and `/implement` Preflight blocks
- **Proposed resolution**: In `test-design-publish.sh` no-arch case, after the upsert-skip pass, assert `tracking-issue-write` appears in `RENAME_LOG`/`CALL_LOG` and `RENAMED=true` in `.design-publish-result.env` (and optionally `rename_pos < publish_pos` when upsert line is absent)

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-harness-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-publish.sh:246-257; scripts/test-design-structure.sh:1326-1331
- **Concern**: Proposed order pins use first rename occurrence and do not prove the old publish-gated rename block was removed. Scenario: A copy-not-move implementation can produce plan→upsert→rename→publish→rename→marker; first-position greps still pass, PUBLISH_OK=false still sees a rename, but happy-path runs keep an extra GitHub rename and may corrupt RENAMED semantics on real idempotent second calls
- **Proposed resolution**: Add one minimum assertion that exactly one designed rename runs, e.g. count tracking-issue-write in CALL_LOG/RENAME_LOG on happy path and/or count one tracking-issue-write.sh rename --state designed structural occurrence

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-harness-parity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:15-17
- **Concern**: Plan omits stale implement admission recovery prose that still ties [DESIGNED] rename to successful publish. Scenario: After the change, /implement can proceed after plan, diagram upsert, and [DESIGNED] rename even when log publish failed; this contract text would still tell operators the rename happens on successful publish
- **Proposed resolution**: Update the single recovery sentence to say /design renames to [DESIGNED] after Gate C plan write/diagram upsert, and log-publish recovery is separate from admission

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-operator-recovery
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1550-1554 skills/design/scripts/render-final-summary.sh:300-315
- **Concern**: Planned failed-publish operator copy treats /implement as unblocked whenever PUBLISH_OK=false, without requiring RENAMED=true. Scenario: After the reorder, rename runs before publish. If tracking-issue-write fails (RENAMED=false) and design-log-publish also fails, Step 5d and append_failed_publish_notes would still say /implement may proceed once [DESIGNED] is set, but the title is often still [DESIGNING]; operators retry /implement, hit missing-designed-prefix, or assume design is done
- **Proposed resolution**: Qualify Step 5d blockquote and the new failed-publish bullet on RENAMED=true (or title already [DESIGNED]); when RENAMED=false, point to the rename WARN and manual rename / re-invoke /design instead of implying admission is ready

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-operator-recovery
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/implement-admission.md:15-17
- **Concern**: The plan updates design-side failed-publish/admission prose but leaves /implement admission recovery docs saying [DESIGNED] is applied "on successful publish".. Scenario: After the PR, a design-log publish failure can occur after the title was already renamed and the larch:plan block written; this contract text still ties the [DESIGNED] transition to publish success and can make an operator wait or rerun /design instead of starting /implement when admission would pass.
- **Proposed resolution**: Add a small docs-only update to scripts/implement-admission.md line 17: say Step 5c renames to [DESIGNED] after the plan/diagram write and before log publish when SESSION_ID is present; log publish success is not required for /implement admission, while a rename failure still requires re-running /design or manually renaming before retrying /implement.
