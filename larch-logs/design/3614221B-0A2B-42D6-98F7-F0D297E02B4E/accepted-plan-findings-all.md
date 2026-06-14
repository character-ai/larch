### FINDING_1: Structure harness pins still require launcher-form design-step2b-postplan.sh
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan replaces launcher postplan fences with `design-step35-settle.sh` in `approval-gates.md` and `discussion-rounds.md` but does not update `scripts/test-design-structure.sh` `assert_reference_updates` pins. Those pins still require launcher-form `design-step2b-postplan.sh` references at the Gate B and discussion-round2 sites. CI / `test-design-structure.sh` can fail even when the new wrapper is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add scripts/test-design-structure.sh to Files to modify/create and retarget pins to design-step35-settle.sh launcher-form references (keep internal postplan mentions only inside settle.md or comments if needed).
  - From Cursor-Innovation: Add scripts/test-design-structure.sh to Files to modify/create and retarget assert_reference_updates to launcher-form design-step35-settle.sh plus retained internal postplan wording
  - From Codex-Requirements: Add scripts/test-design-structure.sh to the plan and update these pins to launcher-form design-step35-settle.sh calls for gate-b and discussion-round2, with separate internal postplan mapping assertions if still needed

### FINDING_2: Double mechanical dedup when settle also runs gate-b-dedup-plan.sh --dedup
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Keeping Shared post-apply pipeline steps 1–5 (including `gate-b-dedup-plan.sh --dedup` at step 5) and then calling `design-step35-settle.sh` (which runs `--dedup` again) double-runs mechanical dedup on every Gate B apply. Today's three prompt-side sites run dedup once before postplan; double dedup adds complexity and can re-trigger trailer validation failures after a successful first pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When settle owns dedup, drop step 5 (and step 6 apply-ready write) from approval-gates prose and keep only snapshot, LLM cleanup, then one settle call; gate-a/discussion-round2 already match that shape.

### FINDING_3: Gate B settle may bind --round-num before STEP3_RESUME_ROUND exists
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-exit-code-compat, Codex-dyn-exit-code-compat
- **Severity**: important
- **Concern**: Proposed Gate B settle uses `--round-num "$STEP3_RESUME_ROUND"` but `STEP3_RESUME_ROUND` is bound later in step 9, after postplan/settle on first apply. On first prompt-side Gate B, `STEP3_RESUME_ROUND` is often empty while `STEP3_REVIEW_ROUND_NUM` or `ROUND_NUM` is set; wrapper invalid-round exit 2 or wrong N markers can follow. Legacy mode and prompt-side apply paths without `STEP3_RESUME_ROUND` can pass an empty round while the wrapper rejects invalid gate-b rounds before writing required markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pass --round-num "${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}" (bind STEP3_RESUME_ROUND from the same expression before step 10) or omit --round-num and rely on the wrapper fallback chain only after validating non-empty N.
  - From Cursor-dyn-exit-code-compat: Use the same round source as current step 6 (`STEP3_REVIEW_ROUND_NUM` / `ROUND_NUM`, with wrapper-side derivation from `FINAL_ROUND_NUM` when `--round-num` is omitted). Bind `STEP3_RESUME_ROUND` later in step 9 unchanged.
  - From Codex-dyn-exit-code-compat: Bind and validate the round before the wrapper call using FINAL_ROUND_NUM then STEP3_REVIEW_ROUND_NUM then ROUND_NUM, or omit --round-num and let the wrapper derive it; keep loop versus legacy continuation branching after rc handling

