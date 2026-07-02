### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: /design degraded-empty-collector self-review must pin the post-plan emit launcher when plan.txt changes. Scenario: The Step 3 branch says to run the same post-plan validation/settle path after in-place plan edits, but it does not name `python/cli.py design postplan-emit` or `design-step2b-postplan.sh`. Other design steps pin that helper for every plan revision. An ad-hoc settle can skip `diff-lines.txt`, trailers, and command validation, and Step 5c publish can fail or ship stale plan metadata.
- **Proposed resolution**: In `skills/design/SKILL.md`, after self-review may edit `plan.txt`, require the same launcher used elsewhere: `python/cli.py design postplan-emit` (or `design-step2b-postplan.sh` with the existing site flags) before `design-step3-gate-b-bypass.sh`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/topology.tsv:14-15
- **Concern**: Conflict-resolution Phase 3 rewrite omits topology row sync. Scenario: The firm rewrite removes the external 3-reviewer conflict panel from `skills/implement/references/conflict-resolution.md`, but the plan does not update `skills/shared/topology.tsv` or regenerate `docs/topology.md`. Row `implement.conflict_review.panel` still requires the literal value `3-reviewer` to appear verbatim in that authority file per `.claude/rules/topology-generation.md`. After Phase 3 drops externals, `python3 python/cli.py generate topology-docs` fails and `docs/topology.md` stays wrong.
- **Proposed resolution**: Add `### UPDATED: skills/shared/topology.tsv` (and regenerated `docs/topology.md`) with a new `value` that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent`), then run `python3 python/cli.py generate topology-docs`.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:3-5
- **Concern**: The plan adds a runtime `self-review-required` caller but leaves the self-review reference header and opening condition scoped only to `self_review=true`.. Scenario: When `/implement` Step 5 receives `STEP5_REVIEW_STATUS=self-review-required`, the branch reads this reference, but the reference still says it loads and runs only for explicit `--self-review`; the runtime fallback can be skipped or treated as outside the reference contract.
- **Proposed resolution**: Update `Consumer`, `When to load`, and the first body sentence to name both entry conditions: explicit `self_review=true` and runtime zero-survivor `STEP5_REVIEW_STATUS=self-review-required`.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/references/self-review.md:1
- **Concern**: The new `/review` self-review handoff writes accepted findings but does not refresh the normal review summary/tally artifacts after self-review adjudication.. Scenario: `review core` already emitted `review-round-summary.md` and `review-summary.json` on the `panel-failed` path with zero accepted findings; if self-review then finds accepted issues, Step 4 and nested heavy-worker parent artifacts can still report the stale zero-finding summary.
- **Proposed resolution**: After self-review adjudication, regenerate the normal summary artifacts from the self-review accepted/rejected counts, for example by writing a small tally env and invoking the existing `review emit-tally` contract before Step 4 or heavy-worker return.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/topology.tsv:14
- **Concern**: skills/shared/topology.tsv not updated when conflict-resolution drops the external panel. Scenario: `python/larch/rendering/_rendering_generators.py` requires each topology `value` to appear verbatim in `runtime_authority`. The plan rewrites `skills/implement/references/conflict-resolution.md` Phase 3 to main-agent self-review and removes the `3-reviewer` panel text, but row `implement.conflict_review.panel` still pins value `3-reviewer` to that file. `python3 python/cli.py generate topology-docs --check` then fails and `docs/topology.md` stays wrong.
- **Proposed resolution**: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`): change `implement.conflict_review.panel` value/composition to the new self-review shape (e.g. `main-agent`) and keep the literal in the rewritten conflict-resolution reference.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:415-420
- **Concern**: `/design` degraded-empty-collector self-review omits the pinned postplan launcher when `plan.txt` changes. Scenario: The new branch says to run the same post-plan validation/settle path after in-place `plan.txt` edits, but unlike Step 2b/Gate B it does not name `python/cli.py design postplan-emit` or `design-step2b-postplan.sh`. Elsewhere the skill requires postplan emit for any plan revision (`diff-lines.txt`, command validation). Ad-hoc settle or `design-step35-settle.sh` can skip trailers/validators or assume Gate B findings artifacts that do not exist on the bypass path.
- **Proposed resolution**: In the `LOOP_STATUS=degraded-empty-collector` branch, when self-review rewrites `plan.txt`, require `python/cli.py design postplan-emit` (or the existing launcher fence) before `design-step3-gate-b-bypass.sh`; skip emit when the plan is unchanged.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/self-review.md:3-5
- **Concern**: `self-review.md` header still limits load to explicit `--self-review` only. Scenario: The plan adds a runtime `STEP5_REVIEW_STATUS=self-review-required` consumer in prose but leaves `**Consumer**` and `**When to load**` bound to `self_review=true` only. An implementer can update `skills/implement/SKILL.md` yet leave the reference telling orchestrators not to load it on the zero-survivor path.
- **Proposed resolution**: Update `**Consumer**` and `**When to load**` to cover both `self_review=true` and `STEP5_REVIEW_STATUS=self-review-required`, matching the new entry-condition note.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/references/self-review.md:121-133
- **Concern**: `/review` self-review handoff does not refresh the Step 4 summary artifacts after replacing panel output with main-agent findings. Scenario: `review core` already wrote `review-round-summary.md` and `review-summary.json` during the zero-survivor `panel-failed` emit with 0 accepted findings. The proposed self-review then writes `findings.md` and `accepted-findings.md`, but proceeds to `/review-and-fix` or Step 4 without rewriting those summary artifacts, so standalone `/review --diff` can print and log a stale zero-finding panel-failed summary even when self-review found accepted issues.
- **Proposed resolution**: Add a minimal summary refresh to `skills/review/references/self-review.md` after accepted-findings adjudication. Reuse the existing `review emit-tally` contract with a self-review tally env, `$ACCEPTED_FINDINGS_FILE`, and `$REVIEW_TMPDIR/oos.md`, or otherwise update `review-round-summary.md` and `review-summary.json` before Step 4.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/references/self-review.md:121-133
- **Concern**: Self-review fallback updates findings but not review summary artifacts. Scenario: `review core` already emitted panel-failed zero-count summary artifacts before the fallback. Inline `/review` can then self-review and apply fixes, but Step 4 prints or logs stale `review-round-summary.md` and `review-summary.json`, silently misreporting accepted findings and fixes.
- **Proposed resolution**: Add a required artifact refresh to the self-review reference before Step 4, shared by inline and heavy-worker paths. Synthesize the self-review counts and run the existing `review emit-tally` path, or explicitly write equivalent `review-round-summary.md` and `review-summary.json` from the self-review artifacts.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: skills/shared/topology.tsv:14-15
- **Concern**: Conflict-resolution rewrite omits topology row sync. Scenario: `python/larch/rendering/_rendering_generators.py` requires each topology `value` to appear verbatim in its `runtime_authority`. Removing the external `3-reviewer` panel from `skills/implement/references/conflict-resolution.md` without updating row `implement.conflict_review.panel` breaks `python3 python/cli.py generate topology-docs` / `generate check` and leaves `docs/topology.md` projecting a removed panel.
- **Proposed resolution**: Add `### UPDATED: skills/shared/topology.tsv` (and regenerate `docs/topology.md`) with a new `implement.conflict_review.panel` value that appears verbatim in the rewritten conflict-resolution reference (for example `main-agent self-review`), plus matching composition text.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: /design degraded-empty-collector self-review does not pin post-plan emit helper. Scenario: Step 3 self-review may edit `plan.txt`, but the plan only says to run the same post-plan validation/settle path without naming `python/cli.py design postplan-emit` or `design-step2b-postplan.sh`. Other design revision sites pin that helper; ad-hoc settle can skip `diff-lines.txt`, trailers, or command validation before Step 3b/5c.
- **Proposed resolution**: In the `LOOP_STATUS=degraded-empty-collector` branch, after any in-place `plan.txt` edit, invoke `python/cli.py design postplan-emit` through the existing launcher (same contract as Gate B / discussion re-emits) before `design-step3-gate-b-bypass.sh`.

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/review/SKILL.md:71-73
- **Concern**: `/review` self-review does not refresh the Step 4 summary artifacts. Scenario: `review core` writes a zero-count `review-round-summary.md` on `panel-failed`; the proposed self-review then can populate `accepted-findings.md` and apply fixes, but Step 4 and `review log-phase` still print or log the stale panel-failed summary. This regresses the existing `/review` artifact contract on the new fallback path.
- **Proposed resolution**: Add a required step in `skills/review/references/self-review.md` or the Step 3 branch to regenerate `review-round-summary.md` and `review-summary.json` from the self-review accepted/rejected/OOS artifacts before Step 4 or heavy-worker return.
