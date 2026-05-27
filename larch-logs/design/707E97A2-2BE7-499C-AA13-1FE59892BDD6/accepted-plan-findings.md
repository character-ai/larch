### FINDING_1: Resume preflight is not an early terminal rehydration path
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Resume detection/load is placed too late and, after LOAD_OK, does not fully rebind restored run state or short-circuit the rest of Step 0b. Paused `[DESIGNING]` issues can be rejected before load, or resumed runs can re-enter clarify/tier/run-param flows and publish under a new run ID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When LOAD_OK=true after 0b.6 skip 0b.3-6 jump to STEP and refresh write-design-current-env from restored KV only
  - From Cursor-Edge: Insert 0b.6 immediately after issue fetch (sub-step 2) and before sub-step 2.5, or add an explicit bypass in 2.5 when <!-- larch:design-pause:start --> is present (DESIGNING only)
  - From Codex-Edge: Move pause-marker detection before lifecycle rejection, or add a narrowly scoped title-filter bypass when larch:design-pause is present and design-pause-load succeeds
  - From Cursor-Innovation: Specify that 0b.6 runs in a dedicated bash fence immediately after title filter; on LOAD_OK=true skip 0b.3-0b.6 and jump to STEP routing; add harness asserting clarify/tier are not re-entered when marker was present
  - From Cursor-Pragmatic: Exempt [DESIGNING] when design-pause marker present, or run resume detection before 2.5 lifecycle-reject
  - From Cursor-Pragmatic: On LOAD_OK=true skip 0b sub-steps 3-6 and jump to STEP per stdout
  - From Cursor-Pragmatic: After load set SESSION_ID/RUN_ID from marker; pass --run-id on 0a when resuming; refresh source-env
  - From Cursor-Requirements: On LOAD_OK=true: restore into $DESIGN_TMPDIR, re-export SESSION_ID/RUN_ID/TIER/BRAINSTORM_DONE from marker, re-run write-design-current-env.sh, skip 0b items 3-6, then branch to STEP


### FINDING_2: Loader relies on unsupported remote archive transport
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned loader uses `git archive --remote` against GitHub-style remotes, which commonly do not support upload-archive. Resume can fail even when the snapshot branch exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Use git fetch then git checkout or git show ref path into DESIGN_TMPDIR per existing repo patterns
  - From Cursor-Pragmatic: Fetch recovery/default ref locally then git archive from local object
  - From Codex-Pragmatic: Fetch the branch/ref locally, then archive or checkout from FETCH_HEAD or refs/remotes/origin/<branch>; test against a non-file remote stub path, not only a local repository


### FINDING_3: Snapshot restore extracts the wrong directory shape
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Load extraction restores `larch-logs/design/<RUN_ID>/...` under the fresh tmpdir instead of placing files like `run-params.json` and `plan.txt` at `$DESIGN_TMPDIR` root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After fetch copy or strip-components=3 from archive tree into DESIGN_TMPDIR root
  - From Codex-Arch: Archive from branch:larch-logs/design/<RUN_ID>/ or extract with the correct --strip-components count, then assert required restored files before LOAD_OK=true
  - From Codex-Edge: Extract with component stripping, e.g. tar -x -C "$DESIGN_TMPDIR" --strip-components=3 after archiving larch-logs/design/<RUN_ID>, and cover this in the round-trip harness
  - From Codex-Innovation: Extract with `tar --strip-components=3 -C "$DESIGN_TMPDIR"` or archive from inside the run directory, and assert the load harness checks restored files at the tmpdir root.
  - From Cursor-Pragmatic: Strip prefix on extract or copy archived files to DESIGN_TMPDIR root after tar
  - From Cursor-Requirements: Archive/extract with strip-components=3 (or publish a flat bundle) and add harness assertions on restored root paths
  - From Codex-Requirements: Archive the contents with path rewriting or extract with the correct strip-components behavior, then assert required root files such as plan.txt/run-params.json/pause-state.txt exist before deleting the marker


### FINDING_4: Pause helpers do not thread tmpdir and repo identity
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: The pause save/load contract does not consistently accept `--design-tmpdir` and `--repo`, so fresh resume tmpdirs and forked/nested repository contexts can target the wrong paths or GitHub issue repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement --design-tmpdir required optional --repo mirror design-pause-save
  - From Codex-Arch: Add --repo to design-pause-save.sh and design-pause-load.sh, pass it through to named-block-write.sh, gh issue view, and design-log-publish.sh, and have SKILL.md resolve REPO before pause save/load