### FINDING_4: SKILL.md Step 3.5 Gate B prose not updated for settle wrapper
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-resume-idempotency, Codex-dyn-resume-idempotency
- **Severity**: important
- **Concern**: The plan updates Step 1e only; Step 3.5 Gate B optional-trailer guard and Gate B resume idempotency still direct orchestrator dedup and resume at Shared post-apply step 7 (`design-postplan-emit`). After settle lands, `main-agent-apply-required` recovery can still follow stale step-7 postplan prose and skip the consolidated wrapper, breaking pause/rehydration and marker contracts. The Gate B marker-resume branch is not in the planned SKILL.md update: if pause or failure happens after `.gate-b-postapply-ready-N`, existing Step 3.5 resume text still resumes at the old direct postplan step, so wrapper-owned snapshot and phase writes can be skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend SKILL.md updates to Step 3.5: snapshot before rewrite, then design-step35-settle.sh --site gate-b on apply and on apply-ready resume (not raw postplan).
  - From Cursor-dyn-resume-idempotency: Add skills/design/SKILL.md Step 3.5 (687-691) to the plan: snapshot-trailers before rewrite, one design-step35-settle.sh --site gate-b call after rewrite, and resume idempotency that re-enters postplan-only (or settle --skip-dedup) when the apply-ready marker already exists
  - From Codex-dyn-resume-idempotency: Update the Step 3.5 idempotency paragraph too. Route marker resumes through design-step35-settle.sh --site gate-b --round-num "$STEP3_RESUME_ROUND" without reapplying findings, or require that branch to perform the same wrapper-owned snapshot and phase writes.

### FINDING_5: Reference updates use bare design-step35-settle.sh without launcher fence
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `approval-gates.md` and `discussion-rounds.md` updates show bare `design-step35-settle.sh` without the `design-run-$PPID.sh` launcher fence required by SKILL.md anti-pattern #3 and existing reference pins. Prompt-side Bash that calls the script directly bypasses wrapper rehydration and pause-check ordering enforced by `test-design-structure.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and pin "$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site ... in each of the three sites; keep transport wording that the launcher supplies session-env and pause ownership.

### FINDING_6: Pause-save can be misclassified as clean settle when POSTPLAN_RC is absent
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-wrapper-contract, Codex-dyn-wrapper-contract, Codex-dyn-exit-code-compat, Codex-dyn-resume-idempotency
- **Severity**: important
- **Concern**: The planned wrapper captures `design-step2b-postplan.sh` and treats child rc 0 with no `POSTPLAN_RC` as clean. On pause, `design-step2b-postplan.sh` execs `design-pause-save.sh` (rc 11 path or `.pause-requested` check), which exits 0 and emits `PAUSE_OK=true` without `POSTPLAN_RC`. The wrapper can then continue and write Gate B clean markers (`plan-after-round-N.txt`, `.step3-round-N.phase=awaiting-continuation`) after a pause-save instead of stopping at the pause boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the settle wrapper detect delegated pause output such as PAUSE_OK=true or POSTPLAN_EMIT_STATUS=paused and exit immediately before clean settlement, or move the pause checkpoint into the settle wrapper before the captured child call so pause remains terminal.
  - From Codex-Pragmatic: Do not treat missing POSTPLAN_RC as clean for the real postplan wrapper. Require a whole-line POSTPLAN_RC=0 for settle, or explicitly detect PAUSE_OK=true or .pause-save-complete and exit without writing settle markers. Keep any no-POSTPLAN clean allowance limited to an explicit test seam if needed.
  - From Codex-Requirements: Add a pause-save terminal branch to the wrapper contract: clear stale .pause-save-complete before the child call, detect PAUSE_OK=true or .pause-save-complete after printing child output, and stop before clean settle markers or caller continuation; add a focused wrapper pause test
  - From Cursor-dyn-wrapper-contract: On rc 11 design-step2b-postplan.sh execs design-pause-save.sh without emitting POSTPLAN_RC=11; the parent sees child exit 0 and no POSTPLAN_RC line. The planned rule treats that as clean and on gate-b writes plan-after-round-N.txt and .step3-round-N.phase=awaiting-continuation while pause is in flight. Exit 11 when postplan stdout lacks POSTPLAN_RC= before pause-save exec, or treat .pause-save-complete / pause breadcrumb as terminal; never write gate-b settle markers unless POSTPLAN_RC=0 is present.
  - From Codex-dyn-wrapper-contract: Do not treat missing POSTPLAN_RC as clean after a pause-save result; detect PAUSE_OK or .pause-save-complete before clean-settle work, stop without writing settle markers, and add a wrapper pause test
  - From Codex-dyn-exit-code-compat: Require an anchored POSTPLAN_RC=0 for clean settle; treat PAUSE_OK=true as a pause outcome that skips clean marker, snapshot, and phase writes, or add an explicit pause branch before the clean path; make stubs emit POSTPLAN_RC=0
  - From Codex-dyn-resume-idempotency: Make design-step35-settle.sh explicitly own rc 11 or pause detection before the clean fallback. Do not write clean Gate B snapshot or awaiting-continuation when child output shows PAUSE_OK or POSTPLAN_EMIT_STATUS=paused. Write awaiting-post-apply before invoking postplan once the Gate B marker exists.

