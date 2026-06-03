### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: **`scripts/ship-pr.sh` / `scripts/implement-finalize.sh`**: Subtractive change removes `classify-bump.sh`, `apply-bump.sh`, `commit-changelog.sh`, and bump-reasoning file reads from the live ship path. That **shrinks** attack surface (fewer shell-outs and fewer session-state file reads). Removed `validate_bump_reasoning_file` (tmpdir containment, symlink rejection, size cap) is not a regression because `postbump` no longer reads `BUMP_REASONING_FILE` from disk.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`scripts/ship-pr.sh` / `scripts/implement-finalize.sh`**: Subtractive change removes `classify-bump.sh`, `apply-bump.sh`, `commit-changelog.sh`, and bump-reasoning file reads from the live ship path. That **shrinks** attack surface (fewer shell-outs and fewer session-state file reads). Removed `validate_bump_reasoning_file` (tmpdir containment, symlink rejection, size cap) is not a regression because `postbump` no longer reads `BUMP_REASONING_FILE` from disk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: **State files**: `ship-pr-state.sh` / `postbump-state.sh` remain parse-only (`awk` / `read_state`); they are not `source`d. argv validation for CR/LF in `--manifest-path` / `--run-id` is unchanged.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **State files**: `ship-pr-state.sh` / `postbump-state.sh` remain parse-only (`awk` / `read_state`); they are not `source`d. argv validation for CR/LF in `--manifest-path` / `--run-id` is unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **`external_launcher_mirror_quota_from_events`** (#3395): Appends a **fixed-format** marker line; only the events **path** is interpolated (quoted `%s`). Quota detection reuses `external_is_quota_failure` on the JSONL stream—no `eval`, no command substitution. Fail-closed quota classification is intentional; false positives degrade to waterfall, not privilege gain.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`external_launcher_mirror_quota_from_events`** (#3395): Appends a **fixed-format** marker line; only the events **path** is interpolated (quoted `%s`). Quota detection reuses `external_is_quota_failure` on the JSONL stream—no `eval`, no command substitution. Fail-closed quota classification is intentional; false positives degrade to waterfall, not privilege gain.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **`launch-review.sh`**: Quota mirroring runs **inside** the transient-retry loop **before** `external_is_transient_infra_failure`, with an explicit `! external_is_quota_failure` guard—reduces quota burn, not a trust-boundary weakening.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`launch-review.sh`**: Quota mirroring runs **inside** the transient-retry loop **before** `external_is_transient_infra_failure`, with an explicit `! external_is_quota_failure` guard—reduces quota burn, not a trust-boundary weakening.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Hooks**: `hook-post-bump-version.sh` is an immediate `exit 0` no-op; `hook-stop-fail-close.sh` drops the `.bump-version-armed` block only because that sentinel is never written post–Phase 1. Remaining Stop-hook still blocks mid–Step 5.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Hooks**: `hook-post-bump-version.sh` is an immediate `exit 0` no-op; `hook-stop-fail-close.sh` drops the `.bump-version-armed` block only because that sentinel is never written post–Phase 1. Remaining Stop-hook still blocks mid–Step 5.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **`python/rebase.py`**: Re-bump/changelog limbs removed; CI-fix path keeps fetch/rebase/`_resolve_conflicts`/force-push. No new deserialization or network fetch from untrusted input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`python/rebase.py`**: Re-bump/changelog limbs removed; CI-fix path keeps fetch/rebase/`_resolve_conflicts`/force-push. No new deserialization or network fetch from untrusted input.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Secrets**: No new credentials, tokens, or literal secret material in production paths (test-only `CURSOR_API_KEY="sl-quota-cursor-key"` in harness fixtures is clearly dummy).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secrets**: No new credentials, tokens, or literal secret material in production paths (test-only `CURSOR_API_KEY="sl-quota-cursor-key"` in harness fixtures is clearly dummy).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/ship-pr.sh:1050-1114
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_bump_phase name and changelog-failed case no longer match behavior Readers misread state machine; dead status arm never taken from postbump Rename phase when convenient; prune changelog-failed from case list
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] CI-fix rebase path skips ship-branch-guard documented at run_bump_phase CI-fix push from wrong branch if checkout/state diverge after pre-ship guard Share guard helper with run_rebase_rebump or document accepted risk in ship-pr.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: correctness: scripts/ship-pr.sh:2673-2675
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] run_rebase_rebump skips ship-branch-guard while run_bump_phase still enforces it. CI-fix rebase+force-push on a wrong or detached checkout can push to the wrong remote branch without the bump-phase guard firing. Relocate ship-branch-guard to run_rebase_rebump entry (and resume path) or document the accepted risk explicitly in ship-pr.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

