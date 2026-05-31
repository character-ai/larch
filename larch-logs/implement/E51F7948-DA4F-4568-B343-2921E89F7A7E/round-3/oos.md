### OOS_1: [OUT_OF_SCOPE] Branch bundles #3265 convergence work with #3266 panel availability work
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-convergence-threshold-removal-output.txt
- **Severity**: latent
- **Concern**: Branch bundles unrelated design-loop changes: convergence-threshold/streak removal and `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` (#3265) with availability-gated panels and `fallback_group` removal (#3266). Large unrelated diff surface in shared design CI shards (`plan-review-loop.sh`, `review-and-fix.sh`) increases merge/review risk, splits review accountability, and makes it easy to ship a partial revert of one policy while believing the plan is satisfied. The attached `larch:plan` covers only panel availability work, not the convergence migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-convergence-threshold-removal-output.txt: Split into separate PRs or extend the plan/acceptance block to include the convergence migration explicitly (caller sweep, docs, harnesses, CHANGELOG) so architecture review and release notes treat both as in-scope.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Case 7 omits stderr capture; covered by 7b
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Case 7 still omits `2>&1` and does not assert absence of WARNING; case 7b covers that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_11: [OUT_OF_SCOPE] test-degraded-tools-gate.md doc drift for cases 8–9 / 7b
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-degraded-tools-gate.md` does not yet document cases 8–9 / 7b (doc-only drift).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] Pre-branch run logs used env-only gate invocations
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Pre-branch run logs show env-only `degraded-tools-gate.sh --skill implement` invocations; that pattern is now intentional for harnesses but remains risky for production orchestrators that skip explicit flags.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] Unused cp failure stub in waterfall harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `cp` failure stub in `scripts/test-dispatch-with-waterfall.sh` (~76–96) is unused after grouped-reuse test removal. Dead code only; no CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Voter fallback status branch is dead after hardcoded vendor tools
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: `fallback` status can never be set in `dispatch-plan-voters.sh` (~179–180) after hardcoding vendor tools; harmless at runtime but contradicts docs that still describe waterfall Claude fallback for voters 2/3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Voter harness effective_paths loop does not read statuses from output
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: The healthy-path `effective_paths` loop in `test-dispatch-plan-voters.sh` (~334–336) uses `$VOTER_1_STATUS` / `$VOTER_2_STATUS` / `$VOTER_3_STATUS` shell variables that are never populated from `$out`, so the assertion does not actually validate path-file line count against emitted statuses (it often passes with `effective_paths=3` by accident).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] dispatch-plan-voters.md documents obsolete three-phase waterfall
- **Reviewer(s)**: dyn-voter-availability-status-output.txt
- **Severity**: nit
- **Concern**: `scripts/dispatch-plan-voters.md` (~14–22) still documents three-phase waterfall and reading `ALL_OUTPUT_FILES` for externals; implementation now uses availability-gated manifest + `--no-fallback` and no longer reads those keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-voter-availability-status-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Runtime convergence-threshold removal appears complete (informational)
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: Runtime removal looks complete for the scout’s sweep: no `--convergence-threshold`, `LARCH_DESIGN_CONVERGENCE_THRESHOLD`, or `CONVERGENCE_STREAK` under `skills/` or `scripts/` (excluding tests); `skills/design/SKILL.md:941-948` passes only `--round-cap`; `plan-review-loop.sh` exports `NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT`; `docs/configuration-and-permissions.md:250` describes hardcoded ≤5 non-nit convergence without streak prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Design vs implement degraded-panel gate on convergence (pre-existing policy)
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: `/design` convergence requires a non-degraded round (`DEGRADED_PANEL != 1`); `/implement` Step 5 in `review-and-fix.sh` applies the same `CONVERGENCE_NON_NIT_MAX=5` without a degraded-panel gate. That policy split predates this branch’s availability work and is intentional surface area, not introduced by the panel changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] Unit convergence algebra coverage is strong; gap is integration-only
- **Reviewer(s)**: dyn-convergence-threshold-removal-output.txt
- **Severity**: nit
- **Concern**: Unit coverage for the new convergence algebra is strong in `test-plan-review-loop.sh` (six latent cap-hit, five non-nit one-round converge, nit-only, many-nits-plus-three-latent with explicit KV assertions); the gap is specifically the integration fixture’s value-level contract, not absence of unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-convergence-threshold-removal-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Verified OK: degraded-tools-gate _SET and flag-over-env behavior
- **Reviewer(s)**: dyn-gate-env-var-inheritance-output.txt
- **Severity**: nit
- **Concern**: Verified OK (no issue): `_SET` distinguishes omitted flags from explicit empty values; case 7b is consistent; cases 8–9 correctly use `2>&1` and assert WARNING substrings; flag parsing runs after env init so explicit flags win when both are supplied; `larch_err` WARNINGs go to stderr (and FD 4 under quiet init).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gate-env-var-inheritance-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

