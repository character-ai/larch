## Decision 1: skills/implement/SKILL.md prose update
- **Question**: Should skills/implement/SKILL.md prose references to timing-ledger.sh / token-ledger.sh be updated in B2?
- **Resolution**: Yes. Update prose to reference python3 cli.py token/timing verbs. Keeps docs consistent with retired scripts.
- **Source**: user

## Decision 2: Output format parity for token_report() / TimingReport
- **Question**: Must Python output match token-report.sh / timing-report.sh byte-for-byte?
- **Resolution**: Functionally equivalent is acceptable. Same sections, data, and HTML-comment anchors; minor whitespace differences OK. Tests updated to match new output.
- **Source**: user

## Decision 3: TimingRecord in tokens.py
- **Question**: Does the existing TimingRecord dataclass in tokens.py conflict with the new timing.py module?
- **Resolution**: No conflict. tokens.py TimingRecord is for vendor sidecar timing (duration_ms). timing.py TimingLedger is for session ledger rows (TSV). Different names and purposes; both stay in their respective modules.
- **Source**: codebase

## Decision 4: implement-bootstrap.sh --timing-ledger flag
- **Question**: implement-bootstrap.sh uses --timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv" as a path argument to other scripts. Does this need to change?
- **Resolution**: No. The --timing-ledger flag passes a file path, not the script name. Only the mark/record-vendor calls (lines 812-813, 865-866, 1059-1060, 1284-1285) need updating. The flag references stay unchanged.
- **Source**: codebase
