### FINDING_1: Scope-anchor plan-block stripping lacks a canonical marker contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-anchor-threading
- **Severity**: important
- **Concern**: The plan requires stripping embedded `larch:plan` content from the scope-anchor source, but does not consistently name a shared helper, marker regex, or malformed-marker behavior. Ad-hoc stripping could leave stale plan text in the binding anchor or diverge from existing marker handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Name the strip implementation: reuse the MARK_START/MARK_END regexes from scripts/plan-block-read.sh (or design-route.sh plan_block_present) and document fail-open vs fail-closed behavior when markers are malformed
  - From Cursor-Edge: Reuse the same MARK_START/MARK_END rules as scripts/plan-block-read.sh: delete the inclusive start/end marker lines and everything between them; keep only exterior body (no new helper required)
  - From Cursor-Innovation, Cursor-Requirements: Add a ### NEW: scripts/plan-block-strip-body.sh (or equivalent) reusing MARK_START/MARK_END from scripts/plan-block-read.sh and call it when materializing plan-review-scope-anchor.txt; document malformed-body behavior
  - From Cursor-dyn-anchor-threading: Reuse plan-block-read marker regexes (or add a small shared strip helper tested beside scripts/test-plan-block.sh) when writing plan-review-scope-anchor.txt; fail loud on malformed multi-marker bodies consistent with plan-block-read.

### FINDING_2: Tagged append and fallback paths can produce duplicate FINDING/OOS headings
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-dyn-marker-contract
- **Severity**: important
- **Concern**: Plan-mode aggregation and marker-preservation fallback can append or forward reviewer-local blocks without a final sequential renumber and uniqueness validation. Because reviewer fragments restart at `FINDING_1`/`OOS_1`, the ballot splitter can reject duplicate headings before voting or tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a final plan-mode combine step that renumbers all FINDING headings after appending preserved tagged blocks and validates uniqueness before AGGREGATED=true
  - From Codex-Edge: When bypassing dedup or composing tagged plus aggregated output, run one final sequential renumber over all FINDING and OOS headings and validate uniqueness before writing the ballot. Do not preserve verbatim IDs.
  - From Codex-Innovation: Renumber the combined aggregated-untagged plus preserved-tagged stream sequentially before AGGREGATED=true, and validate duplicate-free headings
  - From Codex-Pragmatic: After recombining aggregated untagged blocks with preserved tagged blocks, deterministically renumber all FINDING headings before replacing the in-scope findings file; add a duplicate-ID regression
  - From Codex-Pragmatic: Make the fallback skip merging but still split and sequentially renumber in-scope FINDING blocks before ballot creation
  - From Codex-dyn-marker-contract: Keep the minimum contract by adding one final sequential renumber step after any tagged append or pre-dedup fallback and before ballot.txt; preserve block bodies and leading markers, only rewrite headings

### FINDING_3: Proposed tally scope-anchor flag is dead plumbing for MainAgent anchoring
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-anchor-threading
- **Severity**: latent
- **Concern**: The plan threads scope-anchor responsibility into `tally-plan-review.sh`, but the 0-judge MainAgent prompt is composed inline in `SKILL.md`. Adding a tally flag may not affect the adjudication prompt and can split fallback instructions across authorities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not add tally-plan-review --scope-anchor-file; pass sanitized SCOPE_ANCHOR_FILE through Step 3 result state and keep the MainAgent scope-anchor instructions in SKILL.md
  - From Codex-Pragmatic: Drop the tally --scope-anchor-file change and keep SCOPE_ANCHOR_FILE use in the Step 3 MainAgent instructions, or clearly limit tally to accepting but ignoring the flag for compatibility
  - From Codex-dyn-anchor-threading: Keep tally pure: thread sanitized SCOPE_ANCHOR_FILE through Step 3 env to the SKILL MainAgent prompt, and do not add or pass --scope-anchor-file to tally/re-tally unless tally actually renders a prompt that uses it

### FINDING_4: New umbrella scope-anchor harness duplicates focused harness coverage
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-regression-matrix
- **Severity**: important
- **Concern**: The proposed broad scope-anchor harness duplicates cases already assigned to focused per-script harnesses, increasing fixture, Makefile, and maintenance surface without a distinct contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop the new omnibus test-plan-review-scope-anchor.sh target; keep the focused existing harness updates plus the new marker-detector harness
  - From Codex-Pragmatic: Remove test-plan-review-scope-anchor.sh and keep the focused tests plus the new marker-detector harness
  - From Codex-dyn-regression-matrix: Drop the new broad harness, or reduce it to one end-to-end smoke only if it covers behavior not asserted by the existing per-script harnesses; keep the new detector unit test and the existing harness extensions

### FINDING_5: Parity fallback target is undefined without a staged pre-dedup in-scope artifact
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-marker-contract
- **Severity**: important
- **Concern**: The plan describes falling back to a pre-dedup in-scope stream, but the current pipeline only materializes the combined collection, then deduped findings, then the in-scope split. Without naming or staging the fallback artifact, parity failure cannot reliably bypass dedup while preserving scope-reduction markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name the fallback input explicitly (e.g. FINDING blocks from the pre-dedup collect buffer or pre-dedup findings.md) and skip or bypass dedup before aggregation when parity fails
  - From Cursor-dyn-marker-contract: Before the Jaccard deduper runs, split _findings_tmp into findings-in-scope.pre-dedup.md (and OOS if needed), run dedup/parity against that snapshot, and on parity failure copy the pre-dedup in-scope file to findings-in-scope.md before aggregation

