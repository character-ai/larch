### FINDING_1: [OUT_OF_SCOPE] code-quality: larch-logs/implement/003318DB-938E-4AD5-A71A-6D5E07BA6259/
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New implement run-log files appear in the branch diff. Intentional per repo policy; not a structure defect in the feature code. No action required for this review scope.
- **Suggested revision**: Address the concern above.

### FINDING_2: architecture: scripts/dispatch-code-voters.sh:236-244
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unplanned upfront rm -f of the first-pass sidecar before parse-rate classification. Not in the implementation plan; behavior is understandable for harness stale files but is not requirement-traceable. Document as intentional or restrict/move rm so it is plan-aligned.
- **Suggested revision**: Address the concern above.

### FINDING_3: architecture: scripts/dispatch-code-voters.sh:240-242 scripts/larch-log.sh:92
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Non-.txt voter_path sidecar name does not match write-round allow-list If voter_path lacks .txt suffix, sidecar is voter_path-first-pass; round_artifact_included only allows *-vote-output-first-pass.txt, so write-round drops the artifact Align naming with allow-list or extend round_artifact_included and tests for the non-.txt sidecar shape; or remove dead branch if never used
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/dispatch-code-voters.md:126-127
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Documentation says cp failures are ignored while code emits larch_err warning Operators may expect silence on cp failure but still see stderr noise Rephrase docs to match stderr warning plus non-aborting behavior
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/dispatch-code-voters.md:127-region (parse-retry paragraph)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc says cp failures are ignored while code calls larch_err on copy failure. Doc and runtime behavior disagree; misleads maintainers. Align wording with actual stderr behavior or silence the warning to match doc.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/dispatch-code-voters.sh:240-252
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate case on voter_path for first_pass_sidecar and retry_output. Future naming changes might update one case and miss the other. Single case arm assigning both derived paths.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/dispatch-code-voters.sh:263-268
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Retry-success path uses if/else on cp and omits breadcrumb when cp fails; plan described cp || true plus breadcrumb. cp failure yields stderr warning but no breadcrumb line operators might grep for in quiet streams. Use cp || true then emit stderr breadcrumb (optionally noting copy failure) for uniform observability.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/dispatch-code-voters.md:46 vs scripts/dispatch-code-voters.sh:263-267
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Documentation claims cp failures are ignored; code emits larch_err when cp fails. Same cp failure scenario: operators and future maintainers rely on the doc and expect no explicit error emission for a non-blocking copy. Align dispatch-code-voters.md with actual behavior or remove the larch_err branch to match the doc and plan.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/dispatch-code-voters.sh:238-268
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Retry-success first-pass preservation diverges from Plan Change 1: conditional cp without || true; breadcrumb only if cp succeeds; larch_err on cp failure instead of silent fail-open. After a successful parse-retry, cp to the sidecar can fail (disk full, permissions): promotion still runs but the plan-required always-on breadcrumb after a best-effort copy is missing and stderr gets larch_err instead of the specified cp || true + emit_breadcrumb sequence. Match Plan Change 1 (cp to sidecar 2>/dev/null || true; then unconditional emit_breadcrumb) or update the plan and docs if the new behavior is intentional.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Eager rm -f of first-pass sidecar path before parse-rate status runs deletes existing sidecars even when no retry occurs (extends plan beyond do-not-create). Reuse REVIEW_TMPDIR after a prior run left *-vote-output-first-pass.txt; a later substantive OK pass deletes that sidecar at entry before returning OK. Restrict rm -f to the retry-success branch immediately before cp (or only when replacing).
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unconditional rm -f of the first-pass sidecar runs before the NOT_SUBSTANTIVE branch, so the no-retry path deletes any pre-existing *-vote-output-first-pass.txt beside the voter file. A reused or manually populated review tmpdir still holds a first-pass sidecar from an earlier parse-retry; a later run where that voter parses cleanly on first pass deletes the sidecar without performing any retry, silently dropping the earlier preserved narrative. Restrict rm to the parse-retry success branch (or to the NOT_SUBSTANTIVE path only), immediately before cp, so the happy path does not unlink unrelated prior sidecars.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: scripts/test-dispatch-code-voters.sh:426-483,546-568
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Retry-fail tests pre-seed a first-pass sidecar then assert absence; entry rm -f clears the seed so the assertion is coupled to that cleanup not only to fail-path writes. Weaker signal if fail path ever wrote the sidecar in a way masked by lifecycle. Remove pre-seed or restructure assertions so fail-path write is tested independently of entry rm.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/dispatch-code-voters.sh:240-245
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unconditional rm -f of first_pass_sidecar before parse classification A pre-existing *-vote-output-first-pass.txt in REVIEW_TMPDIR can be deleted when the voter ends OK without retry Restrict rm to the NOT_SUBSTANTIVE retry path or document filename ownership and deletion semantics
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/dispatch-code-voters.sh:240-246
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Unconditional rm -f of the first-pass sidecar before parse-rate classification deletes a prior run sidecar even when the current run exits early on substantive OK without a retry. Second dispatch-code-voters invocation (or any reuse of the same REVIEW_TMPDIR paths) after an earlier parse-retry success can remove *-vote-output-first-pass.txt before returning OK, losing first-pass observability with no replacement copy. Restrict rm to the NOT_SUBSTANTIVE path or to immediately before the successful-branch cp (avoid unlink on substantive OK early return).
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/dispatch-code-voters.sh:244-172
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] rm -f runs before early return on non-NOT_SUBSTANTIVE status, deleting any existing sidecar beside voter_path even when no retry runs. Reuse of a tmpdir with a leftover first-pass artifact while parse-rate is OK: artifact is deleted without retry. Move rm -f to the retry-success branch only or gate on harness/production context if deletion is only for test hygiene.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/dispatch-code-voters.sh:244-246
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unconditional rm -f of first-pass sidecar before parse-rate classification OK fast-path deletes any pre-existing sidecar at that path in REVIEW_TMPDIR without a retry Restrict rm to retry-success path or NOT_SUBSTANTIVE branch if foreign sidecars must survive no-retry runs
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/dispatch-code-voters.sh:263-267
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan showed unconditional cp || true plus one breadcrumb; code uses conditional cp emit_breadcrumb to stderr and larch_err on cp failure. No functional mismatch with stated fail-open promotion; minor plan drift. Accept as-is or align comments/plan text with the richer behavior.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: scripts/dispatch-code-voters.sh:263-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Conditional cp + larch_err instead of plan silent cp || true and always-on breadcrumb Monitoring or docs tied to the plan may expect a breadcrumb whenever retry succeeds even if cp fails Align code with plan or update plan/docs for conditional breadcrumb and larch_err on cp failure
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/dispatch-code-voters.sh:263-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Implementation uses conditional cp + larch_err instead of plan's silent cp || true and always-on breadcrumb Operators or docs aligned to the plan may expect a breadcrumb whenever retry succeeds even if cp fails; plan-code drift Align implementation with plan or update plan/docs to describe conditional breadcrumb and larch_err on cp failure
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/test-dispatch-code-voters.sh (retry harness)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No automated coverage for cp failure while mv still promotes A refactor could tie mv to cp success and regress fail-open behavior Add a focused test if an established cp-failure simulation pattern exists
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/test-dispatch-code-voters.sh:424-483 scripts/test-dispatch-code-voters.sh:546-568
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Retry-fail tests seed stale first-pass file then assert absence; coupled to entry rm and no cp on fail Maintainers may read the test as proving cp never runs on failure without noticing seed+rm interaction Add a harness comment or use a fresh tmpdir without seeding for a stricter contract
- **Suggested revision**: Address the concern above.

### FINDING_22: security: scripts/dispatch-code-voters.sh:267
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] larch_err on cp failure prints the full absolute first_pass_sidecar path. A cp failure (disk full, permissions) in CI or shared log aggregation leaks the absolute tmp path (often including the operator username) into stderr. Emit basename-only (or redacted dirname) in the diagnostic, consistent with the emit_breadcrumb line.
- **Suggested revision**: Address the concern above.

### FINDING_23: security: scripts/larch-log.sh:92 and scripts/dispatch-code-voters.sh:263-269
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] New committed artifact type duplicates first-pass voter prose in larch-logs when write-round runs. First-pass narrative may contain more verbose paraphrase of ballot or code context than the promoted structured retry output; more durable copies increase exposure if logs are overshared, though larch_log_redact_file still applies. Document commit-tier sensitivity alongside other voter txt artifacts; ensure consumer guidance treats first-pass files like canonical voter outputs for access control and retention.
- **Suggested revision**: Address the concern above.

