### FINDING_1: **Important** `correctness` `scripts/rebase-push.sh:258-275` — The new force-push retry refreshes the branch ref after a `--force-with-lease` failure, then retries with the default lease. Concrete failing scenario: remote `origin/feature` advances from `A` to another runner’s `B`; this script’s first push fails the lease, line 263 refreshes the tracking ref to `B`, and the retry can now lease against `B` and overwrite it with this local `HEAD`. Preserve the original expected remote OID for all retries, e.g. use `--force-with-lease=refs/heads/$CURRENT_BRANCH:$expected_oid`, and only treat refreshed remote equality with local `HEAD` as success; otherwise fail or rebase rather than retrying against the refreshed lease.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/rebase-push.sh:258-275` — The new force-push retry refreshes the branch ref after a `--force-with-lease` failure, then retries with the default lease. Concrete failing scenario: remote `origin/feature` advances from `A` to another runner’s `B`; this script’s first push fails the lease, line 263 refreshes the tracking ref to `B`, and the retry can now lease against `B` and overwrite it with this local `HEAD`. Preserve the original expected remote OID for all retries, e.g. use `--force-with-lease=refs/heads/$CURRENT_BRANCH:$expected_oid`, and only treat refreshed remote equality with local `HEAD` as success; otherwise fail or rebase rather than retrying against the refreshed lease.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `risk-integration` `scripts/ship-pr.md:66-77` — The new docs say `REBASE_COUNT >= 5`, but line 72 still says an existing `REBASE_COUNT >= 20` guard bounds the retry budget, and line 77 still says `run_evaluate_failure` runs one vendor fix attempt. Update these stale statements to match the new 5-attempt behavior.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `risk-integration` `scripts/ship-pr.md:66-77` — The new docs say `REBASE_COUNT >= 5`, but line 72 still says an existing `REBASE_COUNT >= 20` guard bounds the retry budget, and line 77 still says `run_evaluate_failure` runs one vendor fix attempt. Update these stale statements to match the new 5-attempt behavior.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] **Latent** `correctness` `scripts/git-force-push.sh:65-90` — The pre-existing force-push helper has the same lease-refresh retry shape: after a failed force-with-lease it fetches the branch, then retries with the refreshed default lease. This predates the current PR, but the same concrete overwrite path applies if another writer advanced the remote branch between the local lease snapshot and the retry. Use an explicit expected remote OID across retries or fail when refreshed remote differs from local `HEAD`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Latent** `correctness` `scripts/git-force-push.sh:65-90` — The pre-existing force-push helper has the same lease-refresh retry shape: after a failed force-with-lease it fetches the branch, then retries with the refreshed default lease. This predates the current PR, but the same concrete overwrite path applies if another writer advanced the remote branch between the local lease snapshot and the retry. Use an explicit expected remote OID across retries or fail when refreshed remote differs from local `HEAD`.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: scripts/ship-pr.sh (misc exit_stall sites)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Many historical bare numeric stall codes predate this change. Not introduced here; full stall vocabulary cleanup would be a separate project. Defer unless standardizing all exit_stall tokens is explicitly in scope.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:188-199
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Missing or corrupted REBASE_COUNT in a hand-edited state file can make shell numeric tests error. Not introduced solely by this diff; same empty-key hazard exists for other arithmetic on read_state. Keep state file integrity guarantees; treat as operational hygiene.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Operator-facing SKILL examples for STALL_STEP do not list the new hyphenated stall tokens. Confusion when comparing live STALL_STEP values to SKILL prose; file not part of this feature diff. Follow-up documentation outside this PR if desired.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: scripts/compose-review-findings.sh:57-72 scripts/compose-review-findings.md scripts/test-compose-review-findings.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] HTML-escape pipeline for composed findings is bundled with ship-pr resilience work. Revert/cherry-pick/bisect conflates two unrelated behavioral changes; review surface and blast radius grow without a single coherent feature story. Split compose escaping into its own PR or commit series.
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: .claude/skills/bump-version/scripts/apply-bump.md:54-55
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] First invariant still says worktree must be clean before the next bullet tolerates internal untracked files. Quick read suggests a contradiction with the new tolerance rule. Reword the first invariant to forbid only non-internal dirty states (single coherent bullet).
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/compose-review-findings.sh; scripts/compose-review-findings.md; scripts/test-compose-review-findings.sh; agent-lint.toml; docs/linting.md; Makefile
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated compose-review-findings HTML-escape + lint/doc/Makefile wiring ships in the same branch as ship-pr/apply-bump resilience. Reviewers must reason about two independent behaviors in one PR; bisect/revert and release notes blur. Split PR or separate commits: resilience vs finding-body escaping.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/git-push.sh:2757-2776; scripts/rebase-push.sh:246-276; scripts/ship-pr.sh:1149-1177
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Jitter/backoff formula duplicated across three scripts with integer truncation. Future edits can drift one copy and diverge backoff semantics. Extract a one-function helper or centralize the comment+formula once.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:96-107
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Internal-artifact filter is line-regex plus awk $2 WARN list. Unusual git status quoting or paths with spaces can bypass tolerance or mis-report WARN targets. Use NUL-safe status parsing or a path-based allowlist without awk field splitting.
- **Suggested revision**: Address the concern above.

