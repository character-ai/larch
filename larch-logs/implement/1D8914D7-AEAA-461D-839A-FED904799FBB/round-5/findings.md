### FINDING_1: code-quality: skills/implement/scripts/step-7a.sh:348-355
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Step 7a token/timing marks run before the classifier on every path including small/non-runtime skip. On main, skip paths never invoked generate-code-flow-diagram.sh so those marks were absent; timing/token reports may show an extra Step 7a segment for docs-only PRs. Move marks after the classifier on the generate path only, or document the intentional delta in step-7a.md.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/step-7a.sh:63-74,375-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] is_sanitizer_skip_reason hard-codes REASON_TOKEN patterns that must track sanitize-mermaid-fragment.sh manually. A new sanitizer rejection token could still upsert larch:diagrams until step-7a.sh is updated, violating the sanitizer skip-upsert contract. Share token detection with the sanitizer or generator output (parse REASON_TOKEN / central lib) instead of duplicating case patterns.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:375-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] The STATUS=skipped branch always sets COMMENT_UPSERT_SKIP=true without re-checking is_sanitizer_skip_reason. A future non-sanitizer STATUS=skipped from the generator would suppress the tracking-issue upsert unexpectedly. Skip upsert only when is_sanitizer_skip_reason returns true; remove the unconditional assignment in the skipped case arm.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:132-173
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_log_flush and repeated run_larch_log_write blocks make step-7a.sh a large single-responsibility-heavy orchestrator. Harder to review or reuse pre-bump flush logic; batch-write failures repeat the same append-tool-failure boilerplate. Optionally extract flush to a helper or loop batch definitions; keep scope small if this issue only needs consolidation.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/step-7a.sh:161-169
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_larch_log_write has duplicate set +e after capturing rc. No functional breakage; adds noise when reading control flow. Remove the redundant second set +e.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-7a.sh:208-211
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Non-zero rc handling for capture-session-transcript.sh is likely dead code. No current failure mode; branch only matters if the helper contract changes. Remove the rc check or add a test if non-zero exit becomes valid.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/scripts/step-7a.sh:420-428
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Nested larch_quiet_init on rebase-checkpoint-probe child sends emit_kv to quiet log; stdout capture of rebase_out is empty for production probe. 7a.r conflict: orchestrator misses REBASE_OUTCOME=conflict and CONFLICT_FILES; macro routing may continue past rebase failure. Invoke probe with LARCH_QUIET_DISABLE=1; re-emit captured stdout via emit; add quiet-mode harness using emit_kv stub.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/test-implement-rebase-macro.sh:63-77
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] SKILL.md has 3 direct rebase-checkpoint-probe fences; macro test still requires 4 including 7a.r. make lint / test-implement-rebase-macro fails on assertion (C). Update test to 3 direct fences plus step-7a.sh for 7a.r registry row.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:366-379
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sanitizer STATUS=skipped suppresses larch:diagrams upsert; main SKILL always posted placeholder comment. Sanitizer rejection leaves stale or missing tracking-issue diagrams comment vs pre-change runs. Align acceptance with skip behavior or restore upsert-with-placeholder for sanitizer path.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/implement/scripts/test-step-7a.sh:496-503
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] quiet-rebase-contract uses stdout-printing stub; does not exercise lib-quiet emit_kv probe path. CI green while production loses REBASE_* KV relay under quiet mode. Add stub probe using emit_kv under parent quiet init; assert REBASE_OUTCOME on contract stream.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:123
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Macro text still claims one direct probe invocation per registry row including 7a.r. Operators may copy obsolete 7a.r probe fence from macro section. Document 7a.r as step-7a.sh foreground call with internal probe.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-step-7a.sh:80-348
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] No golden or integration assertion for byte-identical larch:diagrams comment content On a run with a real architecture diagram file and sanitizer edge cases, summary body can drift from SKILL.md without CI failure Add fixture/golden tests for summary-diagrams.md and key upsert inputs across skip/fail/architecture paths
- **Suggested revision**: Address the concern above.

### FINDING_13: **Argv / shell**: `--implement-tmpdir` requires an absolute path; child helpers are invoked with quoted paths. The `bash -lc` redact helper passes `PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` as positional parameters (not interpolated into the `-lc` string), matching the prior SKILL.md pattern.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv / shell**: `--implement-tmpdir` requires an absolute path; child helpers are invoked with quoted paths. The `bash -lc` redact helper passes `PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` as positional parameters (not interpolated into the `-lc` string), matching the prior SKILL.md pattern.
- **Suggested revision**: Address the concern above.

