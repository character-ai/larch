### FINDING_11: [OUT_OF_SCOPE] correctness: scripts/promote-release.sh:79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Multi-line CURRENT_LATEST when multiple isLatest releases exist. Two Latest flags could break promote string compare (pre-existing). Use jq -r '.[0]' after filtering or fail on count != 1.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **architecture** `scripts/promote-release.md:22-24` — Purpose text still describes promoting workflow-created pre-releases from `release-tag.yaml` only; it now also documents `--repo` and `/release` as a consumer, but not that `/release` is the primary cut path. Pre-existing tone; not introduced as a functional gap by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-prepare.sh:108` — `gh release list --limit 100` could theoretically miss a unique `isLatest` release outside the first page on repos with very large release histories. Unlikely for larch; not specified in the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** Plan testing strategy asked for a PR note that live `gh release create/edit` / tag push are left to manual/CI verification per verify-external-tool-invocations; that deliverable is not visible in the committed diff (may exist only in the PR description). --- **Summary:** Implementation matches the SIMPLE-tier plan and acceptance criteria in the diff. No missing planned artifacts, no wrong-language choice, no omitted harnesses from the testing strategy. Safe to treat plan fidelity as satisfied from the code side.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/test-release-finish.sh` — Case 8 covers stale local tag when remote already matches at probe time; there is no harness case for “first `ls-remote` empty → workflow pushes correct tag → stale local tag,” which is the regression shape for the finding above. Contract text in `release-finish.md:40-41` describes push-failure TOCTOU recovery but not local-tag / first-probe ordering.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-180` — `merge_oid` newline stripping and `${merge_oid%% *}` plus the `^[0-9a-fA-F]{7,40}$` gate are adequate for normal `gh -q` output; a multi-token or non-hex first token would be dropped or rejected rather than producing a silent partial hash.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_28: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:209-256,394-418` — When `TARGET_OID` is an ancestor of a later `origin/main` tip (case 10 / harness), tagging the squash-merge OID rather than tip is intentional; version is verified at `TARGET_OID` only, which matches the plan’s fail-closed stance vs `release-tag.yaml` on the same OID.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:303-318` — Post-push failure re-probe and same-OID continuation correctly close the tag-push TOCTOU against `release-tag.yaml`; the gap is asymmetric with the pre-push local-tag path. **Branch commits (vs `main`):** `6576ec069` Add operator-run /release skill … through `9f8c36634` Address code review feedback (round 4).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] `.claude/skills/release/scripts/test-release-prepare.sh` PATH-shims a fake `classify-bump.sh` instead of exercising the real `--base "$BASELINE_TAG" --head origin/main` integration, so regressions in the cross-script contract above would not be caught by the offline prepare harness alone.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - `.claude/skills/release/scripts/test-release-prepare.sh` PATH-shims a fake `classify-bump.sh` instead of exercising the real `--base "$BASELINE_TAG" --head origin/main` integration, so regressions in the cross-script contract above would not be caught by the offline prepare harness alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_34: [OUT_OF_SCOPE] For the wired `/release` path specifically (`release-prepare.sh:235` with paired flags plus `HEAD`/`main`/`origin/main` OID guards at lines 136-144): `CURRENT_VERSION` is correctly read from `git show "${HEAD_COMPARE}:.claude-plugin/plugin.json"`, idempotency is skipped via `--base`, and `NAME_STATUS` / modified-file `git show` calls consistently use `$HEAD_COMPARE` rather than bare `HEAD`.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - For the wired `/release` path specifically (`release-prepare.sh:235` with paired flags plus `HEAD`/`main`/`origin/main` OID guards at lines 136-144): `CURRENT_VERSION` is correctly read from `git show "${HEAD_COMPARE}:.claude-plugin/plugin.json"`, idempotency is skipped via `--base`, and `NAME_STATUS` / modified-file `git show` calls consistently use `$HEAD_COMPARE` rather than bare `HEAD`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-finish.sh:26-30,137-148` — The `_tmp_notes` / `REDACTED_NOTES_FILE` pipeline matches the intended pattern: both paths are covered by the `EXIT` trap; after success `rm` + `unset _tmp_notes` makes the trap’s `[[ -n "${_tmp_notes:-}" ]]` guard avoid double-remove; `REDACTED_NOTES_FILE` is still removed on all `exit` paths (including `gh release` / `promote-release` failures). No defect found in the trap logic the scout asked about.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-finish.sh:155-245` — `fetch_err` temporaries are explicitly `rm -f`’d on every branch; no leak introduced there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_38: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-prepare.sh:234-240` — `classify_err_file` is always `rm -f`’d on success and failure; pre-existing style, not part of the new redaction surface.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/promote-release.sh:79-93
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] promote-release does not fail on ambiguous isLatest unlike release-prepare. Multiple Latest releases could cause unpredictable promote target. Align promote-release with prepare Latest uniqueness guard if desired later.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

