### OOS_1: [OUT_OF_SCOPE] Unrelated upgrade-larch / tooling bundled in branch diff
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Same branch bundles `upgrade-larch`, `plugin.json`, `CHANGELOG`, `lib-net.sh`, or other tooling changes with Step 5c `design-publish` extraction. Reviewers and bisect must separate unrelated work from #3133 Step 5c / design-publish behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split or rebase so feature commits are isolated.
  - From cursor-specialist-plan-fidelity-output.txt: Keep as separate commits/PR slice if merge hygiene matters; not a defect in design-publish itself.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `validate_repo` triplicated across phase drivers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_repo` is duplicated across three phase drivers (`design-publish.sh` 27–33 and siblings); predates this PR. Repo validation rule changes require three edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize in `lib-phase-driver.sh` on next library touch.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] Plan-block-write / upsert `set +e` subshell behavior verified OK
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: nit
- **Concern**: `if ! plan-block-write.sh` failure guard, subshell capture for upsert/publish, and `set -e` restoration after `set +e` behave as intended; `exit` inside `upsert-diagrams-comment.sh` only terminates the `$(…)` subshell, not the driver.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Bash 3.2 indirect expansion in SKILL.md orchestrator block OK
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: nit
- **Concern**: `${!_key:-}` with `printf -v` at `SKILL.md` 1319–1344 is valid on macOS Bash 3.2; parsing vars initialized before use so `set -u` is not tripped.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Happy-path `render-final-summary.sh` without `|| true` under `set -e`
- **Reviewer(s)**: dyn-bash-euo-safety-output.txt
- **Severity**: latent
- **Concern**: Non-zero render on happy path (`238-244`, `281-285`) would abort before publish/rename/result-env—stricter than old inline Step 5c. In practice render is built to fall back and exit `0` for pre/post publish phases unless validation exits early with code `2`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Rename-failure WARN grep pattern behavior
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: Assertion at `test-design-publish.sh` 381–382 uses escaped `\[` `\]` so `[DESIGNED]` is matched literally; driver WARN line matches and does not false-positive with basic grep on this platform.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] `RENAMED_OMIT_LINE` stub unused (not harness contamination)
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: `RENAMED_OMIT_LINE` is defined in the tracking stub (88–90) but no case sets it; unused harness surface, distinct from cross-case export leakage (see FINDING_13).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] Static source line-order pins partially cover marker ordering
- **Reviewer(s)**: dyn-test-harness-isolation-output.txt
- **Severity**: nit
- **Concern**: Runtime marker ordering on `design-publish.sh` is partially covered by `scripts/test-design-structure.sh` source line-order pins; remaining gap is harness-runtime / plan acceptance ordering vs absence of all CI pins (see FINDING_4).
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

