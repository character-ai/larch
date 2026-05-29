### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:85,98 vs plan.txt:13,26,35
- **Concern**: Completeness gate (zero `--simple` grep) conflicts with proposed SKILL/flags/test text that still names `--simple`. Scenario: Implementer cannot satisfy both the manual zero-hit gate and pins like flags.md "including `--simple`" or test-design-structure `--simple`-rejected prose; incomplete removal or a failing self-check
- **Proposed resolution**: Choose one contract: (A) zero grep — use only generic "disallowed public flag" / "default SIMPLE (no --hard)" wording everywhere, pin rejection via `absent` or non-literal harness needles; or (B) allow `--simple` only in a single generic disallow sentence and drop the zero-grep gate

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:74-86 vs plan.txt:12,26,35
- **Concern**: Completeness gate forbids any live `--simple` substring while other plan bullets require naming `--simple` for rejection prose and harness pins. Scenario: Implementer cannot satisfy both zero-grep and pins like flags.md "including `--simple`" or test-design-structure `--simple`-rejected prose; risk of either grep failure or weak rejection docs
- **Proposed resolution**: Pick one contract: (a) grep-clean surface with generic "unknown/disallowed public flag" only and pins on that wording, or (b) allow `--simple` only in negative-test/absent assertions with an explicit grep exclusion list; align SKILL, flags.md, and test-design-structure.sh to the chosen rule

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:12-13,26,35,74-75,85-98
- **Concern**: Completeness gate (zero literal `--simple` on live surface) conflicts with proposed SKILL/flags/test prose that still spells `--simple` (e.g. "including `--simple`", edge-case examples, harness pin for "`--simple`-rejected" prose). Scenario: Implementer follows the plan literally: committed files still contain `--simple` while the manual grep gate is required to pass; or they strip all spellings and drop the only documented rejection contract
- **Proposed resolution**: Q2 already says no `--simple`-specific messages. Align every file edit and `test-design-structure.sh` pin with that: generic "unknown/disallowed leading `--` flag" language only; pin default SIMPLE + disallowed-flag rejection without embedding the removed token; reword Edge cases without the literal flag name

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-outcome-enum-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:12,26,35,85-86
- **Concern**: Proposed SKILL.md / flags.md text and test-design-structure.sh pin spell literal `--simple` while the plan also requires zero live-surface `--simple` matches. Scenario: Implementer cannot satisfy both the completeness grep and the listed prose edits; a new structure-test pin for "`--simple`-rejected" prose would itself fail the gate
- **Proposed resolution**: Keep rejection behavior generic (any unrecognized leading `--` flag is a hard error before Step 0) with no `--simple` literal in runtime/docs/tests; pin default-SIMPLE + `--hard` only in test-design-structure.sh
