### FINDING_1: Retire stale stdout-KV merge structure pin
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still pins the legacy stdout KV merge heredoc, which conflicts with the thin-fence migration and can fail lint/tests even when the new behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit retirement/repoint of the `contains "$SKILL_MD" '<<<"${_postplan_out:-}"'` assertion in the `### UPDATED: scripts/test-design-structure.sh` section (alongside the named `(14c14e)` / `(14c14h)` retirements); replace with thin-fence pins such as `--with-plan-size`, `echo "$out"`, and rc `case` dispatch without stdout KV merge
  - From Cursor-Requirements: Retire pin 517 explicitly; replace with a merged-fence pin that forbids stdout KV merge loops (as the plan already proposes for new pins)

### FINDING_2: Do not pass --repo to design-postplan-emit.sh without parser support
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan requires `${REPO:+--repo "$REPO"}` on merged `design-postplan-emit.sh` calls, but the script’s parser does not accept `--repo`, so implementers following the pin would get rc2 before thin-fence rc handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep repo threading on the prelude and rc11 design-pause-save.sh exec arms only, and pin that design-postplan-emit.sh invocations do not receive --repo unless the plan also adds and documents a real --repo parser contract

### FINDING_3: Step 2b pause-save repo threading and thin-fence scoping are inconsistent
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: Step 2b entry/timing `design-pause-save.sh` calls omit `${REPO:+--repo "$REPO"}` while structure pins or helper assumptions may require it, causing false failures or missed regressions around the Step 2b thin fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Thread `${REPO:+--repo "$REPO"}` on every Step 2b pause-save line in that region (timing guard and thin-fence prelude), not only on `design-postplan-emit.sh` / rc11 arms
  - From Cursor-Innovation: make test-design-structure fails on Step 2b thin-fence pin, or implementers drop the pin to unblock CI Narrow the pin to a sub-region containing only the merged driver fence (new HTML markers), extend assert_thin_fence with a Step-2b mode that skips the classification ordering check, or add REPO to Step 2b prelude pause-save lines in the pinned region

### FINDING_4: Plan-size rc2/rc3 warning path can abort on append-tool-failure.sh failure
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The plan declares plan-size rc2/rc3 nonfatal, but if `append-tool-failure.sh` itself exits nonzero under `set -e`, the promised warning-and-continue path can abort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Wrap the append call in set +e or || true, redirect its stdout/stderr, then always emit the WARN and exit 0 for plan-size rc2/rc3; add a failing-append regression

### FINDING_5: --with-plan-size needs fail-closed result-env write handling
- **Reviewer(s)**: Codex-Edge, Codex-dyn-exit-code-mapper, Codex-dyn-kv-display-boundary
- **Severity**: important
- **Concern**: Merged `--with-plan-size` mode disables stdout KV fallback but does not specify fatal behavior when the result env file cannot be safely written, risking stale/missing context for rc10/12/13/0 handlers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In --with-plan-size, make result-env write failure a specific rc1 diagnostic before any action rc that needs context, or provide another safe non-KV handoff; include a symlink/write-failure test
  - From Codex-dyn-exit-code-mapper: In --with-plan-size, treat result-env write failure as rc1 with a clear diagnostic before any action rc; keep non-flag stdout fallback unchanged and add a symlink/unwritable result-env test.
  - From Codex-dyn-kv-display-boundary: In --with-plan-size, treat result-env write refusal/failure as rc1 with a display diagnostic and no stdout KVs; add a symlink/write-failure test in test-design-postplan-emit.sh and document the rc1 status in design-postplan-emit.md

### FINDING_6: Step 1e and discussion-round2 conflict on --force-validate
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic, Codex-dyn-exit-code-mapper, Codex-dyn-doc-topology-sync
- **Severity**: important
- **Concern**: The same post-discussion Gate A rewrite path is specified with conflicting argv: Step 1e omits `--force-validate`, while discussion-round2 keeps it, risking skipped validation in quick-budget discussion rewrites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Clarify the split or collapse to one owner: if plan.txt was revised by post-plan discussion, make both files specify the same argv and pin only that canonical path
  - From Codex-Pragmatic: Do not pin no --force-validate on the discussion rewrite path; either align the SKILL.md Step 1e discussion-rewrite fence with discussion-round2 --with-plan-size --force-validate, or split/delete the duplicate SKILL guard so only a truly non-discussion Gate A path uses no-force.
  - From Codex-dyn-exit-code-mapper: Clarify the split: either make the Step 1e after-discussion rewrite use --with-plan-size --force-validate, or identify a separate non-discussion Step 1e rewrite site and remove the current “after discussion (per discussion-rounds.md)” overlap.
  - From Codex-dyn-doc-topology-sync: Keep one contract for this path. Minimum change: make the Step 1e optional-trailer re-entry rewrite defer to the discussion-round2 argv and pin --with-plan-size --force-validate, or explicitly split and rename any truly non-discussion Gate A rewrite site before pinning a no-force argv.

