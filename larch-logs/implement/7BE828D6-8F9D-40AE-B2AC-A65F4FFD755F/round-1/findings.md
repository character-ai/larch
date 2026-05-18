### FINDING_1: [OUT_OF_SCOPE] architecture: scripts/test-compose-review-findings.sh (commit 75c59ffb)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Compose harness fixture change ships in the version-bump commit, not in the stall-key plan file list. Reviewers tracing only the ship-pr plan see an extra behavioral change in another script on the same branch. Treat as orthogonal to the stall-key plan; split or document if a single-concern PR is required.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.md:21
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Merge-success paragraph wording can read as if merge-success itself follows a ci-merge failure. Pre-existing clarity issue in the State section; not caused by the new skip-path paragraph. Optional rewrite for reader clarity in a docs-only pass.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/compose-review-findings.sh:53-74,scripts/compose-review-findings.md,scripts/test-compose-review-findings.sh:24-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated compose HTML-escape feature bundled in same branch diff as ship-pr stall-key fix Reviewers must validate two unrelated behaviors in one merge; reverting stall-key fix risks dropping compose behavior (or vice versa), contrary to narrow plan scope Split compose changes into a separate PR or update the feature spec to explicitly include both workstreams
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/ship-pr.md:23
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New contract text says skip-paths are reached only after resume from a prior stall. Operators or tests may hit skip-merge or REPO_UNAVAILABLE without any prior stall; the absolute only misstates when those branches run even though clearing remains correct. Rephrase to describe possible stale keys without claiming exclusivity (e.g. especially after resume).
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.md:23
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims skip-paths are reached only after a prior stall/resume Skip-merge guard can run without any prior stall (e.g. MERGE=false on first ci-merge), so maintainers may misread when clearing is strictly needed Rephrase to state stall keys may persist after a prior ci-merge stall without claiming exclusivity
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/compose-review-findings.sh:57-78
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] escape_finding_body may double-encode existing HTML entities in finding bodies Artifact text that already contains entities can render as corrupted sequences in composed markdown Constrain inputs, use a non-double-encoding escape, or document unsupported pre-escaped content
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/ship-pr.md:23
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New doc claims skip-paths are reached only after a prior-stall resume. Operators may misread when REPO_UNAVAILABLE or skip-merge can run; skip-merge can trigger on first ci-merge without any stall. Soften or split the sentence to describe the stale-key hazard without claiming those paths only run after a stall.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.md:23
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc claims skip-paths are reached only after a prior stall Operators may misread when stall-key clearing applies; first-run MERGE=false or REPO_UNAVAILABLE without a prior stall still hits these paths Rephrase to emphasize stale-state risk without implying exclusivity to resume-after-stall
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/ship-pr.md:State section
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New contract text claims skip-paths are reached only on resume after a prior stall Skip-merge can run on first ci-merge without any stall; REPO_UNAVAILABLE branch is not exclusively a post-stall resume scenario, so readers may misunderstand when clearing applies Soften or replace only to describe that these paths skip merge-success clears so explicit clear_stall_keys_for_postmerge is required; cite resume-after-stall as one important scenario not the sole case
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-compose-review-findings.sh:27-91
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Large compose-review test/fixture changes ride on the same branch as the ship-pr stall-key fix. Reviewers must validate unrelated composer behavior; merges/reverts and bisects conflate two concerns. Split into a separate PR or document mandatory coupling in the PR narrative.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-compose-review-findings.sh:43-90
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Unrelated compose-review harness changes (HTML-escape fixtures/assertions) ride in the same branch diff as the ship-pr stall-key fix. A failure or flake in test-compose-review-findings blocks or obscures bisect/merge attribution for a PR scoped to ship-pr skip-path behavior. Ship compose harness changes in a separate commit/PR or document intentional bundling in the PR description.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-ship-pr.sh:1332-1345 / scripts/ship-pr.sh:1316-1323
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression Case A only covers REPO_UNAVAILABLE=true, not the empty PR_NUMBER disjunct of the same guard. Low: both disjuncts share one code path; a future refactor could split them and drop coverage for the empty-PR case. Add a minimal test that clears PR_NUMBER while keeping REPO_UNAVAILABLE=false if you want explicit coverage of both skip reasons.
- **Suggested revision**: Address the concern above.

