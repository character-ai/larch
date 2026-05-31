### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:55-61,99-110
- **Concern**: Proposed mktemp-backed enumeration does not handle temp-file allocation failure under set -e. Scenario: If TMPDIR points at a missing or unwritable directory, mktemp exits non-zero before the planned find failure branch runs; cleanup aborts without emitting the required removal-count KVs, contradicting the planned cleanup still exits 0 fail-safe
- **Proposed resolution**: Guard each mktemp call: on allocation failure, emit a larch_err warning, skip that pass with count 0, and continue to the next pass; or fall back to /tmp before deciding to skip

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:3-6
- **Concern**: Plan bundles two independent workstreams into one SIMPLE change. Scenario: A cleanup fail-safe and design Step 3 dead-config removal touch unrelated runtime surfaces, docs, and harnesses; a regression in either path can block or obscure the other
- **Proposed resolution**: Split into separate plans/PRs, or narrow this PR to the live Step 3 regression and leave cleanup for its own minimum-change patch

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:55-61,99-110
- **Concern**: Proposed temp-list wrapper adds an unguarded mktemp dependency. Scenario: If TMPDIR is missing or unwritable, cleanup can abort before emitting counts, replacing a find-enumeration warning path with a new hard failure
- **Proposed resolution**: Guard mktemp failure and warn/skip that pass, or use a known writable fallback; add one focused harness case for bad TMPDIR

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:55-61,99-110
- **Concern**: Plan drops the loop-level || true while moving find into an if branch. Scenario: The existing || true suppresses errexit inside the while bodies; removing it changes more than enumeration failure handling, so rm failures or other body failures can make /cleanup exit non-zero even though the plan promises only the enumeration failure path changes
- **Proposed resolution**: Keep || true on the two while loops after reading the temp files; the separated if find branch still observes enumeration failure without changing loop-body failure behavior

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-cleanup-fail-safe
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:20-21; skills/cleanup/scripts/cleanup.sh:56-61,100-110
- **Concern**: Plan drops the loop-level || true as redundant, but in Bash that OR-list context also suppresses errexit inside the while body today. Scenario: An rm failure in either cleanup loop would become a new nonzero script exit and can skip the planned temp-file rm -f, changing behavior beyond top-level enumeration find failures
- **Proposed resolution**: Keep || true on the two read loops after redirecting from the temp files, so the if find branch owns only enumeration failure handling while loop-body failure handling stays unchanged
