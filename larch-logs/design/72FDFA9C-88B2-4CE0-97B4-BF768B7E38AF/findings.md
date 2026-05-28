### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:89-91
- **Concern**: Post-edit grep expects only CHANGELOG hits without excluding committed run logs. Scenario: The proposed verification command will still match historical committed artifacts under larch-logs, so implementers may either fail a good minimum-change removal or start editing archived logs outside the issue scope
- **Proposed resolution**: Narrow the grep to live surfaces being cleaned up, or add path exclusions such as :!larch-logs/**; keep archived run-log references untouched

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:91-91
- **Concern**: Post-edit `git grep` is repo-wide and will still match committed `larch-logs/` review artifacts. Scenario: The verification step claims only `CHANGELOG.md` should match, but `larch-logs/implement/**` already contains many historical references to both harness names; a literal `git grep -nE 'test-report-tokens-recompute|test-rate-assertions'` will fail or block the implementer even when all live surfaces are clean
- **Proposed resolution**: Scope the check, e.g. `git grep -nE 'test-report-tokens-recompute|test-rate-assertions' -- Makefile agent-lint.toml docs/linting.md skills/report-tokens CHANGELOG.md` and expect matches only in `CHANGELOG.md` (historical line ~2107 plus the new `### Removed` bullet), or add `':!larch-logs'`

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-ref-inventory, Codex-dyn-ref-inventory
- **Severity**: latent
- **Focus area**: correctness
- **Location**: larch-logs/measure-md-cost/2026-05-18.tsv:530; larch-logs/design/90628862-9A18-4A56-8420-63DE723F9D81/plan.txt:104-142
- **Concern**: Post-edit grep expectation omits committed historical references. Scenario: The plan's final `git grep -nE 'test-report-tokens-recompute|test-rate-assertions'` is claimed to return only CHANGELOG hits, but tracked `larch-logs/**` files still contain deleted harness names and `test-rate-assertions.md`; running the verification literally will fail or tempt scope creep into historical run logs.
- **Proposed resolution**: Keep the deletion scope as-is, but revise the verification command or expected output to exclude `larch-logs/**` historical artifacts, for example `git grep ... -- . ':(exclude)larch-logs/**'`, and note that committed run logs may retain historical mentions.
