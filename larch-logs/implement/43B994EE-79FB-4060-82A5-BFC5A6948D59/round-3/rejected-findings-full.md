### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicated semver increment for `--bump` override
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` reimplements MAJOR/MINOR/PATCH arithmetic for `--bump` override (lines 242–253) instead of calling the same helper used by `classify-bump.sh` / `apply-bump.sh`. Future bump-rule changes in classify/apply paths will not automatically apply to operator overrides, risking wrong `NEW_VERSION` at release cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared bump-from-type helper (e.g. apply-bump `_apply_bump_type`) and call it from release-prepare override path.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Single `gh pr view` failure aborts entire prepare
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` lines 182–220: any one unresolvable PR number in the git-log-derived list causes `emit_error pr-metadata-incomplete` and aborts the whole cut, even when most PRs and the bump range are valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip-with-warning plus operator confirm or fail only when all PR fetches fail

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Release notes omit commits without `(#N)` in squash subject
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: PR list parsing (lines 170–173) only extracts trailing `(#N)` from commit subjects; merges without that suffix are missing from release notes while aggregate bump still reflects their code changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document or add secondary PR discovery for notes

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: `promote-release.sh` lacks unique-`isLatest` guard before promote
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `promote-release.sh` (lines 79–92) does not verify a unique Latest release before `gh release edit --latest`; metadata corruption between prepare and finish could yield ambiguous Latest promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse unique-Latest guard before gh release edit --latest

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Branch/main guards only in SKILL, not `release-prepare.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: “Must be on `main`” is enforced in SKILL Step 1, not inside `release-prepare.sh`; direct script invocation off `main` can emit misleading version KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add main/HEAD==origin/main guard inside release-prepare.sh

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: No early check for existing `vNEW_VERSION` tag
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Operator can run full PR+CI before `release-finish` fails on duplicate tag; no `ls-remote` tag probe during prepare after `NEW_VERSION` is known.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: ls-remote tag check during prepare after NEW_VERSION computed

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Reasoning log omits compare commit when `--head` is set
- **Reviewer(s)**: dyn-classify-bump-head-coordination-output.txt
- **Severity**: nit
- **Concern**: `classify-bump.sh` reasoning log records base commit only (lines 115–122), not `HEAD_COMPARE` / `--head`, so release debugging can imply classification used local `HEAD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classify-bump-head-coordination-output.txt: Add a “Compare commit” line using `HEAD_COMPARE` (short OID + subject) when `--head` is set.

---


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Dual secrets-redaction paths for release notes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Notes are redacted in SKILL Step 3 and again in `release-finish.sh` (line 129+). If `redact-secrets.sh` behavior changes, both call sites must stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single authoritative redaction site; document optional second pass only if required.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Script index mixes active cut flow with legacy promote helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: SKILL script index lists `promote-latest-release.sh` alongside new cut-a-release scripts without a clear active vs legacy split; operators may invoke obsolete promote-newest flow during a cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split script index into active vs legacy sections.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `BUMP_TYPE=NONE` not fail-fast at prepare
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When `classify-bump.sh` emits `BUMP_TYPE=NONE` (default-path idempotency), `release-prepare.sh` still returns success KVs until `release-set-version` refuses later—operator may confirm, branch, and open a PR before hitting a no-op error. (Note: current `/release` path passes `--base`, which sets `SKIP_IDEMPOTENCY=true`; risk is strongest for direct script use or future caller changes.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Emit ERROR=no-bump-needed at prepare when NONE and no --bump override.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: `classify-bump.sh` `--head` / idempotency / CLI safety
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-classify-bump-head-coordination-output.txt
- **Severity**: latent
- **Concern**: With only `--head` (no `--base`), idempotency still walks local `HEAD` (`IDEMPOTENCY_REF` at lines 159–169) and can emit `BUMP_TYPE=NONE` before the `--head`-scoped diff runs. `/release` always passes both `--base` and `--head`, but the CLI presents the flags as independent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Anchor idempotency walk to HEAD_COMPARE when --head set or reject --head without --base
  - From dyn-classify-bump-head-coordination-output.txt: Document that `--head` requires `--base` for aggregate release use, or auto-set `SKIP_IDEMPOTENCY=true` whenever `--head` is set (and add a harness case for `--head` alone vs `--base`+`--head`).

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