### FINDING_14: **GitHub / issue identifiers**: `ISSUE_NUMBER` is still validated downstream in [`scripts/tracking-issue-summary.sh`](scripts/tracking-issue-summary.sh) (`*[!0-9]*` rejection). Marker shape is still constrained to `<!-- larch:… -->`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **GitHub / issue identifiers**: `ISSUE_NUMBER` is still validated downstream in [`scripts/tracking-issue-summary.sh`](scripts/tracking-issue-summary.sh) (`*[!0-9]*` rejection). Marker shape is still constrained to `<!-- larch:… -->`.
- **Suggested revision**: Address the concern above.

### FINDING_15: **Secret handling**: Failure paths use `append-tool-failure.sh --redact`; diagram upsert still runs `tracking-issue-summary.sh`’s `redact-secrets.sh` / `redact-tmpdir-paths.sh` pipeline before `gh` calls.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Secret handling**: Failure paths use `append-tool-failure.sh --redact`; diagram upsert still runs `tracking-issue-summary.sh`’s `redact-secrets.sh` / `redact-tmpdir-paths.sh` pipeline before `gh` calls.
- **Suggested revision**: Address the concern above.

### FINDING_16: **Mermaid / public comment surface**: Sanitizer-rejection paths suppress the `larch:diagrams` upsert (`COMMENT_UPSERT_SKIP`), which reduces risk of posting unsanitized Mermaid to a public tracking issue compared with the old inline SKILL flow that still upserted on `STATUS=skipped`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Mermaid / public comment surface**: Sanitizer-rejection paths suppress the `larch:diagrams` upsert (`COMMENT_UPSERT_SKIP`), which reduces risk of posting unsanitized Mermaid to a public tracking issue compared with the old inline SKILL flow that still upserted on `STATUS=skipped`.
- **Suggested revision**: Address the concern above.

