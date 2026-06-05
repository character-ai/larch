Normalized merge of 22 reviewer inputs into 11 distinct findings (same behavioral risk merged; different fixes or code paths kept separate).

### FINDING_1: HARD zero-sketch path may never write `step-2a`
- **Reviewer(s)**: Cursor-Arch, Codex-dyn-sentinel-ordering, Cursor-dyn-test-harness-gaps
- **Severity**: important
- **Concern**: The plan folds `step-2a` into the Step 2a.5 prelude host, but the HARD zero-sketch path skips Step 2a.5 and jumps to Step 2b. Item 6 retires the Step 2a success-boundary `: > step-2a` write in favor of the 2a.5-hosted write; only `step-2a.5` may be re-touched at the Step 2b prelude. On both-tools-down zero-sketch, `step-2a` may never be created while `assert_folded_sentinel_writes` still expects it in the 2a.5 fence, leaving pause-save able to route back before the completed sketch phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit step-2a write on the zero-sketch branch (skills/design/SKILL.md:699) or in the Step 2b prelude; extend assert_folded_sentinel_writes to accept that alternate host when the skip prose is present
  - From Codex-dyn-sentinel-ordering: Add an explicit zero-sketch degraded-path instruction to write mkdir -p "$DESIGN_TMPDIR/.completed" and : > "$DESIGN_TMPDIR/.completed/step-2a" before jumping to Step 2b, while keeping the normal HARD path folded into Step 2a.5
  - From Cursor-dyn-test-harness-gaps: Add an explicit `step-2a` host for that branch (e.g. also write `step-2a` in the Step 2b prelude, or keep a zero-sketch-only sentinel write in the existing no-sketches prose path)

### FINDING_2: Step 0c combined Bash fence omits env-source contract
- **Reviewer(s)**: Cursor-Arch, Codex-Edge
- **Severity**: important
- **Concern**: The proposed Step 0c combined Bash call does not specify sourcing the current design env before using `DESIGN_TMPDIR` and `CLAUDE_PLUGIN_ROOT`. A fresh Bash subshell does not preserve Step 0b variables, so the new step-0c plus discussion-block timing fence can fail on unset `DESIGN_TMPDIR`, skip pause handling at the first post-setup driver boundary, or write to the wrong path before Step 1c starts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify the fence as source-env, optional pause-check, then step-0c write and the block timing mark (mirror other driver fences)
  - From Codex-Edge: Start the Step 0c fence by sourcing ~/.cache/larch/sessions/current-design-env-$PPID.sh before the mkdir and timing-ledger lines

### FINDING_3: Missing `step-1d.7` sentinel breaks pause-save ordering
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan leaves step-1d.7 sentinel-less while pause-save still treats 1d.7 as an ordered resumable step. After a folded host writes later sentinels such as `step-2a` and then honors a pause, `design-pause-save` scans the registry, finds missing `step-1d.7` before `step-2a`/`step-2a.5`, records `STEP=1d.7`, and resume can route back through outline handling instead of the intended forward boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add .completed/step-1d.7 to the folded/boundary writes before the Step 2a pause-check, or remove 1d.7 from the pause registry and update the pause tests; also include 1d.7 in the new folded-sentinel assertion so the contract is enforced

### FINDING_4: Step 5c fold may break Check 15b grep substring
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Step 5c fold drops a pinned Check 15b prose substring. Item 17 moves `step-5c` into the `design-publish.sh` fence and rewrites item 6 prose; Check 15b still greps for the exact backtick string ``: > "$DESIGN_TMPDIR/.completed/step-5c"` **only when** `PLAN_WRITE_OK=true`'' in `SKILL.md`. A literal follow of the plan can pass the new `assert_folded_sentinel_writes` checks yet fail `make test-design-structure` / `relevant-checks.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Keep that exact substring in Step 5c item-6 prose (even when the write is in-fence), or extend the plan to update the Check 15b grep to match the in-fence `if [[ "${PLAN_WRITE_OK:-}" == true ]]` block

### FINDING_5: Folding `step-5b` into Step 5c removes last pause boundary before publish
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Folding `step-5b` into the Step 5c publish fence removes the last pause boundary before `design-publish.sh`. When `.pause-requested` is set after OOS filing but before publish, the proposed no-pause Step 5c fence still proceeds to write the plan block, publish logs, and possibly rename the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Keep the step-5b sentinel as a standalone boundary, or add an explicit pause-check before design-publish.sh after writing step-5b if that fence becomes the host

### FINDING_6: `step-5b` in Step 5c fence self-satisfies OOS precondition
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan moves `.completed/step-5b` into the Step 5c publish fence, self-satisfying `design-publish.sh`'s OOS precondition. If orchestration or resume reaches Step 5c with Step 5b not actually settled, the proposed fence creates the sentinel and publish proceeds instead of `design-publish.sh` refusing before plan publication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the step-5b sentinel at the Step 5b boundary, or fold it into Step 5b's own final settled branches, not into the Step 5c publish fence

