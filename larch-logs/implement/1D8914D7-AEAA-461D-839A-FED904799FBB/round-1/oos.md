### FINDING_11: risk-integration: scripts/test-implement-rebase-macro.sh:63-77
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural harness still requires four rebase-checkpoint-probe.sh invocations in SKILL.md including 7a.r. After moving 7a.r into step-7a.sh SKILL.md has three probes; make test-implement-rebase-macro in test-harnesses-10 fails on merge. Update test-implement-rebase-macro.sh to allow 7a.r inside step-7a.sh (three SKILL fences + script pin) and re-run the harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/step-7a.sh:105-106` — `compose_summary_diagrams` still `cat`s `$ARCHITECTURE_DIAGRAM_FILE` with only an existence check, then posts via `tracking-issue-summary.sh` without running `sanitize-mermaid-fragment.sh` on the architecture half (code-flow is sanitized on the success path). A poisoned `ARCHITECTURE_DIAGRAM_FILE` (e.g., via tampered `session-env.sh` or manifest) could publish unsanitized Mermaid or sensitive file content to a GitHub issue comment; `redact-secrets.sh` mitigates secrets but not diagram safety. **Suggested fix:** mirror `pr-body-template.md` and run `sanitize-mermaid-fragment.sh --from-md` on the architecture file before inclusion, or confine reads to paths under `$IMPLEMENT_TMPDIR` / design manifest roots.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/step-7a.sh:287-291` — `--implement-tmpdir` is validated only as an absolute path (`/*`), not as a session cache root (unlike `cleanup-tmpdir.sh` / `test-cache-root-validation` patterns). A mis-set tmpdir could make the helper write logs, transcripts, and token reports outside the intended `~/.cache/larch/sessions/...` tree. **Suggested fix:** reuse the shared cache-root acceptance helper before `mkdir -p` and downstream writes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/scripts/step-7a.sh:369-371` — `COMMENT_UPSERT_SKIP` uses broad `*sanitiz*|*reject*` globbing on `SKIP_REASON`, which is stricter than `main` (always upserted with placeholders) and may skip the entire `larch:diagrams` comment—including the architecture section—when a non-sanitizer failure happens to embed those substrings. **Suggested fix:** match the canonical `sanitizer-rejected` token from `generate-code-flow-diagram.sh` / `sanitize-mermaid-fragment.sh` only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sanitizer rejection now skips larch:diagrams upsert vs main posting placeholder. Intentional acceptance per issue #2741 not introduced by helper bug alone. Document operator-facing behavior change if needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan generator-crash case not in harness. Low residual risk due to * status branch. Add STEP7A_GEN_MODE=crash test if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_35: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:188-191
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] capture-session-transcript non-zero rc handling is unreachable. Dead degraded branch adds maintenance noise only. Remove rc check or add comment that script always exits 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/flush-execution-issues.sh:170-179` — The same `set +e` / `rc=$?` / `set +e` pattern exists in the pre-existing flush helper; not introduced by this branch’s Step 7a consolidation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/step-7a.sh:394-399` — `BASE_ARGS` uses the Bash 3.2–safe `"${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"` expansion; no issue found under `set -u`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_40: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-error-handling-output.txt
- **Concern**: - **code-quality** `skills/implement/scripts/step-7a.sh:177-191` — `capture-session-transcript.sh` always exits 0 per `scripts/capture-session-transcript.sh`; the `rc` check is effectively dead but harmless and mirrors defensive wrapping elsewhere.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_42: [OUT_OF_SCOPE] **COMMENT_UPSERT_SKIP initialization** — `COMMENT_UPSERT_SKIP=false` is set at `skills/implement/scripts/step-7a.sh:243` before diagram generation; the sanitizer branch at `369-371` only runs on the generate path and correctly flips the flag when `SKIP_REASON` matches `*sanitiz*|*reject*`. No defect there.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **COMMENT_UPSERT_SKIP initialization** — `COMMENT_UPSERT_SKIP=false` is set at `skills/implement/scripts/step-7a.sh:243` before diagram generation; the sanitizer branch at `369-371` only runs on the generate path and correctly flips the flag when `SKIP_REASON` matches `*sanitiz*|*reject*`. No defect there.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_43: [OUT_OF_SCOPE] **Empty `gen_status` (crash / missing envelope)** — The `*)` arm at `362-367` maps empty or unknown `STATUS` to `DIAGRAM_STATUS=failed`, appends a Warning, and leaves `COMMENT_UPSERT_SKIP=false` unless `SKIP_REASON` matches the sanitizer pattern. That matches the plan (“treat crash like `STATUS=failed`; still post placeholder comment unless sanitizer rejection is signaled”) and is not a bug.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **Empty `gen_status` (crash / missing envelope)** — The `*)` arm at `362-367` maps empty or unknown `STATUS` to `DIAGRAM_STATUS=failed`, appends a Warning, and leaves `COMMENT_UPSERT_SKIP=false` unless `SKIP_REASON` matches the sanitizer pattern. That matches the plan (“treat crash like `STATUS=failed`; still post placeholder comment unless sanitizer rejection is signaled”) and is not a bug.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_44: [OUT_OF_SCOPE] **Harness gap** — `test-step-7a.sh` case `no-logs-commit` only exercises the happy path; it would not catch the `LOG_FLUSH_STATUS` overwrite above. Fixing the script should include a combined failure test.
- **Reviewer**: dyn-status-state-transitions-output.txt
- **Concern**: - **Harness gap** — `test-step-7a.sh` case `no-logs-commit` only exercises the happy path; it would not catch the `LOG_FLUSH_STATUS` overwrite above. Fixing the script should include a combined failure test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_47: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `scripts/lint-foreground-markers.sh:354` — `foreground_comment_ok_before_anchor_idx` is passed `$merge_start_phy` (1-based index of the first physical fence line of a merged invocation), which matches the background `comment_ok_before_anchor_idx` call at `scripts/lint-foreground-markers.sh:374`. Index arithmetic (`start = anchor_idx - 5`, loop `i < anchor_idx`, array access `FG_FENCE_LINES[i - 1]`) is consistent with the background variant; no `merge_start_phy` vs `abs_anchor` mismatch was found for the step-7a path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_48: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:1418-1431` — The live Step 7a fence places the foreground comment five in-fence lines above the `step-7a.sh` anchor (after rehydration prelude), so the current SKILL.md satisfies the new linter for production paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_49: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-linter-extension-output.txt
- **Concern**: - **architecture** `BASH_AUTHORING.md:50-75` and `scripts/lint-foreground-markers.md:7-19` — Foreground marker text in SKILL.md fences points at “BASH_AUTHORING.md §4”, but §4 still normatively documents only the background+monitor pair; the sibling linter doc also describes a single foreground contract for all denylisted scripts even though the implementation keeps dual contracts (background default, foreground only for `step-7a.sh`). These drifts predate or sit outside the step-7a harness edits and are not introduced solely by the new branch logic.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] code-quality: skills/implement/scripts/step-7a.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] 403-line monolith bundles classifier compose upsert rebase and full flush. Future edits risk higher regression cost than smaller phased helpers. Consider extracting run_log_flush or classifier when a follow-up refactor is scheduled.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] architecture: skills/implement/scripts/step-7a.sh:399
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] rebase-checkpoint-probe suffixed with || true inside always-exit-0 wrapper. Callers relying on probe exit code instead of FD3 KV may miss rebase failures. Ensure Rebase Checkpoint Macro documents KV-only signaling; pre-existing macro concern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

