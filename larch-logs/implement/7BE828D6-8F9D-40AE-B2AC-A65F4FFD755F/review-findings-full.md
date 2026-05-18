### FINDING_4: panel [code-review/accepted]

## code-quality: scripts/ship-pr.md:23

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New contract text says skip-paths are reached only after resume from a prior stall. Operators or tests may hit skip-merge or REPO_UNAVAILABLE without any prior stall; the absolute only misstates when those branches run even though clearing remains correct. Rephrase to describe possible stale keys without claiming exclusivity (e.g. especially after resume).
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: scripts/ship-pr.md:23

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc claims skip-paths are reached only after a prior stall/resume Skip-merge guard can run without any prior stall (e.g. MERGE=false on first ci-merge), so maintainers may misread when clearing is strictly needed Rephrase to state stall keys may persist after a prior ci-merge stall without claiming exclusivity
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## correctness: scripts/compose-review-findings.sh:57-78

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] escape_finding_body may double-encode existing HTML entities in finding bodies Artifact text that already contains entities can render as corrupted sequences in composed markdown Constrain inputs, use a non-double-encoding escape, or document unsupported pre-escaped content
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## correctness: scripts/ship-pr.md:23

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New doc claims skip-paths are reached only after a prior-stall resume. Operators may misread when REPO_UNAVAILABLE or skip-merge can run; skip-merge can trigger on first ci-merge without any stall. Soften or split the sentence to describe the stale-key hazard without claiming those paths only run after a stall.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## correctness: scripts/ship-pr.md:23

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc claims skip-paths are reached only after a prior stall Operators may misread when stall-key clearing applies; first-run MERGE=false or REPO_UNAVAILABLE without a prior stall still hits these paths Rephrase to emphasize stale-state risk without implying exclusivity to resume-after-stall
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: scripts/ship-pr.md:State section

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New contract text claims skip-paths are reached only on resume after a prior stall Skip-merge can run on first ci-merge without any stall; REPO_UNAVAILABLE branch is not exclusively a post-stall resume scenario, so readers may misunderstand when clearing applies Soften or replace only to describe that these paths skip merge-success clears so explicit clear_stall_keys_for_postmerge is required; cite resume-after-stall as one important scenario not the sole case
- **Suggested revision**: Address the concern above.

