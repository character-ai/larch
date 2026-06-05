### FINDING_1: Gate B/C discussion re-entry lacks a cleanup host before Step 1e pause checks
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-sentinel-state-machine, Cursor-dyn-harness-fidelity, Cursor-dyn-contract-drift, Cursor-dyn-harness-fidelity
- **Severity**: important
- **Concern**: Multiple reviewers identify the same pause/resume risk: after Gate B(c) or Gate C(b) routes back into Step 1e, the plan deletes or relies on a missing Step 1e Bash prelude, so stale `.completed` markers from later steps can remain before a pause-check. A pause during the discussion/rewrite path can therefore save an incorrect later STEP and resume past the required discussion/review loop. Test coverage also needs to prove the stale markers are actually removed before the re-entry pause-check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend 11a rerun span through step-4b; add a concrete Gate B/C re-entry Bash fence at Step 1e (source-env → rm stale step-1e..step-4b → pause-check) and a pause-resume fixture that seeds step-4b then pauses at Step 1e before Step 3 entry
  - From Cursor-Innovation: Add a minimal Gate B(c)/Gate C(b) re-entry Bash fence at Step 1e: source-env then rm stale step-1e through step-4b (not only through step-2b) then pause-check; keep the Phase 7 fold for first-time 1e skip paths
  - From Codex-Innovation: Add one small transition fence on Gate B Switch-to-discussion and Gate C Discuss further, or retain a Step 1e re-entry-only fence, that clears the rerun-span sentinels before its pause-check
  - From Cursor-Pragmatic: Extend plan items 11/11a and SKILL.md Step 1e optional trailer guard: on the first rewrite bash fence (gate-b-dedup --snapshot-trailers), after source-env and before pause-check, rm -f stale $DESIGN_TMPDIR/.completed/step-3 through step-4b; add a pause-resume fixture that pauses mid-rewrite and asserts STEP is 3 (or 1e), not 5b+
  - From Cursor-dyn-sentinel-state-machine: Add a minimal re-entry-only Bash fence at Gate B(c)/Gate C(b)→Step 1e (and/or the first discussion-round2 postplan fence) that runs source-env → rm stale step-3…step-4b (and step-1e…step-2b.5) → pause-check before any Step 1e prose; do not rely on a deleted Step 1e prelude
  - From Cursor-dyn-harness-fidelity: Add a concrete bash host on the Step 1e re-entry path (minimal source-env → rm stale step-1e…step-2b → pause-check) or route Gate B(c)/Gate C(b) through an existing prelude that performs the clears before any Step 1e work; pin that host in assert_folded_sentinel_writes / backward re-entry guards
  - From Cursor-dyn-contract-drift: Add a re-entry-only Bash host (clears step-1e…step-4b, then pause-check) at Gate B(c)/Gate C(b) → Step 1e and/or prepend the same clears to the Gate A postplan-emit fence before its pause-check; do not rely on Step 3 entry alone
  - From Cursor-dyn-harness-fidelity: Seed stale markers, execute the documented re-entry prelude shell (or a copied excerpt) before pause-save, assert the stale files are absent on disk, then assert LOAD STEP; mirror Gate B(c)→Step 1e if a clear host is added


### FINDING_2: Architectural retries can republish a stale prior diagram
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Edge, Codex-Innovation, Codex-dyn-sentinel-state-machine, Codex-dyn-contract-drift, Cursor-dyn-harness-fidelity
- **Severity**: important
- **Concern**: The architectural Step 3b path clears only the skip sentinel, not previously promoted diagram files. If a prior Gate C pass produced `architecture-diagram.md` and a later architectural retry fails generation or sanitizer validation, `design-publish.sh` can treat the old diagram as current and publish it. The structure harness also needs branch-local assertions so prose cannot satisfy this contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Pragmatic: Add branch-entry cleanup for architectural paths: rm -f "$DESIGN_TMPDIR/architecture-diagram.md" "$DESIGN_TMPDIR/architecture-diagram.candidate.md" "$DESIGN_TMPDIR/architecture-diagram.skipped" before fresh generation, or at minimum delete architecture-diagram.md on generation/sanitizer failure before Step 3b FINALIZE.
  - From Codex-Edge: At architectural Step 3b entry remove stale architecture-diagram.md and candidate as well as skipped; if failure should clear the tracking-issue Architecture section, also emit the clear sentinel or another explicit clear trigger on failure
  - From Codex-Innovation: At architectural path entry, remove stale architecture-diagram.md and architecture-diagram.candidate.md along with architecture-diagram.skipped before generating; keep the non-architectural skip cleanup as planned and add the structure assertion for this case
  - From Codex-dyn-sentinel-state-machine: On architectural Step 3b entry, remove stale architecture-diagram.md and architecture-diagram.candidate.md before generation, then promote only the current candidate on success.
  - From Codex-dyn-contract-drift: Add branch-local cleanup for architectural paths: remove stale architecture-diagram.md and architecture-diagram.candidate.md before generation, or remove them on rejection/failure before FINALIZE; extend the Step 3b structure assertion to cover this
  - From Cursor-dyn-harness-fidelity: Replace lines 961–962 with branch-scoped fence extraction: skip-path fence must contain rm -f architecture-diagram.md and .candidate.md before : > architecture-diagram.skipped; architectural entry must rm -f .skipped before generation; FINALIZE boundary must not write .skipped


