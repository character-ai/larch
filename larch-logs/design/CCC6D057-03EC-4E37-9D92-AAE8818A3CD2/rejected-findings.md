### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:212-244
- **Concern**: is_anchor_for_basename matches basename inside quoted paths on assignment lines. Scenario: WATERFALL_SH=.../dispatch-with-waterfall.sh lines (e.g. decompose-panel-dispatch.sh:145) fire without unset in prior 5 lines; planned unset before "$WATERFALL_SH" at :153 does not satisfy look-back for :145
- **Proposed resolution**: Exclude simple VAR= assignments (no command substitution) from the new scan, or place unset immediately above each assignment alias line


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:48-53
- **Concern**: Edge case promises symmetric Cursor ledger tracking; body is Codex-only before phase2. Scenario: Cursor-primary slots in same group may still double Cursor fallbacks
- **Proposed resolution**: Add explicit phase2 dedup for whichever alt tool is launched, or narrow edge-case prose to Codex-only


### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/dispatch-with-waterfall.sh:91-118
- **Concern**: FINDING_5 New fallback_group TSV data lacks a validation plan. Scenario: The ledger format is group<TAB>slot_name<TAB>tool<TAB>output_path<TAB>status, but fallback_group and slot names can currently be arbitrary strings; tabs or newlines can corrupt rows and cause wrong dedup matches or misleading sidecars
- **Proposed resolution**: Add manifest validation for fallback_group and any ledger-written fields, rejecting tab, CR, and LF at minimum, and add malformed fallback_group regression tests


### [Plan Review] FINDING_41

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/dispatch-with-waterfall.sh:77-124
- **Concern**: Plan mentions a session mapping file but not parallel per-slot fallback_group storage alongside slot_names[]. Scenario: Implementers may omit group lookup by slot index and break dedup at launch time
- **Proposed resolution**: Add slot_fallback_groups+=() during manifest parse (jq -r '.fallback_group // empty'); skip ledger logic when empty


### [Plan Review] FINDING_43

### FINDING_43:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:49-50
- **Concern**: Ledger status value OK,reused embeds a comma inside the status column. Scenario: Naive TSV parsers or grep for status=OK may miss reused rows or split fields wrong
- **Proposed resolution**: Use a single-token status (reused) plus optional source_slot column, or document strict five-field tab parsing only


### [Plan Review] FINDING_44

### FINDING_44:
- **Reviewer(s)**: Cursor-dyn-bash32-ledger-design
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/dispatch-with-waterfall.sh:84-95
- **Concern**: Optional fallback_group has no jq type guard when present. Scenario: Non-string fallback_group could corrupt ledger keys or scans
- **Proposed resolution**: Add jq elif for has("fallback_group") requiring a non-empty string, mirroring agent/prompt_file checks


### [Plan Review] FINDING_47

### FINDING_47:
- **Reviewer(s)**: Codex-dyn-bash32-ledger-design
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:82-123,388-396
- **Concern**: The proposed raw TSV ledger lacks a validation or escaping rule for fallback_group, slot_name, and output_path fields. Scenario: Current parsing accepts arbitrary non-empty slot strings and output paths with tabs; a tab or newline in a grouped field can shift TSV columns or create synthetic rows, causing missed or wrong dedup reuse
- **Proposed resolution**: Specify and implement Bash-3.2-compatible validation for grouped ledger fields: reject tab, LF, and CR in fallback_group and slot_name, and reject tab in grouped output paths or switch the ledger to JSONL parsed with jq/read loops


