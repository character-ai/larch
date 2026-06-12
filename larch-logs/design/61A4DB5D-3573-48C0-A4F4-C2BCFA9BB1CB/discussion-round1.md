## Decision 1: Read modes scope
- **Question**: Should the Python `tracking-issue read` port implement all 4 modes (issue+prompt, issue-only, prompt/stdin, sentinel) or only sentinel?
- **Resolution**: All 4 modes. Full parity port.
- **Source**: user

## Decision 2: step-0-bootstrap.sh cutover
- **Question**: Should skills/implement/scripts/step-0-bootstrap.sh (which calls tracking-issue-read.sh --sentinel) be cut over in this piece?
- **Resolution**: Yes, cut over step-0-bootstrap.sh alongside implement-bootstrap.sh.
- **Source**: user