### FINDING_12: correctness: .claude/skills/bump-version/scripts/apply-bump.sh:96-107
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Porcelain line filtering and awk column 2 for WARN may mishandle quoted or multi-token paths from git status. Internal artifacts with unusual path metadata might still fail the bump (safe) or emit an incomplete WARN path (cosmetic). Optional: parse porcelain with -z or match paths after the status prefix without assuming a single-token path.
- **Suggested revision**: Address the concern above.

### FINDING_13: correctness: scripts/rebase-push.sh:263-267
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Lease-recovery fetch compares HEAD to BASE_REMOTE/CURRENT_BRANCH while push may target a different remote. Rare multi-remote setups: optimistic already-landed exit may be keyed off the wrong ref; at minimum wasted retries. Refresh the push remote ref or gate the exit-0 shortcut on the ref lease uses.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: implementation_plan §Testing vs scripts/test-git-push.sh (+ Makefile)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Explicit plan line says no git-push retry harness; diff adds test-git-push.sh/md and Makefile targets. Plan fidelity and review scope assume no new harness; CI/Makefile/agent-lint surface grows beyond enumerated files. Remove harness to match plan or revise plan to require and list test-git-push artifacts.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/ship-pr.sh:1110-1160
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] run_evaluate_failure mixes legacy exit_stall token 12c with new 12-max-retries and 12-detached-head strings. Automation or runbooks that parse STALL_STEP now need special cases for the same ci-merge evaluate_failure phase depending on which branch was taken. Unify naming (e.g. rename the empty FAILED_RUN_ID stall to 12-missing-run-id) or document 12c as the sole legacy exception in ship-pr.md and any consumer docs.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: scripts/ship-pr.sh:1142-1187
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] New STALL_STEP strings (10-max-retries, 12-max-retries, 10-detached-head, 12-detached-head) replace coarser tokens on some exhaustion paths. External automation that matched old STALL_STEP values may mis-handle stalls after upgrade. Document token churn in ship-pr contract / release notes for operators.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: scripts/ship-pr.sh:1143-1187,scripts/ship-pr.sh:1155-1161
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] STALL_STEP values for vendor/rebase exhaustion and detached HEAD changed from numeric-style 10 / 12c to hyphenated strings (10-max-retries, 12-max-retries, 10-detached-head, 12-detached-head). Downstream automation or docs that key off exact STALL_STEP=10 or STALL_STEP=12c for evaluate-failure exhaustion will no longer match; stalls may be mis-routed or ignored in custom tooling. Update every consumer of STALL_STEP to accept the new tokens, or add a parallel machine-readable reason field while keeping legacy stall codes stable.
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/compose-review-findings.sh:57-72
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Escape pipeline only replaces & < > after redaction. If output is ever embedded in HTML/XML or shell-interpreted contexts without a second encoding layer, other characters could still be unsafe for that consumer. Document the threat model as markdown-on-disk only, or adopt full contextual encoding if a second consumer is introduced.
- **Suggested revision**: Address the concern above.