### FINDING_6: Tagged split must reconcile with aggregate validation before move
- **Reviewer(s)**: Cursor-dyn-marker-contract
- **Severity**: important
- **Concern**: Plan-mode aggregation excludes tagged blocks from the LLM prompt but may leave existing validation expecting every reviewer from the full input to appear in the raw candidate. If a tagged block is the only finding for a reviewer, validation can fail and force fallback instead of the intended conservative merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-marker-contract: In plan mode, build the LLM prompt from untagged blocks only, append tagged blocks after a successful untagged merge, and run marker/reviewer validation on the combined output (or validate untagged-only input against the LLM candidate plus a separate tagged-preservation gate)

### FINDING_7: Marker detector tests may miss the live inline TSV emitter shape
- **Reviewer(s)**: Cursor-dyn-marker-contract
- **Severity**: important
- **Concern**: Production `/design` emits findings through inline TSV conversion with separate `Severity` and `Concern` lines, while `collect-findings.sh` folds severity into the concern body. Tests that only exercise the collect script can pass while marker detection fails on the live format after dedup or aggregation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-marker-contract: Add test-plan-review-loop or test-check-scope-reduction-marker fixtures that use the inline emitter shape (- **Severity**: important / - **Concern**: [SCOPE-REDUCTION] ...) and assert detection after collect, dedup, and plan-mode aggregation

### FINDING_8: Dedup merge order can drop tagged markers before parity
- **Reviewer(s)**: Cursor-dyn-marker-contract
- **Severity**: important
- **Concern**: The current dedup merge keeps the first Jaccard match body. If an untagged duplicate appears before a tagged one, the `[SCOPE-REDUCTION]` marker can be lost until parity fallback, making marker preservation depend on a degraded heuristic path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-marker-contract: Implement the planned tagged-wins rule inside the dedup loop (prefer tagged body or reinsert leading marker before parity) so tagged markers survive the primary path without depending on fallback

### FINDING_9: Jaccard comparison treats marker words as problem text
- **Reviewer(s)**: Codex-dyn-marker-contract
- **Severity**: latent
- **Concern**: Dedup and parity comparison still include marker tokens, so a short tagged finding and its untagged duplicate can fail the similarity threshold and remain separate ballot findings for the same scope cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-marker-contract: Strip one leading severity bracket and [SCOPE-REDUCTION] from the comparison text used by dedup/parity only, then keep the tagged body when a merge occurs.

### FINDING_10: Durable Step 3 handoff omits SCOPE_ANCHOR_FILE
- **Reviewer(s)**: Cursor-dyn-anchor-threading
- **Severity**: important
- **Concern**: The plan says to emit `SCOPE_ANCHOR_FILE`, but the durable handoff writers, loop KVs, parser allowlists, phase result env, and SKILL handoff fence omit it. As a result, the staged anchor path can be lost during re-tally or Step 3 orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-anchor-threading: Add SCOPE_ANCHOR_FILE to write_step3_result_env, emit_loop_kvs stdout emit, run-step3-review.sh inner/outer parse allowlists, phase_driver_write_result_env, and SKILL.md handoff fence; document in plan-review-loop.md durable-handoff schema.

### FINDING_11: Scope anchor can inherit the wrong feature file from IMPLEMENT_TMPDIR
- **Reviewer(s)**: Codex-dyn-anchor-threading
- **Severity**: important
- **Concern**: `run-step3-review.sh` can resolve the feature description from `IMPLEMENT_TMPDIR` before `DESIGN_TMPDIR`. If another run has set `IMPLEMENT_TMPDIR`, plan review can stage the wrong issue text as the binding scope anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-anchor-threading: Update the plan to change run-step3-review.sh's plan-review launch to use $DESIGN_TMPDIR/feature-description.txt as the design source, or explicitly validate that the resolved feature file is the current design feature before staging the anchor

### FINDING_12: Existing brainstorm integration test still enforces old binding feature contract
- **Reviewer(s)**: Cursor-dyn-regression-matrix
- **Severity**: important
- **Concern**: The current brainstorm integration case expects brainstorm-merged feature text to be dispatched as the binding feature file. After the scope-anchor change, the binding anchor should exclude brainstorm context, so the old test will either fail or preserve the obsolete contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-regression-matrix: Add an explicit step to rewrite or replace this case: assert plan-review-scope-anchor.txt is passed to panel/voter/tally/revise stubs and that brainstorm lives only in plan-review-feature-context.txt (or is omitted from binding argv)

### FINDING_13: Revise prompt untrusted-framing assertion belongs in the direct revise harness
- **Reviewer(s)**: Codex-dyn-regression-matrix
- **Severity**: important
- **Concern**: The plan assigns revise prompt untrusted-framing coverage to `plan-review-loop`, which can only prove argv wiring. Direct callers of `revise-plan-with-waterfall.sh` would remain uncovered if `compose_prompt` omits or misorders the untrusted-evidence framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-regression-matrix: Add the untrusted framing and before-<feature> assertion to scripts/test-revise-plan-with-waterfall.sh by checking plan-review/round-1/revise/prompt.txt or the launched --prompt-file; leave plan-review-loop focused on passing the staged --feature-file path
