### OOS_1: [OUT_OF_SCOPE] `amend_add` omits index-lock retry from bundled git lock work
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `amend_add` omits index-lock retry from bundled git lock work; amend after lock contention may still fail unlike add/commit.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] Stale-lock failure detection uses brittle stderr substring match
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Stale-lock failure detection is a brittle substring match; diagnostic text change breaks stale-index-lock classification.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_3: [OUT_OF_SCOPE] `verify-completeness` vs `audit-runs` disagree on `pr_number: 0` / `"0"` as evidence
- **Reviewer(s)**: dyn-audit-tolerance-output.txt
- **Severity**: latent
- **Concern**: `verify-completeness` treats `pr_number: 0` / `"0"` as evidence (`bool(manifest_pr_number)`), while `audit-runs` rejects `"0"` in `_manifest_pr_evidence_matches`; the tools can disagree on that edge case.
- **Suggested revisions (informational for voters; coder decides)**:
