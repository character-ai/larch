## Goal
Implement issue #6155: [IMPLEMENTING] md-to-py-XII: bank the #5983 savings; excise rendered gate copy from approval-gates.md.

## Implementation Plan
## Plan

## Approach

Draft from direct inspection. `approach-synthesis.txt` is `NO_SKETCHES`, so do not claim planning-panel agreement.

Keep the approved outline strict:

- Do not edit `python/larch/design/design_gate_render.py`.
- Do not change rendered Gate A/B/C strings.
- Do not edit `approval-gates-explicit.md` or other conditional references.
- Keep every literal pinned by `scripts/test-design-structure.sh`, `skills/design/scripts/test-gate-b-apply-mode.sh`, and `skills/design/scripts/test-step3-review-cap.sh`.

## Files to modify/create

### UPDATED: skills/design/references/approval-gates.md

Compress only prose that duplicates renderer-owned or Python-owned facts.

Required retained literals (verbatim, do not paraphrase or drop even while trimming adjacent sentences):

- `Run renderer commands as \`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" design render-gate ...\`.`
- `**Shape 2: re-entry from Gate B(c) or Gate C(b) (post-plan)**: run \`python/cli.py design render-gate --gate A\`. Pass the rendered \`HEADER\`, \`QUESTION\`, and option rows directly to \`AskUserQuestion\`.`
- `Run \`python/cli.py design render-gate --gate B --accepted-count "$N" --approve-requested false\`, print \`AUTO_APPLY_MESSAGE\`, then Execute \`### Apply-all body\` verbatim.`
- `Run \`python/cli.py design render-gate --gate C --design-tmpdir "$DESIGN_TMPDIR"\` and pass the rendered \`HEADER\`, \`QUESTION\`, and option rows directly to \`AskUserQuestion\`.`
- `approval-gates-explicit.md`
- The Gate B resume idempotency guard literals pinned near `scripts/test-design-structure.sh` lines 620 onward.
- The numbered settle-dispatch steps, including their indentation.
- `Prompt-side Gate B apply runs only on loop bail-outs` (grep-pinned by `test-step3-review-cap.sh`).
- `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` (grep-pinned by `test-step3-review-cap.sh`).
- The `FINDING_IDS` non-contiguous iteration sentence: "Go-through-each mode: parse `FINDING_IDS` from `gate-b-counts`; it is comma-separated and in document order. Iterate that list only. Never assume a contiguous `1..ACCEPTED_COUNT` range."
- The Severity classification KV binding block (structured `N`/`H`/`M`/`L`; fallback adds `C`).
- The Gate A re-entry fail-closed missing-plan branch: the warning-plus-re-prompt behavior currently under "See full plan branch (re-entry only)" (may be folded inline into the Shape 2 bullet, but the warning text and `--without-see-full-plan` re-prompt instruction must survive somewhere).

Edits:

1. Replace `## Review-round cap` and `### Gate C tier cap` with a short pointer to renderer output:
   - Gate C option shaping comes from `design render-gate`.
   - Consume `REVIEW_ROUND_CAP`, option rows, and `REVIEW_ROUND_COUNT_WARN`.
   - Do not restate `_review_count`, `_gate_c_options`, `effective_authorized_cap`, or cap math.
   - Keep the non-renderer orchestration bullets: Step 3 authority note, Gate A "Discuss more" loops remain uncapped, and the escalation-authorized-cap distinction (Round 3 offered only when escalation/substantiality recorded).

2. Tighten `## Renderer parsing contract`:
   - Keep the invocation and fail-closed parsing rules.
   - Remove repeated "do not reconstruct fallback prompt copy" variants elsewhere.

3. In Gate A:
   - Keep re-entry-only scope, discussion-round2 ownership, and Step 3 re-entry routing.
   - Remove duplicate "See full plan" and "Ready for review" mechanics only where a second bullet restates the same routing already given once; do not remove the only copy of any routing instruction.
   - Preserve the fail-closed missing-`plan.txt` re-entry branch (warning text plus `--without-see-full-plan` re-prompt) — keep it as its own subsection or fold it verbatim into the Shape 2 "See full plan" bullet before deleting the subsection heading; do not drop the branch itself.
   - Do not inline renderer-owned question text.

