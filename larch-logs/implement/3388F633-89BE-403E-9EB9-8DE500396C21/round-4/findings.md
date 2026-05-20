### FINDING_1: **Important** `risk-integration` [skills/implement/SKILL.md:1675](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1675): Step 7a calls `capture-session-transcript.sh` without `--defer-commit true`, so the wrapper commits immediately at [scripts/capture-session-transcript.sh:204](<OPERATOR_REPO_PATH>/scripts/capture-session-transcript.sh:204) and the outer Step 7a flush commits again at [skills/implement/SKILL.md:1698](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1698). A normal run with a valid transcript now produces two pre-bump `chore(larch-logs)` commits, with the first committed before the post-transcript `execution-issues` status is flushed. Pass `--defer-commit true` at the Step 7a call site and let the existing Step 7a `larch-log.sh commit` own the single flush commit.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/implement/SKILL.md:1675](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1675): Step 7a calls `capture-session-transcript.sh` without `--defer-commit true`, so the wrapper commits immediately at [scripts/capture-session-transcript.sh:204](<OPERATOR_REPO_PATH>/scripts/capture-session-transcript.sh:204) and the outer Step 7a flush commits again at [skills/implement/SKILL.md:1698](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1698). A normal run with a valid transcript now produces two pre-bump `chore(larch-logs)` commits, with the first committed before the post-transcript `execution-issues` status is flushed. Pass `--defer-commit true` at the Step 7a call site and let the existing Step 7a `larch-log.sh commit` own the single flush commit.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `security` [scripts/capture-session-transcript.sh:139](<OPERATOR_REPO_PATH>/scripts/capture-session-transcript.sh:139): The fallback recovery warning includes the full recovered raw transcript path, and the new post-transcript flush at [skills/implement/SKILL.md:1682](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1682) makes that warning durable in `execution-issues.ndjson`. If Step 0’s source snapshot is missing, a public run log can now include paths like `<OPERATOR_REPO_PATH>/projects/<encoded-private-workspace>/<session>.jsonl`; the larch-log redaction path only strips tmpdir paths and token patterns, not arbitrary home/project paths. Change the warning to record only a non-sensitive basename/status, or explicitly redact the recovered path before appending it.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` [scripts/capture-session-transcript.sh:139](<OPERATOR_REPO_PATH>/scripts/capture-session-transcript.sh:139): The fallback recovery warning includes the full recovered raw transcript path, and the new post-transcript flush at [skills/implement/SKILL.md:1682](<OPERATOR_REPO_PATH>/skills/implement/SKILL.md:1682) makes that warning durable in `execution-issues.ndjson`. If Step 0’s source snapshot is missing, a public run log can now include paths like `<OPERATOR_REPO_PATH>/projects/<encoded-private-workspace>/<session>.jsonl`; the larch-log redaction path only strips tmpdir paths and token patterns, not arbitrary home/project paths. Change the warning to record only a non-sensitive basename/status, or explicitly redact the recovered path before appending it.
- **Suggested revision**: Address the concern above.

### FINDING_3: **[risk-integration]** [`docs/run-logs-required-files.tsv:11-14`](docs/run-logs-required-files.tsv) — The Step-7a block lists `token-report.json`, `timing-report.json`, and `execution-issues.ndjson` but **no** `session-transcript.jsonl` row, so [`scripts/verify-run-log-completeness.sh:84-100`](scripts/verify-run-log-completeness.sh) never treats a missing transcript as `MISSING=...`. That weakens the “merged run must carry session-transcript” integration guarantee the branch is aimed at; add a `session-transcript.jsonl` row with `step7a` (and extend [`scripts/verify-run-log-completeness.sh:38-71`](scripts/verify-run-log-completeness.sh) / [`scripts/test-verify-run-log-completeness.sh:28-34`](scripts/test-verify-run-log-completeness.sh) if the `step7a` inference predicate needs to treat transcript as a first-class signal).
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[risk-integration]** [`docs/run-logs-required-files.tsv:11-14`](docs/run-logs-required-files.tsv) — The Step-7a block lists `token-report.json`, `timing-report.json`, and `execution-issues.ndjson` but **no** `session-transcript.jsonl` row, so [`scripts/verify-run-log-completeness.sh:84-100`](scripts/verify-run-log-completeness.sh) never treats a missing transcript as `MISSING=...`. That weakens the “merged run must carry session-transcript” integration guarantee the branch is aimed at; add a `session-transcript.jsonl` row with `step7a` (and extend [`scripts/verify-run-log-completeness.sh:38-71`](scripts/verify-run-log-completeness.sh) / [`scripts/test-verify-run-log-completeness.sh:28-34`](scripts/test-verify-run-log-completeness.sh) if the `step7a` inference predicate needs to treat transcript as a first-class signal).
- **Suggested revision**: Address the concern above.

