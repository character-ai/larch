### OOS_1: [OUT_OF_SCOPE] Gitleaks allowlist for python/test_redact.py and cache paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Gitleaks does not scan synthetic secret fixtures in `python/test_redact.py` and excludes python cache paths; accidental live secrets in allowlisted paths may skip layers 1–2. Documented tradeoff—rely on synthetic fixtures, discipline, and TruffleHog for live creds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] create-pr.sh wraps gh pr create in with_transient_retry by design
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: Bash/Python divergence on create retry is plan-intentional (duplicate-create avoidance).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] absent first_tier in tiers is intentional Python footgun
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: latent
- **Concern**: When `first_tier` ∉ `tiers`, rotation is skipped and `tier_list[0]` is the policy tier; bash never hits this because it derives `first_tier` from the same array it iterates—document or require membership for Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] waterfall wrapper_rc == 0 requirement for short-circuit is intentional
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Matches bash and `test_waterfall_continues_on_wrapper_rc_2`; asymmetry vs `other` with nonzero `wrapper_rc` is intentional.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_13: [OUT_OF_SCOPE] waterfall success return on launcher_exit == 0 aligned with bash
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Success returns immediately with `winning_tier` set—aligned with bash `2069-2072`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_14: [OUT_OF_SCOPE] no unit test for bash run_ship_pr_2632_t4d three-tier cascade
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Manual trace suggests correct behavior for cursor health → codex other → claude still runs; colocated test would lock parity but implementation appears correct.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] redact unit tests omit some GitHub token prefix families
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tests omit vectors for some token prefix families (e.g. `gho_`/`github_pat_`), so regex drift in `redact.py` is less likely to be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] retry/agents ordering matches bash lib-net and launcher common
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: `retry.py` and `agents.py` match bash ordering guards, substring families, health/other/none mapping, and `parse_launcher_failure_class` whitelist parity with `scripts/ship-pr.sh:1696-1706` (positive parity note, not a defect).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] redact() tmpdir-before-secrets chain matches canonical bash
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: Python `redact()` order matches canonical bash chain (`redact-tmpdir-paths.sh | redact-secrets.sh`); some legacy bash call sites still pipe secrets before tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] redact parity coverage thinner than bash harness
- **Reviewer(s)**: dyn-bash-parity-output.txt
- **Severity**: nit
- **Concern**: `python/test_redact.py` omits several single-line vectors from `scripts/test-redact-tmpdir-paths.sh`; multiline `$`-anchor gap (FINDING_15) is the material hole.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] mutating gh helpers intentionally omit read retry wrappers
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: `pr_merge`, `run_rerun`, `issue_comment`, `issue_edit` call `_gh` directly—matches planned asymmetric retry policy.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] _body_file_args lifecycle and redaction before write
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: Temp body files are written and unlinked safely; `redact()` runs before creation; `pr_create` parses stdout after context exit—no post-delete body read (positive note).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] _redact_gh_scalar newline handling for scalar flags
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: `_redact_gh_scalar` correctly strips `redact()` trailing newline for scalar gh flags while preserving intentional input newlines (positive note).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] pr_create single create + one conflict list pass by design
- **Reviewer(s)**: dyn-gh-retry-policy-output.txt
- **Severity**: nit
- **Concern**: No internal create/list loop—intentional policy, not a defect in this branch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