### FINDING_3: Discussion re-entry cleanup may clear required Step 2 markers before direct Step 3 review
- **Reviewer(s)**: Codex-Edge, Codex-dyn-sentinel-state-machine
- **Severity**: important
- **Concern**: The proposed backward discussion cleanup clears Step 2 markers, but the Ready-for-review route can jump directly from Gate A to Step 3 without restoring them. A pause after that point may see missing Step 2 sentinels and resume too far upstream instead of continuing the fresh review path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Narrow the backward re-entry clear to step-1e and post-review sentinels, or have the Step 3 direct-review entry restore step-2a step-2a.5 step-2b and step-2b.5 before pause-check
  - From Codex-dyn-sentinel-state-machine: Do not clear step-2a/step-2a.5/step-2b on Gate A discussion re-entry. Clear only step-1e before Gate A and let Step 3 clear downstream review/Gate-C markers, or ensure the Gate A post-rewrite fence re-writes step-2b before any Step 3 pause-check.


### FINDING_4: Step 2a SIMPLE marker ordering is underspecified before pause-check
- **Reviewer(s)**: Cursor-Requirements, Codex-dyn-harness-fidelity
- **Severity**: important
- **Concern**: The plan adds or tests Step 2a marker writes before pause-check, but the SKILL edit instructions only explicitly insert folded discussion writes and say to preserve the existing SIMPLE block, which is currently after pause-check. An implementation could therefore leave SIMPLE markers too late or satisfy tests by making an edit the plan did not actually specify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: A pause at Step 2a entry can exec design-pause-save.sh before SIMPLE markers are written, leaving an incomplete resume package Spell out in item 7 that the SIMPLE guarded block (artifacts plus step-2a and step-2a.5 writes) moves to after source-env and before pause-check, with timing mark after pause-check
  - From Codex-dyn-harness-fidelity: Make the Step 2a entry ordering explicit: source env, folded discussion writes, read classification plus SIMPLE guarded artifact and step-2a/step-2a.5 writes if intended, then pause-check; or relax the planned assertion if SIMPLE markers need not precede pause-check


### FINDING_6: Already-planned Q&A-only branch writes a non-contiguous sentinel
- **Reviewer(s)**: Codex-dyn-sentinel-state-machine
- **Severity**: important
- **Concern**: Writing only `step-1d.5` at the terminal boundary of the already-planned Q&A-only branch does not create a contiguous registry prefix. If earlier registry markers remain absent, pause-save can still resume before that point and replay brainstorm flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-sentinel-state-machine: Either drop the new Q&A-only step-1d.5 terminal write as unnecessary, or make the branch write a contiguous registry prefix through step-1d.5 before any pause-save-capable terminal boundary.


### FINDING_7: Folded sentinel harness can pass without proving branch guards
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Concern**: The proposed structure assertion checks for literal marker writes but may not prove that those writes occur under the required branch guards or after the required parse/decision points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-fidelity: Extend assert_folded_sentinel_writes to require branch guards (brainstorm_requested false via run-params.json/jq, HARD-only classification guard on 2a.5 prelude, [[ PLAN_WRITE_OK=true ]] block with step-5c write after the parse loop) using line-order checks inside the extracted fence body


### FINDING_8: Zero-sketch degraded branch lacks a distinct harness extraction anchor
- **Reviewer(s)**: Cursor-dyn-harness-fidelity
- **Severity**: important
- **Concern**: The planned harness extraction only captures the first Bash fence after Step 2a, so it may miss the degraded zero-sketch branch fence and fail to assert its marker writes and ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-fidelity: Add extract_bash_fence_after with a dedicated marker (e.g. proximity to “ran 0 sketches (degraded)” / zero-sketch jump prose) and register that fence separately in assert_folded_sentinel_writes


### FINDING_9: Pause-load docs retain a stale issue-marker deletion contract
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Concern**: The plan updates restored `.pause-requested` handling but leaves sibling documentation saying the issue-body pause marker is deleted on load, conflicting with the script and harness behavior where the issue marker remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-drift: Update design-pause-load.md to say load removes only the restored live $DESIGN_TMPDIR/.pause-requested marker; the issue-body larch:design-pause marker remains until existing terminal cleanup/marker handling


### FINDING_10: Step 3 chat-order note still names an obsolete preview helper
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: latent
- **Concern**: The plan preserves a Step 3 chat-order clause that still references `run-step3-review.sh --preview-only`, even though the current SKILL path uses `emit-design-plan-preview.sh --variant step3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-drift: While editing the note, change the Step 3 helper name to emit-design-plan-preview.sh --variant step3; keep the rest of the Step 3 ordering unchanged