### FINDING_4: **[risk-integration]** [`scripts/capture-session-transcript.sh:200-214`](scripts/capture-session-transcript.sh) and [`skills/implement/SKILL.md:1675-1698`](skills/implement/SKILL.md) — On the Step 7a path, `capture-session-transcript.sh` runs `larch-log.sh commit` **before** `emit_status` appends the `SESSION_TRANSCRIPT_STATUS` warning to [`$IMPLEMENT_TMPDIR/execution-issues.md`](skills/implement/SKILL.md) and before [`skills/implement/scripts/flush-execution-issues.sh`](skills/implement/SKILL.md) (lines 1682–1696) materializes that tail into [`larch-logs/implement/<RUN_ID>/execution-issues.ndjson`](scripts/larch-log.sh). The follow-up flush is best-effort (`|| true` with tool-failure append), and the **final** `larch-log.sh commit` is also `|| true` ([`skills/implement/SKILL.md:1697-1698`](skills/implement/SKILL.md)). If the post-transcript flush or the outer commit fails without recovery, the repo can retain a newly committed [`session-transcript.jsonl`](scripts/capture-session-transcript.sh) while the durable [`execution-issues.ndjson`](docs/run-logs.md) never records the status—**worse than the prior single-commit Step 7a tail** where one failed commit did not leave an ahead-of-audit transcript artifact. Mitigation options: use `--defer-commit true` in Step 7a (mirror [`scripts/refresh-run-logs.sh:89-98`](scripts/refresh-run-logs.sh)) so one commit covers transcript + flushed warnings, or harden the outer commit / flush failure path so a failed audit append cannot follow a successful transcript commit.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[risk-integration]** [`scripts/capture-session-transcript.sh:200-214`](scripts/capture-session-transcript.sh) and [`skills/implement/SKILL.md:1675-1698`](skills/implement/SKILL.md) — On the Step 7a path, `capture-session-transcript.sh` runs `larch-log.sh commit` **before** `emit_status` appends the `SESSION_TRANSCRIPT_STATUS` warning to [`$IMPLEMENT_TMPDIR/execution-issues.md`](skills/implement/SKILL.md) and before [`skills/implement/scripts/flush-execution-issues.sh`](skills/implement/SKILL.md) (lines 1682–1696) materializes that tail into [`larch-logs/implement/<RUN_ID>/execution-issues.ndjson`](scripts/larch-log.sh). The follow-up flush is best-effort (`|| true` with tool-failure append), and the **final** `larch-log.sh commit` is also `|| true` ([`skills/implement/SKILL.md:1697-1698`](skills/implement/SKILL.md)). If the post-transcript flush or the outer commit fails without recovery, the repo can retain a newly committed [`session-transcript.jsonl`](scripts/capture-session-transcript.sh) while the durable [`execution-issues.ndjson`](docs/run-logs.md) never records the status—**worse than the prior single-commit Step 7a tail** where one failed commit did not leave an ahead-of-audit transcript artifact. Mitigation options: use `--defer-commit true` in Step 7a (mirror [`scripts/refresh-run-logs.sh:89-98`](scripts/refresh-run-logs.sh)) so one commit covers transcript + flushed warnings, or harden the outer commit / flush failure path so a failed audit append cannot follow a successful transcript commit.
- **Suggested revision**: Address the concern above.

