### FINDING_1: Gate B literal pins must survive dedupe
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-Gate Prompt Contract
- **Severity**: blocking
- **Concern**: The planned Gate B dedupe risks deleting exact strings that `skills/design/scripts/test-step3-review-cap.sh` grep-pins, including `Prompt-side Gate B apply runs only on loop bail-outs` and `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation`. Paraphrase or deletion would break the review-cap harness even if the behavior stays the same.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add both strings to Required retained literals (or an explicit do-not-remove harness pins bullet). Gate B dedupe must keep at least one copy of each exact line.
  - From Codex-Innovation: Keep that sentence verbatim in the condensed rewrite, or preserve the exact literal in an equivalent nearby line.
  - From Cursor-Pragmatic: Add that literal to Required retained literals (or an explicit harness pin list) and say dedupe must preserve it verbatim while trimming only the adjacent duplicate clause.
  - From Cursor-dyn-Gate Prompt Contract: Add `Prompt-side Gate B apply runs only on loop bail-outs` and `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` to required retained literals. Narrow edit item 4: remove only the preceding `The script-internal controller…does not apply` sentence; keep line 84 verbatim.


### FINDING_3: Closure savings target needs an explicit pass/fail gate
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan records before/after closure totals, but nothing makes the ~1k-token eager-closure reduction a merge blocker. That allows a green, low-savings edit to land without meeting the stated acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After the Markdown edit, require `python3 python/cli.py skill-closure report` to show a material `design` closure drop (issue ballpark ~1k tokens). If below target, keep compressing within `approval-gates.md` before merge; do not lower `python/skill-closure-baseline.json` unless closure actually drops.
  - From Cursor-Innovation: With diff_lines: 140 and most file volume in non-renderer routing (Gate B post-apply, Gate C presentation), a prose-only pass can land well under 1k tokens yet still pass listed tests, repeating #5983's 1-byte savings outcome. Add an explicit completion gate: after skill-closure report, require closure_content_estimated_tokens to fall by at least ~1000 vs pre-edit (and forbid baseline raise); if not met, continue trimming renderer-duplicated prose before PR.
  - From Cursor-Pragmatic: Add an explicit acceptance check after `skill-closure report`: require a meaningful closure drop (per issue ballpark) before merge; if short, continue compressing within pinned literals or stop without lowering the baseline.
  - From Cursor-Requirements: Add an explicit pass/fail gate: after compression, require closure_estimated_tokens (or name the authoritative metric) to fall by at least ~1000 vs the pre-edit report; if not met, iterate on additional renderer-owned duplicate prose before merge; do not raise python/skill-closure-baseline.json in the same PR


### FINDING_5: Severity classification compression needs the routing contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Shortening the severity section risks dropping the `FINDING_IDS` iteration contract, the replay rule for `REVIEW_ROUND_COUNT_WARN`, or the KV bindings that keep explicit-mode and fallback handling aligned. Those are routing contracts, not optional prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When shortening §Severity classification, explicitly retain the `FINDING_IDS` / non-contiguous iteration bullet as a required behavioral literal alongside the CLI list.
  - From Cursor-Innovation: Add that full sentence to Required retained literals (or an explicit do-not-remove pin beside the renderer invocation literals).
  - From Cursor-Innovation: Extend Required retained literals with the KV binding block (N/H/M/L, optional C, and FINDING_IDS iteration rule) or mark that subsection as do-not-compress beyond de-duplicating the duplicate controller sentence on line 83.
  - From Cursor-Requirements: In item 4, name minimum retained contracts: gate-b-counts is sole authority; keep only a one-line pointer that explicit-mode FINDING_IDS / GATE_B_SEVERITY_MODE live in approval-gates-explicit.md; explicitly remove line 73 predicate-bucketing prose


### FINDING_6: Gate A re-entry must preserve the fail-closed missing-plan branch
- **Reviewer(s)**: Cursor-dyn-Gate Prompt Contract
- **Severity**: important
- **Concern**: Compressing the See full plan / Ready for review mechanics can drop the fail-closed re-entry path for absent or empty plan.txt, leaving no normative way to re-render Gate A with the no-plan branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Gate Prompt Contract: Exempt line 45 from dedupe: either keep `### See full plan branch (re-entry only)` or inline its warning plus `--without-see-full-plan` re-prompt into the Shape 2 See full plan bullet before removing the subsection.


