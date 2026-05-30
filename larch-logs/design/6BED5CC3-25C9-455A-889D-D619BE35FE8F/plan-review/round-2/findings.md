### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:38-39
- **Concern**: Ambiguous (3175) grep edit span conflates distinct pins. Scenario: Plan says replace weak `snapshot` checks at 403–404 and 407–408 with `--snapshot-trailers` / `--dedup` greps; in `scripts/test-design-structure.sh` only 403 and 407 are `grep -Fq 'snapshot'`, while 404 is `diff_added` and 408 is `mechanical_churn`. A literal read can drop or overwrite the non-snapshot pins and weaken the guard.
- **Proposed resolution**: Spell the edit as: replace only the `snapshot` greps at 403 and 407; add separate `grep -Fq '--snapshot-trailers'` and `grep -Fq '--dedup'` lines for `$APPROVAL_MD` and `$DISCUSSION_MD`; keep existing `diff_added` / `mechanical_churn` greps at 404–406 and 408–410 unchanged.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:403-410
- **Concern**: Plan line ranges conflate weak snapshot greps with separate preservation greps. Scenario: Replacing 403-404 and 407-408 with only --snapshot-trailers/--dedup drops diff_added (approval-gates) and mechanical_churn (discussion-rounds) pins; structural regression guard weakens
- **Proposed resolution**: Replace only the snapshot substring greps at 403 and 407; add --dedup greps for $APPROVAL_MD and $DISCUSSION_MD; keep 404 and 408 (and existing diff_deleted greps) unchanged

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-trailer-awk.sh:1-50
- **Concern**: Testing strategy labels parse line 1 as trailer count. Scenario: First parse output is block_len (contiguous metadata lines in the upward scan), not present-key count; wrong expected values on block-boundary or duplicate-line fixtures
- **Proposed resolution**: Assert line 1 against block_len from fixtures; rename in plan/docs to metadata block line count

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:38-39
- **Concern**: (3175) grep edit span bundles non-snapshot pins with snapshot replacements. Scenario: Plan says replace checks at 403–404 and 407–408 with `--snapshot-trailers` / `--dedup` greps; in `scripts/test-design-structure.sh` only 403 and 407 are `grep -Fq 'snapshot'`, while 404 pins `diff_added` on `$APPROVAL_MD` and 408 pins `mechanical_churn` on `$DISCUSSION_MD`. A literal two-for-two swap drops those preservation pins and weakens the guard.
- **Proposed resolution**: Replace only the `snapshot` greps at 403 and 407; add separate `grep -Fq '--snapshot-trailers'` and `grep -Fq '--dedup'` lines for `$APPROVAL_MD` and `$DISCUSSION_MD`; keep 404 and 408 (and existing `diff_deleted` greps) unchanged.

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:14-15,52-74
- **Concern**: Harness scope cites Testing strategy only while Edge cases bind extra awk behaviors. Scenario: `test-trailer-awk.sh` is specified to cover “edge cases in **Testing strategy** below,” not the Edge cases section; Testing strategy omits `mechanical_churn` true vs false and `010` retention called out in Edge cases (issue #3204 gap #2 cited missing `mechanical_churn` / `0[89]` coverage). An implementer can satisfy Testing strategy and leave Edge-case bullets untested.
- **Proposed resolution**: Add explicit Testing strategy fixtures/assertions for churn true/false and `010` kept, or trim Edge cases to match the slimmer matrix and fix line 15 to a single source of truth.

### OOS_1:
- **Description**: Full trailer-set .md backfill beyond the new awk harness. Scenario: Seven new/updated sibling docs (~200+ lines) for claim #2 (awk unit gap); SIMPLE minimum is test-trailer-awk.md + lib-plan-optional-trailers.md only
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-trailer-dedup.md:1-30
- **Phase**: design
