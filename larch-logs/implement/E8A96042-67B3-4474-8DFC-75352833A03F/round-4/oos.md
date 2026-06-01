### OOS_1: [OUT_OF_SCOPE] `docs/linting.md` harness shard numbering mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap` shard documented as harness-7 vs Makefile harness-15 causes CI shard lookup confusion for maintainers only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `plugin-root.env` sourcing in dirty-tree recovery
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Malicious `plugin-root.env` in `IMPLEMENT_TMPDIR` could execute arbitrary shell code in the orchestrator during dirty-tree recovery. Pre-existing; harden separately (signing, minimal exports, refuse symlinks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Heredoc `EOF` delimiter could truncate envelope parse
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A lone `EOF` line in bootstrap stdout could theoretically truncate envelope parse via heredoc delimiter; no known producer emits that line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Non-2 bootstrap rc lacks formatted wrapper operator stderr
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing class: exit 1 failures lack formatted Step 0 messages; debugging relies on raw bootstrap output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] `implement-bootstrap.md` missing parse scripts in edit-in-sync block
- **Reviewer(s)**: dyn-missing-file-coverage-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.md` documents the invoke wrapper but does not list `parse-bootstrap-routing-envelope.*` in its edit-in-sync block (unlike `implement-bootstrap-invoke.md`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-missing-file-coverage-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] `test-implement-structure.sh` awk extract diagnosability only
- **Reviewer(s)**: dyn-envelope-key-completeness-output.txt
- **Severity**: nit
- **Concern**: `awk` extraction of `_inv_routing_keys` fails generically on empty extract; dedicated non-empty assertions would improve failure messages only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-envelope-key-completeness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_7: [OUT_OF_SCOPE] Harness `mktemp` uses hardcoded `/tmp`
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap-invoke.sh` harness `mktemp` templates use hardcoded `/tmp/…` rather than `${TMPDIR:-/tmp}`; consistent with other offline harnesses, not production Step 0 code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

