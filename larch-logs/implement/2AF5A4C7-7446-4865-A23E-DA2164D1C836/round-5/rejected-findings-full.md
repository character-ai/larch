### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/ship-pr.sh:2658-2912 / scripts/test-ship-pr-rebase.sh:19-44
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] run_rebase_rebump CI-fix path lacks sandbox integration tests; coverage is mostly grep plus one die_usage guard. Typo in defer-push wiring or phase-14 resume branch breaks production CI-fix rebase while rebase-push unit tests pass. Add stubbed-git cases in test-ship-pr-rebase.sh for defer-push invocation and resume handoff success.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/test-implement-finalize.sh:947-949 / skills/implement/SKILL.md:85
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Postbump rebase conflicts no longer hand off to conflict-resolution.md; tests lock in manual recovery. First postbump rebase conflict after upgrade stalls without automated Phase 1-4 recovery. Document operator-facing degradation; re-wire only if a follow-up phase intends automated postbump recovery.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: (commits d45f89d90 vs d37ec4e86)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] #3390 launcher quota mirroring bundled with #3364 versioning PR Revert/bisect of versioning work also reverts or conflicts with unrelated Codex classifier fix; review surface mixes two features Split #3390 to its own PR or document explicit batching decision
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: architecture: scripts/implement-finalize.sh:405-448
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Postbump Step 8b rebase conflicts return rebase-failed and stall at 8b without CONFLICT_FILES or conflict-resolution.md, unlike CI-fix run_rebase_rebump. Feature branch is behind origin/main with conflicts in non-version files at pre-PR ship; implement-finalize aborts rebase, ship-pr exit_stall 8b, and the run stalls with no automated Phase 1-4 recovery despite CI-fix rebases still having that path. Document loudly in stall copy, or align postbump with --keep-on-conflict plus ship_pr_pre_push handoff if product wants parity (SKILL.md already notes accepted degradation).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: correctness: python/rebase.py:12
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan said drop import changelog; file still imports changelog for conflict auto_resolve. Plan auditors or Phase 7 cutover may treat Python mirror as incomplete. Clarify plan or module docstring that changelog import is conflict-resolution-only, not re-bump.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: architecture: scripts/ship-pr.sh:3279-3281
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Dead CALLER_KIND branch step10_rebase_then_evaluate with no writer after rebump removal. Future maintainers think evaluate-failure routing differs for step10 rebase paths. Remove dead case arm or document and restore a writer if still needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: **architecture** `scripts/ship-pr.sh:3213-3268` — `write_initial_state` and `require_key` were pruned consistently (`HAS_BUMP` / `BUMP_TYPE` / `NEW_VERSION` removed from `ship-pr-state.sh`; stubs live only in `write_postbump_state` → `postbump-state.sh` at `809-826`), and there are no unset `$HAS_BUMP` references under `set -u`. However, legacy keys left **inside** an existing `ship-pr-state.sh` are never stripped at load: extra keys are harmless, but stale `RESUME_PHASE` / `CALLER_KIND` can remain until bump entry or a successful `run_rebase_rebump` clear (`2684`), so a mid-CI stall can still expose `RESUME_PHASE=force-push-gate` + `CALLER_KIND=step8b_rebase` to the orchestrator even though Exit 5 / sub-procedure routing is gone. **Suggested fix:** After `validate_state_syntax` / `_ci_fix_pending_hydrate`, normalize legacy resume metadata once (mirror `_clear_phase1_postbump_residue`: blank `RESUME_PHASE`/`CALLER_KIND` when values are in the retired set, or when `PHASE` is not `bump` and `RESUME_PHASE` is not `ship-pr-rrr-phase14`), so persisted state cannot contradict Phase 1 semantics across CI phases.
- **Reviewer**: dyn-resume-compat-output.txt
- **Concern**: - **architecture** `scripts/ship-pr.sh:3213-3268` — `write_initial_state` and `require_key` were pruned consistently (`HAS_BUMP` / `BUMP_TYPE` / `NEW_VERSION` removed from `ship-pr-state.sh`; stubs live only in `write_postbump_state` → `postbump-state.sh` at `809-826`), and there are no unset `$HAS_BUMP` references under `set -u`. However, legacy keys left **inside** an existing `ship-pr-state.sh` are never stripped at load: extra keys are harmless, but stale `RESUME_PHASE` / `CALLER_KIND` can remain until bump entry or a successful `run_rebase_rebump` clear (`2684`), so a mid-CI stall can still expose `RESUME_PHASE=force-push-gate` + `CALLER_KIND=step8b_rebase` to the orchestrator even though Exit 5 / sub-procedure routing is gone. **Suggested fix:** After `validate_state_syntax` / `_ci_fix_pending_hydrate`, normalize legacy resume metadata once (mirror `_clear_phase1_postbump_residue`: blank `RESUME_PHASE`/`CALLER_KIND` when values are in the retired set, or when `PHASE` is not `bump` and `RESUME_PHASE` is not `ship-pr-rrr-phase14`), so persisted state cannot contradict Phase 1 semantics across CI phases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/ship-pr.sh,skills/implement/references/rebase-rebump-subprocedure.md:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Misleading re-bump/bump naming on rebase-only paths Operators grep for rebump and land in dead mental model or wrong docs Rename symbols or add legacy-phase-id comments at entry points
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: code-quality: scripts/implement-finalize.sh:354-373
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead force-push-gate checkpoint reader after writer removal Harder to see actual postbump control flow; false sense resume still exists Remove or simplify checkpoint machinery
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: scripts/implement-finalize.sh:405-448
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Postbump Step 8b rebase uses rebase-push --no-push without --keep-on-conflict; conflicts hard-stall at STALL_STEP=8b with no CONFLICT_FILES handoff. Branch behind main with overlapping non-bump file hits rebase conflict during postbump; run stalls with no automated conflict-resolution path. Wire keep-on-conflict handoff for postbump 8b or add harness pinning documented hard-stall contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

