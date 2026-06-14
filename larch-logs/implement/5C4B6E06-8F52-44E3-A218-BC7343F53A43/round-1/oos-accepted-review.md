### OOS_1: [OUT_OF_SCOPE] research_eval rejects allowed blocking severity
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Structured reviewer validation rejects blocking severity even though reviewer prompts allow it. A reviewer using an allowed blocking TSV or JSONL severity can be marked NOT_SUBSTANTIVE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Align allowed severities with the prompt contract and add JSONL and TSV tests for blocking.


