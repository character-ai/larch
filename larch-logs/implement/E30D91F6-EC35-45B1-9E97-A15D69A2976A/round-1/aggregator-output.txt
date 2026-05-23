Here is the normalized aggregation. Same behavioral risks are merged; `[OUT_OF_SCOPE]` stays on headings only where every merged source was OOS or the merged group includes an OOS-tagged input and the rule requires the tag (here OOS-only groups and standalone OOS items keep the tag; **FINDING_6** is in-scope only—**not** merged with **FINDING_22**).

---

### FINDING_1: Progress Reporting still documents nested /design breadcrumb behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: After nested-mode / `SESSION_ENV_PATH` removal, `skills/design/SKILL.md` (Progress Reporting, ~34–36) still tells orchestrators to prepend parent context “when nested,” which contradicts standalone-only /design and can be read as supported nested transport or optional nested mode distinct from `STEP_NUM_PREFIX` / `PARENT_SKILL_PATH` env prefixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_2: CHANGELOG 41.0.0 understates co-shipped /design and tally/test surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The 41.0.0 section emphasizes round-trip removal but omits or underplays /design nested-mode cleanup, tally/OOS contract changes, and related harness/assertion updates shipped in the same bump, weakening traceability for operators and automation that read only the CHANGELOG.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_3: Large combined diff complicates bisect, testing focus, and PR narrative
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Round-trip removal, /design nested cleanup, version bump, and `larch-logs` (and related churn) land together, so regressions are harder to bisect/revert/cherry-pick and reviewers may under-test non-design areas when the PR is framed narrowly (e.g. #2597 only).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_4: Recursive grep assertions lack binary-file guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `scripts/test-design-structure.sh` (around 4255–4262) uses recursive `grep` without guarding against binary matches; future non-text under `skills/design/` could make `-rEq` noisy or ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_5: [OUT_OF_SCOPE] Stale historical CHANGELOG bullets about nested tally/plan/review flushing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Sections before 41.0.0 can still describe removed nested flushing; readers who do not respect version boundaries may think removed behavior still exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_6: voting-protocol still maps design OOS to IMPLEMENT_TMPDIR after design-local layout change
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `skills/shared/voting-protocol.md` (around 277) still implies design/review-accepted OOS for voting lives under `$IMPLEMENT_TMPDIR`; post parent-tmpdir handoff / #2588-style split, design OOS is written under `$DESIGN_TMPDIR`, so readers may expect `IMPLEMENT_TMPDIR/oos-accepted-design.md` from plan review incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### FINDING_7: [OUT_OF_SCOPE] Committed run-log / larch-logs diff volume as review noise
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Large `larch-logs/**` (and similar) diffs add review friction; treated as policy-intentional / expected artifacts, not a regression from this feature set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_8: Plan acceptance implies /design --trivial E2E smoke but diff shows only static tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Acceptance text calls for a real `/design --trivial` smoke; the diff may not record that run, risking merge without exercising loader paths (e.g. `CLAUDE_PLUGIN_ROOT` expansion) and interactive behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_9: Check 13 comment still describes parent /implement OOS handoff removed from tally-plan-review
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `scripts/test-design-structure.sh` (around 4269–4272) comment still references parent `/implement` OOS handoff via `plan-review.md` / parent tmpdir wiring that `tally-plan-review.sh` no longer implements; misleads maintainers searching for obsolete paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_10: Token-ledger marks removed from design Steps 3 / 3.5 / 3b
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Removing token-ledger marks from plan review, Gate B, and diagram timing loses fine-grained token attribution for those phases versus prior behavior, without a clear runtime error—budget comparisons across plugin versions may skew unless omission is intentional and documented or marks are restored in a standalone-safe way.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_11: CLAUDE_PLUGIN_ROOT export depends on loader expansion; weak static detection
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: `skills/design/SKILL.md` export of `CLAUDE_PLUGIN_ROOT` relies on the skill loader expanding `${CLAUDE_PLUGIN_ROOT}` inside quotes before Bash; A5 cannot catch missing expansion, so failures surface late as broken paths; security angle: empty or wrong value could resolve `scripts/...` under an unintended root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document manual /design smoke in PR; consider future render-time self-check if tooling allows.
  - From cursor-specialist-security-output.txt: Keep A5 pin; add post-export non-empty guard with explicit error exit or document fatal misconfiguration in SECURITY.md writer contract.

---

### FINDING_12: Farewell anti-pattern still references returning to /implement orchestrator
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `skills/design/SKILL.md` (around 733) farewell examples still point at `/implement`, which is a minor inconsistency with standalone-only framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_13: Lifecycle rename no longer strips legacy [ROUND-TRIP] marker from titles
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `scripts/tracking-issue-write.sh` (around 439–471): after removing round-trip compose/strip helpers, renames may preserve mistaken `[ROUND-TRIP]` (or similar legacy bracket) text in titles indefinitely without a narrow managed-marker strip or documented recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_14: Implement / ship-pr still read IMPLEMENT_TMPDIR oos-accepted-design.md while tally no longer mirrors parent tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `skills/implement/SKILL.md` and `scripts/ship-pr.sh` still treat `IMPLEMENT_TMPDIR/oos-accepted-design.md` as an input; if tally no longer materializes that path from standalone design, Step 9a.1 / OOS combine can be silently empty vs older nested-era expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_15: Finalize harness lost rename-time `gh issue view` teardown coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `scripts/test-implement-finalize.sh` teardown removed `STUB_GH_ISSUE_VIEW_FAIL` branch and argv assertions tied to deleted prefetch; fewer guardrails for future regressions in rename-time GitHub fetch behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_16: [OUT_OF_SCOPE] Historical CHANGELOG + run logs still mention removed round-trip harness vocabulary
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Noise for grep-based audits; acknowledged policy context (#2596 plan); not required for this PR beyond existing policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_17: [OUT_OF_SCOPE] agent-lint.toml hyphenless cleanup-roundtrip test name near round-trip grep discussions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Pre-existing confusion between distinct harness names; keep greps hyphen-specific per plan notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_18: implement-finalize: dropped issue-body fetch before tracking rename (sensitive persistence / semantics)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Removing `gh issue view` body fetch and round-trip detector before rename reduces sensitive issue-body persistence on disk during finalize and does not introduce a new injection channel; product semantics may change if body-derived rename signals were still desired—worth monitoring, not a required security fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_19: [OUT_OF_SCOPE] voting-protocol doc lag vs design-local OOS layout (not introduced here)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Same class of IMPLEMENT_TMPDIR vs design-local artifact mapping as in-scope doc drift, explicitly scoped as future doc sync only and not introduced by this PR from the security slot’s perspective—kept separate from **FINDING_6** per source distinction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_20: [OUT_OF_SCOPE] CHANGELOG 41.0.0 editorial: unrelated headline features in one section
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Release readers may conflate round-trip removal risk with /design nested cleanup when bullets share one section; optional follow-up editorial pass to split bullets/subsections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Notes:** `cursor-specialist-security-output.txt` **FINDING_21** (“tally-plan-review removal … no change required for security”) states there is no security action; it is not promoted as a separate actionable finding. **FINDING_10** merges two slots whose suggested revision text was literally identical (“Address the concern above.”) but the instruction requires per-slot bullets when wording differs—here identical, so one shared bullet is used for both slots.

Because this output contains one or more `### FINDING_N:` blocks, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this file.
