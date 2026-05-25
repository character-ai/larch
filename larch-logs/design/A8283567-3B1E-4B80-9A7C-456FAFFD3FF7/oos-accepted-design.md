### OOS_3:
- **Description**: FAILED_JOBS and reasons may echo untrusted CI job names into logs or bail strings. Scenario: If a job name or matrix label were crafted to contain newlines or control bytes parsers or downstream prompts could mis-split lines
- **Reviewer**: Cursor-dyn-fd3-capture
- **Severity**: latent
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:39-42 and proposed scripts/ci-failed-jobs.sh KV and TSV rows
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2798