### FINDING_5: **correctness** [`scripts/ship-pr.md:91`](scripts/ship-pr.md) — The postmerge paragraph still says “Token-report refresh, `larch:final-summary` upsert, **session-transcript capture**, and tmpdir teardown still run in the **prompt-side Step 18** orchestrator.” This branch moves primary capture to Step 7a (pre-bump flush) and refresh to [`scripts/refresh-run-logs.sh:84-98`](scripts/refresh-run-logs.sh), and [`docs/run-logs.md`](docs/run-logs.md) / [`scripts/capture-session-transcript.md`](scripts/capture-session-transcript.md) are updated accordingly. **Suggested fix:** Rewrite that sentence so session-transcript capture is attributed to Step 7a + `refresh-run-logs.sh` (and CI-retry refresh), and reserve Step 18 for teardown / remaining orchestrator-only work that still applies.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **correctness** [`scripts/ship-pr.md:91`](scripts/ship-pr.md) — The postmerge paragraph still says “Token-report refresh, `larch:final-summary` upsert, **session-transcript capture**, and tmpdir teardown still run in the **prompt-side Step 18** orchestrator.” This branch moves primary capture to Step 7a (pre-bump flush) and refresh to [`scripts/refresh-run-logs.sh:84-98`](scripts/refresh-run-logs.sh), and [`docs/run-logs.md`](docs/run-logs.md) / [`scripts/capture-session-transcript.md`](scripts/capture-session-transcript.md) are updated accordingly. **Suggested fix:** Rewrite that sentence so session-transcript capture is attributed to Step 7a + `refresh-run-logs.sh` (and CI-retry refresh), and reserve Step 18 for teardown / remaining orchestrator-only work that still applies.
- **Suggested revision**: Address the concern above.

