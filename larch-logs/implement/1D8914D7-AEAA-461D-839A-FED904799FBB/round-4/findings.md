### FINDING_1: code-quality: scripts/test-implement-structure.sh:264-265
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Structural harness still pins Step 7a timing mark inside generate-code-flow-diagram.sh after marks moved to step-7a.sh. make test-implement-structure fails on shard 14 despite correct runtime marking via step-7a.sh. Retarget the grep pin to step-7a.sh (or allow either script) alongside the existing Step 4/7 commit-script pins.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/test-implement-rebase-macro.sh:65-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] test-implement-rebase-macro still requires four rebase-checkpoint-probe.sh fences in SKILL.md including 7a.r. SKILL.md now has three probe fences; make test-implement-rebase-macro fails on wrapper_count and missing 7a.r literal. Update harness for step-7a.sh as the 7a.r call site; keep three direct probe rows and add step-7a.sh / forked argv pins.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/scripts/step-7a.sh:350-354
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] upsert skip uses STATUS=skipped only, not plan-specified SKIP_REASON matching on failed. A generator emitting STATUS=failed with a sanitizer SKIP_REASON would still upsert larch:diagrams. Add SKIP_REASON / sanitizer-log detection for failed status and a harness regression case.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/step-7a.sh:119-174
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Eight repetitive run_larch_log_write blocks increase maintenance cost when batches change. New optional batches are easy to omit or duplicate incorrectly. Replace with a batch/path loop preserving existing conditionals.
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: skills/implement/scripts/step-7a.sh:343-368
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan phase 6 SKIP_REASON sanitizer detection on STATUS=failed is not implemented; only STATUS=skipped sets COMMENT_UPSERT_SKIP If generate-code-flow-diagram.sh regresses to STATUS=failed with a sanitizer SKIP_REASON step-7a still upserts larch:diagrams with placeholder text instead of skipping upsert Parse SKIP_REASON from gen_out and set COMMENT_UPSERT_SKIP on skipped status or failed+sanitizer substring per plan edge cases
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: skills/implement/scripts/step-7a.sh:350-354 vs main:skills/implement/SKILL.md:1452-1485
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sanitizer rejection skips tracking-issue upsert but main SKILL always upserted on STATUS=skipped|failed Mermaid sanitizer reject leaves stale larch:diagrams comment vs main which posted Architecture plus Code flow diagram not available Document intentional contract change or restore main upsert-with-placeholder behavior for sanitizer rejection
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/scripts/step-7a.sh:94-100
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] is_small_non_runtime_change returns true when all diff paths are blank lines CHANGED_COUNT 1-2 with only empty path lines skips diagram generation incorrectly Require at least one non-empty path evaluated before classifying as small/non-runtime
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/scripts/step-7a.sh:188-191
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] capture-session-transcript rc check is dead code because the helper always exits 0 LOG_FLUSH_STATUS never becomes degraded from transcript capture failure Remove rc check or gate degraded on SESSION_TRANSCRIPT_STATUS parsing
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/scripts/step-7a.sh:335
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Small/non-runtime skip hardcodes elapsed=0s instead of measured elapsed Breadcrumb no longer reflects real Step 7a timing Compute elapsed or drop the field to match SKILL contract
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-implement-rebase-macro.sh:63-78
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structural rebase-macro harness still requires four direct rebase-checkpoint-probe fences including 7a.r in SKILL.md. make lint runs test-implement-rebase-macro on shard 10; with only three probe fences and 7a.r inside step-7a.sh the harness fails and blocks CI. Update assertions to three direct probe calls plus a step-7a.sh pin for 7a.r; fix registry row padding match if needed.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-implement-structure.sh:263-265
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Implement-structure harness still pins Step 7a timing-ledger mark inside generate-code-flow-diagram.sh. test-implement-structure fails because marks moved to step-7a.sh, blocking shard 14 and make lint. Move the grep pin to skills/implement/scripts/step-7a.sh for both token and timing Step 7a marks.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: skills/implement/scripts/test-step-7a.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Offline harness does not verify byte-identical larch:diagrams upsert payloads against a baseline. Acceptance requires byte-identical tracking-issue comments; stub upsert only checks substring presence on one green-path summary file. Add golden fixtures for summary-diagrams.md and/or recorded upsert content on skip failure and sanitizer-skip paths.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/scripts/test-step-7a.sh:349-360
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Classifier regression coverage stops at a one-file docs/ skip case. Plan also defines two-file and CHANGELOG/.txt/.tsv-only eligibility; bugs there would not fail make test-step-7a. Add git-fixture cases for two-file docs/ diff and CHANGELOG-only diff classification.
- **Suggested revision**: Address the concern above.

