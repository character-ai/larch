### FINDING_10: [OUT_OF_SCOPE] **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_11: [OUT_OF_SCOPE] **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