### FINDING_17: **KV relay**: Re-emitting `rebase-checkpoint-probe.sh` and `capture-session-transcript.sh` stdout through `emit` keeps the same trusted-child model as direct foreground invocation; captured lines are structured `emit_kv` output, not arbitrary file content.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **KV relay**: Re-emitting `rebase-checkpoint-probe.sh` and `capture-session-transcript.sh` stdout through `emit` keeps the same trusted-child model as direct foreground invocation; captured lines are structured `emit_kv` output, not arbitrary file content.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Diff scan**: No new hard-coded credentials or auth material in the feature diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Diff scan**: No new hard-coded credentials or auth material in the feature diff.
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/step-7a.sh:118-119` — `ARCHITECTURE_DIAGRAM_FILE` is still read with only `-f` gating (no repo-root confinement or symlink hardening) before inclusion in `summary-diagrams.md` and GitHub upsert. **Why out of scope:** identical trust model to the removed inline Step 7a fences in `SKILL.md`; this change relocates rather than widens the behavior. **Suggested fix (if ever hardening):** resolve/canonicalize under a known design-artifact directory before `cat`, or reject non-regular files/symlinks outside an allowlist root.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/implement/scripts/step-7a.sh:366-414
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sanitizer rejection suppresses larch:diagrams upsert unlike main which always upserted with placeholder. Tracking issue keeps a prior run's diagram comment after sanitizer rejection; reviewers see stale Mermaid. Restore always-upsert placeholder behavior or document contract change and align acceptance/tests.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: skills/implement/scripts/step-7a.sh:429-433
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Rebase failure exits before pre-bump log flush. Orchestrator that ignores exit code reaches Step 8 without larch-log commit batches. Harden SKILL.md gate on non-zero exit; assert missing flush artifacts in rebase-conflict harness case.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/scripts/step-7a.sh:63-74
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] is_sanitizer_skip_reason allowlist may miss future REASON_TOKEN values on STATUS=failed. New sanitizer token on failed path still upserts placeholder instead of skipping upsert. Add substring reject/sanitiz guard or share REASON_TOKEN set with sanitize-mermaid-fragment.sh.
- **Suggested revision**: Address the concern above.

### FINDING_23: architecture: skills/implement/scripts/step-7a.sh:1434-1437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] capture-session-transcript rc check is dead because child always exits 0. LOG_FLUSH_STATUS stays ok when transcript capture fails internally. Set degraded from relayed SESSION_TRANSCRIPT_STATUS or remove dead rc branch.
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Harness omits ARCHITECTURE_DIAGRAM_FILE present path. Regression in architecture section composition would not be caught offline. Add harness case with ARCHITECTURE_DIAGRAM_FILE set and assert summary prefix.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/test-implement-rebase-macro.sh:62-78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Harness still requires four rebase-checkpoint-probe.sh fences in SKILL.md including 7a.r. After consolidation SKILL.md has three direct probe calls; make test-implement-rebase-macro fails and blocks make lint acceptance. Update harness to expect three SKILL fences; pin 7a.r via step-7a.sh and adjust forked-target guard coverage.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Harness still requires Step 7a timing-ledger mark in generate-code-flow-diagram.sh. Marks moved to step-7a.sh; make test-implement-structure fails on every lint run. Retarget grep to step-7a.sh; optionally assert generator no longer contains Step 7a marks.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `skills/implement/scripts/step-7a.sh:375-379` — The `skipped` arm of the `gen_status` case sets `COMMENT_UPSERT_SKIP=true` unconditionally, even though Phase 6 in the implementation plan requires upsert suppression only when `is_sanitizer_skip_reason` matches `SKIP_REASON`. Lines 366–367 already apply that sanitizer gate before the `case`, so line 379 is redundant for today’s generator and over-broad for any future `STATUS=skipped` envelope that is not sanitizer-driven. **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` branch and rely solely on the pre-case `is_sanitizer_skip_reason "$gen_skip_reason"` check (mirror the `failed` branch, which only sets the flag via that helper).
- **Reviewer**: dyn-generator-skip-upsert-gate-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:375-379` — The `skipped` arm of the `gen_status` case sets `COMMENT_UPSERT_SKIP=true` unconditionally, even though Phase 6 in the implementation plan requires upsert suppression only when `is_sanitizer_skip_reason` matches `SKIP_REASON`. Lines 366–367 already apply that sanitizer gate before the `case`, so line 379 is redundant for today’s generator and over-broad for any future `STATUS=skipped` envelope that is not sanitizer-driven. **Suggested fix:** Remove `COMMENT_UPSERT_SKIP=true` from the `skipped` branch and rely solely on the pre-case `is_sanitizer_skip_reason "$gen_skip_reason"` check (mirror the `failed` branch, which only sets the flag via that helper).
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-generator-skip-upsert-gate-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-step-7a.sh:122-126,363-384` — The `diagram-rejected` stub emits `STATUS=skipped` with a sanitizer-class `SKIP_REASON`, so it passes under both the token gate and the unconditional `skipped` assignment; it does not exercise a `STATUS=skipped` + non-sanitizer `SKIP_REASON` case that would expose the Phase 6 mismatch.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-generator-skip-upsert-gate-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/generate-code-flow-diagram.sh:99-103` — Production code only emits `STATUS=skipped` on sanitizer failure, so the unconditional `skipped`-branch upsert skip is latent today, not observable in live `/implement` runs with the current generator.
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-generator-skip-upsert-gate-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.md:49` — Sibling docs state upsert is suppressed on `STATUS=skipped` OR sanitizer `SKIP_REASON`, which matches current code but diverges from the plan’s sanitizer-token-only Phase 6 wording; align doc and script if the token-only gate is the intended contract.
- **Suggested revision**: Address the concern above.

