### FINDING_1: Plan grep span conflates snapshot vs preservation pins
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation, unknown-slot
- **Severity**: important
- **Concern**: Plan text that replaces weak snapshot checks at lines 403–404 and 407–408 with `--snapshot-trailers` / `--dedup` greps bundles distinct pins. In `scripts/test-design-structure.sh`, only 403 and 407 are `grep -Fq 'snapshot'`; 404 pins `diff_added` on `$APPROVAL_MD` and 408 pins `mechanical_churn` on `$DISCUSSION_MD`. A literal range swap can drop or overwrite those preservation greps and weaken the structural regression guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Spell the edit as: replace only the `snapshot` greps at 403 and 407; add separate `grep -Fq '--snapshot-trailers'` and `grep -Fq '--dedup'` lines for `$APPROVAL_MD` and `$DISCUSSION_MD`; keep existing `diff_added` / `mechanical_churn` greps at 404–406 and 408–410 unchanged.
  - From Cursor-Innovation: Replace only the snapshot substring greps at 403 and 407; add --dedup greps for $APPROVAL_MD and $DISCUSSION_MD; keep 404 and 408 (and existing diff_deleted greps) unchanged
  - From unknown-slot: Replace only the `snapshot` greps at 403 and 407; add separate `grep -Fq '--snapshot-trailers'` and `grep -Fq '--dedup'` lines for `$APPROVAL_MD` and `$DISCUSSION_MD`; keep 404 and 408 (and existing `diff_deleted` greps) unchanged.


### FINDING_2: Trailer-awk test mislabels parse line 1 as trailer count
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: Testing strategy labels parse line 1 as trailer count, but the first parse output is `block_len` (contiguous metadata lines in the upward scan), not present-key count. Block-boundary or duplicate-line fixtures can get wrong expected values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Assert line 1 against block_len from fixtures; rename in plan/docs to metadata block line count


### FINDING_3: Harness scope vs Edge cases matrix mismatch
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Concern**: Harness scope cites Testing strategy only while Edge cases bind extra awk behaviors. `test-trailer-awk.sh` is specified to cover edge cases in Testing strategy below, not the Edge cases section; Testing strategy omits `mechanical_churn` true vs false and `010` retention called out in Edge cases (issue #3204 gap #2). An implementer can satisfy Testing strategy and leave Edge-case bullets untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Add explicit Testing strategy fixtures/assertions for churn true/false and `010` kept, or trim Edge cases to match the slimmer matrix and fix line 15 to a single source of truth.

