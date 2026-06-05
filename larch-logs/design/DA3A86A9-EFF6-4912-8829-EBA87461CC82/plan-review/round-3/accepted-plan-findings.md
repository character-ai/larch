### FINDING_1: Step 3b completion boundary missing on routing surfaces, cap guard, and harness coverage
- **Reviewer(s)**: Codex-Arch, Codex-Requirements, Cursor-dyn-bypass-path-coverage, Codex-dyn-bypass-path-coverage, Codex-dyn-harness-regression-completeness
- **Severity**: important
- **Concern**: The plan retargets SKILL.md Step 3b exit routing but leaves other normative and runtime paths (approval-gates Gate B/C and cap routing, `run-step3-review.sh`, pinned structure tests) on direct Step 3b → Step 4 / Gate C hops. Cap-reached, zero-findings, passive-summary, bypass, and shorthand routes (including `skills/design/SKILL.md:1059` “jump to Step 3b/4/4b”) can still reach Step 4 after standalone Step 4 FINALIZE is removed, skipping the Step 3b completion boundary. The planned routing harness is too narrow (`continue to Step 4` on a Step 3 slice only) and misses `proceed` / `auto-continue` / arrow forms in approval-gates; stale positive pins (e.g. `test-design-structure.sh:344`, `371-379`, `1568`) conflict with boundary-qualified wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Include these route strings and their test pins in the same minimum-change retarget: say "run the Step 3b completion boundary, then Step 4/Gate C" everywhere, or keep Step 4 FINALIZE until all normative routes are boundary-aware.
  - From Codex-Requirements: Update those surfaces to say run the Step 3b completion boundary before Step 4, and adjust the pinned test needles/add a run-step3-review.sh routing assertion.
  - From Cursor-dyn-bypass-path-coverage: Add skills/design/SKILL.md:1059 to the retarget list (require Step 3b completion boundary before Step 4) and extend scripts/test-design-structure.sh routing guards to fail Step 3b/4 or Step 3b/4/4b unless the same line names the completion boundary
  - From Codex-dyn-bypass-path-coverage: Update this exact assertion to the new boundary-qualified cap wording or replace it with the planned line-scoped Gate-B-bypass routing guard.
  - From Codex-dyn-harness-regression-completeness: Use one line-scoped scanner for SKILL Step 3b, SKILL Step 3/Gate-B-bypass, and approval-gates route prose; match continue/proceed/auto-continue/route/jump/enter/go plus Step 4 and Step 3b arrow/comma forms, and require the same line to mention the Step 3b completion boundary. Update the existing approval-gates positive pins to the boundary-qualified wording.


### FINDING_2: Step 2a fence calls `read-design-classification.sh` without plugin-root path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Proposed Step 2a fence names `read-design-classification.sh` without the plugin-root path. A literal unqualified call will usually be command-not-found, hit the HARD fallback, and SIMPLE runs will not write the folded sentinels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Use "${CLAUDE_PLUGIN_ROOT}/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json" in the Step 2a entry fence and pin that qualified path in the new structure assertion


### FINDING_4: Step 4 compatibility branch lacks enforced non-zero exit on FINALIZE failure (FM6)
- **Reviewer(s)**: Cursor-dyn-harness-regression-completeness
- **Severity**: important
- **Concern**: FM6 mitigation requires nonzero exit on both Step 3b boundary and Step 4 compatibility branches, but the proposed harness pins only the Step 3b completion fence. Step 4 entry guard can regress to warning-only (e.g. `skills/design/SKILL.md:1364`) while CI still passes; paused sessions can resume into Step 4 reads without FINALIZE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-regression-completeness: Add a Step 4 entry-fence-scoped pin mirroring the Step 3b check: the compatibility guard must contain a non-zero exit on FINALIZE failure (e.g. exit "$_finalize_rc"), not merely a repair warning

---

**Merge notes (for voters, not part of machine output):**
- Original FINDING_1 and FINDING_4 were merged (same stale normative/runtime routing risk).
- Original FINDING_5 and FINDING_6 were folded into FINDING_1 (same cap-route / test-pin gap).
- Original FINDING_8 was folded into FINDING_1 (harness scope vs. approval-gates and alternate route phrasing); distinct from FINDING_3 (false positive) and FINDING_4 (Step 4 exit enforcement).
- Original FINDING_2 → FINDING_2; FINDING_3 → FINDING_3; FINDING_7 → FINDING_4.

No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line — four in-scope findings remain.

