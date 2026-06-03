### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Duplicate `--run-id` silently last-wins
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Duplicate `--run-id` is allowed; last value wins (`--run-id a --run-id b` keeps only `b`) with no validation error, unlike duplicate `--hard` which is rejected.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `flags.md` scope drift vs plan boundary
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan scoped `flags.md` to a one-line parser pointer without restating allowlist/positional rules; implementation also edits the Positional tail bullet with tail-ignore semantics. Behavior is documented in two places instead of one canonical pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Keep only the one-line pointer in flags.md and leave tail-ignore detail in parse-design-argv.md, or explicitly amend the plan/issue to allow the extra sentence.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `POSITIONAL_KIND=none` not gated before Step 0b issue fetch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When Step 0-pre succeeds with `POSITIONAL_KIND=none`, Step 0b still flows into `gh issue view "$ISSUE_NUMBER"` and `design-route.sh --issue` with an empty issue number. `/design` with only flags and no positional runs session-setup in 0a, then fails or misbehaves at issue fetch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document orchestrator halt on none or add an explicit guard in a follow-up.
  - From cursor-specialist-edge-cases-output.txt: Add an explicit none branch before fetch/route that matches legacy empty-invocation handling.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Step 0-pre consumer does not validate boolean KV tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: The Step 0-pre consumer assigns `*_REQUESTED` KVs verbatim with no `true`/`false` validation. A corrupted line like `HARD_REQUESTED=yes` could propagate wrong tier or router flags into downstream init, disagreeing with Step 0b tier prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Validate hard_requested/partition_requested/etc. are exactly true or false after ingest, or re-use parser-only output without ad-hoc line mutation.
  - From dyn-kv-protocol-output.txt: In the `case` arms for the five `*_REQUESTED` keys, reject values other than `true`/`false` with the same abort path used for unexpected keys; keep `RUN_ID` / positional fields unrestricted aside from the parser’s newline guard.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Duplicate numeric-issue classification regex in parser
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `parse-design-argv.sh` applies `^[0-9]+$` twice in positional tail handling (lines 86–87 and 101–102). The two branches must stay in sync on future edits.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Numeric issue positionals silently ignore trailing tokens
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When the first positional is numeric, all tokens after the first digit run are ignored without error (e.g. `/design 3249 fix the parser` designs issue 3249 and drops trailing words). Either reject trailing tokens with `VALIDATION_ERROR` or document explicitly that extra words after an issue number are ignored.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