### FINDING_31: **architecture** `larch-logs/implement/1D8914D7-AEAA-461D-839A-FED904799FBB/plan-goals-test.md:44` — Phase 12 still says `step-7a.sh` “exit stays 0” on rebase failure while the shipped helper does `exit "$rebase_rc"` at `skills/implement/scripts/step-7a.sh:429-432`. That contradicts the authoritative surfaces updated on this branch (`skills/implement/scripts/step-7a.md:31-37`, `skills/implement/SKILL.md:129-147,1436-1437`, `skills/implement/scripts/test-step-7a.sh:476-494`). The runtime behavior is correct for the Rebase Checkpoint Macro (orchestrator must see probe exit 1/3 on the wrapper process, not only stdout KVs), but the stale run-log plan can mislead a follow-up change into “fixing” working exit propagation. **Suggested fix:** Update the committed plan snapshot (and any mirrored design plan text) to state that `step-7a.sh` preserves `rebase-checkpoint-probe.sh` exit codes 1/3 (and other non-zero codes), sets `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, emits the diagram KV tail, and skips pre-bump flush on non-zero rebase; keep argv as the only `STEP_7A_BAIL_REASON` path (`exit 2`).
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `larch-logs/implement/1D8914D7-AEAA-461D-839A-FED904799FBB/plan-goals-test.md:44` — Phase 12 still says `step-7a.sh` “exit stays 0” on rebase failure while the shipped helper does `exit "$rebase_rc"` at `skills/implement/scripts/step-7a.sh:429-432`. That contradicts the authoritative surfaces updated on this branch (`skills/implement/scripts/step-7a.md:31-37`, `skills/implement/SKILL.md:129-147,1436-1437`, `skills/implement/scripts/test-step-7a.sh:476-494`). The runtime behavior is correct for the Rebase Checkpoint Macro (orchestrator must see probe exit 1/3 on the wrapper process, not only stdout KVs), but the stale run-log plan can mislead a follow-up change into “fixing” working exit propagation. **Suggested fix:** Update the committed plan snapshot (and any mirrored design plan text) to state that `step-7a.sh` preserves `rebase-checkpoint-probe.sh` exit codes 1/3 (and other non-zero codes), sets `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, emits the diagram KV tail, and skips pre-bump flush on non-zero rebase; keep argv as the only `STEP_7A_BAIL_REASON` path (`exit 2`).
- **Suggested revision**: Address the concern above.

### FINDING_32: **architecture** `skills/implement/scripts/step-7a.md:31-38` — The exit table documents `0`, `1`, `3`, and `2` but not the macro’s “other non-zero exit” branch (`skills/implement/SKILL.md:133`, `scripts/rebase-checkpoint-probe.md:24`), even though `step-7a.sh:432` forwards any non-zero `rebase_rc` verbatim. That gap is amplified by this branch because 7a.r is no longer a separate foreground probe call. **Suggested fix:** Add a row such as “other non-zero: preserved probe exit; orchestrator uses the macro’s `unexpected-rc-<n>` / other-non-zero routing” and note that only `REBASE_OUTCOME=ok|skipped` runs the pre-bump flush phase.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.md:31-38` — The exit table documents `0`, `1`, `3`, and `2` but not the macro’s “other non-zero exit” branch (`skills/implement/SKILL.md:133`, `scripts/rebase-checkpoint-probe.md:24`), even though `step-7a.sh:432` forwards any non-zero `rebase_rc` verbatim. That gap is amplified by this branch because 7a.r is no longer a separate foreground probe call. **Suggested fix:** Add a row such as “other non-zero: preserved probe exit; orchestrator uses the macro’s `unexpected-rc-<n>` / other-non-zero routing” and note that only `REBASE_OUTCOME=ok|skipped` runs the pre-bump flush phase.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `skills/implement/scripts/test-step-7a.sh` — Rebase exit propagation is covered for conflict (`exit 1`) and failed (`exit 3`), but there is no case where the stub probe exits with an unexpected code (e.g. `5` with `REBASE_ERROR=unexpected-rc-5`) to pin the third macro branch after consolidation. **Suggested fix:** Add a `rebase-unexpected-rc` harness case asserting `rc=5`, relayed `REBASE_OUTCOME=failed` / `REBASE_ERROR=unexpected-rc-5`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and no flush helpers in `calls.log`.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/test-step-7a.sh` — Rebase exit propagation is covered for conflict (`exit 1`) and failed (`exit 3`), but there is no case where the stub probe exits with an unexpected code (e.g. `5` with `REBASE_ERROR=unexpected-rc-5`) to pin the third macro branch after consolidation. **Suggested fix:** Add a `rebase-unexpected-rc` harness case asserting `rc=5`, relayed `REBASE_OUTCOME=failed` / `REBASE_ERROR=unexpected-rc-5`, `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, and no flush helpers in `calls.log`.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:1436-1438` — Step 7a tells the orchestrator to apply Rebase Checkpoint Macro routing after `step-7a.sh` returns, then immediately says “Continue to Step 8 IMMEDIATELY.” That anti-halt line predates this consolidation; macro bail branches (conflict / failed / other non-zero) must override it. No regression introduced by exit propagation itself.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] Shipped code, `step-7a.md`, `SKILL.md`, and `test-step-7a.sh` are **internally consistent** on rebase exit propagation: propagating `rebase_rc` is the correct design versus the obsolete plan text that assumed `exit 0` plus caller-only macro routing. Pre-consolidation behavior exposed probe exit codes directly; the wrapper preserves that contract for `7a.r`.
- **Reviewer**: dyn-rebase-exit-propagation-output.txt
- **Concern**: - Shipped code, `step-7a.md`, `SKILL.md`, and `test-step-7a.sh` are **internally consistent** on rebase exit propagation: propagating `rebase_rc` is the correct design versus the obsolete plan text that assumed `exit 0` plus caller-only macro routing. Pre-consolidation behavior exposed probe exit codes directly; the wrapper preserves that contract for `7a.r`.
- **Suggested revision**: Address the concern above.

### FINDING_36: **architecture** `skills/implement/scripts/step-7a.sh:351-355` — After `larch_quiet_init` (line 10), the small/non-runtime skip path uses raw `printf` for `⏩ 7a: diagrams status=skip reason=small-non-runtime-change …`. Under production `/implement`, that writes to the quiet log (redirected FD 1), not the caller-visible contract stream (FD 3). On `main`, the same line was orchestrator-visible because the classifier lived in an ordinary Bash fence without quiet redirection. `SKILL.md` Verbosity Control (lines 113–115) explicitly preserves non-rebase `⏩` skip lines; hiding them is a regression. The harness masks this: `test-step-7a.sh` exports `LARCH_QUIET_DISABLE=1` (line 6), so `diagram-skip` sees the line in captured `2>&1` output even though production would not. **Suggested fix:** Emit the skip line through the contract API (`emit '⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=…'` or an appropriate `emit_breadcrumb --category=progress …`) so it lands on FD 3 in quiet mode; add a `run_helper_quiet` assertion for that line (mirroring `quiet-rebase-contract`).
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:351-355` — After `larch_quiet_init` (line 10), the small/non-runtime skip path uses raw `printf` for `⏩ 7a: diagrams status=skip reason=small-non-runtime-change …`. Under production `/implement`, that writes to the quiet log (redirected FD 1), not the caller-visible contract stream (FD 3). On `main`, the same line was orchestrator-visible because the classifier lived in an ordinary Bash fence without quiet redirection. `SKILL.md` Verbosity Control (lines 113–115) explicitly preserves non-rebase `⏩` skip lines; hiding them is a regression. The harness masks this: `test-step-7a.sh` exports `LARCH_QUIET_DISABLE=1` (line 6), so `diagram-skip` sees the line in captured `2>&1` output even though production would not. **Suggested fix:** Emit the skip line through the contract API (`emit '⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=…'` or an appropriate `emit_breadcrumb --category=progress …`) so it lands on FD 3 in quiet mode; add a `run_helper_quiet` assertion for that line (mirroring `quiet-rebase-contract`).
- **Suggested revision**: Address the concern above.

