### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:348-355
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Step 7a token/timing marks run before the classifier on every path including small/non-runtime skip. On main, skip paths never invoked generate-code-flow-diagram.sh so those marks were absent; timing/token reports may show an extra Step 7a segment for docs-only PRs. Move marks after the classifier on the generate path only, or document the intentional delta in step-7a.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: skills/implement/scripts/test-step-7a.sh:496-503
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] quiet-rebase-contract uses stdout-printing stub; does not exercise lib-quiet emit_kv probe path. CI green while production loses REBASE_* KV relay under quiet mode. Add stub probe using emit_kv under parent quiet init; assert REBASE_OUTCOME on contract stream.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: **Argv / shell**: `--implement-tmpdir` requires an absolute path; child helpers are invoked with quoted paths. The `bash -lc` redact helper passes `PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` as positional parameters (not interpolated into the `-lc` string), matching the prior SKILL.md pattern.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv / shell**: `--implement-tmpdir` requires an absolute path; child helpers are invoked with quoted paths. The `bash -lc` redact helper passes `PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` as positional parameters (not interpolated into the `-lc` string), matching the prior SKILL.md pattern.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **GitHub / issue identifiers**: `ISSUE_NUMBER` is still validated downstream in [`scripts/tracking-issue-summary.sh`](scripts/tracking-issue-summary.sh) (`*[!0-9]*` rejection). Marker shape is still constrained to `<!-- larch:… -->`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **GitHub / issue identifiers**: `ISSUE_NUMBER` is still validated downstream in [`scripts/tracking-issue-summary.sh`](scripts/tracking-issue-summary.sh) (`*[!0-9]*` rejection). Marker shape is still constrained to `<!-- larch:… -->`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Secret handling**: Failure paths use `append-tool-failure.sh --redact`; diagram upsert still runs `tracking-issue-summary.sh`’s `redact-secrets.sh` / `redact-tmpdir-paths.sh` pipeline before `gh` calls.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secret handling**: Failure paths use `append-tool-failure.sh --redact`; diagram upsert still runs `tracking-issue-summary.sh`’s `redact-secrets.sh` / `redact-tmpdir-paths.sh` pipeline before `gh` calls.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Mermaid / public comment surface**: Sanitizer-rejection paths suppress the `larch:diagrams` upsert (`COMMENT_UPSERT_SKIP`), which reduces risk of posting unsanitized Mermaid to a public tracking issue compared with the old inline SKILL flow that still upserted on `STATUS=skipped`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Mermaid / public comment surface**: Sanitizer-rejection paths suppress the `larch:diagrams` upsert (`COMMENT_UPSERT_SKIP`), which reduces risk of posting unsanitized Mermaid to a public tracking issue compared with the old inline SKILL flow that still upserted on `STATUS=skipped`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **KV relay**: Re-emitting `rebase-checkpoint-probe.sh` and `capture-session-transcript.sh` stdout through `emit` keeps the same trusted-child model as direct foreground invocation; captured lines are structured `emit_kv` output, not arbitrary file content.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **KV relay**: Re-emitting `rebase-checkpoint-probe.sh` and `capture-session-transcript.sh` stdout through `emit` keeps the same trusted-child model as direct foreground invocation; captured lines are structured `emit_kv` output, not arbitrary file content.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Diff scan**: No new hard-coded credentials or auth material in the feature diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Diff scan**: No new hard-coded credentials or auth material in the feature diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/implement/scripts/step-7a.sh:63-74,375-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] is_sanitizer_skip_reason hard-codes REASON_TOKEN patterns that must track sanitize-mermaid-fragment.sh manually. A new sanitizer rejection token could still upsert larch:diagrams until step-7a.sh is updated, violating the sanitizer skip-upsert contract. Share token detection with the sanitizer or generator output (parse REASON_TOKEN / central lib) instead of duplicating case patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: risk-integration: skills/implement/scripts/step-7a.sh:429-433
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Rebase failure exits before pre-bump log flush. Orchestrator that ignores exit code reaches Step 8 without larch-log commit batches. Harden SKILL.md gate on non-zero exit; assert missing flush artifacts in rebase-conflict harness case.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: correctness: skills/implement/scripts/step-7a.sh:63-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] is_sanitizer_skip_reason allowlist may miss future REASON_TOKEN values on STATUS=failed. New sanitizer token on failed path still upserts placeholder instead of skipping upsert. Add substring reject/sanitiz guard or share REASON_TOKEN set with sanitize-mermaid-fragment.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: skills/implement/scripts/step-7a.sh:1434-1437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] capture-session-transcript rc check is dead because child always exits 0. LOG_FLUSH_STATUS stays ok when transcript capture fails internally. Set degraded from relayed SESSION_TRANSCRIPT_STATUS or remove dead rc branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: code-quality: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits ARCHITECTURE_DIAGRAM_FILE present path. Regression in architecture section composition would not be caught offline. Add harness case with ARCHITECTURE_DIAGRAM_FILE set and assert summary prefix.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: **correctness** `skills/implement/scripts/step-7a.sh:375-379` — The `skipped` arm of the `gen_status` case sets `COMMENT_UPSERT_SKIP=true` unconditionally, even though Phase 6 in the implementation plan requires upsert suppression only when `is_sanitizer_skip_reason` matches `SKIP_REASON`. Lines 366–367 already apply that sanitizer gate before the `case`, so line 379 is redundant for today’s generator and over-broad for any future `STATUS=skipped` envelope that is not sanitizer-driven. **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` branch and rely solely on the pre-case `is_sanitizer_skip_reason "$gen_skip_reason"` check (mirror the `failed` branch, which only sets the flag via that helper).
- **Reviewer**: dyn-generator-skip-upsert-gate-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:375-379` — The `skipped` arm of the `gen_status` case sets `COMMENT_UPSERT_SKIP=true` unconditionally, even though Phase 6 in the implementation plan requires upsert suppression only when `is_sanitizer_skip_reason` matches `SKIP_REASON`. Lines 366–367 already apply that sanitizer gate before the `case`, so line 379 is redundant for today’s generator and over-broad for any future `STATUS=skipped` envelope that is not sanitizer-driven. **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` branch and rely solely on the pre-case `is_sanitizer_skip_reason "$gen_skip_reason"` check (mirror the `failed` branch, which only sets the flag via that helper).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:375-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The STATUS=skipped branch always sets COMMENT_UPSERT_SKIP=true without re-checking is_sanitizer_skip_reason. A future non-sanitizer STATUS=skipped from the generator would suppress the tracking-issue upsert unexpectedly. Skip upsert only when is_sanitizer_skip_reason returns true; remove the unconditional assignment in the skipped case arm.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_37: **architecture** `skills/implement/scripts/step-7a.sh:422-428` — Rebase macro KVs are propagated by redirecting probe stdout to `$IMPLEMENT_TMPDIR/rebase-checkpoint-probe.stdout` and re-emitting each line with `emit`, not by FD 3 inheritance as `step-7a.md` (line 29) and the issue plan still describe. This works today because `rebase-checkpoint-probe.sh` never calls `larch_quiet_init`, so `emit_kv` in the child falls through to stdout (child `$$` ≠ parent `LARCH_QUIET_PID`) and is captured in the file. If the probe later adopts `larch_quiet_init` without changing the capture contract, KVs would go to the child’s FD 3 (dup of the capture file) while breadcrumbs/other lines could split across streams, and maintainers might remove the relay loop assuming inheritance. **Suggested fix:** Document the stdout-capture relay as the required contract in `step-7a.md` (and drop “inheritance” wording), or invoke the probe with `LARCH_QUIET_DISABLE=1` (matching its internal `rebase-push.sh` call) and keep the explicit re-emit loop; optionally set `LARCH_QUIET_BREADCRUMB_FD` per `lib-quiet.md` if breadcrumb routing is tightened.
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:422-428` — Rebase macro KVs are propagated by redirecting probe stdout to `$IMPLEMENT_TMPDIR/rebase-checkpoint-probe.stdout` and re-emitting each line with `emit`, not by FD 3 inheritance as `step-7a.md` (line 29) and the issue plan still describe. This works today because `rebase-checkpoint-probe.sh` never calls `larch_quiet_init`, so `emit_kv` in the child falls through to stdout (child `$$` ≠ parent `LARCH_QUIET_PID`) and is captured in the file. If the probe later adopts `larch_quiet_init` without changing the capture contract, KVs would go to the child’s FD 3 (dup of the capture file) while breadcrumbs/other lines could split across streams, and maintainers might remove the relay loop assuming inheritance. **Suggested fix:** Document the stdout-capture relay as the required contract in `step-7a.md` (and drop “inheritance” wording), or invoke the probe with `LARCH_QUIET_DISABLE=1` (matching its internal `rebase-push.sh` call) and keep the explicit re-emit loop; optionally set `LARCH_QUIET_BREADCRUMB_FD` per `lib-quiet.md` if breadcrumb routing is tightened.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: **architecture** `skills/implement/scripts/step-7a.sh:192-206` — `capture-session-transcript.sh` is run with `LARCH_QUIET_DISABLE=1`, stdout captured to `capture-session-transcript.stdout`, then lines re-emitted via `emit`. That correctly re-homes `SESSION_TRANSCRIPT_STATUS` on step-7a’s FD 3 for the orchestrator, but it differs from the old inline SKILL path where the helper ran with its own `larch_quiet_init` and the status line appeared directly on the subprocess contract stream without a parent relay. Ordering is also batched: the status line appears only after capture finishes, not interleaved with earlier step output. **Suggested fix:** Keep the relay (it is sound); document in `step-7a.md` that transcript status is relayed, not passthrough-inherited; extend `quiet-rebase-contract` in `test-step-7a.sh` to assert `SESSION_TRANSCRIPT_STATUS=ok` under quiet mode (green path already asserts this only with `LARCH_QUIET_DISABLE=1` at line 339).
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:192-206` — `capture-session-transcript.sh` is run with `LARCH_QUIET_DISABLE=1`, stdout captured to `capture-session-transcript.stdout`, then lines re-emitted via `emit`. That correctly re-homes `SESSION_TRANSCRIPT_STATUS` on step-7a’s FD 3 for the orchestrator, but it differs from the old inline SKILL path where the helper ran with its own `larch_quiet_init` and the status line appeared directly on the subprocess contract stream without a parent relay. Ordering is also batched: the status line appears only after capture finishes, not interleaved with earlier step output. **Suggested fix:** Keep the relay (it is sound); document in `step-7a.md` that transcript status is relayed, not passthrough-inherited; extend `quiet-rebase-contract` in `test-step-7a.sh` to assert `SESSION_TRANSCRIPT_STATUS=ok` under quiet mode (green path already asserts this only with `LARCH_QUIET_DISABLE=1` at line 339).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:132-173
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_log_flush and repeated run_larch_log_write blocks make step-7a.sh a large single-responsibility-heavy orchestrator. Harder to review or reuse pre-bump flush logic; batch-write failures repeat the same append-tool-failure boilerplate. Optionally extract flush to a helper or loop batch definitions; keep scope small if this issue only needs consolidation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:161-169
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_larch_log_write has duplicate set +e after capturing rc. No functional breakage; adds noise when reading control flow. Remove the redundant second set +e.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: correctness: skills/implement/scripts/step-7a.sh:420-428
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Nested larch_quiet_init on rebase-checkpoint-probe child sends emit_kv to quiet log; stdout capture of rebase_out is empty for production probe. 7a.r conflict: orchestrator misses REBASE_OUTCOME=conflict and CONFLICT_FILES; macro routing may continue past rebase failure. Invoke probe with LARCH_QUIET_DISABLE=1; re-emit captured stdout via emit; add quiet-mode harness using emit_kv stub.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