4. In Gate B:
   - Keep zero-findings, mode selection, resume idempotency, apply-all body, shared post-apply pipeline, settle dispatch, and size-trigger semantics.
   - Remove only the single duplicate sentence restating that the script-internal controller does not apply findings (the earlier one in the mode-selection paragraph); keep the `Prompt-side Gate B apply runs only on loop bail-outs` sentence and its loop-mode resume instruction verbatim exactly as they read today.
   - Shorten the Severity classification contract prose (the CLI list and the Python-owned framing sentence) but keep the KV binding block verbatim, including the `FINDING_IDS` non-contiguous iteration sentence; the only prunable line is the fallback-bucketing predicate-matching sentence if it duplicates the CLI's own doc.
   - Keep the explicit-mode load gate intact.

5. In Gate C:
   - Keep presentation, guideline persistence fail-closed behavior, panel-failed warning, Other dispatch, and approve-is-not-a-halt.
   - Remove renderer-owned prompt copy and cap-option restatements (including `### Gate C tier cap` per edit item 1).
   - Use labels only where branch behavior needs them.

### MAY_UPDATE: python/skill-closure-baseline.json

Update only if the live `design` eager closure drops after the Markdown edit.

Procedure:

1. Run `python3 python/cli.py skill-closure report` before and after the edit; record both `closure_estimated_tokens` and `closure_content_estimated_tokens` for `design`.
2. **Acceptance gate (blocking, not just informational)**: the post-edit `design` closure token count (or content-token count, name whichever is reported) must fall by at least ~1000 tokens versus the pre-edit measurement, matching the issue's ballpark target. If the drop is short of that, continue compressing renderer-duplicated prose within the retained-literal constraints above before finishing — do not stop at "tests pass" alone.
3. Once the target drop is confirmed, run `python3 python/cli.py lint skill-closure-growth --write`.
4. Inspect the JSON diff. Keep only expected lower baseline changes. Do not commit a same-PR raise.
5. If the design closure does not drop at all, do not edit this file.

## Edge cases

- `approval-gates.md` is prompt contract, not ordinary docs. Keep operational routing even when prose is compressed.
- Literal grep pins are brittle, and span three harnesses (`test-design-structure.sh`, `test-gate-b-apply-mode.sh`, `test-step3-review-cap.sh`). Check the exact strings before finalizing.
- Do not remove the `approval-gates-explicit.md` conditional load. It protects eager closure while preserving `--per-round-approval`.
- Do not move Gate C behavior into Python. The renderer owns prompt copy only, not all gate control flow.
- A tied or low-confidence savings pass (e.g., dropping only a few tokens like #5983) fails the acceptance gate in item 2 above even if every test is green.

## Failure modes

- Over-trimming can change gate semantics by dropping fail-closed stops, resume phases, or post-apply settle routing.
- Lowering the closure baseline from an unclean environment can create unrelated baseline churn.
- Removing a pinned string can fail structure tests even if behavior is unchanged.
- Leaving renderer-owned copy in `approval-gates.md` (including `### Gate C tier cap`) can miss the token-savings goal.

## Testing strategy

Run targeted checks:

1. `python3 python/cli.py skill-closure report` (before and after; enforce the acceptance gate above)
2. `bash scripts/test-design-structure.sh`
3. `bash skills/design/scripts/test-gate-b-apply-mode.sh`
4. `bash skills/design/scripts/test-step3-review-cap.sh`
5. `python3 -m pytest python/tests/design/test_design_gate_render.py`
6. If `python/skill-closure-baseline.json` changes, run `python3 python/cli.py lint skill-closure-growth --skill design`.

Record the before and after design closure totals in the implementation summary.

## Acceptance

Run targeted checks:

1. `python3 python/cli.py skill-closure report` (before and after; enforce the acceptance gate above)
2. `bash scripts/test-design-structure.sh`
3. `bash skills/design/scripts/test-gate-b-apply-mode.sh`
4. `bash skills/design/scripts/test-step3-review-cap.sh`
5. `python3 -m pytest python/tests/design/test_design_gate_render.py`
6. If `python/skill-closure-baseline.json` changes, run `python3 python/cli.py lint skill-closure-growth --skill design`.

Record the before and after design closure totals in the implementation summary.

diff_lines: 150

## Test plan
(no test plan section in plan-file)
