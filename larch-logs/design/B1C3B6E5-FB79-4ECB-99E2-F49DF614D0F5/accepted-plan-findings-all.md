### FINDING_1: Stale skip-approve carve-out
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The Gate C `--skip-approve` flow still has a stale auto-approve carve-out and an insufficient post-audit predicate, so unattended runs can approve before audit or ignore strong dissent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the Gate C opening carve-out to match the new flow: run accepted-findings audit after guideline persistence; auto-approve only when `skip_approve_requested=true` and audit has no strong dissent; otherwise force the Gate C prompt.
  - From Cursor-Arch: Update Step 4b to compute auto-approve only after Presentation audit completes (`skip_approve_requested && !strong_audit_dissent`); on strong dissent, require `AskUserQuestion` and pass `--accepted-audit-escalation true` to `design render-gate`.
  - From Cursor-Innovation: Gate C --skip-approve and render-gate contracts still describe pre-audit auto-approve. Scenario: Line 149 still auto-approves immediately after persist-design-assessment, and the Prompt section still documents render-gate --gate C without --accepted-audit-escalation; an implementer could follow those stale paragraphs and skip the audit or omit dissent in the AskUserQuestion
  - From Cursor-Pragmatic: Rewrite the line-149 carve-out to run accepted-findings audit after guideline persistence and auto-approve only when audit has no strong dissent; in Prompt, pass --accepted-audit-escalation true alongside existing flags when strong dissent is recorded
  - From Cursor-Requirements: Replace approval-gates.md:149-149 carve-out text so auto-approve runs only after accepted-findings audit persistence succeeds and records no strong disagreement; keep strong dissent forcing AskUserQuestion even when skip_approve_requested=true.


### FINDING_2: Render-gate calls miss escalation flag
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Gate C prompt render calls do not reliably propagate the audit outcome into `--accepted-audit-escalation`, so strong dissent can be dropped from the prompt on initial and re-fire paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Initial Gate C prompt and See full plan re-fires still document design render-gate --gate C with only --panel-failed / --without-see-full-plan. Strong dissent would stay in chat prose only and drop from the rendered approval question on re-prompt paths.
  - From Cursor-Requirements: Update every Gate C render-gate invocation in approval-gates.md (and matching SKILL.md Step 4b prose) to pass `--accepted-audit-escalation true|false` from the audit outcome; pin the flag in test-design-structure.sh if command text is pinned.


### FINDING_3: Audit read set misses refusal/outline context
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The Gate C audit read list omits durable Round 1 refusal and approved-outline non-goal sources, so the strong-dissent bar can miss conflicts that are not copied into `plan.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add non-empty $DESIGN_TMPDIR/discussion-round1.md and approved $DESIGN_TMPDIR/design-outline.md to the mandatory Gate C audit reads, or an equivalent source that contains both Round 1 refusals and outline non-goals, before classifying strong disagreement.
  - From Cursor-Innovation: Add non-empty discussion-round1.md and, when .outline-approved exists, design-outline.md to the mandatory read list before classification
  - From Cursor-Pragmatic: Add discussion-round1.md and, when .outline-approved exists, design-outline.md to the mandatory read list (untrusted evidence) before classification
  - From Codex-Pragmatic: Add `discussion-round1.md` and `design-outline.md`, or another durable artifact containing both explicit refusals and approved non-goals, to the Gate C audit read list when present. Treat them as untrusted evidence.
  - From Cursor-Requirements: Add discussion-round1.md when non-empty and design-outline.md when non-empty and .outline-approved exists to the mandatory audit read list; state they are untrusted evidence for refusal/non-goal checks only.
  - From Codex-Requirements: Add the relevant durable context to the mandatory audit read list, at least discussion-round1.md for explicit refusals and design-outline.md for approved-outline non-goals when present, and restrict their use to the stated strong-disagreement check


### FINDING_4: Gate B skip markers need filtering
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Auditing raw `accepted-plan-findings-all.md` without one-by-one skip filtering can misclassify operator-skipped findings as application failures or false dissent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the Gate C audit instructions, when rejected-findings.md contains that one-by-one marker, classify only the filtered accepted set (reuse compose_review._filter_gate_b or equivalent); do not treat operator-skipped findings as missing application fidelity or strong dissent
  - From Cursor-Requirements: For acceptance vs fidelity, read accepted-plan-findings.md as the applied set; when rejected-findings.md contains one-by-one skip markers, exclude those blocks from fidelity checks (mirror compose_review _filter_gate_b) instead of treating -all as sole authority.


### FINDING_6: Gate C audit must rerun on re-entry
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: An old accepted-findings audit can be reused on Gate C re-entry, so later discussion or fixes may ship against stale audit state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: A stale audit from an earlier Gate C pass can approve the wrong plan after discussion, re-run review, or postplan fixes Mirror the guideline contract: rerun the full audit on every Gate C Presentation, including resume@4b, and overwrite accepted-plan-findings-audit.md


### FINDING_8: Mild audit notes need printing
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: Mild disagreements need a printed compact digest before prompt or skip-approve breadcrumb, or the audit trail becomes non-obvious.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Require Gate C to print a compact non-clean audit digest before either the prompt or the `--skip-approve` auto-approval breadcrumb. Keep the clean path silent except for the persisted clean note.


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


