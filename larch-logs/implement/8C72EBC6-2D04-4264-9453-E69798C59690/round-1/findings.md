### FINDING_1: code-quality: scripts/clarify-comment-post.sh:41-58 (duplicated across clarify-*, plan-block-*, tracking-issue-read.sh, tracking-issue-write.sh)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Seven near-identical copies of redact_gh_error including the new truncation case guard. Future edits to marker text, messages, or control flow will likely diverge across helpers and reintroduce inconsistent fail-closed behavior. Source a single shared redact_gh_error (or thin wrappers) from one scripts/lib-*.sh file.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: scripts/tracking-issue-write.sh:216-254; scripts/tracking-issue-write.md:35-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Gh stderr redaction pipeline failure now exits 2 via emit_gh_failure instead of exit 3 via emit_redaction_failure. Automation or operators distinguishing gh/API failures (exit 2) from redaction helper failures (exit 3) mis-classifies redactor outages on gh error paths. Document the new split in tracking-issue-write.md or preserve exit 3 for pipeline failure on the gh stderr path while keeping ERROR= generic.
- **Suggested revision**: Address the concern above.

### FINDING_3: risk-integration: CHANGELOG.md (branch vs main)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Branch stacks unrelated apply-bump and audit-runs work with the redaction change per git log merge-base..HEAD. Single merge bundles unrelated behavioral and test surface; harder review, bisect, and revert than the narrow implementation_plan implies. Split into separate PRs or narrow the branch to the redaction work before merge.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/tracking-issue-write.sh:223-227 (and sibling redact_gh_error copies)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Truncation fail-closed path keys only on substring [content truncated. If redact-secrets.sh changes the sentinel wording without that prefix, partially redacted bytes could still be emitted into ERROR= up to 500 bytes. Couple detection to redact-secrets.sh via a single shared constant or explicit exit/marker contract.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/clarify-comment-post.sh:44-54 vs scripts/tracking-issue-write.sh:220-225
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent generic ERROR strings and conflation of truncation with missing helper in sibling scripts. Harder cross-script log correlation for operators triaging failures. Unify strings in a shared helper or shared constants.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/tracking-issue-read.md:48-52
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Contract omits explicit fail-closed description for redact_gh_error while SECURITY.md documents it. Readers of the read helper contract may assume older fail-open semantics for read-side ERROR= emissions. Add a one-line fail-closed note beside the existing ERROR= flatten/cap description.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/tracking-issue-read.sh:115-120
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Scrubber stderr is discarded via 2>/dev/null in redact_gh_error. WARN lines from redact-secrets.sh remain invisible on read paths; pre-existing pattern not newly worsened by this diff. Track as a separate observability change if WARN visibility is desired.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/tracking-issue-write.sh:216-254
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Gh stderr redaction failure no longer exits 3 via emit_redaction_failure; emit_gh_failure always exits 2. Wrapper or runbook that keys only on exit 3 to detect redaction-helper breakage will mis-classify a rename path where gh fails and redact_gh_error falls back to generic ERROR=. Document exit 2 vs 3 split or restore exit 3 on redact_gh_error generic branch.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/tracking-issue-write.md:35-42 scripts/tracking-issue-write.sh:49-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Exit-code docs/header still imply all redaction helper failures are code 3 with redaction: ERROR=. Readers assume stderr redaction outage maps to exit 3; actual exit is 2. Add carve-out lines aligning docs with behavior.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/clarify-*.sh scripts/plan-block-*.sh scripts/tracking-issue-write.sh
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Inconsistent generic ERROR= strings across redact_gh_error copies. Low impact: harder to grep uniformly across tools. Optional string normalization or short doc note.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: Branch vs merge-base
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Additional commits (#2514 apply-bump #2516 audit) and large larch-logs diff bundled with redact hardening. PR scope and review surface larger than the redaction plan; unrelated regressions need separate review. Split PRs or review non-redact files independently.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: SECURITY.md gitleaks allowlist sentence
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Allowlist references test-tracking-issue-write.md alongside .sh harness. Pre-existing doc/path typo; not introduced for redaction. Fix filename in a docs-only follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-tracking-issue-write.sh:108-167 scripts/tracking-issue-write.sh:216-229
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Truncation-marker fail-closed path for gh stderr is documented but not exercised by the harness. A future change removes or narrows the case arm matching [content truncated while redact() still returns 0; CI stays green and raw or partially redacted gh/jq material could return to ERROR=. Add a stub redact-secrets.sh that prints the real truncation marker plus a fake token and assert generic ERROR= and no token leakage.
- **Suggested revision**: Address the concern above.

### FINDING_14: security: scripts/tracking-issue-write.sh:223-228 (duplicated in scripts/tracking-issue-read.sh:128-132, scripts/clarify-comment-post.sh, scripts/clarify-label.sh, scripts/clarify-state.sh, scripts/plan-block-read.sh, scripts/plan-block-write.sh)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Truncation fail-closed path keys off a loose prefix match on [content truncated in redacted stdout. If redact-secrets.sh changes the marker while still exiting 0, partial sensitive material could pass the case statement; conversely a legitimate gh error containing that substring would be replaced with the generic string. Define a stable machine contract from redact-secrets.sh (or a shared sourced helper) instead of ad hoc substring checks duplicated across scripts.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security: scripts/tracking-issue-read.sh:115-133; scripts/clarify-comment-post.sh; scripts/clarify-label.sh; scripts/clarify-state.sh; scripts/plan-block-read.sh; scripts/plan-block-write.sh
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Gh stderr redaction for read/clarify/plan helpers still omits redact-tmpdir-paths.sh unlike tracking-issue-write.sh. Session tmpdir paths may still appear in ERROR= lines after secret scrubbing. Not requested in this change set; consider aligning pipelines in a follow-up if path leakage in public ERROR= is unacceptable.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/tracking-issue-write.md:41-42
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Exit-code table still implies redaction helper failures always exit 3, but gh stderr fail-closed redaction now exits 2 via emit_gh_failure. Operators or automation using exit 3 as the sole signal that the redaction subsystem failed will miss stderr-side redact_gh_error failures, which now look identical to ordinary gh failures. Document that stderr-side redact_gh_error failures intentionally use the exit 2 gh failure envelope with a generic ERROR=, distinct from exit 3 body/title redaction.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/clarify-state.sh:41-58 scripts/clarify-label.sh:41-58 scripts/clarify-comment-post.sh:41-58 scripts/plan-block-read.sh:41-58 scripts/plan-block-write.sh:41-58 scripts/tracking-issue-write.sh:216-229
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Identical redact_gh_error logic is duplicated across six scripts. A future one-off edit could update only some copies, reintroducing inconsistent fail-closed behavior across GitHub-touching helpers. Centralize redact_gh_error in one sourced fragment or helper script with a single regression surface.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/test-tracking-issue-write.sh:7088-7147
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness lacks a truncation-marker success-path case for redact_gh_error. A regression could break the truncation substring guard or reorder truncation vs flattening without failing CI. Add a stub redactor or stdin fixture that emits the documented truncation marker with exit 0 and assert generic ERROR= and no secret leakage.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: scripts/clarify-state.sh:44-54 vs scripts/tracking-issue-write.sh:220-225
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Inconsistent generic ERROR= token shapes across scripts (gh stderr redaction failed/unavailable vs gh failure: redaction unavailable). Log parsers or humans comparing failures across tools may infer different root causes for the same underlying condition. Normalize fallback strings or document per-script ERROR= vocabulary explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/clarify-state.sh:52-53 (duplicated siblings)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Truncation detection uses a loose substring on [content truncated. A pathological upstream error string containing that fragment could be over-sanitized into the generic ERROR= despite successful redaction. Anchor the match to the full documented marker text from redact-secrets.sh or another stable internal sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] risk-integration: scripts/tracking-issue-read.sh:123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] redact_gh_error still redirects scrubber stderr to /dev/null, hiding PEM truncation WARN lines. This behavior predates the new fail-closed stdout handling and was not introduced by the diff hunk, but it remains a mild observability gap versus the write-side guidance. Remove 2>/dev/null or tee warnings without re-leaking raw gh bytes into captured variables.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration: (branch vs main)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Large unrelated diffs (apply-bump harness, audit log completeness, larch-logs) ride alongside the redaction change. Review noise and bisect complexity increase; any issues there are unrelated to redact_gh_error unless they share code paths. Split unrelated work into separate branches/PRs when feasible.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] risk-integration: merge-base..HEAD
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Multi-commit branch diff bundles #2518 and #2520 work alongside the redact_gh_error plan; the stated plan’s file list does not describe those deltas. Plan-fidelity traceability against only the redact plan is ambiguous when the precomputed diff includes unrelated surfaces. Scope the diff to the redact commit or update the plan to list every touched artifact for one-to-one traceability.
- **Suggested revision**: Address the concern above.