### FINDING_7: Gate B operator brakes lose awaiting-postplan-operator phase
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan only writes `.step3-round-N.phase=awaiting-continuation` on clean Gate B. Existing operator-brake resumes rely on `awaiting-postplan-operator`. `design-step3-review.sh --postplan-operator-continue` only writes a continue marker, so a non-plan-changing Override or Continue after rc10/13 can re-enter from a stale apply phase and re-run apply/dedup instead of continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: In design-step35-settle.sh, when site=gate-b and postplan emits rc10 or rc13, atomically write .step3-round-N.phase to awaiting-postplan-operator before returning the brake rc. Keep rc0 writing awaiting-continuation. Add one wrapper assertion for this state.

### FINDING_8: Dedup exit 1 revise-again loop dropped in four-arm settle branch
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `design-step35-settle.sh` relays dedup exit 1 unchanged but approval-gates dedup-rc-1 revise-again prose is dropped with only a four-arm settle branch. `gate-b-dedup-plan.sh --dedup` still exits 1 when optional trailer keys or values are lost. After consolidation, trailer-loss rewrite would hard-stop as a generic wrapper failure instead of the current revise-again loop operators rely on for Gate B, Gate A, and discussion Round 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Preserve dedup exit 1 as a distinct orchestrator branch (revise plan.txt and re-call settle) or map trailer-loss to a dedicated settle exit code documented in design-step35-settle.md
  - From Cursor-Requirements: Preserve rc 1 (and document it in `design-step35-settle.md`): relay dedup rc 1 from the wrapper and add an explicit prompt-side branch to re-run the LLM duplicate/trailer rewrite before calling settle again; do not fold rc 1 into the generic abort path.
