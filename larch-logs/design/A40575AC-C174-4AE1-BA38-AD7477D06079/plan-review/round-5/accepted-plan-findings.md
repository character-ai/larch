### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-normalize-awk-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/scripts/normalize-oos-block-header.sh:16-17
- **Concern**: Plan says rewrite header on line 1 only but specifies bare sub() with no NR==1 guard. Scenario: A multi-line block passed via --block-file or stdin can contain another line matching ^###[[:space:]]+[A-Za-z]+_[0-9]+: (e.g. a cited heading in Concern/Suggested revision, or an unsplit skipped-findings aggregate); sub() on every line would rewrite those ids to ### OOS_<seq>: and corrupt block body text
- **Proposed resolution**: Wrap the sub in NR==1 { sub(/^###[[:space:]]+[A-Za-z]+_[0-9]+:/, "### OOS_" seq ":") }; { print } and add a harness case where line 2 is ### FINDING_2: and must remain unchanged after normalization


