### OOS_1: Audit-runs skill table omits the new guideline-ship-outcome scan
- **Description**: Audit-runs skill table omits the new guideline-ship-outcome scan. Scenario: The scans-implement.tsv row and compute-counters KVs will exist, but the operator-facing audit-runs skill still documents only the older implement scan set, so carry-forward summaries will not mention guideline outcome counters without reading scan output directly.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: .claude/skills/audit-runs/SKILL.md:67-80
- **Phase**: design



### OOS_2: Stable reason tokens are unspecified
- **Description**: Stable reason tokens are unspecified. Scenario: Outcome JSON carries a `reason` field used for histograms, but the plan does not define a bounded token set or validation beyond audit presence checks. Typos will fragment drop analytics over time.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/larch/implement/ship_guidelines.py
- **Phase**: design



### OOS_3: Guideline outcome counters are not wired into audit report frontmatter
- **Description**: Guideline outcome counters are not wired into audit report frontmatter. Scenario: The plan adds `GUIDELINE_OUTCOME_*` keys to `compute-counters`, but the audit-runs skill still only reads the legacy counter set when composing chain-of-history reports. Drop-rate deltas will not carry forward across audits until the skill prompt and frontmatter keys are extended.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude/skills/audit-runs/SKILL.md:237-249
- **Phase**: design