### FINDING_6: Pause-save stdout contract is underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Failure modes mention parseable pause-save output, but the new script contract does not define `PAUSE_OK` and `ERROR` lines consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Align design-pause-save.md with PAUSE_OK ERROR KV lines matching failure modes section
  - From Cursor-Requirements: Document and emit PAUSE_OK=true|false plus ERROR= on design-pause-save.sh stdout mirroring PUBLISH_OK patterns


### FINDING_7: Resume step selection must follow registry order
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: Picking the lexicographically smallest missing step can choose the wrong pause boundary when registry order differs from string sort order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Walk step-name-registry.tsv in file order pick first missing step-id sentinel


### FINDING_8: Step registry coverage is incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-step-registry-coverage, Codex-dyn-step-registry-coverage
- **Severity**: important
- **Concern**: The registry omits pauseable steps/substeps such as 0c and Step 5 finalization substeps, so save/resume can route past unfinished work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit 0c row plan currently leaves conditional
  - From Cursor-dyn-step-registry-coverage: Add `5b`, `5c`, and (if pausable) `5d` rows; write `touch "$DESIGN_TMPDIR/.completed/step-<id>"` at each sub-step entry Bash block, not only the Step 5 timing fence at :895-897
  - From Codex-dyn-step-registry-coverage: Do not use one entry sentinel for all Step 5, or add routed registry/sentinel coverage for 5b, 5c, and 5d with save/resume tests


### FINDING_9: ISSUE_NUMBER is not guaranteed in current-design-env
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-step-registry-coverage
- **Severity**: important
- **Concern**: `/larch:pause` depends on `ISSUE_NUMBER`, but Step 0 writes the session env before issue binding and the plan does not require a post-bind refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a required Step 0b writer refresh immediately after issue binding using write-design-current-env.sh --issue-number "$ISSUE_NUMBER" --claude-pid "$PPID", and cover it in the pause harness
  - From Codex-Edge: Add a mandatory write-design-current-env.sh re-invocation immediately after Step 0b binds ISSUE_NUMBER, passing --issue-number "$ISSUE_NUMBER" and --claude-pid "$PPID", before any pauseable Step 1c+ boundary
  - From Codex-Innovation: Add a required Step 0b refresh immediately after issue binding, passing `--issue-number "$ISSUE_NUMBER"` with the same reviewer flags and `--claude-pid "$PPID"`; add a pause skill harness for this path.
  - From Cursor-Pragmatic: Mandate write-design-current-env --issue-number bash block in Step 0b after bind, or derive issue from tmpdir artifact in pause skill
  - From Codex-Pragmatic: Add an explicit Step 0b writer re-invocation immediately after ISSUE_NUMBER is bound, passing --issue-number "$ISSUE_NUMBER" and --claude-pid "$PPID"; cover this in the pause harness
  - From Cursor-Requirements: Add a mandatory write-design-current-env.sh re-invocation (with --issue-number and --claude-pid) immediately after ISSUE_NUMBER is bound in Step 0b, before any pauseable Step 1c+ boundary
  - From Codex-dyn-step-registry-coverage: Add a Step 0b follow-up write-design-current-env.sh invocation immediately after ISSUE_NUMBER is bound, passing --issue-number "$ISSUE_NUMBER" and --claude-pid "$PPID"


### FINDING_10: Entry-time .completed sentinels can skip unfinished work
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Writing `.completed/step-*` at step entry marks in-flight work complete before durable artifacts exist. A pause mid-step can resume too far ahead and skip required work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep .completed for after-success completion only; use a separate .entered or .current-step sentinel for observability, and compute resume from registry-ordered completed sentinels
  - From Codex-Edge: Write .completed/step-<id> only after the step completes, or use separate .entered sentinels and compute resume from the last completed step
  - From Codex-Innovation: Write checkpoint sentinels only after each step reaches a restart-safe completion point, or store an explicit `resume_step` before entering each non-idempotent block.
  - From Codex-Pragmatic: Use completion sentinels written only after each step's durable outputs are complete, or track current-step separately and resume from the current step when its completion sentinel is absent
  - From Cursor-Requirements: Write completion sentinels only after restart-safe outputs exist, or record STEP as the current in-flight step when pause fires and route resume to re-enter that step


### FINDING_11: Pause publish idempotency misses remote branch and worktree conflicts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Pause idempotency handles local branch reuse but not existing remote recovery branches, open PRs, or stale worktrees, so repeated pause of the same run can fail before recovery output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: For --reason pause, explicitly update the existing remote branch with --force-with-lease or detect and reuse/update the open PR; preserve recovery output when the remote update fails
  - From Codex-Innovation: For `--reason pause`, handle existing remote refs explicitly with `--force-with-lease` or a delete-and-push protocol, and test the `RECOVERY_BRANCH` then repause same `RUN_ID` case.
  - From Cursor-Pragmatic: Teardown stale worktree for larch-log-design-RUN_ID before recreate, or document operator cleanup
  - From Codex-Pragmatic: For --reason pause, handle remote branch reuse explicitly with fetch plus force-with-lease/update, or use unique per-snapshot recovery branch names and persist the selected branch in the marker
  - From Cursor-Requirements: For --reason pause add fetch/force-with-lease or per-snapshot recovery branch names; persist the chosen branch in LOG_RECOVERY_BRANCH and test publish-fail-republish