### FINDING_6: **correctness** [`scripts/test-verify-run-log-completeness.sh:45-48`](scripts/test-verify-run-log-completeness.sh) — `assert_manifest_matches_batch_table` only cross-checks `batch_slug` / `extension` against [`scripts/larch-log-batches.sh`](scripts/larch-log-batches.sh) for `always` and `step5` rows; rows with conditions `step7a`, `step8`, and `step9a1` in [`docs/run-logs-required-files.tsv:10-14`](docs/run-logs-required-files.tsv) skip the guard. A typo in those columns would not fail CI. **Suggested fix:** Extend the `case "$condition"` arm to include `step7a|step8|step9a1` (still skipping `manifest`), or validate all data rows uniformly.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **correctness** [`scripts/test-verify-run-log-completeness.sh:45-48`](scripts/test-verify-run-log-completeness.sh) — `assert_manifest_matches_batch_table` only cross-checks `batch_slug` / `extension` against [`scripts/larch-log-batches.sh`](scripts/larch-log-batches.sh) for `always` and `step5` rows; rows with conditions `step7a`, `step8`, and `step9a1` in [`docs/run-logs-required-files.tsv:10-14`](docs/run-logs-required-files.tsv) skip the guard. A typo in those columns would not fail CI. **Suggested fix:** Extend the `case "$condition"` arm to include `step7a|step8|step9a1` (still skipping `manifest`), or validate all data rows uniformly.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **[architecture]** [`scripts/refresh-run-logs.sh:87-98`](scripts/refresh-run-logs.sh) — `SESSION_TRANSCRIPT_STATUS` is redirected to `/dev/null`, so operators relying on stdout for that signal get no signal on the refresh path (stderr is also suppressed on the flush helpers). Minor observability trade-off, not an ordering defect.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[architecture]** [`scripts/refresh-run-logs.sh:87-98`](scripts/refresh-run-logs.sh) — `SESSION_TRANSCRIPT_STATUS` is redirected to `/dev/null`, so operators relying on stdout for that signal get no signal on the refresh path (stderr is also suppressed on the flush helpers). Minor observability trade-off, not an ordering defect.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] **[risk-integration]** [`scripts/refresh-run-logs.sh:62-70`](scripts/refresh-run-logs.sh) and [`scripts/refresh-run-logs.sh:99-107`](scripts/refresh-run-logs.sh) — Post-transcript `flush-execution-issues.sh` only runs when `execution-issues.md` is non-empty **and** (checkpoint **or** sentinel **or** [`execution-issues.ndjson`](scripts/refresh-run-logs.sh)) exists. That matches normal post–Step-7a runs (checkpoint is created even on an empty pre-bump flush via [`skills/implement/scripts/flush-execution-issues.sh:86-90`](skills/implement/scripts/flush-execution-issues.sh)); a refresh without any of those signals is an unusual / hand-stubbed case rather than something this diff newly breaks.
- **Reviewer**: dyn-lifecycle-ordering-output.txt
- **Concern**: - **[risk-integration]** [`scripts/refresh-run-logs.sh:62-70`](scripts/refresh-run-logs.sh) and [`scripts/refresh-run-logs.sh:99-107`](scripts/refresh-run-logs.sh) — Post-transcript `flush-execution-issues.sh` only runs when `execution-issues.md` is non-empty **and** (checkpoint **or** sentinel **or** [`execution-issues.ndjson`](scripts/refresh-run-logs.sh)) exists. That matches normal post–Step-7a runs (checkpoint is created even on an empty pre-bump flush via [`skills/implement/scripts/flush-execution-issues.sh:86-90`](skills/implement/scripts/flush-execution-issues.sh)); a refresh without any of those signals is an unusual / hand-stubbed case rather than something this diff newly breaks.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] **code-quality** [`scripts/verify-run-log-completeness.sh:84-99`](scripts/verify-run-log-completeness.sh) — TSV rows are not CRLF-trimmed or field-normalized; Windows-style `\r` line endings could yield odd `relative_path` keys (editor hygiene / `.gitattributes` mitigation). Low practical risk for a repo-maintained TSV.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **code-quality** [`scripts/verify-run-log-completeness.sh:84-99`](scripts/verify-run-log-completeness.sh) — TSV rows are not CRLF-trimmed or field-normalized; Windows-style `\r` line endings could yield odd `relative_path` keys (editor hygiene / `.gitattributes` mitigation). Low practical risk for a repo-maintained TSV.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] **correctness** [`docs/run-logs-required-files.tsv:1-4`](docs/run-logs-required-files.tsv), [`scripts/verify-run-log-completeness.md:35-36`](scripts/verify-run-log-completeness.md), [`scripts/test-verify-run-log-completeness.sh:73-85`](scripts/test-verify-run-log-completeness.sh) — Excluding `session-transcript.jsonl` from the manifest matches the stated best-effort policy; the “complete run” harness never creates that file and still expects `OK`, which matches the intended contract.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **correctness** [`docs/run-logs-required-files.tsv:1-4`](docs/run-logs-required-files.tsv), [`scripts/verify-run-log-completeness.md:35-36`](scripts/verify-run-log-completeness.md), [`scripts/test-verify-run-log-completeness.sh:73-85`](scripts/test-verify-run-log-completeness.sh) — Excluding `session-transcript.jsonl` from the manifest matches the stated best-effort policy; the “complete run” harness never creates that file and still expects `OK`, which matches the intended contract.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] **correctness** [`scripts/verify-run-log-completeness.sh:37-70`](scripts/verify-run-log-completeness.sh) — `condition_reached` chains `step5 → step7a → step8 → step9a1` only forward; `step9a1` does not recurse back into `step8`/`step7a`, so there is no mutual-recursion cycle given the current table.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **correctness** [`scripts/verify-run-log-completeness.sh:37-70`](scripts/verify-run-log-completeness.sh) — `condition_reached` chains `step5 → step7a → step8 → step9a1` only forward; `step9a1` does not recurse back into `step8`/`step7a`, so there is no mutual-recursion cycle given the current table.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] **correctness** [`scripts/verify-run-log-completeness.sh:54-64`](scripts/verify-run-log-completeness.sh) — `MANIFEST_PR_NUMBER` appears in both `step8` and `step9a1` disjuncts; [`scripts/test-verify-run-log-completeness.sh:145-157`](scripts/test-verify-run-log-completeness.sh) encodes the strict outcome (synthetic manifest with `pr_number` forces `version-bump-reasoning.md` and `run-statistics.md`). With `pr_number` deferred to postmerge in [`scripts/ship-pr.sh:1635-1639`](scripts/ship-pr.sh), committed trees with `pr_number` but no bump reasoning are unlikely in normal flow; remaining risk is hand-edited or recovered manifests.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **correctness** [`scripts/verify-run-log-completeness.sh:54-64`](scripts/verify-run-log-completeness.sh) — `MANIFEST_PR_NUMBER` appears in both `step8` and `step9a1` disjuncts; [`scripts/test-verify-run-log-completeness.sh:145-157`](scripts/test-verify-run-log-completeness.sh) encodes the strict outcome (synthetic manifest with `pr_number` forces `version-bump-reasoning.md` and `run-statistics.md`). With `pr_number` deferred to postmerge in [`scripts/ship-pr.sh:1635-1639`](scripts/ship-pr.sh), committed trees with `pr_number` but no bump reasoning are unlikely in normal flow; remaining risk is hand-edited or recovered manifests.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] **security** [`scripts/verify-run-log-completeness.sh:16-30`](scripts/verify-run-log-completeness.sh) — `manifest_pr_number` passes `"$RUN_DIR/manifest.json"` as a single Python `sys.argv[1]`; shell splitting is not applied. Exotic paths (e.g. embedded newlines) are the usual low-level footgun for any CLI path argument, not a practical injection surface here.
- **Reviewer**: dyn-completeness-inference-output.txt
- **Concern**: - **security** [`scripts/verify-run-log-completeness.sh:16-30`](scripts/verify-run-log-completeness.sh) — `manifest_pr_number` passes `"$RUN_DIR/manifest.json"` as a single Python `sys.argv[1]`; shell splitting is not applied. Exotic paths (e.g. embedded newlines) are the usual low-level footgun for any CLI path argument, not a practical injection surface here.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:316
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Changelog still names suppressed-default-branch transcript status. Readers may think that status still exists if they stop at changelog. None required here; update only if you want changelog to reflect current API in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] risk-integration: SECURITY.md; agent-lint.toml
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Edits extend beyond enumerated plan items 1-10. None for plan traceability; readers should sanity-check SECURITY claims against refresh-run-logs.sh and ship-pr.sh. Human pass for factual alignment if desired.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1697-1698
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Outer Step 7a larch-log.sh commit uses || true swallowing failures. Pre-existing pattern now interacts with an added mid-step capture commit see in-scope finding 1. Address via defer-commit consolidation in-scope fix.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security: scripts/capture-session-transcript.sh:79-88
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Double-quoted $message in append_warning predates this diff for other statuses (e.g. recovery path, render-failed). Not introduced solely by this branch; still a latent trust-boundary smell if messages ever carry hostile content. Harden append_warning globally in a follow-up (same fixes as above).
- **Suggested revision**: Address the concern above.