### FINDING_14: **GitHub publication** still goes through `tracking-issue-summary.sh`, which enforces numeric `--issue`, marker shape, and `redact-secrets.sh` / `redact-tmpdir-paths.sh` before `gh` calls (`scripts/tracking-issue-summary.sh:52-63`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **GitHub publication** still goes through `tracking-issue-summary.sh`, which enforces numeric `--issue`, marker shape, and `redact-secrets.sh` / `redact-tmpdir-paths.sh` before `gh` calls (`scripts/tracking-issue-summary.sh:52-63`).
- **Suggested revision**: Address the concern above.

### FINDING_15: **Tool-failure logging** uses `append-tool-failure.sh --redact` for generator stderr and flush failures (`skills/implement/scripts/step-7a.sh:43-50`, `360`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Tool-failure logging** uses `append-tool-failure.sh --redact` for generator stderr and flush failures (`skills/implement/scripts/step-7a.sh:43-50`, `360`).
- **Suggested revision**: Address the concern above.

### FINDING_16: **Argv hardening** requires an absolute `--implement-tmpdir` and rejects unknown flags with exit 2 (`skills/implement/scripts/step-7a.sh:286-289`).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Argv hardening** requires an absolute `--implement-tmpdir` and rejects unknown flags with exit 2 (`skills/implement/scripts/step-7a.sh:286-289`).
- **Suggested revision**: Address the concern above.

