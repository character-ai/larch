### FINDING_1: [OUT_OF_SCOPE] code-quality: scripts/dispatch-code-voters.md:43
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Launcher-stderr text attributes diagnostics to subprocess fail() only. Minor imprecision when failure is launch-claude-review.sh validation only. Clarify in a separate change that stderr can originate from either script in the stack.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] correctness: scripts/dispatch-code-voters.md:53
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Global failed gloss says missing or empty output only Voter 1 can be failed with non-empty output when rc is non-zero Align the gloss with per-slot definitions or qualify it excludes voter1
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] risk-integration: (branch vs cached diff)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Round-2 diff cache may omit files touched only in the other commit. Review based only on diff.txt might miss non-doc changes from 157897da. Regenerate full-branch diff or read `git diff main...HEAD` when validating the whole PR.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Single dense paragraph mixes fingerprint semantics and recovery policy. Harder to scan during incidents. Split into short bullets aligned with neighboring Behavior lists.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] New voter1_rc guidance is a single dense paragraph. Operators or editors miss part of the triage story or introduce typos when changing one clause. Split into short bullets or sub-paragraphs with the same content.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Long single paragraph bundles exit-code taxonomy incident note recovery and DISPATCH_OK semantics reducing scanability and editability compared to nearby bullet style Operators skim for rc meaning and miss the DISPATCH_OK or round-2 nuance buried mid paragraph Split into a small subsubsection or bullets for rc=1 heuristic rc=2 meaning and ops DISPATCH_OK note
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Rc narrative centers on 1 vs 2 but voter1_rc forwards other subprocess exits (e.g. 124 timeout, 99 zero-output guard). Triage treats a timeout or 99 remap as an API-class rc=1 transient. Note non-2 codes are not all API-class 1; mention 124/99 or point to .done/timing sidecars.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Exit-code story centers on rc=1 vs rc=2 as API vs launch-stack. A maintainer assumes every rc=1 with body+empty launcher-stderr is an API error; rare rc=1 from mktemp or other causes, or rc=124/99, does not match the story. Add a brief caveat and optionally mention companion files (e.g. .stderr) or other documented exit codes.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/dispatch-code-voters.md:32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Narrative implies voter1_rc is mainly 1 versus 2 without mentioning other forwarded exit codes from launch-claude-subprocess.sh A timeout 124 or empty-output guard 99 can be misclassified as API-class rc=1 Add a brief note listing 124 99 and rare pre-CLI exit 1 or point readers to the voter output sidecars and subprocess script for full taxonomy
- **Suggested revision**: Address the concern above.