### FINDING_37: **architecture** `skills/implement/scripts/step-7a.sh:422-428` — Rebase macro KVs are propagated by redirecting probe stdout to `$IMPLEMENT_TMPDIR/rebase-checkpoint-probe.stdout` and re-emitting each line with `emit`, not by FD 3 inheritance as `step-7a.md` (line 29) and the issue plan still describe. This works today because `rebase-checkpoint-probe.sh` never calls `larch_quiet_init`, so `emit_kv` in the child falls through to stdout (child `$$` ≠ parent `LARCH_QUIET_PID`) and is captured in the file. If the probe later adopts `larch_quiet_init` without changing the capture contract, KVs would go to the child’s FD 3 (dup of the capture file) while breadcrumbs/other lines could split across streams, and maintainers might remove the relay loop assuming inheritance. **Suggested fix:** Document the stdout-capture relay as the required contract in `step-7a.md` (and drop “inheritance” wording), or invoke the probe with `LARCH_QUIET_DISABLE=1` (matching its internal `rebase-push.sh` call) and keep the explicit re-emit loop; optionally set `LARCH_QUIET_BREADCRUMB_FD` per `lib-quiet.md` if breadcrumb routing is tightened.
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:422-428` — Rebase macro KVs are propagated by redirecting probe stdout to `$IMPLEMENT_TMPDIR/rebase-checkpoint-probe.stdout` and re-emitting each line with `emit`, not by FD 3 inheritance as `step-7a.md` (line 29) and the issue plan still describe. This works today because `rebase-checkpoint-probe.sh` never calls `larch_quiet_init`, so `emit_kv` in the child falls through to stdout (child `$$` ≠ parent `LARCH_QUIET_PID`) and is captured in the file. If the probe later adopts `larch_quiet_init` without changing the capture contract, KVs would go to the child’s FD 3 (dup of the capture file) while breadcrumbs/other lines could split across streams, and maintainers might remove the relay loop assuming inheritance. **Suggested fix:** Document the stdout-capture relay as the required contract in `step-7a.md` (and drop “inheritance” wording), or invoke the probe with `LARCH_QUIET_DISABLE=1` (matching its internal `rebase-push.sh` call) and keep the explicit re-emit loop; optionally set `LARCH_QUIET_BREADCRUMB_FD` per `lib-quiet.md` if breadcrumb routing is tightened.
- **Suggested revision**: Address the concern above.

### FINDING_38: **architecture** `skills/implement/scripts/step-7a.sh:192-206` — `capture-session-transcript.sh` is run with `LARCH_QUIET_DISABLE=1`, stdout captured to `capture-session-transcript.stdout`, then lines re-emitted via `emit`. That correctly re-homes `SESSION_TRANSCRIPT_STATUS` on step-7a’s FD 3 for the orchestrator, but it differs from the old inline SKILL path where the helper ran with its own `larch_quiet_init` and the status line appeared directly on the subprocess contract stream without a parent relay. Ordering is also batched: the status line appears only after capture finishes, not interleaved with earlier step output. **Suggested fix:** Keep the relay (it is sound); document in `step-7a.md` that transcript status is relayed, not passthrough-inherited; extend `quiet-rebase-contract` in `test-step-7a.sh` to assert `SESSION_TRANSCRIPT_STATUS=ok` under quiet mode (green path already asserts this only with `LARCH_QUIET_DISABLE=1` at line 339).
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/step-7a.sh:192-206` — `capture-session-transcript.sh` is run with `LARCH_QUIET_DISABLE=1`, stdout captured to `capture-session-transcript.stdout`, then lines re-emitted via `emit`. That correctly re-homes `SESSION_TRANSCRIPT_STATUS` on step-7a’s FD 3 for the orchestrator, but it differs from the old inline SKILL path where the helper ran with its own `larch_quiet_init` and the status line appeared directly on the subprocess contract stream without a parent relay. Ordering is also batched: the status line appears only after capture finishes, not interleaved with earlier step output. **Suggested fix:** Keep the relay (it is sound); document in `step-7a.md` that transcript status is relayed, not passthrough-inherited; extend `quiet-rebase-contract` in `test-step-7a.sh` to assert `SESSION_TRANSCRIPT_STATUS=ok` under quiet mode (green path already asserts this only with `LARCH_QUIET_DISABLE=1` at line 339).
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/scripts/test-step-7a.sh:6,292-303` — Seventeen of eighteen cases run with `LARCH_QUIET_DISABLE=1`; only `quiet-rebase-contract` exercises production-like quiet + command-substitution FD 3 capture. Combined `2>&1` capture does exercise FD 3 when quiet is active (per `scripts/test-lib-quiet.sh`), but the global disable means most assertions validate stdout-routed `emit`/`emit_kv`, not the production path end-to-end.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:208-211` — `capture-session-transcript.sh` always exits 0 via `emit_status`; the `rc -ne 0` degraded branch is effectively dead unless the helper aborts before emitting. Harmless but misleading for readers tracing `LOG_FLUSH_STATUS=degraded`.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-kv-fd3-contract-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:129-147` vs issue plan — The branch intentionally has `step-7a.sh` exit with the probe’s rc on rebase conflict/failure (`step-7a.sh:429-432`) while the original plan said step-7a stays exit 0; `SKILL.md` was updated to match the implementation. Not a KV defect, but worth noting for anyone diffing against the plan block in the feature description.
- **Suggested revision**: Address the concern above.

