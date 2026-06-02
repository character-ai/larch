### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] CI-fix run_rebase_rebump skips ship-branch-guard present in run_bump_phase. State BRANCH_NAME mismatch at CI rebase; wrong branch may be rebased/force-pushed. Relocate guard to post-rebase push path or accept and document in ship-pr.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: scripts/ship-pr.sh:1106-1107
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Dead STATUS=conflict arm in run_bump_phase after postbump contract change. No runtime effect; confuses readers and reviewers. Remove conflict arm or align postbump STATUS values with ship-pr case table.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: correctness: scripts/ship-pr.sh:1105-1107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] run_bump_phase conflict status branch is dead code after implement-finalize stopped emitting STATUS=conflict. Future readers may think Exit 5 / conflict handoff still exists from this case arm. Remove conflict arm or restore real STATUS=conflict emission from implement-finalize.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/ship-pr.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Large ship-pr.sh deletion with no replacement integration harness after test-ship-pr removal (plan acknowledges). CI-fix rebase regression or accidental classify-bump/commit-changelog call could ship without failing make targets that still run. Add offline ship-pr phase harness for run_bump_phase/run_rebase_rebump or narrow acceptance to Python path + document bash gap until Phase 7.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: (plan acceptance)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No automated test for concurrency acceptance (second PR merges without rebase when disjoint). Keystone cost goal regresses silently if bump/CHANGELOG writes reappear on another path. Add manual repro doc or hermetic two-PR fixture; mark optional in CI.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard; only run_bump_phase enforces it. CI-fix rebase on wrong branch or detached HEAD may proceed further before detached-head check. Relocate shared guard into run_rebase_rebump entry or add harness for CI-fix branch alignment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **No new injection surfaces** — removed code paths (`classify-bump.sh` / `apply-bump.sh` / `commit-changelog.sh`, rebump helpers, reasoning-file reads) shrink shell/git invocation driven by bump state; remaining paths keep existing validation (`resolve_checks_log_path`, `ship-pr-state.sh` never sourced).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new injection surfaces** — removed code paths (`classify-bump.sh` / `apply-bump.sh` / `commit-changelog.sh`, rebump helpers, reasoning-file reads) shrink shell/git invocation driven by bump state; remaining paths keep existing validation (`resolve_checks_log_path`, `ship-pr-state.sh` never sourced).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Branch safety preserved** — `bump-branch-guard` logic was relocated/renamed to `ship-branch-guard` inside `run_bump_phase` (empty branch, name mismatch, non-forked `main`/`master` stall).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Branch safety preserved** — `bump-branch-guard` logic was relocated/renamed to `ship-branch-guard` inside `run_bump_phase` (empty branch, name mismatch, non-forked `main`/`master` stall).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **Hooks reduced** — `hook-post-bump-version.sh` is an immediate no-op; `hook-stop-fail-close.sh` no longer arms `.bump-version-armed` / reads `postbump-state.sh` mid-ship.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Hooks reduced** — `hook-post-bump-version.sh` is an immediate no-op; `hook-stop-fail-close.sh` no longer arms `.bump-version-armed` / reads `postbump-state.sh` mid-ship.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: **#3390 quota mirroring** — `external_launcher_mirror_quota_from_events` reuses `external_is_quota_failure` on a launcher-controlled `${OUTPUT}.events.jsonl`; appends a fixed-format marker with `%s` for the path (no format-string injection). Sidecar is local classification input only; intentional recall-biased regex per comments.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **#3390 quota mirroring** — `external_launcher_mirror_quota_from_events` reuses `external_is_quota_failure` on a launcher-controlled `${OUTPUT}.events.jsonl`; appends a fixed-format marker with `%s` for the path (no format-string injection). Sidecar is local classification input only; intentional recall-biased regex per comments.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: **`--timing-task-kind` validation** in `launch-review.sh` (non-empty, non-flag-like) closes argv-smuggling mis-parsing (#1480 class) — defensive, not a regression.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--timing-task-kind` validation** in `launch-review.sh` (non-empty, non-flag-like) closes argv-smuggling mis-parsing (#1480 class) — defensive, not a regression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: **No secrets introduced** in the reviewed code diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No secrets introduced** in the reviewed code diff. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: risk-integration: scripts/launch-codex-ci.sh,scripts/launch-review.sh,scripts/lib-external-launcher-common.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] #3390 Codex quota mirroring is bundled with #3364 versioning removal Revert or debug of one concern affects unrelated launcher classification Split #3390 to its own PR or isolate commits in the PR description
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: architecture: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard documented for run_bump_phase only. Wrong-branch or main/master checkout during CI-fix rebase may force-push or stall late without bump-phase guardrails. Share bump-branch-guard (or equivalent) before run_rebase_rebump rebase-push, or document as explicit accepted risk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: correctness: scripts/ship-pr.sh:1101-1110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] run_bump_phase still handles postbump STATUS=conflict but postbump no longer returns it. Future maintainer may think conflict exit_stall 8b is live; debugging wrong branch. Remove or narrow the conflict case to match implement-finalize postbump statuses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/ship-pr.sh:1050-1103,3258-3260
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Legacy phase id bump and run_bump_phase name after bump removal Operators and resume keys (RESUME_PHASE=bump) read as if versioning still runs Rename in a follow-up or document legacy id in ship-pr.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: python/rebase.py:285-303
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] rebase_and_rebump name persists though rebump logic was removed Phase 7 Python cutover readers assume bump still happens in this module Rename to rebase_and_push when editing python/ next
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: scripts/implement-finalize.sh:443-452
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Step 8b rebase conflicts stall (rebase-failed) instead of conflict-resolution handoff. Main moves during review; pre-PR rebase conflicts; run exits 4 with no automated conflict procedure. Confirm intent; either restore conflict handoff or document stall-only behavior in SKILL.md (fix line 951 overclaim).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

