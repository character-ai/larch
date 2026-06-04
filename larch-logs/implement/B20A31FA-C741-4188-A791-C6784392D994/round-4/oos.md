### OOS_1: [OUT_OF_SCOPE] Implement login symlink harness gap was marked not an introduced regression
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Source marked this as a harness gap rather than an introduced product regression: implement tests do not assert login fallback creates an `auth.json` symlink, so the behavior is less pinned than review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] CI launcher temp lifecycle appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found the CI launcher installs the trap before auth prep and still runs cleanup on auth-prep failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] Temp cleanup harness gap without demonstrated runtime leak
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: latent
- **Concern**: Source marked this as an acceptance/harness gap, not a demonstrated leak: tests do not assert leftover probe or review-and-fix temp homes after all relevant scenarios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_12: [OUT_OF_SCOPE] Probe trust argv harness gap
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: latent
- **Concern**: Source marked the missing probe `trust_level="trusted"` argv assertion as out-of-scope; implementation appears correct but CI would not catch that regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_13: [OUT_OF_SCOPE] Legacy pre-branch probe stamps are harmless
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: Old unsplit probe stamp files are no longer read after auth-mode-specific stamp names; they may remain briefly but are harmless.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_14: [OUT_OF_SCOPE] Launcher argv asymmetries are intentional
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Source observed that differences such as `--full-auto`, `--sandbox read-only`, `--add-dir`, and probe omissions match the plan and parity rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_15: [OUT_OF_SCOPE] Auth-prep failure exit semantics predate this branch
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Implement/CI, review, and review-and-fix have different auth-prep failure exit semantics, but the source marked this as preexisting and not a new argv-ordering regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_16: [OUT_OF_SCOPE] Trust/auth/output ordering is otherwise consistent
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: Source observed that among the five wired call sites, trust/auth/output ordering is consistent where model args exist; the main outlier is the in-scope review-and-fix model-args omission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Low-risk env-key config interaction observation
- **Reviewer(s)**: dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Source marked the env-key config interaction as low-risk/out-of-scope: legacy top-level `env_key` in copied config may remain, but argv provider overrides likely make this benign.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] CMD_JSON contains only env var name, not key value
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: nit
- **Concern**: No value leak was found in `CMD_JSON`; env-key mode serializes the variable name `OPENAI_API_KEY`, matching the existing retry-state sensitivity policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Secret-safe detection is implemented correctly
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: nit
- **Concern**: Source observed that detection uses presence/length checks without expanding the key value, and harnesses assert sentinel values do not leak.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Login fallback auth.json secret semantics predate this branch
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Login fallback still symlinks `auth.json`, which may contain plaintext key material if created that way, but this behavior predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_6: [OUT_OF_SCOPE] Uncovered Codex paths are unchanged
- **Reviewer(s)**: dyn-secret-surfaces-output.txt
- **Severity**: latent
- **Concern**: Direct `/research` and other uncovered Codex lanes still use prior auth behavior and were not changed by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surfaces-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Review-and-fix temp-home lifecycle appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found that review-and-fix temp homes are removed inline with the script EXIT trap as backstop; no leak was found on paths added by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] Check-reviewers probe cleanup appears sound
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source found every probe return path inline-removes the temp home; stale `PROBE_DIRS` entries only cause redundant exit-time cleanup, not leaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] Implement launcher early auth-prep trap issue appears fixed
- **Reviewer(s)**: dyn-temp-lifecycle-output.txt
- **Severity**: nit
- **Concern**: Source observed that moving the EXIT trap and guarding unset variables fixes the early auth-prep/nounset trap failure mode in production code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

