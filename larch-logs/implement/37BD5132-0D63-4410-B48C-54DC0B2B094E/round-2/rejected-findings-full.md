### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: security: skills/design/SKILL.md:1044-1046
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Step 5d --body-file trusts CLAUDE_PLUGIN_ROOT to resolve the committed literal path Misconfigured or attacker-controlled CLAUDE_PLUGIN_ROOT on an operator machine could cause gh to post arbitrary file contents to public upstream issue #2672 when gates pass Verify resolved path is a regular file under the expected plugin install root before gh issue comment
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: security: .claude/rules/gh-body-file.md:85-90
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Process-substitution example may skip redaction checkpoint for dynamic bodies Authors copy --body-file <(printf '%s' "$body") for large session-derived bodies and publish unredacted content Restrict example to fixed literals or show redaction before substitution; prefer mktemp + redact + --body-file path
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: architecture: scripts/design-log-publish.sh:440-456
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Post-commit pre-push mktemp/printf failure drops worktree without recovery ref or stderr preservation Design log commit exists only on disposable branch after body-file setup fails; operator sees PUBLISH_OK=false with no recovery hint unlike push-failure path Mirror push-failure recovery ref + stderr on mktemp/printf failure after commit; document in design-log-publish.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Committed literal has no trailing newline gh --body-file may normalize EOF and change upstream comment bytes vs historical inline post Verify gh behavior once or document byte-identical expectation after smoke test
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: .claude/rules/gh-body-file.md:2-39
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Frontmatter lists 37 paths while acceptance criterion 1 documents 33. Sign-off against acceptance item 1 fails literally even though coverage improved. Reconcile acceptance/plan YAML with the 37-path discovered set.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: **architecture** `skills/review-and-fix/scripts/review-and-fix.sh:682-692` — `skills/review-and-fix/scripts/review-and-fix.{sh,md}` are in `paths:` but contain no `gh … --body` / `--notes` invocation (only `write-tally.sh --body-file`). That inflates the trigger surface without matching the rule’s stated “every `gh … --body`” scope and can dilute trust in the frontmatter as an exhaustive caller map. **Suggested fix:** Either remove `skills/review-and-fix/scripts/review-and-fix.{sh,md}` from `paths:` or add a frontmatter comment in the rule body clarifying that `paths:` also lists adjacent body-file helpers when they sit on the same edit path as `gh` callers—prefer removal unless review-and-fix is expected to gain direct `gh` body writes soon.
- **Reviewer**: dyn-rule-coverage-drift-output.txt
- **Concern**: - **architecture** `skills/review-and-fix/scripts/review-and-fix.sh:682-692` — `skills/review-and-fix/scripts/review-and-fix.{sh,md}` are in `paths:` but contain no `gh … --body` / `--notes` invocation (only `write-tally.sh --body-file`). That inflates the trigger surface without matching the rule’s stated “every `gh … --body`” scope and can dilute trust in the frontmatter as an exhaustive caller map. **Suggested fix:** Either remove `skills/review-and-fix/scripts/review-and-fix.{sh,md}` from `paths:` or add a frontmatter comment in the rule body clarifying that `paths:` also lists adjacent body-file helpers when they sit on the same edit path as `gh` callers—prefer removal unless review-and-fix is expected to gain direct `gh` body writes soon.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: skills/design/references/l3-velocity-deferral-comment.txt:1
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Committed literal has no EOF newline; acceptance text was ambiguous. Editor normalization could change upstream comment bytes vs prior inline literal. Document no-trailing-newline invariant or verify gh preserves bytes and lock with a test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