### FINDING_7: `step-6` placement conflicts with before-pause folded-write ordering rule
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-test-harness-gaps, Codex-Requirements, Cursor-dyn-sentinel-ordering, Codex-dyn-sentinel-ordering
- **Severity**: important
- **Concern**: The plan's generic rule requires every folded sentinel in a pause-bearing host fence to appear after source-env and before `design-pause-save.sh`, but Step 6 item 19 places `step-6` after the pause-check and immediately before `cleanup-tmpdir.sh` (intentional so pause before cleanup does not mark step-6 complete). Implementing both the plan and `assert_folded_sentinel_writes` forces `step-6` before the pause boundary, breaking documented cleanup-boundary semantics and reintroducing failure mode 1 (resume skips cleanup), or CI fails even when `SKILL.md` matches item 19.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Exempt step-6 from the before-pause ordering check or assert step-6 after design-pause-save.sh and before cleanup-tmpdir.sh instead
  - From Cursor-Pragmatic: Exempt the cleanup-tmpdir.sh host from the before-pause ordering rule (or assert step-6 after pause-check and before cleanup-tmpdir.sh only); document step-6 as the sole deliberate exception in the audit table and failure-mode mitigation text
  - From Cursor-Requirements: Special-case `step-6` in `assert_folded_sentinel_writes`: require the literal after pause-check and before `cleanup-tmpdir.sh`; keep before-pause ordering for all other absorbed sentinels
  - From Codex-dyn-test-harness-gaps: Special-case `step-6` in `assert_folded_sentinel_writes`: require the literal after pause-check and before `cleanup-tmpdir.sh`; keep before-pause ordering for all other absorbed sentinels
  - From Codex-Requirements: Special-case step-6 in assert_folded_sentinel_writes: require it after the pause-check and before cleanup-tmpdir.sh, while keeping before-pause ordering for absorbed prior-step sentinels.
  - From Cursor-dyn-sentinel-ordering: CI fails on the cleanup fence even when SKILL.md matches item 19, or an implementer "fixes" red CI by moving step-6 before pause-check and reintroduces failure mode 1 (resume skips cleanup). Exempt step-6 from the before-pause line-order rule in assert_folded_sentinel_writes (only require the literal in the cleanup-tmpdir fence), or assert step-6 is after pause-check and before cleanup-tmpdir.sh; align item 2 / the audit table with that exception.
  - From Codex-dyn-sentinel-ordering: Move the step-6 mkdir and redirection to immediately after the source-env line and before the pause-check in the cleanup fence, or explicitly remove Step 6 from the invariant and folded-write assertion

### FINDING_8: Indented `design-publish.sh` fence not reachable by `extract_first_bash_fence_after`
- **Reviewer(s)**: Codex-Innovation, Cursor-Requirements, Codex-Requirements, Codex-dyn-test-harness-gaps
- **Severity**: important
- **Concern**: The planned folded-sentinel test reuses `extract_first_bash_fence_after`, which only matches unindented `` ```bash `` fences and has no contained-token mode. The Step 5c `design-publish.sh` fence is indented inside a numbered list (`skills/design/SKILL.md:1446`), so a host lookup after `### 5c` returns the Step 6 cleanup fence instead. The new `step-5b` and `step-5c` assertions either cannot find the host fence and fail CI, or skip the only publish-hosted folded writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: For the new assertion, add a minimal extractor that accepts optional leading whitespace around ```bash/``` or special-case the design-publish fence search before checking the two sentinel writes
  - From Cursor-Requirements: Add a token-scoped extractor that accepts indented fence delimiters (or un-indent the publish fence) and use it for the `design-publish.sh` host pair only
  - From Codex-Requirements: Add a small fence extractor that accepts optional leading spaces and can locate a bash fence by contained token; use it for the design-publish.sh folded-write checks.
  - From Codex-dyn-test-harness-gaps: Add a small token-containing fence extractor that accepts optional leading spaces on fence delimiters, and use it for step-5b/step-5c; leave extract_first_bash_fence_after for the simple unindented step-anchor hosts.

### FINDING_9: `assert_step2a_entry_simple_guard` left unchanged after sentinel relocation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan moves `.completed/step-2a` and `step-2a.5` out of the Step 2a entry fence but leaves `assert_step2a_entry_simple_guard` unchanged. Implementing items 6–8 removes the literals that guard requires inside the SIMPLE branch of the first fence after `<!-- step:2a —`; `make test-design-structure` fails while `SKILL.md` prose still claims the entry fence is the primary marker site.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Update the harness (and anti-pattern #1 / SIMPLE skip prose) so artifacts stay pinned in the Step 2a entry guard while `step-2a` is asserted in the `### 2a.5` prelude fence and `step-2a.5` in the Step 2b prelude fence; drop the “unchanged” claim on line 61

### FINDING_10: Stale SIMPLE routing and edge-case prose after sentinel relocation
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Edge-case text and multiple SIMPLE routing sites still say Step 2a entry writes `step-2a` / `step-2a.5` in one turn after items 6–8 relocate those writes. Resume/skip prose and anti-pattern #1 can mislead the orchestrator on SIMPLE fresh runs and paused repair even if fences are edited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Align edge-case § SIMPLE fresh run with the 2a.5 / 2b host-fence contract and update anti-pattern #1, § SIMPLE branch, § 2a.2, and the 2a.5 skip note to name the new write sites

### FINDING_11: Restored `.pause-requested` causes immediate re-pause at Step 2a
- **Reviewer(s)**: Codex-dyn-resume-routing-audit
- **Severity**: important
- **Concern**: The plan relies on unchanged pause/load, but pause snapshots keep `.pause-requested`. After the proposed Step 2a fence writes `step-1c`, `step-1d`, `step-1d.5`, and `step-1e` before the pause-check, `design-pause-save` publishes the snapshot before removing `.pause-requested`. `design-log-publish` includes `.pause-requested` for `--reason pause`, and `design-pause-load` restores it without clearing. Resume can route through 1d.7 via `.outline-approved`, but Step 2a then immediately sees the restored `.pause-requested` and pauses again instead of continuing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-resume-routing-audit: Keep the routing fold, but add the minimum pause-resume fix: clear .pause-requested after a successful restore in design-pause-load.sh, or exclude it from pause snapshots for --reason pause. Add a focused pause-resume harness case for four discussion sentinels plus .outline-approved so the resume reaches Step 2a once instead of re-pausing.
