### FINDING_15: [OUT_OF_SCOPE] Stall sentinel text is interpolated into SessionStart advisory context
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Crafted `larch-stalled-run.txt` fields can influence SessionStart advisory JSON context before `jq --arg`; reviewer marked this pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral


### FINDING_18: [OUT_OF_SCOPE] gh-unavailable path reinstalls instead of taking idempotent cone-ok path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-sparse-cone-output.txt
- **Severity**: latent
- **Concern**: When `gh` is unavailable, `already_latest_and_cone_ok` cannot run and the script falls through to unconditional reinstall even if version and cone already match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-sparse-cone-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] Skill-tool fallback can run stale installed upgrade code
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If no cache root resolves, the release fallback may invoke the installed `/upgrade-larch` skill, which can lag the working tree in dev or no-marketplace-install scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] HOME-less root resolution remains unguarded in pre-existing paths
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: nit
- **Concern**: `get_installed_larch_version` and `resolve_release_step7_root` still dereference `$HOME/.claude/...` without an empty-HOME guard; reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


