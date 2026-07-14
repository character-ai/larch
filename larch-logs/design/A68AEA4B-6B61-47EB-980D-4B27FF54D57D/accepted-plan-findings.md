### FINDING_7: Exception disclosure lacks secret redaction
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A validated exception rationale is appended to an issue-upserted final summary without a redaction requirement, so secret-shaped values from the plan or note could be published.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add secret redaction before appending the exception disclosure and test that a valid exception with a secret-shaped rationale is redacted in the final summary.


### FINDING_8: Tier-2 counters lack defined consumption points
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: The plan does not define when tier-2 counters are consumed. Repairs, failed settles, pause/resume, or guideline declines could re-enter Gate C without charging the round, violating the one-round-per-kind bound.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify atomic tier-2 counter consumption before each main-agent repair or guideline decline, including failed-settle recovery, and add pause/re-entry coverage for that bound.


### FINDING_9: Generated implementer outputs are omitted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Changes to `agents/_implementer-base.md` would leave the generated external implementer prompts stale, causing agent-sync or generation checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `agents/codex-implementer.md` and `agents/cursor-implementer.md` as regenerated updated files; run both generators and `python3 python/cli.py generate check`.


