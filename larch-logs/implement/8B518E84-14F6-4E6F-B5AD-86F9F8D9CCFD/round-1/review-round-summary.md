# Review Round 1

- Mode: `diff`
- 2 accepted, 7 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Auto-compose duplicates top-level `## Plan` header
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Auto-compose wraps full `plan.txt` including its leading `## Plan` inside another `## Plan` section. Production `plan.txt` normally starts with `## Plan`, so auto-composed `composed-plan.md` gets duplicate `## Plan` headers unlike orchestrator-authored artifacts; publish may succeed with the wrong `larch:plan` shape. Tests only use `plan.txt` starting with `## Approach`, not the production `## Plan` shape, so CI passes while the dominant auto-compose path emits double `## Plan` on real runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Strip leading `## Plan` (and blank lines) from `body_lines` before wrapping, matching manual composition.
  - From cursor-specialist-correctness-output.txt: Add test with `plan.txt` starting `## Plan`; assert single top-level `## Plan` in composed output.


### FINDING_11: Missing terminal `diff_lines` trailer should fall back to `diff-lines.txt`
- **Reviewer(s)**: dyn-dyn-auto-compose-output.txt
- **Severity**: important
- **Concern**: When `plan.txt` has no valid terminal `diff_lines:` trailer, auto-compose puts the full file under `## Plan` and emits no trailer block. `finalize-step5.md` and `skills/design/SKILL.md` say composition may take `diff_lines` from `$DESIGN_TMPDIR/diff-lines.txt`; `plan_review.py` writes that file during review. A plan that lost its trailer but still has `diff-lines.txt` will auto-compose without `diff_lines:`, and `design_publish._splice_plan_provenance` then splices `review_status` / `rounds_completed` without a stable trailer anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-auto-compose-output.txt: After the split, if no trailer block was found, read `diff-lines.txt` (and optional size trailers when present) and append a canonical trailer block before writing `composed-plan.md`.


