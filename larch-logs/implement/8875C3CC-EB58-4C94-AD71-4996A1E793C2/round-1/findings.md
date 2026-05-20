### FINDING_1: [OUT_OF_SCOPE] architecture: larch-logs/implement/**
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Large committed implement run logs appear in the diff. Per repo policy these are expected artifacts, not omissions from the coder-dispatch plan. No action required for plan fidelity of the stated feature.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/review-and-fix.sh:236-266
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] run_coder_dispatch ignores CODEX_AVAILABLE/CURSOR_AVAILABLE and always tries Codex after Cursor path. Environments with only one external tool still hit the second tool attempt; pre-existing design not introduced by this diff. None for this PR; track separately if session gating should align with lint-fix-loop.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] correctness: scripts/dispatch-code-voters.sh:330-333
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] .diag head -c lacks || true unlike new voter-output head. Rare read error could truncate diag file before later sections. Match defensive || true or set +e around all head -c reads in the group (follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] risk-integration: scripts/dispatch-code-voters.sh:349-360
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] append-tool-failure stderr/stdout discarded with || true hides append/redaction failures. Harder to notice when execution-issues.md was not updated despite a voter failure path. Log append failures or surface non-zero exits in CI (follow-up).
- **Suggested revision**: Address the concern above.

### FINDING_5: architecture: scripts/test-dispatch-code-voters.sh:120-210
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Branch diff modifies voter dispatch test harness and stubs outside the supplied four-file implementation plan. Reviewers or automation treating the plan as exhaustive will miss unrelated behavioral and assertion changes bundled on the same branch. Amend the plan to include this file or split unrelated work into its own PR/branch.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: CHANGELOG.md:50-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Release notes for 29.8.43 omit the dispatch-order behavior change. Consumers relying on CHANGELOG for operational semantics may miss the new Cursor-first fallback story. Document Cursor-first external coder dispatch with Codex fallback in the Changed section.
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/dispatch-code-voters.sh:319-328;scripts/dispatch-code-voters.md:51;scripts/test-dispatch-code-voters.sh:120-207
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Voter1 diagnostic + harness + doc shipped alongside the four-file cursor-first coder dispatch plan Reviewers must validate unrelated execution-issues behavior and test harness changes in the same PR; reverts/bisect conflate two features Split unrelated voter work into its own PR or document it explicitly in requirements/changelog so scope matches the change
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: CHANGELOG.md:16-20
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Changelog section for 29.8.43 documents #2440 only; the later cursor-first coder dispatch change has no changelog entry. Operators reading CHANGELOG for 29.8.43 see no mention of Cursor-first review-fix/lint-fix dispatch despite it being on the branch. Add an Unreleased or next-version bullet describing Prefer Cursor over Codex for review-fix and lint-fix dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: CHANGELOG.md:16-20
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] 29.8.43 notes only #2440 despite additional shipped behavior on the branch. Release archaeology misses the Cursor-first dispatch change tied to its issue/PR. Add Closed lines (or bullets) for each distinct user-visible change in that version.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-lint-fix-loop.sh:56-59
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] The plan claims this harness verifies dispatch ordering but sessions force CURSOR_PRESENT=false so cursor-first ordering is never exercised. A regression that restores codex-first while leaving CURSOR_PRESENT=false tests green would slip past this harness. Add a both-tools-present case with stubs or soften the plan verification wording.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/review-and-fix/scripts/review-and-fix.sh:265
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Breadcrumb text implies both tools were dispatched when Cursor may have been skipped before spawn. Auth/setup failure for Cursor yields only a Codex attempt but logs read as dual-tool failure. Use neutral wording or separate breadcrumbs for skipped vs attempted Cursor.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: CHANGELOG.md:16-20
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] [29.8.43] release notes omit Cursor-first review-fix/lint-fix dispatch shipped at the same plugin version. Operators read CHANGELOG for 29.8.43 and see only #2440 while the plugin at HEAD prefers Cursor then Codex for those paths, so dispatch-order expectations can be wrong. Add a Changed bullet describing Cursor-then-Codex dispatch for review-and-fix and lint-fix-loop (or adjust version sectioning if 29.8.43 is not yet published).
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/dispatch-code-voters.md:41-51
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Glossary says failed means missing/empty while new prose documents non-empty failed voter output. Operators misinterpret VOTER_1_STATUS=failed when a non-empty file exists and bytes were logged. Qualify failed semantics per slot or align glossary with dispatch-code-voters.sh rules.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/dispatch-code-voters.sh:325-328
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Unescaped model bytes embedded into Markdown-oriented diagnostics. Voter output includes ``` lines or control bytes; execution-issues.md consumers mis-parse sections or render unsafe HTML-like content. Base64-encode or escape fence-breaking sequences in the captured slice.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/lint-fix-loop.sh:258-263
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Cursor-first dispatch and Codex fallback are untested in lint-fix-loop harness. scripts/test-lint-fix-loop.sh forces CURSOR_PRESENT=false so CI never runs the new primary branch or fallback ordering. Add a harness case with CURSOR_PRESENT=true, stubbed Cursor failure, Codex success, and assertions on CODER_TOOL and dispatch order.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/test-dispatch-code-voters.sh:2243-2297
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unrelated voter failure-diagnostics test changes ship in the same change-set as coder dispatch reorder. Larger diff and mixed blame make regressions harder to bisect and reviews conflate two concerns. Split voter harness changes into a separate commit/PR from review-and-fix/lint-fix dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: scripts/dispatch-code-voters.sh:325-328
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Raw first 200 bytes of voter stdout are written into voter1-diag before redacted append; redaction may miss novel secrets. Failed Claude voter emits prose containing a token or PII; operators or CI publish execution-issues.md or retain REVIEW_TMPDIR artifacts, leaking content past pattern redaction or via the raw sidecar file. Redact or printable-sanitize before writing the voter-output section to voter1-diag; or use opt-in / hashed preview only.
- **Suggested revision**: Address the concern above.

