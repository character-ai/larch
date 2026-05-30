### FINDING_13: [OUT_OF_SCOPE] `SECURITY.md` does not document new Bash branch
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing Read-poll reminder bullet covers path non-reflection but not Bash command parsing on every Bash PostToolUse or session/task-id state files; doc drift, not a vulnerability (warn-only, command bodies not persisted).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Per `AGENTS.md`, a short SECURITY.md addendum noting “Bash commands are classified in-memory only; never persisted or echoed” would close the gap.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] Generic Read state still stores full `sanitized_path` in TSV
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pre-existing generic Read polling stores full `sanitized_path` in `state-<cwd_hash>.tsv`; paths with sensitive tokens in directory names can land in `/tmp` with mode `600` within same-UID trust model.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] `test-hook-anti-read-poll.md` stub vs grown harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-hook-anti-read-poll.md` remains a one-line stub while harness grew; `script-md-siblings` prefers stubs pointing at primary contract; plan did not require updating test sibling.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — informational only; source provided only generic “Address the concern above.”)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] `chore(larch-logs)` commits on branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Intentional run-log flushes per project convention; not plan scope for #3195.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — informational only)


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] Pre-existing generic Read polling edge cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Generic Read offset string compare and unlocked TSV RMW predate this branch; unchanged generic-read edge cases not introduced by #3195. Fix only if hardening generic Read polling is in scope separately.
- **Suggested revisions (informational for voters; coder decides)**:
  - (none — source provided only generic “Address the concern above.”)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] `tasks/…\.output` regex may match `.output.bak` paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `grep -oE tasks/…\.output` can match a prefix inside `tasks/foo.output.bak`; `cat …/tasks/foo.output.bak` could be counted as task-output polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten token extraction (e.g. require `.output` not followed by alnum) if backup paths are plausible.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

