### FINDING_2: Conflict-resolution rewrite omits topology row sync
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan rewrites `skills/implement/references/conflict-resolution.md` Phase 3 to drop the external 3-reviewer panel, but does not update `skills/shared/topology.tsv` or regenerate `docs/topology.md`. Row `implement.conflict_review.panel` still pins value `3-reviewer` to that authority file. `python/larch/rendering/_rendering_generators.py` requires each topology `value` to appear verbatim in `runtime_authority`, so `python3 python/cli.py generate topology-docs` / `--check` fails and `docs/topology.md` keeps projecting a removed panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/shared/topology.tsv` (and regenerated `docs/topology.md`) with a new `value` that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent`), then run `python3 python/cli.py generate topology-docs`.
  - From Cursor-Innovation: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`): change `implement.conflict_review.panel` value/composition to the new self-review shape (e.g. `main-agent`) and keep the literal in the rewritten conflict-resolution reference.
  - From Cursor-Requirements: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`) with a new `implement.conflict_review.panel` value that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent self-review`), plus matching composition text.


### FINDING_4: /review self-review handoff does not refresh summary/tally artifacts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: On the zero-survivor `panel-failed` path, `review core` already emits `review-round-summary.md` and `review-summary.json` with zero accepted findings. The proposed self-review fallback then writes `findings.md` and `accepted-findings.md`, but Step 4, `review log-phase`, and heavy-worker parent artifacts still read the stale panel-failed summary. Standalone `/review --diff` can print and log a zero-finding summary even when self-review found accepted issues and applied fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: After self-review adjudication, regenerate the normal summary artifacts from the self-review accepted/rejected counts, for example by writing a small tally env and invoking the existing `review emit-tally` contract before Step 4 or heavy-worker return.
  - From Codex-Innovation: Add a minimal summary refresh to `skills/review/references/self-review.md` after accepted-findings adjudication. Reuse the existing `review emit-tally` contract with a self-review tally env, `$ACCEPTED_FINDINGS_FILE`, and `$REVIEW_TMPDIR/oos.md`, or otherwise update `review-round-summary.md` and `review-summary.json` before Step 4.
  - From Codex-Pragmatic: Add a required artifact refresh to the self-review reference before Step 4, shared by inline and heavy-worker paths. Synthesize the self-review counts and run the existing `review emit-tally` path, or explicitly write equivalent `review-round-summary.md` and `review-summary.json` from the self-review artifacts.
  - From Codex-Requirements: Add a required step in `skills/review/references/self-review.md` or the Step 3 branch to regenerate `review-round-summary.md` and `review-summary.json` from the self-review accepted/rejected/OOS artifacts before Step 4 or heavy-worker return.


