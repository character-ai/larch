### OOS_1: [OUT_OF_SCOPE] Auto-error-reporting dedup and relocated `panel-init-failed` semantics
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Removing the auto-error-reporting sentence that distinguished terminal `panel-init-failed` from non-terminal `panel-failed` / `tally-error` / `degraded-empty-collector` is intentional dedup; those semantics now live in the `NEXT_ACTION` table and lazy-loaded `plan-review.md` (including terminal framing at `plan-review.md:65` and `NEXT_ACTION=final-summary:failed-judge-panel`). Always-loaded context is thinner, but this is a plan-accepted tradeoff; terminal hard-stop coverage remains via scope-anchoring and `final-summary:failed-judge-panel`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: No change required unless operators report confusion; the plan explicitly targeted always-loaded dedup.

### OOS_2: [OUT_OF_SCOPE] `record-escalation` ownership relocation and harness coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: `record-escalation` ownership no longer appears in always-loaded `SKILL.md`; it moved entirely to `plan-review.md:63` per explicit plan intent. The wrapper still owns escalation mechanically (`design-step3-review.sh` + tests), and first-time Step 3 entry requires reading `plan-review.md`. The relocated note is not grep-pinned in harnesses (only `python/larch/review/plan_review.py` is, via `test-design-step3-review.sh`); orchestrator mis-calls are prevented by Python, not prose regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a one-line grep in `test-design-step3-mav.sh` prose checks if prompt-side duplicate `record-escalation` calls recur.

### OOS_3: [OUT_OF_SCOPE] Missing CI harness for dedup structural invariants
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Plan acceptance lists manual structural grep checks (single fallback sentence, absent report-gate block, `NEXT_ACTION` wording), but no CI harness pins those invariants. A future reintroduction of duplicate prose or the deleted report-gate block would not fail automated tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Optional follow-up: add grep pins to `test-step3-orchestrator-fence.sh` or `test-step3-review-cap.sh` if dedup regressions become recurring; out of scope for this prose-only change per plan.

**Merge notes**
- In-scope FINDING_1–3 are distinct code-path anchors (prelaunch hard-stop, terminal `final-summary:*`, non-terminal `step3b-bypass`); not merged.
- OOS FINDING_4 + FINDING_7 merged (same relocated auto-error-reporting / `panel-init-failed` semantics theme).
- OOS FINDING_5 + FINDING_8 merged (same `record-escalation` relocation theme; different fix directions kept as separate bullets).
- OOS FINDING_6 kept separate (SKILL.md structural-invariant CI gap, distinct from FINDING_5’s `plan-review.md` grep gap).
- `cursor-specialist-edge-cases`: FINDING_1–5. `cursor-specialist-testing`: FINDING_4–6 only (out-of-scope-only slot; never on in-scope blocks).
- In-scope blocks omit revision bullets where sources gave no verbatim fix (placeholder “Address the concern above” not quoted).