### FINDING_18: architecture: skills/implement/SKILL.md Step 7a batch-mapping row vs Step 7a bash block
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] The table still reads as one log-flush commit but Step 7a can perform capture-session-transcript.sh's internal larch-log.sh commit plus a later larch-log.sh commit after post-transcript flush. Slight mismatch between documented single flush commit and possible two-commit tail. Rephrase the batch-mapping row or Step 7a prose to mention transcript capture commit vs follow-up commit for post-transcript execution-issues.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/implement/SKILL.md:1675-1698
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 7a runs capture-session-transcript.sh with default defer-commit false so capture performs larch-log.sh commit before post-transcript flush and before the outer Step 7a commit producing two chore commits per tail and splitting transcript vs post-transcript execution-issues persistence. If the first commit succeeds and the outer commit is skipped or fails silently the branch can lack post-transcript execution-issues.ndjson updates while transcript is already committed. Use --defer-commit true for Step 7a capture mirroring refresh-run-logs.sh and retain a single trailing larch-log.sh commit after post-transcript flush.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/test-capture-session-transcript.sh:38-47
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_capture uses nine positional parameters for optional capture flags. Mis-ordered arguments when extending tests. Switch to env vars or a structured arg array for new flags.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/test-verify-run-log-completeness.md:12 and scripts/test-verify-run-log-completeness.sh:45-48
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Coverage claims full manifest vs larch-log-batches alignment but harness only validates always and step5 rows. step7a TSV slug/extension drift would pass CI while docs promise alignment. Extend assert_manifest_matches_batch_table to include step7a (and other rows as needed) or narrow the Coverage bullet.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: skills/implement/SKILL.md:1683-1696 and scripts/refresh-run-logs.sh:98-106
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated post-transcript flush block and labels. Two edit sites for the same operational contract. Optional shared helper or script fragment later.
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: skills/implement/SKILL.md:742
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Intro sentence omits explicit mention of session-transcript batch while table includes it. Skimmers miss where session transcript is written. Mention session-transcript in the durable-writes intro line.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: docs/run-logs-required-files.tsv; scripts/verify-run-log-completeness.md; docs/run-logs.md; implementation plan Verification
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] The completeness manifest and verifier deliberately omit session-transcript.jsonl while the implementation plan verification expects MISSING=session-transcript.jsonl for a Step-7a-complete run dir. Following the plan's verification command will not show MISSING=session-transcript.jsonl; CI or operators cannot use the verifier to detect missing transcripts for otherwise complete runs. Either add session-transcript.jsonl to docs/run-logs-required-files.tsv under an appropriate condition and extend verify-run-log-completeness tests, or update the plan verification bullet and manifest intent to match intentional exclusion.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: scripts/verify-run-log-completeness.sh:48-52
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] step7a reachability includes has_file execution-issues.ndjson alone. Unusual partial directories with only that file force MISSING for other Step 7a artifacts rather than a clean pre-7a OK which may surprise operators running the tool on hand-edited trees. Optional tighten signals or document that abnormal trees are diagnosed via MISSING not OK.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/verify-run-log-completeness.sh:79
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] MANIFEST_STATUS parsed with quote-field awk instead of JSON parser. manifest.json format change could mis-infer step9a1 reachability. Parse status with python3 like manifest_pr_number().
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/verify-run-log-completeness.sh:79
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] MANIFEST_STATUS parsed via fragile awk on manifest.json. Reformatted manifest.json can mis-detect status=done / pr_number-driven gates and emit wrong MISSING/OK. Parse manifest.json with python3 (or jq) like manifest_pr_number().
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/verify-run-log-completeness.sh:79-80
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] MANIFEST_STATUS is parsed with awk field splitting that assumes status is the first quoted key in manifest.json. Reordered JSON keys make $4 the literal key name status so step9a1 never treats status=done as reached yielding false OK when run-statistics.md and oos-issues.ndjson are absent without pr_number. Parse status with python3 json like manifest_pr_number().
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: skills/implement/SKILL.md Step 18 (transcript removal hunk)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan asked to replace Step 18 suppression prose with a simpler note; the diff deletes capture and long prose without adding a short replacement pointer. Operators relying on Step 18 prose alone may not see where transcript capture moved or how failures are surfaced. Add one concise Step 18 sentence pointing to Step 7a and scripts/capture-session-transcript.md (and larch-log.sh commit policy).
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: docs/run-logs.md; scripts/verify-run-log-completeness.md:24-28
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Required-file verifier excludes session-transcript.jsonl by design. Prompt implementation_plan verification expecting MISSING=session-transcript.jsonl will not reproduce; plan and tool behavior diverge. Update the plan or add an explicit optional-batch mode / doc for operators.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/test-refresh-run-logs.sh:173-176
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Refresh test only greps for session-transcript status substring. Regression in defer-commit plus commit pairing or transcript write can hide behind any status line; CI would still pass. Assert session-transcript.jsonl refresh and/or captured status with a real TRANSCRIPT_PATH fixture in session-env.sh.
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: scripts/test-verify-run-log-completeness.sh:45-48
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Manifest vs larch-log-batches alignment skips step7a (and other) TSV rows. Typo in token-report/timing-report/execution-issues slug or extension in docs/run-logs-required-files.tsv never fails the new harness; wrong files could ship until runtime larch-log write breaks. Include step7a (and step8/step9a1) conditions in assert_manifest_matches_batch_table or validate all data rows.
- **Suggested revision**: Address the concern above.

### FINDING_33: security: scripts/capture-session-transcript.sh:176-211
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Trimmed stderr from render/larch-log is interpolated into double-quoted --entry (same expansion class as WARNING_STEP_LABEL/message). Malformed or hostile stderr containing backticks or $(...) could execute on expansion; stderr may also carry sensitive diagnostics into committed execution-issues. Stop double-quote expansion for dynamic segments (entry file, printf-safe construction); consider redacting stderr before logging.
- **Suggested revision**: Address the concern above.

### FINDING_34: security: scripts/capture-session-transcript.sh:79-88
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] New --warning-step-label is expanded inside double-quoted --entry to append-execution-issue.sh, enabling shell command substitution. capture-session-transcript.sh ... --warning-step-label '$(touch /tmp/pwned)' causes arbitrary command execution when a warning is appended. Allowlist or strictly validate WARNING_STEP_LABEL; or pass static labels only; or use --entry-file / no re-expansion for dynamic text.
- **Suggested revision**: Address the concern above.

