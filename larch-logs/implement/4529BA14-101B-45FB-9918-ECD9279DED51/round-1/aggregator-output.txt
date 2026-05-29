### FINDING_1: unsafe eval while recovering prior reviewer env
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-eval-safety-output.txt
- **Severity**: important
- **Concern**: `scripts/write-design-current-env.sh` recovers reviewer keys by `eval`ing matching `export KEY=...` lines from the prior output file. A hand-edited or attacker-controlled `source-env.sh` can execute shell during refresh; eval errors may also be swallowed. Parse only strict `export KEY=true|false` lines, or use the repo's safe parser, and validate recovered values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-eval-safety-output.txt: Address the concern above.

### FINDING_2: recovered reviewer booleans bypass validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Recovered `CODEX_PRESENT`, `CURSOR_PRESENT`, `CODEX_AVAILABLE`, and `CURSOR_AVAILABLE` values are re-emitted without `validate_bool`. Corrupt prior values such as `maybe`, empty values, or invalid enums can survive refresh and fail later in downstream reviewer dispatch or Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Case 14 test lacks strict unset detection and symmetric coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Case 14 in `skills/design/scripts/test-write-design-current-env.sh` omits `set -u`, unlike Case 13, so missing exports might not fail the harness. One reviewer also notes missing symmetric cursor-only partial mirror coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: missing test for no-prior-output refresh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: No harness case covers recovery when `--output` does not yet exist. First-write no-flag refresh behavior is therefore not pinned, making regressions in the missing-file guard harder to catch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] both-explicit alias pairs can remain contradictory
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When callers explicitly pass conflicting `PRESENT` and `AVAILABLE` values for the same reviewer, the script preserves both values rather than normalizing or rejecting them. This is marked out of scope by the source.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] output path is not constrained to validated design tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-eval-safety-output.txt
- **Severity**: latent
- **Concern**: `--design-tmpdir` is validated, but `--output` is only required to be absolute. A mismatched output can read or write env state outside the validated session directory. Sources identify this as pre-existing or outside the reviewed diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-eval-safety-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] stable prelude symlink TOCTOU
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The stable prelude path has a symlink TOCTOU risk. The source marks this as not introduced by the current diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: no-flag recovery preserves mismatched alias pairs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: During no-flag refresh, prior mismatched `PRESENT` and `AVAILABLE` values can be preserved independently because partial CLI mirroring does not run. The source suggests either documenting byte-preserving recovery or adding post-recovery pair sync when neither side was explicitly set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] resume refresh omits reviewer CLI flags
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Resume refresh can still omit reviewer CLI flags, so resuming into an env file that never had the four reviewer keys still drops them. The source marks this as not introduced by the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] plan-review-loop still requires non-empty boolean argv
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `plan-review-loop` still requires non-empty `true|false` argv, so recovery failure can leave the same `${2:?}` missing-key failure mode as before. The source marks consumer coercion as out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] unrelated implement log artifacts in diff
- **Reviewer(s)**: dyn-eval-safety-output.txt, dyn-recovery-semantics-output.txt
- **Severity**: nit
- **Concern**: The reviewed diff includes `larch-logs/implement/4529BA14-.../` artifacts unrelated to the env-refresh fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-eval-safety-output.txt: Address the concern above.
  - From dyn-recovery-semantics-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] canonical writer-only round trip is sound
- **Reviewer(s)**: dyn-eval-safety-output.txt
- **Severity**: nit
- **Concern**: For writer-only `source-env.sh` content, the existing `%q` plus single-line grep/tail/eval round trip is sound; the residual risk comes from untrusted or hand-edited file content. This is contextual out-of-scope analysis rather than a requested fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-eval-safety-output.txt: Address the concern above.

### FINDING_13: explicit empty reviewer flag can be overwritten by recovery
- **Reviewer(s)**: dyn-recovery-semantics-output.txt
- **Severity**: latent
- **Concern**: Recovery checks whether the variable value is empty rather than whether the corresponding flag was omitted. Because `validate_bool` accepts empty values, an explicit `--codex-present ""` can be repopulated from the prior file, contradicting the documented contract that explicit flags override recovered values. The source says documented `/design` callers do not hit this, making it manual/custom-caller reachable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-recovery-semantics-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] both-explicit alias pair scenario is not a defect
- **Reviewer(s)**: dyn-recovery-semantics-output.txt
- **Severity**: nit
- **Concern**: One reviewer notes that when both sides of an alias pair are explicitly set, mirroring does not overwrite either side and recovery only fills empty keys, so the scout’s both-set differing-values scenario is not a defect for that reviewer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-recovery-semantics-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] branch commit inventory
- **Reviewer(s)**: dyn-recovery-semantics-output.txt
- **Severity**: nit
- **Concern**: The branch contains commits `30b14b5e0` for the fix and `f8684b9e1` for implement log flush. This is contextual metadata, not a code finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-recovery-semantics-output.txt: Address the concern above.