### FINDING_12: Named block delete semantics conflict with plan-block compatibility
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-script-contract-mirror, Codex-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: Generic empty-content deletion can break the existing `plan-block-write.sh` contract, while design-pause marker removal still needs explicit delete behavior to avoid resume loops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make deletion explicit, for example --delete, or have plan-block-write.sh pass a compatibility flag that preserves empty-content replacement and the existing MODE set
  - From Codex-Pragmatic: Make deletion explicit, for example --delete or /dev/null-only for non-plan callers, and keep marker=plan empty files writing start/end markers as today
  - From Cursor-Requirements: Implement empty+present => delete (MODE=removed) in named-block-write.sh and cover with test-design-pause-resume.sh case (c)
  - From Cursor-dyn-script-contract-mirror: Limit delete semantics to named-block-write --marker design-pause only; in named-block-write reject /dev/null when --marker plan
  - From Cursor-dyn-script-contract-mirror: Document and implement delete only for --content-file /dev/null (or explicit --remove flag)
  - From Codex-dyn-script-contract-mirror: Make deletion an explicit flag or opt-in mode used only by design-pause callers; keep --marker plan wrapper preserving empty-block replace/append and add regression cases to scripts/test-plan-block.sh


### FINDING_13: Generic marker names need validation
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-dyn-script-contract-mirror, Codex-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: `--marker` is interpolated into regexes and marker literals without a strict validation/escaping contract, allowing malformed marker names to corrupt block matching.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Validate marker names against a strict allowlist such as ^[A-Za-z0-9][A-Za-z0-9_-]*$ and fail before any gh calls; keep the documented marker registry in sync
  - From Codex-Innovation: Validate `--marker` against a small registry (`plan`, `design-pause` initially) or a strict slug regex before building regexes or canonical marker strings.
  - From Cursor-dyn-script-contract-mirror: Validate --marker against ^[a-z0-9][a-z0-9-]*$ before building MARK_START/MARK_END
  - From Codex-dyn-script-contract-mirror: Specify and test either a fixed marker registry {plan,design-pause} or strict NAME validation plus ERE escaping before constructing MARK_START and MARK_END


### FINDING_14: Documented gh retry behavior does not exist
- **Reviewer(s)**: Codex-Edge, Cursor-dyn-script-contract-mirror, Codex-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: The plan claims inherited retry behavior for issue-body writes, but the current writer performs single-shot `gh issue view/edit` calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Either add bounded retry/backoff to named-block-write.sh and test it, or change the edge-case contract to say marker writes fail fast and are retried only by re-invoking /larch:pause
  - From Cursor-dyn-script-contract-mirror: Remove the retry claim or implement the same retry policy in named-block-write.sh and document it in named-block-write.md
  - From Codex-dyn-script-contract-mirror: Add explicit bounded retry/backoff to named-block-write.sh if pause requires it, or revise the edge-case/failure-mode text and tests to reflect single-shot behavior


### FINDING_15: Progress sentinels are not persisted in pause snapshots
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The publisher stages top-level files and selected directories, but not `.completed/`, so resumed sessions lose progress state and later pause/resume cycles miscompute the next step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an explicit pause-mode allowlist for `.completed/` or store all resume progress in a top-level persisted state file; cover a real publish-load-publish cycle in the harness.
  - From Cursor-Pragmatic: Publish .completed on pause reason, or drop sentinel-restore claim and rely only on marker KVs
  - From Cursor-Requirements: Extend design-log-publish.sh --reason pause (or always) to stage .completed/ into RUN_DEST, or persist progress solely in the marker/KV file and stop depending on unpublished sentinels; assert in test-design-pause-resume.sh
  - From Codex-Requirements: Add explicit sentinel writes at every step-entry Bash block, extend the publish/load contract to include .completed with symlink/path validation, and test that .completed survives save/load cycles


