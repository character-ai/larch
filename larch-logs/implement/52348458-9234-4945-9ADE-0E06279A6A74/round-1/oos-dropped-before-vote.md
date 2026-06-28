### OOS_1: [OUT_OF_SCOPE] Plan fidelity, edge cases, cross-refs, and prior regression fix verified
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Implementation matches the approved split: `approval-gates-explicit.md` holds the former Gate B `Prompt` and `One-by-one iteration prompt` bodies unchanged; `approval-gates.md` adds `### Explicit-mode load gate` after `### Presentation` with load only when `approve_requested=true` and post-apply-only resume excluded; `SKILL.md` Step 3.5 forbids entry-level load and defers to the Gate B body. Zero-findings short-circuit still runs before Presentation, explicit load, and prompts; default auto-apply skips explicit load to `### Apply-all body`; post-apply-only resume is handled by the Step 3.5 entry idempotency guard before the Gate B body. References to `### Apply-all body` and `### Shared post-apply pipeline` remain valid because Step 3.5 still MANDATORY-reads `approval-gates.md` first. The earlier design finding about loading `approval-gates-explicit.md` at Step 3.5 entry (before zero-findings / resume guards) is addressed by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Harness and lint checks pass; manual acceptance greps hold
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `bash skills/design/scripts/test-gate-b-apply-mode.sh` — PASS. `bash scripts/test-design-structure.sh` — PASS. `python3 python/cli.py lint readability-preamble` — exit 0. Manual acceptance greps from the plan also hold (zero-findings short-circuit and auto-apply breadcrumb in `approval-gates.md`; `## Prompt` / `## One-by-one` / **When to load** in `approval-gates-explicit.md`; no entry-level `MANDATORY` read of `approval-gates-explicit.md` in `SKILL.md`).
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Normative-source prose drift after explicit Gate B split
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md:353` and `skills/design/references/approval-gates.md:7,11` still say `approval-gates.md` is the **single normative source** for Gate A/B/C prompts, but explicit Gate B prompt choreography now lives in `approval-gates-explicit.md`. That predates this split but is amplified by it; an orchestrator could treat the Step 3.5 whole-file read as sufficient and under-load explicit mode, though Step 3.5 now also says not to load at entry and the load gate has a `MANDATORY READ`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Split normative-source prose in Step 1e and the `approval-gates.md` Contract/Binding header to match the deferred-load contract.

### OOS_4: [OUT_OF_SCOPE] CI does not assert deferred-load contract for `approval-gates-explicit.md`
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: latent
- **Concern**: The split’s core contract (deferred explicit load, no entry-level SKILL load, prompt bodies only in the child reference) is verified by manual grep in acceptance, not by harness assertions. Existing tests still grep legacy `approval-gates.md` strings only; reintroducing early load or inline prompts would pass CI. The Gate B harness (`test-gate-b-apply-mode.sh:72-75`) does not assert that `approval-gates-explicit.md` is loaded only through the deferred load gate; future wording drift could slip past CI because coverage only checks the auto-apply breadcrumb and a prose hint. Plan scoped test changes out, so this is follow-up hardening, not a merge blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add structural greps (mirroring round VII `progress-reporting` / `step-prefix-encoding` manual-verify pattern, or pins in `test-design-structure.sh`). Plan scoped this out ("do not change … tests"), so this is follow-up hardening, not a merge blocker.
  - From codex-specialist-testing: Extend the harness with one assertion that the explicit file is loaded only through the deferred load gate

### OOS_5: [OUT_OF_SCOPE] `approval-gates-explicit.md` absent from readability-preamble lint manifest
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `scripts/lint-readability-preamble.tsv` does not list `approval-gates-explicit.md`. Lint still passes because only listed files are checked. Low risk today (the file is prompt choreography, not user-facing prose composition), but future edits would not get preamble enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a manifest row if the file grows orchestrator-inline prose.

---

**Merge notes (for voters, not machine output):**
- Input FINDING_1–4 → **FINDING_1** (same slot, all affirmative verification).
- Input FINDING_5 kept in-scope as **FINDING_2**; input FINDING_9 kept separate as **FINDING_4** `[OUT_OF_SCOPE]` (same risk, different scope tags).
- Input FINDING_6–8 → **FINDING_3**.
- Input FINDING_10 + FINDING_12 → **FINDING_5** `[OUT_OF_SCOPE]`.
- Input FINDING_11 → **FINDING_6** `[OUT_OF_SCOPE]`.
- All four inventory slots appear; `codex-specialist-testing` appears only in the `[OUT_OF_SCOPE]` **FINDING_5** block.

