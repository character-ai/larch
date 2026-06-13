### OOS_8: [OUT_OF_SCOPE] compose fail-opens when is-security-block classifier errors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Pre-existing asymmetry: `compose-review-findings.sh` fail-opens when `is-security-block` errors while tally fail-closes. Security-tagged OOS could reach JSONL if the classifier subprocess fails during compose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align compose with tally: check exit code and fail closed on classifier errors.


### OOS_9: [OUT_OF_SCOPE] compose body_severity and focus_area extraction-before-truncation untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed `body_severity` and `focus_area` extraction-before-truncation (and reviewer_slots tmpdir redaction) lack focused pytest. Long concern bodies can truncate before marker extraction, leaving empty metadata in committed JSONL without failing current compose tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add fixture with markers after 2000+ chars assert JSONL fields populated while prose_body is capped.
  - From cursor-specialist-testing-output.txt: Add focused compose pytest when touching compose_review redaction paths.


