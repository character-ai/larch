# Accepted plan-review findings (main-agent adjudicated)

Step 3 voting failed on tooling (Codex voter exit-7; Claude voter returned a non-responsive "Ready to review…" message → 15/15 unparseable; only Cursor voted). The panel's findings were sound, so the main agent adjudicated the ballot and applied all of them to `plan.txt`.

All findings **ACCEPTED and APPLIED**:

- FINDING_1 / FINDING_10 — HARD round-1 assessor fixtures + `apply_step3_6_handoff` still expect skip → rewrite for round-1 dispatch on both tiers (`test-design-plan-quality-assessor.sh`).
- FINDING_2 — orphaned classification-WARN fixtures in `test-design-postplan-emit.sh` → enumerate and drop/rewrite.
- FINDING_3 — remaining `HARD-only` Step 3.6 prose in `SKILL.md` (Gate-B handoff + helper catalog) → drop.
- FINDING_4 / OOS_1 — `approval-gates.md` + `plan-review.md` "on HARD runs" qualifiers → both tiers.
- FINDING_5 — `test-design-structure.sh` pins the retired `design_classification=…; skipped` breadcrumb → replace with a both-tier assessor-invocation pin; update the `(HARD-only)` comment pins.
- FINDING_6 — `test-assess-plan-round.sh` two-entry integration Entry 1 still expects skip → rewrite for round-1 dispatch.
- FINDING_7 — `test-run-step3-review.sh` SIMPLE cursor-advance coverage is a non-existent "mirror" → add an explicit new SIMPLE success case.
- FINDING_8 — `scripts/design-pause-load.sh` `STEP=3b`→`3.6` upgrade is `== "HARD"`-gated → drop the tier condition so SIMPLE resumes also reach the assessor; add a SIMPLE resume case to `test-design-pause-resume.sh`.
- FINDING_9 / OOS_2 — `SECURITY.md:135` labels the assessor lane HARD-only → tier-agnostic wording, controls preserved.
- FINDING_11 — round-1 prompt duplicates Original/Previous anchors with no guidance → add a round-1 note in `render-assessor-prompt.sh` + test coverage.
- FINDING_12 (scope-reduction) — keep `--design-classification` as an accepted-but-ignored compat no-op rather than deleting it and churning the caller.
- OOS_3 — `design-postplan-emit.sh` `snapshot-failed` message says "HARD assessor flow" → drop "HARD".

OOS_1/OOS_2/OOS_3 folded in-scope (one-line doc/message consistency for this same tier-opening change; not filed as separate issues).
