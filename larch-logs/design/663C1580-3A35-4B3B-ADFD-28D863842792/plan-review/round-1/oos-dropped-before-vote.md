### FINDING_9: Committed record count differs from the scope anchor [OUT_OF_SCOPE]
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Concern**: The scope anchor cites 1,136 entries while the checked-in baseline contains 1,135; this is harmless documentation drift.

### FINDING_10: Flag mutual exclusion is also noted as follow-up hygiene [OUT_OF_SCOPE]
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Concern**: Mutual exclusion between `--migrate` and `--write` is unspecified for the one-shot operator command; this is low-risk CLI hygiene.

