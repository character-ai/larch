### OOS_3: Pre-existing asymmetry between `write_initial_state` and `require_key` in scripts/ship-pr.sh
- **Reviewer(s)**: 1 reviewer (cursor-dyn-plan-coherence)
- **Focus area**: architecture
- **Description**: `scripts/ship-pr.sh:2437-2446` `require_key` lists 32 keys; `write_initial_state` already emits keys like BAIL_REASON, DESIGN_ONLY_DONE, EXPECTED_SESSION_ID, EXPECTED_TMPDIR_BASENAME_PREFIX that are not required. Pre-existing inconsistency the current PR doesn't address. Worth filing as a follow-up tightening issue.

### OOS_4: Drift guard between SKILL.md key bullets and ship-pr.sh emitted keys
- **Reviewer(s)**: 1 reviewer (cursor-arch)
- **Focus area**: risk-integration
- **Description**: `skills/implement/SKILL.md:1550-1559` key bullets and `scripts/ship-pr.sh:239-298` `write_initial_state` are now two parallel sources of truth. Consider extending `scripts/test-implement-structure.sh` to assert they match. Not blocking this PR.

