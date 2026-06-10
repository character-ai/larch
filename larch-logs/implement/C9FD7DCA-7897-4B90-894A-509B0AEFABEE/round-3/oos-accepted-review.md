### OOS_6: [OUT_OF_SCOPE] accepted-low-value prints 0.0% for empty accept sets
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `fluff-analysis.py` can display `0.0% (0/0)` when a period has no accepts, which operators may misread as a real zero low-value rate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Skip the line or print n/a when accepted count is zero.


### OOS_7: [OUT_OF_SCOPE] design artifact allowlist docs are stale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-artifact-gate-regression-output.txt
- **Severity**: latent
- **Concern**: Documentation still describes legacy broad per-round design artifacts instead of the current four-file concise allowlist/debug-gated contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update lib-design-round-artifacts.md to match lib-design-round-artifacts.sh.
  - From dyn-artifact-gate-regression-output.txt: Rewrite the allowlist section to match the four-file default contract, debug-gated families, and root `plan.txt` keep-set; align `scripts/design-log-publish.md` (lines 62–72 still claim per-round `findings.md`/`voting-tally.md` are canonical and that `plan.diff` is generated for rounds ≥2).


### OOS_8: [OUT_OF_SCOPE] trailing-content normalization changed across old/new scans
- **Reviewer(s)**: dyn-log-schema-migration-output.txt
- **Severity**: nit
- **Concern**: New `trailing_content()` producer behavior intentionally differs from the removed raw first-line grep scan, so pre/post concise logs are not strictly comparable for that scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-log-schema-migration-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] wrapper_logs still commit full wrapper stdout/stderr
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `wrapper_logs` remain a pre-existing high-volume committed channel that can include launcher stderr/stdout and potential secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Trim or redact wrapper_logs in round-meta; keep only duration/status fields needed for analysis.


### OOS_10: [OUT_OF_SCOPE] root voting-tally.md conflicts with concise design-log contract
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-artifact-gate-regression-output.txt
- **Severity**: latent
- **Concern**: Top-level `voting-tally.md` is still committed even though per-round tally prose is excluded, creating a bloat/contract inconsistency for concise design logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Move exon scan to findings-classification.tsv or stage a minimal tally derivative without full prose.
  - From dyn-artifact-gate-regression-output.txt: Either drop the carve-out and rely on `findings-classification.tsv` + `round-summary.env` for post-analysis, or document and test root `voting-tally.md` as an explicit fifth consumer-core artifact (and add it to the byte-budget guard).


