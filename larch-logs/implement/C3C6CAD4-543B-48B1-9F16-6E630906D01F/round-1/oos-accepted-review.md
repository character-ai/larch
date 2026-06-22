### OOS_1: [OUT_OF_SCOPE] Unclosed bash fence openers treated as closed at EOF
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Unclosed bash fence openers are absorbed through EOF without a parse diagnostic; the parser skips the remainder of the file. A typo'd or truncated closing backtick causes later bash fences in the same file to be absorbed into one fence body, so consecutive-bash violations after the typo are never reported and lint can exit 0 incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Fail closed on unclosed fences and add a pytest case with a missing closer followed by a second valid `bash` fence.


### OOS_2: [OUT_OF_SCOPE] docs/linting.md misstates example-fence suppression scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Documentation claims only explicit WRONG/CORRECT examples are ignored, but `_is_example_fence` also ignores any fence when wrong/correct/example appear in preceding context or first body comment. Operators may rely on the doc and assume ordinary prose with "example" will not suppress enforcement, then be surprised by false negatives or over-broad suppressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] `_is_example_fence` / `EXAMPLE_RE` suppresses on broad prose keywords
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `EXAMPLE_RE` / `_is_example_fence` excludes fences when preceding prose or first body comment contains `\bexample\b`, `\bcorrect\b`, or `\bwrong\b`, not only WRONG/CORRECT teaching blocks. Two adjacent real bash fences under a "For example:" lead-in can evade the linter because the first fence is dropped from the candidate list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Narrow suppression to explicit WRONG/CORRECT labels and add a negative test.


