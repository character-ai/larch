### FINDING_10: risk-integration: skills/implement/scripts/test-stall-recovery-report.sh:368-384
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan acceptance #10 manual Step 18a dry-run integration is not automated; only helper subcommands are tested under dry-run. A future SKILL.md or reference edit could break the consumer print path or re-enable gh/issue filing under LARCH_STALL_RECOVERY_DRY_RUN=1 without CI signal until someone runs the manual checklist. Add a fixture-based integration harness or extend test-implement-structure.sh to exercise the Step 18a sequence and assert no gh calls plus expected chat output.
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/implement/scripts/test-stall-recovery-report.sh:90-93
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Plan case 2 cites jest markers but harness only covers pytest evidence. A jest-only failure log could be misclassified as unrecoverable while pytest-shaped logs still pass CI. Add a classify fixture asserting test-failure for jest output.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/scripts/stall-recovery-report.sh:253-268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Retry caps are hardcoded in shell while stall-recovery-report.md claims to be the single normative source; lint does not compare them. Documentation could be updated to new caps without changing retry-policy behavior, misleading operators during stall triage. Extend lint or harness case 7 to parse the markdown cap table and compare against retry-policy output.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-implement-structure.sh:52-67
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Structural tests cover stall-recovery.md but not SKILL.md Step 18a/18b split or no-stall fast path. SKILL.md could collapse 18a/18b or drop the fast-path breadcrumb while reference tests still pass. Add greps pinning Step 18a, Step 18b, and the no-stall detected line in SKILL.md.
- **Suggested revision**: Address the concern above.


### FINDING_17: security: skills/implement/scripts/stall-recovery-report.sh:242-250,377
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] safe_bail_reason_value allows PAT-shaped strings in classify BAIL_REASON KV outside the four public surfaces PAT in BAIL_REASON/IMPLEMENT_BAIL_REASON is emitted to stall-recovery-classification.env and may leak via orchestrator logs or execution-issues even when bug-body stays clean Restrict emitted bail to a closed known-token enum; otherwise always redact; do not treat generic lowercase token regex as safe
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: skills/implement/SKILL.md:1748-1750
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 18a skip uses only memory+disk but entry requires any-of-three layers including session-env. When session-env has STALL_TRACKING=true but memory and ship-pr-state are false, orchestrator prints no-stall skip and bypasses recovery while reference and line 1750 require the full gate. Change skip condition to require all three layers false/empty; align prose with references/stall-recovery.md step 1.
- **Suggested revision**: Address the concern above.


### FINDING_2: code-quality: skills/implement/scripts/stall-recovery-report.sh:253-262; skills/implement/scripts/stall-recovery-report.md:87-95; skills/implement/scripts/test-stall-recovery-report.sh:151-159
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Retry caps maintained in shell functions markdown table and harness heredoc without mechanical doc-code link lint subcommand will not catch doc cap edits that diverge from retry-policy output causing silent over or under retry Extend lint or harness to compare retry-policy output against markdown table or single caps source
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/implement/references/stall-recovery.md:15-22
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Same-cause alternate restart is gated by retry-policy MAX_ATTEMPTS=1 against global attempt_count after the repeat-triggering attempt is already recorded. After one failed recovery dispatch, re-classify yields same-cause-repeat with attempt_count=1; 1>=1 skips Step 6 alternate strategy and goes straight to terminal failure despite the plan allowing one alternate restart. Track alternate-strategy attempts separately (e.g. outcome=alternate only) or apply same-cause cap only to redispatch, not the alternate path; add an integration harness for classify→record→re-classify→cap-check.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/implement/scripts/stall-recovery-report.sh:192-210
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] resume_hint_for fail-closes unlisted STALL_STEP tokens to none. A new mark_stall step label not in the 2/5/8-15 list gets RESUME_HINT=none even when FAILURE_CLASS is recoverable, blocking ship-pr redispatch. Document and test-sync allowed STALL_STEP values with ship-pr mark_stall call sites.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: skills/implement/scripts/stall-recovery-report.sh:351-355
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] classify forces FAILURE_CLASS=unrecoverable when STALL_TRACKING is false on all layers. A hypothetical caller invoking classify without a true stall layer gets unrecoverable instead of a no-stall signal, misrouting recovery. Document precondition or emit explicit not-stalled KVs when stall_tracking is false.
- **Suggested revision**: Address the concern above.


