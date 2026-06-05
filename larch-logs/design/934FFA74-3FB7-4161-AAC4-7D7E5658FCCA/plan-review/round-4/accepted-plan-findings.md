### FINDING_1: Step 2a/2a.5 folded marker hosts break SIMPLE entry semantics and stale NEVER guidance
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan moves or rewords Step 2a/2a.5 sentinel writes without preserving the SIMPLE entry-fence writes that skip-to-2b depends on, and leaves consolidated NEVER/Anti-pattern guidance inconsistent with the new folded hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly keep `.completed/step-2a` and `.completed/step-2a.5` in the Step 2a entry SIMPLE block (items 7-8); limit items 9-10 to HARD/degraded paths; update Anti-pattern #1 and lines 651/677-679/815 to match
  - From Cursor-Pragmatic: Add a SKILL.md plan bullet to rewrite NEVER #1 HARD wording to the folded hosts (Step 2a.5 prelude, Step 2b prelude, zero-sketch branch fence) while keeping the SIMPLE Step 2a entry carve-out


### FINDING_2: No-brainstorm folded path omits required step-1d.5 sentinel
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-resume-state
- **Severity**: important
- **Concern**: The no-brainstorm route can bypass Step 1d.5 while the registry still requires `step-1d.5` before later discussion markers, causing pause-save to resume backward into the skipped brainstorm step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Either keep running the retained Step 1d.5 entry guard so its skipped-path boundary writes step-1d.5, or have the Step 2a entry fence write step-1d.5 only when brainstorm_requested is not true. Add a pause-resume test for no-brainstorm after Step 2a.
  - From Codex-Innovation: Add the minimal conditional skipped-step marker: when brainstorm is not requested and Step 2a is repairing folded discussion markers, write .completed/step-1d.5 before pause-check, or write it at the 1d→1d.7 skip boundary. Pin this in the folded-order structure test and pause/resume regression.
  - From Codex-Pragmatic: Add an idempotent skipped-brainstorm step-1d.5 write for the no-brainstorm path before any Step 2a pause-check, or route no-brainstorm through the retained Step 1d.5 entry guard so its boundary-local skipped write runs; pin this in structure and pause/resume tests.
  - From Codex-dyn-resume-state: Conditionally write step-1d.5 in the Step 2a entry repair only when brainstorm was not requested or .brainstorm-done exists, or instead make the Step 1d.5 entry guard always run and write its boundary marker on the skip path


### FINDING_3: Architecture diagram skip sentinel and stale artifacts are not mutually cleaned
- **Reviewer(s)**: Codex-Arch, Codex-Requirements, Codex-dyn-resume-state
- **Severity**: important
- **Concern**: Branch-local architecture/non-architecture handling can leave stale `architecture-diagram.md` or `architecture-diagram.skipped` artifacts from prior Gate C loops, causing publish to either republish stale Architecture content or clear Architecture for a later architectural plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In the branch-local non-architectural skip fence, remove architecture-diagram.md and architecture-diagram.candidate.md before touching architecture-diagram.skipped, or change design-publish.sh so the skipped sentinel wins over a stale diagram file.
  - From Codex-Requirements: Revise Step 3b to clear stale artifacts at the classifier branch: on non-architectural skip, remove architecture-diagram.md before touching architecture-diagram.skipped; on architectural paths, remove architecture-diagram.skipped before generation/failure/success handling. Add a structure test for these branch-local cleanup lines.
  - From Codex-dyn-resume-state: At Step 3b architectural-branch entry, remove any stale $DESIGN_TMPDIR/architecture-diagram.skipped before generation/failure handling, and pin this in the structure test so only the current non-architectural branch leaves the skip sentinel in place


### FINDING_4: Backward Gate B/Gate C loops can resume at stale downstream sentinels
- **Reviewer(s)**: Codex-Edge, Codex-dyn-operator-contract
- **Severity**: important
- **Concern**: Folded entry fences do not reset stale downstream `.completed` markers before pause checks on backward Gate C/Gate B routes, so pause-save can select a later registry step and skip required fresh discussion or review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: For Step 3 re-entry routes, clear stale downstream sentinels for the review-to-Gate-C span before the pause-check, or add an explicit resume-step override. Add the regression with existing step-3/3.5/3.6/3b/4 markers and missing step-4b.
  - From Codex-dyn-operator-contract: Add a minimal route-local sentinel reset before backward jumps: clear step-1e and the rerun range for discussion loops, and clear step-3 through step-4b for review reruns, before entering the earlier step. Extend the pause/resume regression with fixtures that seed prior downstream sentinels and assert pause-save resumes at Gate A or Step 3, not Gate C.


### FINDING_6: Requirements/resume reviewers could not read plan or repository inputs
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-resume-state
- **Severity**: important
- **Concern**: Reviewer slots reported that plan or repository reads failed, so their expected validation did not actually occur and the pipeline must not treat those slots as clean approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Re-run this reviewer slot once plan.txt is readable; do not treat this pass as plan approval
  - From Cursor-dyn-resume-state: Re-run this review slot after plan.txt and repo reads succeed; do not merge on a salvaged empty result


### FINDING_7: Folded sentinel structure tests may match prose instead of shell writes
- **Reviewer(s)**: Codex-dyn-structure-harness
- **Severity**: important
- **Concern**: The folded sentinel checks can pass on bare token mentions in comments or prose rather than verifying actual non-comment shell writes in the intended host fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-structure-harness: Make assert_folded_sentinel_writes match actual non-comment shell write lines like : > "$DESIGN_TMPDIR/.completed/step-X" inside the extracted host fence, then check source-env < write < pause-check


### FINDING_8: Structure harness misses indented bash fences
- **Reviewer(s)**: Codex-dyn-structure-harness
- **Severity**: important
- **Concern**: Existing scans only recognize unindented bash fences, so checks for deleted preludes, publish/Gate C folded ordering, or pause checks can miss indented target fences and falsely pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-structure-harness: Use the new whitespace-tolerant fence extractor for the folded host checks, deleted-prelude negative guards, and pause-check scan; match both opening and closing fences with optional leading whitespace


### FINDING_9: Moving step-4 completion into Gate C widens the STEP=4 resume window
- **Reviewer(s)**: Cursor-dyn-operator-contract
- **Severity**: important
- **Concern**: Deferring `.completed/step-4` from the Step 4 success boundary to the merged Gate C preview fence creates a gap where a pause still saves `STEP=4`, causing resume to replay Step 4 instead of Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-contract: Write `step-4` at the Step 4 success boundary (after rejected-findings output, before Step 4b), or in a minimal Step 4b entry prelude (`source-env` → `step-4` → pause-check) before Gate C presentation; keep the merged gatec fence for timing + preview only, or make its `step-4` write idempotent after the earlier boundary write

