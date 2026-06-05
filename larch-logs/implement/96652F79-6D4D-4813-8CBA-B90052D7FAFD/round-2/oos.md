### FINDING_15: risk-integration: python/test_report_tokens_cli.py:51-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required CLI test only asserts post_issue receives skill=implement; no --skill design forwarding test. report_tokens_cli could regress to hardcoding skill=implement while design issue trim labels break silently. Add test_main path calling main(["--skill","design"]) and assert posted == [("o/r","design")].
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/render-run-summary.sh:253-255` — The renderer still emits `- **Path**:` for `--skill implement` whenever any caller passes a non-empty `--workflow-path`; only the primary implement caller (`write-final-report.sh`) was updated to omit the flag. A future or alternate caller could still push arbitrary strings into tracking-issue / final-summary markdown (a public GitHub boundary). **Suggested fix:** Ignore or reject `--workflow-path` when `--skill implement` (defense in depth), matching the implement contract that Path is design-only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `python/run_logs.py:105-118` — `_report_subprocess_env` still clones the full parent `os.environ` before overlaying implement pins. This is the existing trust model, but any unexpected inherited variable could affect child script behavior beyond the newly pinned keys. **Suggested fix:** Consider an allowlist-based env for timing-report subprocesses in a future hardening pass (out of scope for this workflow-removal change).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_24: architecture: scripts/launch-codex-implement.sh:225-238
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] External implementer launchers record vendor timing without pinning LARCH_TIMING_SKILL=implement. A Claude session polluted with LARCH_TIMING_SKILL=design from a prior /design run can tag Step 2/5 vendor rows with skill=design in the implement ledger; per-step implement durations stay correct because marks are pinned, but vendor-row skill metadata is silently wrong for downstream ledger consumers. Export or inline-prefix LARCH_TIMING_SKILL=implement on every implement-scoped record-vendor-task invocation in launch-codex-implement.sh launch-cursor-implement.sh and launch-review.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: code-quality: python/report_tokens_issue.py:20-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _TITLE_BY_SECTION still maps aggregate to design-only label Aggregate cost by workflow while implement relies on _section_label special-casing. A maintainer using the map directly for implement trim notices could reintroduce design-only omission text. Split or neutralize the aggregate title map so implement and design labels are explicit without a hidden override.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/compute-pr-line-counts.sh; skills/implement/scripts/write-final-report.sh:6493-6518
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] compute-pr-line-counts validation and write-final-report LINES_DATA_OK simplification are outside the workflow plan. Unrelated behavioral change bundled into the same PR increases review surface. Track as separate follow-up or note explicitly in PR summary.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_34: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `scripts/launch-codex-implement.sh:230-238` and `scripts/launch-review.sh:94-102` — External implementer/reviewer launchers still call `timing-ledger.sh record-vendor-task` without `LARCH_TIMING_SKILL=implement`, so a session that still exports `LARCH_TIMING_SKILL=design` after `/design` can stamp vendor rows with `design` in column 4. This predates the branch, was not changed in the diff, and current `timing-report.sh` vendor aggregation ignores that skill column; impact is mostly ledger hygiene, not SIMPLE/HARD workflow leakage.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-timing-env-output.txt
- **Concern**: - **risk-integration** `python/checks.py:186-201` — The Python relevant-checks parity path spreads `os.environ` into timing-ledger marks without pinning `LARCH_TIMING_SKILL=implement`, while the live `/implement` shell helper `run-relevant-checks-captured.sh` was updated in this branch. This is dev/CI Phase-4 parity only (not the live orchestrator path) and unchanged by the diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - **code-quality** `scripts/test-implement-timing-rehydration.sh:155-156` — The hard-coded expectation `plugin_root_source_count == 42` will break on any unrelated `SKILL.md` fence edit; consider deriving the count from a single documented invariant or bumping via a named constant in the harness header.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_42: [OUT_OF_SCOPE] No Bash 3.2 portability problems found in the workflow-removal edits: same-line env assignment (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement cmd`), `"${array[@]+"${array[@]}"}"` nounset-safe expansion, and `--workflow` removal in `step2-implement.sh` / `run-step2-dispatch.sh` all look correct; argv loops use proper `shift 2` and terminate unknown flags with exit 2.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - No Bash 3.2 portability problems found in the workflow-removal edits: same-line env assignment (`DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement cmd`), `"${array[@]+"${array[@]}"}"` nounset-safe expansion, and `--workflow` removal in `step2-implement.sh` / `run-step2-dispatch.sh` all look correct; argv loops use proper `shift 2` and terminate unknown flags with exit 2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] Production implement surfaces no longer read or persist `WORKFLOW_PATH` / `--workflow`; fixed `LAUNCHER_TIMEOUT=7200` in `skills/implement/scripts/step2-implement.sh:657`; `scripts/timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; `python/run_logs.py:105-109` clears `DESIGN_TMPDIR` for timing-report subprocesses; and `skills/implement/scripts/write-final-report.sh` omits `--workflow-path` when calling `render-run-summary.sh`.
- **Reviewer**: dyn-bash-compat-output.txt
- **Concern**: - Production implement surfaces no longer read or persist `WORKFLOW_PATH` / `--workflow`; fixed `LAUNCHER_TIMEOUT=7200` in `skills/implement/scripts/step2-implement.sh:657`; `scripts/timing-report.sh` gates `resolve_workflow_fallback` on `LARCH_TIMING_SKILL=design`; `python/run_logs.py:105-109` clears `DESIGN_TMPDIR` for timing-report subprocesses; and `skills/implement/scripts/write-final-report.sh` omits `--workflow-path` when calling `render-run-summary.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=1 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/degraded-tools-gate.sh:1-200
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unrelated degraded-tools gate refactor is bundled with workflow-removal work. Higher coupling makes bisect/revert of workflow removal harder if design gate behavior regresses. Land gate fixes separately or isolate commits by feature.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/compute-pr-line-counts.sh:1151-1168
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated repo-slug validation and write-final-report LINES_DATA_OK simplification ride along in the same PR. Increases diff size and review time for a workflow-classification change. Split into a focused follow-up if not required for round-1 review fixes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