### FINDING_16: Pause/resume tests are not wired into CI
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-script-contract-mirror, Codex-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: The plan promises new pause/resume harness coverage but omits required Makefile/shard and lint registration changes, so coverage may not run under `make lint` or `relevant-checks`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add `Makefile` to the plan with `test-design-pause-resume` target and shard membership, plus any lint allowlist/docs updates needed for the new script sibling.
  - From Cursor-Pragmatic: Register target on test-harnesses-14 or -20 with harness-timer.sh
  - From Codex-Pragmatic: Include Makefile in the plan, add a test-design-pause-resume target, and place it in one test-harnesses-N shard so scripts/relevant-checks.sh exercises it
  - From Cursor-Requirements: Add UPDATED Makefile with test-design-pause-resume target on a test-harnesses-N shard; extend scripts/test-design-log-publish.sh for --reason pause
  - From Codex-Requirements: Add Makefile target, PHONY entry, shard membership, and agent-lint exclusions for skills/design/scripts/test-design-pause-resume.sh and its sibling md
  - From Cursor-dyn-script-contract-mirror: Add Makefile target and register on a test-harnesses-N shard like test-plan-block
  - From Codex-dyn-script-contract-mirror: Add UPDATED: Makefile to the plan and register test-design-pause-resume in the appropriate harness shard


### FINDING_17: Pause request can be orphaned after cancellation
- **Reviewer(s)**: Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `/larch:pause` is modeled as writing a request for a still-running inline `/design` to observe later. If Esc cancels the design turn, no later boundary may save a checkpoint; if only a flag exists and no marker, a fresh `/design` can discard the pause intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Make /larch:pause perform design-pause-save.sh directly from the sourced session env, or change the trigger to an in-band /design checkpoint mechanism that does not require a cancelled turn to continue
  - From Cursor-Requirements: In Step 0b before clarify: if pause-requested flag exists and marker absent, either run design-pause-save from a still-live env or fail-closed with an explicit retry message; clear the flag after successful save


### FINDING_18: Pause prelude is not guaranteed at all runtime Bash boundaries
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-step-registry-coverage, Cursor-dyn-prelude-injection-audit, Codex-dyn-prelude-injection-audit
- **Severity**: important
- **Concern**: Updating the canonical prelude prose alone will not patch duplicated Bash fences in `SKILL.md` or referenced design files, so pause checks can be missed or delayed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add test-design-structure check counting two-line prelude from Step 1c onward
  - From Codex-dyn-step-registry-coverage: Add the referenced files to the plan and insert the canonical pause-check/sentinel prelude at every runtime Bash block, or centralize the prelude in a shared sourced helper used by those blocks
  - From Cursor-dyn-prelude-injection-audit: Promote a documented two-line prelude (source + pause-check) at :66-72, then require the same pair prepended to every ```bash fence from Step 1c through Step 6 (enumerate ~29 instances at :299-1039 plus nested fences at :648-650, :851-853, :913-915)
  - From Codex-dyn-prelude-injection-audit: Update the plan to state explicitly that the prelude is duplicated inline, enumerate every Step 1c-through-Step 6 instance to patch, and require a grep/harness check that no current-design-env-$PPID.sh Bash fence lacks the pause-check line
  - From Codex-dyn-prelude-injection-audit: Update the file list and implementation steps to include skills/design/references/brainstorm.md and skills/design/references/plan-review.md, or explicitly justify excluding illustrative fences and add tests/documentation so runtime collection snippets still get the pause-check behavior


### FINDING_20: User-editable marker values are not validated before git/control-flow use
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: `RUN_ID`, `STEP`, and `LOG_RECOVERY_BRANCH` are parsed from issue-body marker content without required validation before use in git commands and resume routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Validate RUN_ID with the existing larch_log_slug_is_valid contract, STEP against step-name-registry.tsv, and LOG_RECOVERY_BRANCH with git check-ref-format plus the expected larch-log-design prefix; reject option-looking or path-containing values before any git command


### FINDING_21: Shipped pause skill is missing consumer docs
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Concern**: The new `/larch:pause` skill would ship without updates to the public skill catalog/docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update README skill table and docs/skills.md with /pause arguments, behavior, and source link alongside skills/pause/SKILL.md


### FINDING_22: Malformed-token count is inconsistent
- **Reviewer(s)**: Cursor-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: The named-block-write plan says there are four malformed tokens instead of five, risking dropped end-before-start handling in docs or extraction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-contract-mirror: Align named-block-write.md with five tokens and keep scripts/test-plan-block.sh coverage


### FINDING_25: New gh body writer is missing path-triggered rule coverage
- **Reviewer(s)**: Codex-dyn-script-contract-mirror
- **Severity**: latent
- **Concern**: The shared issue-body writer is not added to the repository rule that enforces body-file and redaction practices for matching paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-script-contract-mirror: Add scripts/named-block-write.sh and scripts/named-block-write.md to .claude/rules/gh-body-file.md frontmatter### OOS_1:
- **Description**: No trust note for pause-requested issue flag files. Scenario: Same-UID cache tampering undocumented for new marker
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: security
- **Location**: SECURITY.md:51-51
- **Phase**: design


