### FINDING_1: [OUT_OF_SCOPE] architecture: skills/fix-issue/SKILL.md:191-210
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Pre-existing Step 3 not-material markdown corruption (orphaned bash, wrong numbering) unchanged from main. Orchestrator confusion risk remains but was not introduced by this diff. Future cleanup only; not part of #2468 deliverables unless explicitly rescoped.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: .claude/skills/audit-runs/SKILL.md (969c474f area)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated audit-runs behavior change bundled on same branch Inflates diff and mixes review concerns with #2468 Ship as separate PR or document intentional batching
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: .claude/skills/audit-runs/SKILL.md:111
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Documented gh issue list --search still interpolates finding keywords without escaping guidance. Longstanding foot-gun for shell/gh search syntax if pasted blindly; not part of the run-summary script changes. Document escaping or move search text to a file; optional hardening outside this branch scope.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: 693afbe6 larch-logs/implement/*
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large larch-logs flush commit on branch. Expected per run-logs policy; not a failure-mode regression from summary code. No code change; clarify in PR if reviewers object to size.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: 693afbe6:larch-logs/implement/*
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Large committed run-log directory from implement flush. Diff noise only per repo policy. No action required for this review lens.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: 969c474f .claude/skills/audit-runs/*
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Audit-runs changes bundled on same branch as summary work. Review noise and mixed rollback units if issues found. Keep PR narrative split or follow-up split per team process.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: 969c474f:.claude/skills/audit-runs/*
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Unrelated audit-runs change set rides on the same branch as run-summary work. Larger CI/review surface per PR; bisect noise if lint fails. Split PRs next time or accept bundled delivery risk.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: Branch commit list vs single-issue PR expectation
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Multiple commits including audit-runs #2469 and larch-logs flush broaden PR scope beyond the summarized plan. Reviewers must mentally partition changes; does not violate a specific #2468 code requirement. Split PRs or narrow branch for final merge hygiene if desired.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: Branch history (merge-base..HEAD)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Multiple independent features ship on one branch (#2468 + audit-runs + run-log flush + version bump). Reviewers may mis-attribute a regression in audit-runs or logs to the run-summary change set. Partition review by commit or split PRs for bisect-friendly history.
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: skills/fix-issue/SKILL.md:336-338
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Append OUTCOME with >> while read_kv is first-match. Duplicate OUTCOME keys make the first stale value win silently. Use full-file atomic state writes or last-wins read_kv for OUTCOME.
- **Suggested revision**: Address the concern above.

### FINDING_11: architecture: skills/fix-issue/scripts/write-final-report.md (absent)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Planned sibling contract file for fix-issue write-final-report.sh was never added. No markdown authority for /fix-issue final-report CLI/tmpdir contract, marker/upsert rules, or stdout/stderr split; diverges from repo convention and the written implementation plan file list. Add skills/fix-issue/scripts/write-final-report.md aligned with implement sibling + render-run-summary.md; wire into agent-lint if required by policy.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: docs/run-logs.md:160
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] final-summary.md doc claims body starts with HTML sentinel and uses stale PR: N/A wording Consumers or scripts infer wrong first-line shape or search for legacy PR: prefix Reword to match render-run-summary output (## header first sentinel inside block markdown PR bullet N/A)
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: requirements / skills/implement/scripts/test-write-final-report.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Harness adds bailed-needs-user-input outside the eight-outcome enum from spec Plan and feature text promised eight outcomes tests drift from locked enum Add ninth to spec or fold into existing outcome and adjust tests
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: skills/fix-issue/scripts/test-write-final-report.sh:52-59
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] closed-non-pr fixture uses CLASSIFICATION=PR Misleading test data versus real NON_PR path Use NON_PR classification in fixture
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: skills/implement/scripts/write-final-report.md:5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sibling contract says markdown starts with run-summary sentinel Contradicts scripts/render-run-summary.sh and invites incorrect harness expectations Align opening line description with renderer and summary-comment-template
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: skills/implement/scripts/write-final-report.md:5864-5866;docs/run-logs.md:~1042
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Docs claim the run-summary sentinel starts the body; renderer emits ## header first and sentinel ends the bullet block. Misleading operator/docs for consumers keying off “first line” detection. Reword to describe sentinel placement relative to bullets vs optional notes.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/implement/scripts/write-final-report.md:5882-5885 vs skills/implement/scripts/write-final-report.sh:6077-6097
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Contract lists PR_CLOSED but script never reads it. Readers assume PR-closed affects outcome text when it does not. Remove PR_CLOSED from the table or implement mapping + tests.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: skills/implement/scripts/write-final-report.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Monolithic script combines many responsibilities Higher regression cost on future edits Consider small extracted collectors if file grows again
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/render-run-summary.sh:4220-4227
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Non-numeric OOS_COUNT rendered as raw text in OOS filed line. Garbage env/CLI yields plausible but wrong OOS counts. Coerce invalid OOS_COUNT to 0 or N/A like other counters.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/fix-issue/SKILL.md:359-365
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] MERGE_RESULT already_merged mapped to pr-open in Step 6c. Child /implement merged externally; fix-issue terminal summary still says pr-open. Extend case to map already_merged to pr-merged or a dedicated merged-externally outcome aligned with implement.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/fix-issue/SKILL.md:359-365
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 6c maps only merged admin_merged to pr-merged leaving already_merged as pr-open Child emits MERGE_RESULT=already_merged after external merge terminal fix-issue outcome disagrees with implement summary Extend case for already_merged or document explicit non-parity
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/SKILL.md:5574-5581
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Step 17 wraps write-final-report in || true while prose mandates failure capture to step17 failure logs. On upsert/render failure the orchestrator never sees non-zero exit, so Step 17 failure logging instructions are dead and stall/debug telemetry can be lost. Replace || true with explicit if ! …; then log/append-tool-failure; fi or revise prose to the actual swallowing contract.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: skills/implement/scripts/write-final-report.sh:118-134
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Outcome pr-created requires MERGE=false; MERGE=true with empty MERGE_RESULT falls through to bailed. A PR exists with merge requested but merge result not yet materialized in state; published summary shows bailed instead of a PR-pending outcome. Add an explicit merge-pending outcome or document the bailed fallback as intentional.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/implement/scripts/write-final-report.sh:118-138
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implement outcome resolver emits a ninth token bailed-needs-user-input not enumerated in the locked 8-outcome spec. Downstream parsers or dashboards keyed to eight outcomes misclassify or drop this terminal string; plan traceability to issue #2468 enum is incomplete. Either merge into bailed with notes-only detail or expand the locked spec and all references to a 9-value enum plus tests.
- **Suggested revision**: Address the concern above.

### FINDING_25: correctness: skills/implement/scripts/write-final-report.sh:269-318 and scripts/render-run-summary.sh:224-225
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Embedded render-run-summary.sh keeps emitting STATUS/OUTPUT_FILE KV lines to stderr while stdout is discarded. Operators or parsers tailing Step 17/18 stderr see duplicate STATUS noise and may confuse renderer vs parent KV. Redirect renderer stderr when wrapped, or add a quiet/no-envelope mode for internal composition calls.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/implement/scripts/write-final-report.sh:81-133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Empty MERGE key with PR_NUMBER set leaves outcome as bailed and mode line without --no-merge. Early refresh or partial ship-pr-state shows merged-looking PR but summary says bailed; operators mis-triage stall vs open PR. Default MERGE to false when PR_NUMBER is set or treat missing MERGE as false for pr-created classification.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/test-render-run-summary.sh:4711-4740
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] --print-stdout test discards stdout; does not prove markdown-only channel. KV leakage to stdout could regress without failing this harness. Capture stdout and assert no KEY=value envelope lines; optionally diff against output file.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/fix-issue/scripts/test-write-final-report.sh:5219-5287
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Fix-issue harness skips byte-identical and marker argv assertions; fixtures use inconsistent CLASSIFICATION for closed-non-pr. Drift in upsert marker or body vs stdout could pass CI; weak signal if CLASSIFICATION becomes load-bearing. Assert stdout equals stubbed content-file bytes; grep TRACKING_LOG for fix-issue marker; align CLASSIFICATION with real state.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/fix-issue/scripts/write-final-report.sh:95-98
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Bail outcomes skip GitHub upsert even with valid ISSUE_NUMBER. If /implement never posted a final summary, issue thread has no durable run summary. Post a slim fix-issue summary on bail when implement summary absent or document trade-off.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/implement/SKILL.md:1860-1865
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Step 17 prose requires failure logging but fenced bash only uses || true. Final report / upsert failures leave no step17 failure log or Tool Failures entry. Add capture + append-tool-failure to the fenced block or relax prose to match code.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/implement/SKILL.md:1863-1865
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Step 17 mandates failure capture for write-final-report.sh but the Bash snippet uses unconditional || true, swallowing non-zero exits from upsert failures. GitHub upsert fails (exit 1); orchestrator still sees success, no step17 failure log or append-tool-failure path runs despite the prose contract. Replace || true with structured if/else (or capture-on-failure) that logs stdout/stderr and appends Tool Failures on non-zero or STATUS=failed; align Step 18 similarly if needed.
- **Suggested revision**: Address the concern above.

### FINDING_32: risk-integration: skills/implement/scripts/test-write-final-report.sh:5699-5852
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Implement harness omits plan-required coverage: full outcome matrix, --print-stdout vs KV-only stdout, N/A/parametric stripping, note-line fixtures, already_merged. Regression in outcome text, cost line, or stdout/KV split can ship without failing CI because only a subset of branches is exercised. Add fixture-driven cases per outcome resolver branch; assert --print-stdout stdout equals written summary body and lacks KV lines; assert non-print stdout is KV-only; add N/A and note-line regressions.
- **Suggested revision**: Address the concern above.

### FINDING_33: risk-integration: skills/implement/scripts/write-final-report.sh:334-361
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Summary files written before ISSUE_NUMBER numeric validation Malformed parent-issue could write misleading local artifacts before failing upsert Validate issue earlier or document as acceptable
- **Suggested revision**: Address the concern above.

### FINDING_34: security: skills/implement/scripts/write-final-report.sh:104-110
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] RUN_ID from parent-issue/session-id is joined into filesystem paths without traversal validation. mkdir/cp/jq can follow a crafted RUN_ID with enough .. segments and write or read outside the intended larch-logs run subtree, corrupting sibling paths or the wider filesystem within umask/permissions. Mirror refresh-run-logs run_id validation (reject */ and ..) or enforce a strict RUN_ID grammar before mkdir/cp and any run_dir-relative reads.
- **Suggested revision**: Address the concern above.

### FINDING_35: security: skills/implement/scripts/write-final-report.sh:242-244
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] UPSTREAM_DESIGN_ISSUE is expanded unquoted into Markdown note lines that are posted to GitHub. Attacker-controlled or mistaken KV content injects extra Markdown lines, misleading Closes text, or breaks comment structure in the public tracking issue. Validate as digits-only (or omit note); build the line with printf '%s' and a sanitized variable; avoid double-quote expansion of raw env content.
- **Suggested revision**: Address the concern above.

