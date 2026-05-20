# Review Round 2

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 6
- Exonerated findings: 6
- Neutral findings: 2

## Accepted Findings

### FINDING_10: code-quality: scripts/auto-resolve-changelog.md:1-24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documentation describes Markdown-only merge rules while the script implements RST and bare-CHANGELOG heuristics. Operators misread why auto-resolve skipped or how entries were ordered. Update the sibling doc to cover RST, basename rules, and exit-1 deferral cases.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/auto-resolve-changelog.sh:130-148
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Extensionless CHANGELOG paths fall back to RST parsing when Markdown ## first headings do not match on both sides. A Markdown CHANGELOG without a shared first ## line can be parsed as RST; rare false RST title detection could merge incorrectly instead of exiting 1. Narrow heuristics (e.g. treat bare CHANGELOG as Markdown-only when lines match /^## / anywhere) or default to exit 1 unless .rst or explicit shared ## match.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: scripts/auto-resolve-changelog.sh:148-188
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tail after first ## is always taken from stage :2: only; stage :3: tail can differ. Rebase conflict only in a released section while ## Unreleased matches on both sides: script exits 0, writes upstream tail, branch edits to older releases vanish while the path is staged resolved. Compare post-first-section spans of :2: vs :3: (or refuse) and exit 1 when they differ so the vendor does a real merge.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/auto-resolve-changelog.sh:191-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] RST merge repeats upstream-only tail after first section. Same class of bug for RST-shaped logs: matching first title but divergent later sections yields silent loss of :3: content. Guard tail equality or document and enforce upstream-wins-only for released sections with explicit opt-in.
- **Suggested revision**: Address the concern above.


