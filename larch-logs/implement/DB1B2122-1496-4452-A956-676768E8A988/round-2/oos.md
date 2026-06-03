### OOS_1: [OUT_OF_SCOPE] Empty `/design` invocation UX predates this refactor
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 0b fetches the issue even when `POSITIONAL_KIND=none`. `/design --hard` with no issue may fail at `gh issue view`; behavior unchanged by this branch and explicitly left out of refactor scope, but empty invocations remain fragile.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Positional tail doc omits numeric tail-ignore semantics
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: The top-level Positional tail bullet describes only “first non-flag token” and does not mention that a numeric issue consumes only the first positional token and ignores later tokens (documented in `references/flags.md` and `parse-design-argv.md`). Minor doc drift, not introduced by the KV consumer loop itself.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] No harness case for `=` inside `RUN_ID` / `POSITIONAL_VALUE`
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: Harness `kv_value` correctly uses `substr($0, length(k)+2)` (so `RUN_ID=a=b` would parse correctly), but there is no case covering `=` inside `RUN_ID` or `POSITIONAL_VALUE`. Protocol supports it; coverage gap only.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] `test-parse-design-argv` lacks explicit Makefile `contains` pin
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Some newer design harnesses (e.g. assessor family around lines 1250–1254) get explicit `Makefile` `contains` pins; `test-parse-design-argv` does not, though it is wired in `Makefile` and `test-harnesses-16`. Low risk given shard membership; optional consistency improvement only.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_5: [OUT_OF_SCOPE] Numeric-first positional ignores later flags — operator footgun
- **Reviewer(s)**: dyn-template-expansion-output.txt
- **Severity**: nit
- **Concern**: `references/flags.md:29` and harness case `3249 extra words` document that a numeric first positional ignores trailing tokens (`3249 --hard` keeps `HARD_REQUESTED=false`). That matches the plan but is an operator footgun if users expect GNU-style “flags anywhere” parsing.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

