### OOS_1: `write_state` harness fixture omits NO_LOGS_COMMIT line
- **Reviewer(s)**: 4 reviewers (cursor-dyn-harness-integration, cursor-dyn-state-key-enumeration, cursor-edge, cursor-dyn-plan-coherence)
- **Focus area**: risk-integration
- **Description**: `scripts/test-ship-pr.sh:304-347` `write_state()` helper currently omits a `NO_LOGS_COMMIT=` line. Track this as a follow-up: if `require_key` is ever extended to require that key (rejected in this PR per FINDING_1), every `write_state`-seeded scenario in the harness would need updating to add it.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: NEVER #18 prose in skills/implement/SKILL.md describes heredoc-based state rewrites
- **Reviewer(s)**: 2 reviewers (cursor-innovation, cursor-pragmatic)
- **Focus area**: code-quality
- **Description**: `skills/implement/SKILL.md:70` NEVER #18 instructs the orchestrator to use a key-based rewrite when clearing `OOS_PENDING=false`. After argv-init removes most orchestrator state-write paths, consider a documentation pass so OOS guidance names key-based edits only. Not blocking this PR.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: Pre-existing asymmetry between `write_initial_state` and `require_key` in scripts/ship-pr.sh
- **Reviewer(s)**: 1 reviewer (cursor-dyn-plan-coherence)
- **Focus area**: architecture
- **Description**: `scripts/ship-pr.sh:2437-2446` `require_key` lists 32 keys; `write_initial_state` already emits keys like BAIL_REASON, DESIGN_ONLY_DONE, EXPECTED_SESSION_ID, EXPECTED_TMPDIR_BASENAME_PREFIX that are not required. Pre-existing inconsistency the current PR doesn't address. Worth filing as a follow-up tightening issue.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: Drift guard between SKILL.md key bullets and ship-pr.sh emitted keys
- **Reviewer(s)**: 1 reviewer (cursor-arch)
- **Focus area**: risk-integration
- **Description**: `skills/implement/SKILL.md:1550-1559` key bullets and `scripts/ship-pr.sh:239-298` `write_initial_state` are now two parallel sources of truth. Consider extending `scripts/test-implement-structure.sh` to assert they match. Not blocking this PR.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: Fixture drift risk in `skills/implement/scripts/test-write-final-report.sh`
- **Reviewer(s)**: 1 reviewer (cursor-requirements)
- **Focus area**: architecture
- **Description**: `skills/implement/scripts/test-write-final-report.sh:52-200` contains ship-pr-state.sh fixtures that may need updating if `require_key` ever tightens. Track as follow-up.

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