### FINDING_7: plan-review-loop still misses partition_requested handoff
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-exit-code-mapper
- **Severity**: important
- **Concern**: The retained `plan-review-loop.sh` path only branches on hard size triggers, so `/design --partition` can auto-revise a clean small plan and proceed without the required Split-path handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the change local: in the plan-review-loop size block, read partition_requested from run-params.json with the same boolean fallback and surface the existing plan-size-trigger handoff when true and hard is false; add one harness case for that path
  - From Codex-dyn-exit-code-mapper: In plan-review-loop.sh, after the hard parse, read partition_requested with the same boolean-safe fallback and surface the retained Step 2b.5 handoff when hard=false and partition_requested=true; add a focused harness case.

### FINDING_8: Retire stale Step 2b inline check-plan-size structure pin
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-doc-topology-sync
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still requires an inline `check-plan-size.sh` call after `design-postplan-emit.sh` in Step 2b, which conflicts with collapsing Step 2b into merged `--with-plan-size` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-doc-topology-sync: Repoint or drop FINDING_21 lines 689-695 in the same test-design-structure.sh pass (e.g. require --with-plan-size on design-postplan-emit.sh and/or assert_thin_fence for <!-- step:2b through <!-- step:3)

### FINDING_9: Step 3 plan-size-trigger caller lacks site-aware Override prompt coverage
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The retained Step 3 `LOOP_STATUS=plan-size-trigger` caller is not included in the site-aware hard-prompt bucket, even though its Step 2b.5 flow requires Split/Override/Cancel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend site-aware Step 2b.5 prose and structure pins so Step 3 plan-size-trigger uses the Override-capable prompt set

### FINDING_10: Step 2b fat guards preempt rc10/11/12/13 dispatch
- **Reviewer(s)**: Cursor-dyn-exit-code-mapper
- **Severity**: important
- **Concern**: Existing post-driver mandatory-key, `VALIDATE_STATUS`, and generic nonzero guards can run before the intended thin `case` dispatch, preventing rc10/11/12/13 from reaching their handlers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-exit-code-mapper: Replace the Step 2b fence with echo-then-case only: drop stdout KV merge and the rc 0/1 mandatory-key gate for merged `--with-plan-size` calls; route defects via rc 10 (not `VALIDATE_STATUS` after rc 0); handle 11/12/13 before the generic `ne 0` abort

### FINDING_11: Initial rc12/rc13 Split path must preserve step-2b sentinel lifecycle
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle, Codex-dyn-sentinel-lifecycle
- **Severity**: important
- **Concern**: The merged rc12/rc13 Split Refine path only requires `.completed/step-2b.5`, but legacy initial flow writes `.completed/step-2b` before Step 2b.5; missing it can make pause/resume replay Step 2b instead of continuing correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-lifecycle: Write `.completed/step-2b` on merged rc12/rc13 Split entry (after successful emit/validate, before Split-path), matching legacy `SKILL.md:973` timing; keep Refine-return `step-2b.5` touch. Pin Split-entry `step-2b` in `test-design-structure.sh` sentinel pins, not only Refine-return `step-2b.5`
  - From Codex-dyn-sentinel-lifecycle: Add an initial-site Split Refine-return instruction to write .completed/step-2b before or with .completed/step-2b.5

### FINDING_12: Merged rc12/rc13 display ownership conflicts with Step 2b.5 prose
- **Reviewer(s)**: Cursor-dyn-kv-display-boundary
- **Severity**: important
- **Concern**: The plan moves hard/partition/soft-advisory display into `design-postplan-emit.sh --with-plan-size` FD3 output, but Step 2b.5 still tells the orchestrator to print those sections, risking duplicated or omitted plan-size display.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-display-boundary: Merged rc12/rc13 arms that still run Step 2b.5 §4–§6 after the thin fence will duplicate plan-size sections (or, if only the rc arm runs, omit driver-emitted headers the procedure no longer supplies) In `skills/design/SKILL.md`, state that merged fences must not call Step 2b.5 steps 4–6 after `echo "$out"`; rc12/13 only run the AskUserQuestion/Split-path arms. Scope standalone Step 2b.5 to Override, `LOOP_STATUS=plan-size-trigger`, and other retained callers
