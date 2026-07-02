### FINDING_1: /design degraded-empty-collector must pin postplan emit after plan.txt edits
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: On the `LOOP_STATUS=degraded-empty-collector` path, Step 3 self-review may rewrite `plan.txt`, but the plan only says to run the same post-plan validation/settle path without naming the pinned launcher (`python/cli.py design postplan-emit` or `design-step2b-postplan.sh`). Other design revision sites require that helper for every plan change. An ad-hoc settle or Gate B bypass can skip `diff-lines.txt`, trailers, and command validation, causing Step 3b/5c publish failures or stale plan metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/design/SKILL.md`, after self-review may edit `plan.txt`, require the same launcher used elsewhere: `python/cli.py design postplan-emit` (or `design-step2b-postplan.sh` with the existing site flags) before `design-step3-gate-b-bypass.sh`.
  - From Cursor-Innovation: In the `LOOP_STATUS=degraded-empty-collector` branch, when self-review rewrites `plan.txt`, require `python/cli.py design postplan-emit` (or the existing launcher fence) before `design-step3-gate-b-bypass.sh`; skip emit when the plan is unchanged.
  - From Cursor-Requirements: In the `LOOP_STATUS=degraded-empty-collector` branch, after any in-place `plan.txt` edit, invoke `python/cli.py design postplan-emit` through the existing launcher (same contract as Gate B / discussion re-emits) before `design-step3-gate-b-bypass.sh`.

### FINDING_2: Conflict-resolution rewrite omits topology row sync
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan rewrites `skills/implement/references/conflict-resolution.md` Phase 3 to drop the external 3-reviewer panel, but does not update `skills/shared/topology.tsv` or regenerate `docs/topology.md`. Row `implement.conflict_review.panel` still pins value `3-reviewer` to that authority file. `python/larch/rendering/_rendering_generators.py` requires each topology `value` to appear verbatim in `runtime_authority`, so `python3 python/cli.py generate topology-docs` / `--check` fails and `docs/topology.md` keeps projecting a removed panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: skills/shared/topology.tsv` (and regenerated `docs/topology.md`) with a new `value` that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent`), then run `python3 python/cli.py generate topology-docs`.
  - From Cursor-Innovation: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`): change `implement.conflict_review.panel` value/composition to the new self-review shape (e.g. `main-agent`) and keep the literal in the rewritten conflict-resolution reference.
  - From Cursor-Requirements: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`) with a new `implement.conflict_review.panel` value that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent self-review`), plus matching composition text.

### FINDING_3: Implement self-review reference scoped only to explicit `--self-review`
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a runtime `STEP5_REVIEW_STATUS=self-review-required` consumer in `/implement` Step 5, but `skills/implement/references/self-review.md` still limits `Consumer`, `When to load`, and the opening body to explicit `self_review=true` / `--self-review`. Orchestrators on the zero-survivor fallback path can skip or treat the reference as out of contract even after `skills/implement/SKILL.md` is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update `Consumer`, `When to load`, and the first body sentence to name both entry conditions: explicit `self_review=true` and runtime zero-survivor `STEP5_REVIEW_STATUS=self-review-required`.
  - From Cursor-Innovation: Update `**Consumer**` and `**When to load**` to cover both `self_review=true` and `STEP5_REVIEW_STATUS=self-review-required`, matching the new entry-condition note.

### FINDING_4: /review self-review handoff does not refresh summary/tally artifacts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: On the zero-survivor `panel-failed` path, `review core` already emits `review-round-summary.md` and `review-summary.json` with zero accepted findings. The proposed self-review fallback then writes `findings.md` and `accepted-findings.md`, but Step 4, `review log-phase`, and heavy-worker parent artifacts still read the stale panel-failed summary. Standalone `/review --diff` can print and log a zero-finding summary even when self-review found accepted issues and applied fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: After self-review adjudication, regenerate the normal summary artifacts from the self-review accepted/rejected counts, for example by writing a small tally env and invoking the existing `review emit-tally` contract before Step 4 or heavy-worker return.
  - From Codex-Innovation: Add a minimal summary refresh to `skills/review/references/self-review.md` after accepted-findings adjudication. Reuse the existing `review emit-tally` contract with a self-review tally env, `$ACCEPTED_FINDINGS_FILE`, and `$REVIEW_TMPDIR/oos.md`, or otherwise update `review-round-summary.md` and `review-summary.json` before Step 4.
  - From Codex-Pragmatic: Add a required artifact refresh to the self-review reference before Step 4, shared by inline and heavy-worker paths. Synthesize the self-review counts and run the existing `review emit-tally` path, or explicitly write equivalent `review-round-summary.md` and `review-summary.json` from the self-review artifacts.
  - From Codex-Requirements: Add a required step in `skills/review/references/self-review.md` or the Step 3 branch to regenerate `review-round-summary.md` and `review-summary.json` from the self-review accepted/rejected/OOS artifacts before Step 4 or heavy-worker return.
