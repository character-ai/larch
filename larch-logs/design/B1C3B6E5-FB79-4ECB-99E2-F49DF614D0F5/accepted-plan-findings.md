### FINDING_1: Pin the accepted corpus for the skip filter
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Gate C must explicitly select the accepted findings corpus it passes to `filter-gate-b-skipped`, and its fallback precedence must mirror `compose_review.py`; otherwise it can filter the wrong set and mis-handle cumulative accepted findings or one-by-one skips.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the Accepted plan-review findings audit section, add an explicit filter invocation: `--accepted "$DESIGN_TMPDIR/accepted-plan-findings-all.md"` when that file is non-empty, else `--accepted "$DESIGN_TMPDIR/accepted-plan-findings.md"` (mirror `compose_review.py` precedence), with `--rejected "$DESIGN_TMPDIR/rejected-findings.md"`. State that stdout replaces the classification set input.
  - From Cursor-Arch: Change the edge-case and step-1/2 rules to mirror compose precedence: use non-empty `accepted-plan-findings-all.md`, else non-empty `accepted-plan-findings.md`, else no findings. Apply the same source when calling `filter-gate-b-skipped`.


### FINDING_3: Use the cumulative accepted findings set for fidelity
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Gate C fidelity must compare the final plan against the cumulative applied findings set, not only the last round’s `accepted-plan-findings.md`, or it can misread valid earlier applied changes as unrelated damage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define the Gate C end-state fidelity source as the filtered cumulative accepted-plan-findings-all.md for all Step 3 changes, with accepted-plan-findings.md used only as the active/current Gate B apply file when needed.
  - From Codex-Pragmatic: Define the fidelity set as the filtered cumulative `accepted-plan-findings-all.md`, with Gate B one-by-one skips removed, or add a new cumulative applied-set artifact. Use `accepted-plan-findings.md` only as the latest-round/current apply-set hint, not as the end-state diff authority.
  - From Cursor-Requirements: In audit step 6, trace end-state fidelity against Gate-B-filtered `accepted-plan-findings-all.md` (the cumulative applied set). Reserve `accepted-plan-findings.md` for the current-round Gate B apply set only. Mirror the same rule in `plan-review.md`.
  - From Codex-Requirements: Treat the filtered cumulative accepted-plan-findings-all.md as the end-state applied set for Gate C fidelity, using accepted-plan-findings.md only as latest-round/Gate B context, and update the plan-review.md and approval-gates.md instructions accordingly


### FINDING_4: Fail closed when the skip filter fails
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: If `filter-gate-b-skipped` fails, Gate C must stop rather than continue with an unfiltered accepted set; otherwise it can emit false dissent or fidelity failures and incorrectly block `--skip-approve`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add to audit step 2 and Failure modes: on filter non-zero, print a bounded warning, stop Gate C before persist/prompt/auto-approve (mirror persist-accepted-audit fail-closed). Optionally pin a structural or pytest case for filter failure at Gate C.
  - From Cursor-Pragmatic: When the skip marker is present, require a successful filter helper exit before classification; on non-zero, print a bounded Gate C warning, stop before prompt/auto-approve/Step 5, and preserve `$DESIGN_TMPDIR` for repair (mirror the persist fail-closed block).


