### FINDING_3: `since-ISO` merged-at filter can match partial date-only prefixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The since-ISO matcher may accept partial prefixes, so merged-at filtering can diverge from intended full instant comparisons against GitHub timestamps.
- **Suggested revision**: Align matching to the documented full ISO grammar and reject/error on partial inputs.