```

**Merge summary:** 22 source findings collapsed to **8** distinct behavioral risks. Five clusters (structure pins, round binding, SKILL.md Step 3.5, pause misclassification, dedup rc 1) each merged 2–7 slots. Three findings stayed separate (double dedup, launcher fence, `awaiting-postplan-operator`).

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:66-67
- **Concern**: [SCOPE-REDUCTION] Clean gate-b settle writes plan-after-round-N.txt even though issue non-goals forbid reintroducing #4019 HARD-only snapshot sub-steps and no current Shared post-apply site writes that file.. Scenario: This adds new snapshot behavior beyond consolidating the three existing rewrite sites and may revive removed HARD machinery Gate C prose still mentions only historically.
- **Proposed resolution**: Drop plan-after-round-N.txt from wrapper ownership unless a separate Gate C cursor contract is in scope; keep .gate-b-postapply-ready-N and .step3-round-N.phase only where loop/prompt resume already depends on them.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-wrapper-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:14,138-150; skills/design/scripts/design-step2b-postplan.sh:128-133; skills/design/references/discussion-rounds.md:119; skills/design/references/approval-gates.md:154
- **Concern**: [SCOPE-REDUCTION] Scout-manifest clearing is assigned outside the existing postplan owner. Scenario: The plan adds scout-manifest clearing to the new wrapper while design-step2b-postplan.sh already clears it for every non-initial postplan site, and current prompt prose still has a direct clearing instruction
- **Proposed resolution**: Remove wrapper-owned scout clearing and remove prompt-side clearing prose from the rewritten sections; keep design-step2b-postplan.sh as the sole owner for mapped non-initial sites


### FINDING_1: Wrapper exit code 1 conflates dedup revise-again with postplan failure
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned wrapper reserves exit code 1 for dedup “revise again,” but `design-step2b-postplan.sh` also relays unexpected postplan child exit 1 as wrapper exit 1. A `design-postplan-emit` failure can be misread as dedup revise-again instead of operator repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Map unexpected postplan child nonzero without POSTPLAN_RC or pause output to wrapper rc 3 or another non-1 failure; keep rc 1 only for dedup revise-again


### FINDING_2: Gate B apply-ready marker uses `:-current` fallback while settle wrapper requires numeric round
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Gate B apply-ready marker paths still use `STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-current}` in prose (`approval-gates.md` step 6, `SKILL.md` resume idempotency), while the planned `design-step35-settle.sh` derives a validated numeric round (`FINAL_ROUND_NUM` → `STEP3_REVIEW_ROUND_NUM` → `ROUND_NUM`) and fails closed when missing. The wrapper can write `.gate-b-postapply-ready-N` while resume/idempotency probes `.gate-b-postapply-ready-current` or a different suffix, causing double-apply or missed idempotency skip.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require the same round derivation everywhere marker paths are referenced (settle call, resume guard, approval-gates prose): drop the `current` literal and bind one validated numeric `N` before any `.gate-b-postapply-ready-N` / `.step3-round-N.phase` use
  - From Cursor-Innovation: Resume checks for .gate-b-postapply-ready-current while design-step35-settle.sh writes .gate-b-postapply-ready-N; idempotency fails and accepted findings can be applied twice. In the same edit pass, replace every .gate-b-postapply-ready-${...:-current} probe with the wrapper's numeric derivation and fail closed when the round is empty or non-numeric.


### FINDING_3: Settle wrapper must pass `--design-tmpdir` to `gate-b-dedup-plan.sh --dedup`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan calls `gate-b-dedup-plan.sh --dedup` inside `design-step35-settle.sh` but does not require `--design-tmpdir "$DESIGN_TMPDIR"`. `gate-b-dedup-plan.sh` hard-requires that flag; a bare `--dedup` call exits 3 and the wrapper never reaches postplan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and implement dedup as "$DESIGN_STEP35_DEDUP_PLAN_SH" --design-tmpdir "$DESIGN_TMPDIR" --dedup, matching review-design-step3-loop.sh and approval-gates.md.


### FINDING_4: `approval-gates.md` rewrite must retain shared post-apply steps 9–10
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `approval-gates.md` update replaces steps 6–8 with the settle-wrapper branch table but only says to “keep continuation semantics”; it does not explicitly retain steps 9–10 (`STEP3_RESUME_ROUND` bind plus loop-mode vs legacy continuation split). A prose trim can drop those steps while collapsing the seven-arm postplan `case`, breaking loop-mode Gate B resume at the wrong phase or skipping legacy continuation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep steps 9-10 verbatim (or equivalent) after the settle-wrapper branch table, unchanged except for renaming _postplan_rc to _settle_rc where needed.


### FINDING_6: Step 1e Gate A rc 12 must use discussion-round2 Split-path semantics, not generic Step 2b.5
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 1e maps settle/postplan rc 12 to retained Step 2b.5 behavior, but the Gate A postplan site is `discussion-round2`. That site’s hard plan-size brakes use Split-path with Split/Cancel only; routing Gate A rewrites through generic Step 2b.5 can surface Gate B Override semantics and break byte-compatible rc 12 handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Change Step 1e rc 12 branch to match discussion-round2 Split-path semantics (same as rc 13), not generic Step 2b.5



