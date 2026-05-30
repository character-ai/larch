### OOS_1: [OUT_OF_SCOPE] _stage_and_push_ci_fixes modularization debt (#3132)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_stage_and_push_ci_fixes` grew into a multi-mode coordinator; pre-existing maintainability debt amplified by #3210. Track under #3132 modularization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Fail-open BEHIND_COUNT=0 (operational awareness)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Fail-open `BEHIND_COUNT=0` on fetch/rev-list errors can skip rebase and plain-push on stale base when the probe fails. Operational awareness; optional stricter mode behind an env flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Unrelated anti-polling / hook / AGENTS / CHANGELOG bundle on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Large unrelated hook, `AGENTS.md`, `hook-anti-read-poll.sh`, and 47.0.4 anti-polling / changelog work rides on the #3210 branch—not in the #3210 plan—raising review noise, mixed concerns, and harder failure attribution. Split PRs, dedicated review, or explicit PR description; track anti-polling under #3217 where noted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Duplicate BEHIND_COUNT parsing (maintainability)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Duplicate `BEHIND_COUNT` parsing styles between `ci-status.sh` and ship-pr (`awk` vs `kv_value`). Maintainability only—share `kv_value` or a tiny parse helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] test-ship-pr-3210-spot.sh redundant with fix-loop target
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Spot script duplicates `test-ship-pr-fix-loop`; redundant local entrypoint unless sharded. Remove or shard; prefer `make test-ship-pr-fix-loop` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Missing harness for behind>0 + missing TSV on gh-run-logs failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No harness for behind>0 with missing TSV when `gh-run-logs` fails; regression risk for post-rebase TSV policy. Add fix-loop case stubbing `BEHIND_COUNT=1`, empty TSV, degraded `gh-run-logs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] CHANGELOG 47.0.4 omits #3210 feature
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: 47.0.4 changelog omits #3210 feature documented in `workflow-lifecycle.md`; release readers miss CI-fix rebase-before-push behavior. Add #3210 bullet to the version changelog entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):** 43 raw slots collapsed to **20 in-scope** findings and **7 OOS** blocks. Highest-impact clusters: **FINDING_2** (five slots), **FINDING_10** (three slots, elevated to important), **FINDING_4** / **FINDING_8** / **FINDING_13** (plan testing gaps). **FINDING_9** vs **FINDING_19** stay separate (vendor rotation vs push-failure `PENDING` semantics). In-scope **FINDING_10** vs **OOS_2** both mention fail-open; OOS_2 kept for the structure reviewer’s operational-only tag. **FINDING_7** vs **OOS_4**: same parser topic; in-scope nit vs OOS maintainability per source tagging.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