### FINDING_17: **Sanitizer rejection** now suppresses the public `larch:diagrams` upsert when `generate-code-flow-diagram.sh` returns `STATUS=skipped` (`skills/implement/scripts/step-7a.sh:350-354`, `373`), which is stricter than `main`’s SKILL prose (which always upserted when `ISSUE_NUMBER` was set) and reduces risk of posting unsanitized Mermaid to a tracking issue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Sanitizer rejection** now suppresses the public `larch:diagrams` upsert when `generate-code-flow-diagram.sh` returns `STATUS=skipped` (`skills/implement/scripts/step-7a.sh:350-354`, `373`), which is stricter than `main`’s SKILL prose (which always upserted when `ISSUE_NUMBER` was set) and reduces risk of posting unsanitized Mermaid to a tracking issue.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Foreground contract** adds `step-7a.sh` to the denylist with dedicated banner/comment lint rules (`scripts/lint-foreground-markers.sh`), which is operational safety rather than a vulnerability but does not weaken parsing-only lint behavior.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Foreground contract** adds `step-7a.sh` to the denylist with dedicated banner/comment lint rules (`scripts/lint-foreground-markers.sh`), which is operational safety rather than a vulnerability but does not weaken parsing-only lint behavior. Child script invocations use quoted paths; the retained `bash -lc` redaction one-liner passes `PLUGIN_ROOT` and `IMPLEMENT_TMPDIR` as positional parameters (same pattern as the removed SKILL.md fence). Rebase KV relay uses `emit "$line"` without `eval`/`source` (`skills/implement/scripts/step-7a.sh:400-403`).
- **Suggested revision**: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/step-7a.sh:295-301` — `LARCH_CLAUDE_PLUGIN_ROOT` from `$IMPLEMENT_TMPDIR/session-env.sh` can repoint all subsequent helper execution with no path allowlist check. This matches pre-existing `/implement` session rehydration; consolidation only centralizes the same trust assumption. **Suggested fix:** If hardening is desired repo-wide, validate rehydrated roots against `CLAUDE_PLUGIN_ROOT` / plugin install path before overriding `PLUGIN_ROOT` (shared helper, not Step 7a–only).
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `skills/implement/scripts/step-7a.sh:105-106` — `ARCHITECTURE_DIAGRAM_FILE` is read with `[ -f ... ]` and `cat` without canonicalization under a repo root, so a poisoned session env could exfiltrate arbitrary local file content into `summary-diagrams.md` (mitigated at post time by `redact-secrets.sh`, not pre-read). Preserved from prior SKILL.md composition. **Suggested fix:** Restrict to paths under the implementation workspace or a known design-artifact directory before `cat`.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `skills/implement/scripts/step-7a.sh:176-185` — Pre-bump flush still copies session transcripts and token/timing JSON into committed `larch-logs/` via `capture-session-transcript.sh` and `larch-log.sh write|commit`. Pre-existing `/implement` data-handling model; the chore `larch-logs/implement/...` commit in this branch is intentional per `docs/run-logs.md`. **Suggested fix:** N/A unless changing the run-log contract globally.
- **Suggested revision**: Address the concern above.

### FINDING_22: `cdc28eeb` — Consolidate implement Step 7a helper
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `cdc28eeb` — Consolidate implement Step 7a helper
- **Suggested revision**: Address the concern above.

### FINDING_23: `e2805a30` — chore(larch-logs) flush (excluded per review rules)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `e2805a30` — chore(larch-logs) flush (excluded per review rules)
- **Suggested revision**: Address the concern above.

### FINDING_24: `0defd491` / `968595cc` / `4ebc3b89` — Address code review feedback (rounds 1–3)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `0defd491` / `968595cc` / `4ebc3b89` — Address code review feedback (rounds 1–3)
- **Suggested revision**: Address the concern above.

### FINDING_25: **Important** — `skills/implement/scripts/step-7a.sh:176-191` — `capture-session-transcript.sh` emits `SESSION_TRANSCRIPT_STATUS=…` via `emit_kv` on the lib-quiet FD 3 contract stream, but when invoked from `step-7a.sh` the child’s FD 3 is wired to the parent helper’s quiet log, not the orchestrator-visible stream. Only stderr is captured to `capture-session-transcript.log`; the status line never gets relayed the way `rebase-checkpoint-probe.sh` output is (lines 397–403). **Suggested fix:** After the capture call, tee or redirect capture stdout to a temp file and relay
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** — `skills/implement/scripts/step-7a.sh:176-191` — `capture-session-transcript.sh` emits `SESSION_TRANSCRIPT_STATUS=…` via `emit_kv` on the lib-quiet FD 3 contract stream, but when invoked from `step-7a.sh` the child’s FD 3 is wired to the parent helper’s quiet log, not the orchestrator-visible stream. Only stderr is captured to `capture-session-transcript.log`; the status line never gets relayed the way `rebase-checkpoint-probe.sh` output is (lines 397–403). **Suggested fix:** After the capture call, tee or redirect capture stdout to a temp file and relay
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/implement/scripts/step-7a.sh:404-408
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Rebase failure exits with probe rc and skips pre-bump flush; plan required exit 0 and unconditional flush after probe. On 7a.r conflict/failure the helper exits 1/3 with LOG_FLUSH_STATUS=skipped-rebase-checkpoint and never runs token/timing flush or larch-log commit, diverging from plan phase 12 though matching updated SKILL.md. Reconcile plan vs SKILL: either document preserved rebase exits as normative or revert to exit 0 + always run flush per original plan.
- **Suggested revision**: Address the concern above.

### FINDING_27: **correctness** `skills/implement/scripts/step-7a.sh:343-354` — Sanitizer rejection is detected only by mapping `gen_status=skipped` to `COMMENT_UPSERT_SKIP=true`; `SKIP_REASON` is never read from `code-flow-diagram.stdout` despite the plan’s phase 6 and the captured stdout already containing it. That matches today’s generator (`generate-code-flow-diagram.sh:99-103` is the sole `STATUS=skipped` path, always after `sanitize-mermaid-fragment.sh` rejection with a `REASON_TOKEN` in `SKIP_REASON`), but it is an implicit cross-script contract: any new `STATUS=skipped` meaning in `generate-code-flow-diagram.sh` would wrongly suppress the `larch:diagrams` upsert, and a future sanitizer signal emitted as `STATUS=failed` with a reject/sanitizer `SKIP_REASON` (as the plan’s edge-case note describes) would still upsert a placeholder comment because the `failed` branch never sets `COMMENT_UPSERT_SKIP`. **Suggested fix:** After parsing stdout, read `SKIP_REASON` (and optionally `REASON_TOKEN`-style tokens) and set `COMMENT_UPSERT_SKIP` from explicit sanitizer-rejection rules; keep `STATUS=skipped` as a fast path only if the generator documents that invariant in `generate-code-flow-diagram.md`, or add an explicit envelope key (e.g. `SUPPRESS_DIAGRAMS_UPSERT=true`) from the generator.
- **Reviewer**: dyn-sanitizer-rejection-logic-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/step-7a.sh:343-354` — Sanitizer rejection is detected only by mapping `gen_status=skipped` to `COMMENT_UPSERT_SKIP=true`; `SKIP_REASON` is never read from `code-flow-diagram.stdout` despite the plan’s phase 6 and the captured stdout already containing it. That matches today’s generator (`generate-code-flow-diagram.sh:99-103` is the sole `STATUS=skipped` path, always after `sanitize-mermaid-fragment.sh` rejection with a `REASON_TOKEN` in `SKIP_REASON`), but it is an implicit cross-script contract: any new `STATUS=skipped` meaning in `generate-code-flow-diagram.sh` would wrongly suppress the `larch:diagrams` upsert, and a future sanitizer signal emitted as `STATUS=failed` with a reject/sanitizer `SKIP_REASON` (as the plan’s edge-case note describes) would still upsert a placeholder comment because the `failed` branch never sets `COMMENT_UPSERT_SKIP`. **Suggested fix:** After parsing stdout, read `SKIP_REASON` (and optionally `REASON_TOKEN`-style tokens) and set `COMMENT_UPSERT_SKIP` from explicit sanitizer-rejection rules; keep `STATUS=skipped` as a fast path only if the generator documents that invariant in `generate-code-flow-diagram.md`, or add an explicit envelope key (e.g. `SUPPRESS_DIAGRAMS_UPSERT=true`) from the generator.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **Harness alignment:** `test-step-7a.sh` stubs sanitizer rejection with `STATUS=skipped` and tokenized `SKIP_REASON` (`122-126`, cases at `362-384`), which exercises the implemented `STATUS` path, not the original plan harness sketch that used `STATUS=failed` + `SKIP_REASON=sanitizer-rejected`. There is no case for `STATUS=failed` with a sanitizer-like `SKIP_REASON`, so the `SKIP_REASON`-inspection gap above is untested.
- **Reviewer**: dyn-sanitizer-rejection-logic-output.txt
- **Concern**: - **Harness alignment:** `test-step-7a.sh` stubs sanitizer rejection with `STATUS=skipped` and tokenized `SKIP_REASON` (`122-126`, cases at `362-384`), which exercises the implemented `STATUS` path, not the original plan harness sketch that used `STATUS=failed` + `SKIP_REASON=sanitizer-rejected`. There is no case for `STATUS=failed` with a sanitizer-like `SKIP_REASON`, so the `SKIP_REASON`-inspection gap above is untested.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **Main-branch behavior change:** On `main`, `SKILL.md` treated `STATUS=skipped|failed` the same for comment composition and still ran `tracking-issue-summary.sh upsert-summary` whenever `ISSUE_NUMBER` was set (`1475-1485`); the branch skips upsert on `STATUS=skipped`. That matches issue Round 1 Decision 2 and `step-7a.md:48`, but it is not byte-identical to `main`’s `larch:diagrams` output on sanitizer rejection (no comment vs placeholder comment).
- **Reviewer**: dyn-sanitizer-rejection-logic-output.txt
- **Concern**: - **Main-branch behavior change:** On `main`, `SKILL.md` treated `STATUS=skipped|failed` the same for comment composition and still ran `tracking-issue-summary.sh upsert-summary` whenever `ISSUE_NUMBER` was set (`1475-1485`); the branch skips upsert on `STATUS=skipped`. That matches issue Round 1 Decision 2 and `step-7a.md:48`, but it is not byte-identical to `main`’s `larch:diagrams` output on sanitizer rejection (no comment vs placeholder comment).
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **Documentation split:** `step-7a.md:48` documents the “`skipped` means sanitizer only” invariant; `generate-code-flow-diagram.md:18-20` only lists `STATUS=ok|skipped|failed` without tying `skipped` to sanitizer rejection, so the coupling lives in one sibling doc rather than at the producer.
- **Reviewer**: dyn-sanitizer-rejection-logic-output.txt
- **Concern**: - **Documentation split:** `step-7a.md:48` documents the “`skipped` means sanitizer only” invariant; `generate-code-flow-diagram.md:18-20` only lists `STATUS=ok|skipped|failed` without tying `skipped` to sanitizer rejection, so the coupling lives in one sibling doc rather than at the producer.
- **Suggested revision**: Address the concern above.

