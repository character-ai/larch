### OOS_1: [OUT_OF_SCOPE] Branch bundles `lint-literal-counts` larch-logs exclusion with Phase 4
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Harness change unrelated to checks port; split or note in PR description.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Nested `bash -c` lock wrapper vs in-shell acquire in bash port
- **Reviewer(s)**: dyn-shell-inject-output.txt
- **Severity**: nit
- **Concern**: Structural difference between Python wrapper and `lint-fix-loop.sh:241-242` explains divergent exploitability; branch commits noted for context.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_11: [OUT_OF_SCOPE] `log_dir` mkdir/symlink/chmod TOCTOU matches bash parity
- **Reviewer(s)**: dyn-toctou-atomicity-output.txt
- **Severity**: latent
- **Concern**: Inherited from `run-relevant-checks-captured.sh:152-162`; branch does not materially amplify beyond shell port.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] Failure-path redacted logs use plain `write_text` like bash
- **Reviewer(s)**: dyn-toctou-atomicity-output.txt
- **Severity**: latent
- **Concern**: No `O_EXCL` on failure-path redacted writes; same as `run-relevant-checks-captured.sh:224-234`.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** 66 raw slots collapsed to **34 in-scope** `FINDING_*` blocks and **12** `OOS_*` blocks. Highest-density merges: agents classifiers (×4), codex events JSONL (×5), forbidden reset (×2), tmpdir validation (×3), site/`ValueError` (×3), site `..` (×2), plan test gaps (×4), serial-lock injection (×2). Generic “Address the concern above” bullets were omitted per aggregator rules. `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is not present because structured findings exist.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Faster poll intervals in `test-plan-review-loop.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Design-skill harness timing change bundled with Phase 4 checks work.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Ancillary version bump and CI harness edits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `.claude-plugin/plugin.json`, `lint-literal-counts`, and design test changes outside checks correctness scope.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Implement dogfood commit on feature branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Unrelated run-log commit on branch; drop or exclude from PR if unintended.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: [OUT_OF_SCOPE] Plan mentions agents classifiers; acceptance overstates vs bash
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Not a new test gap if bash local fixer also skips classifiers; align plan/acceptance or add classifiers only if bash gains them.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] `/tmp` direct-child session dirs accepted (bash parity)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Predictable `/tmp/claude-implement-*` names; shared hardening belongs in `session-setup` / `validate_tmpdir` repo-wide.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Pre-existing bash git path handling without root checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Same traversal class in `lint-fix-loop.sh` before cutover; coordinate bash+Python hardening later.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] Missing regression tests noted as follow-up, not blocking this diff scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Edge reviewer lists structural failure tests as general follow-up rather than in-scope Phase 4 gate.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] `python/test_agents.py` pre-existing `bash -c` f-string pattern
- **Reviewer(s)**: dyn-shell-inject-output.txt
- **Severity**: latent
- **Concern**: Test helper uses same unsafe `source "{LIB_COMMON}"` pattern; not introduced by this branch runtime surface.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

