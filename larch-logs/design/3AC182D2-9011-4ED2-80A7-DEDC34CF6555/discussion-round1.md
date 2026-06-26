## Decision 1: Pre-filter YES threshold
- **Question**: What qualifies as "some-YES" for keeping a rejected finding?
- **Resolution**: Any rejected finding with ≥1 YES vote advances past the cheap pre-filter (regardless of total voter count). 0-YES "dismissed" findings are dropped.
- **Source**: user

## Decision 2: Verify cap
- **Question**: What is the default cap on findings entering the expensive per-agent verify step?
- **Resolution**: 100 findings. Log what was dropped per the no-silent-caps principle.
- **Source**: user

## Decision 3: Log collection scope
- **Question**: Does standalone /review produce committed larch-logs/ that should be collected?
- **Resolution**: Collect from both larch-logs/implement/ and larch-logs/review/. The review/ directory may be empty today but should be supported.
- **Source**: user

## Decision 4: "high-severity" in pre-filter
- **Question**: Is "high-severity" a separate OR inclusion condition (keep even 0-YES findings that are high-severity)?
- **Resolution**: High-severity (major/blocker) is a prioritization signal, not a separate inclusion gate. Only ≥1 YES findings advance; high-severity ones are sorted to the front of the verify queue so the cap preferentially covers them.
- **Source**: codebase (body_severity field is often absent in schema v2; per-voter severity in findings-classification.tsv; consistent with "≥1 YES" user answer)
