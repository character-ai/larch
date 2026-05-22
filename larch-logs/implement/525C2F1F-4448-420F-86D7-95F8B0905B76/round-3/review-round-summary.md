# Review Round 3

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 0
- Exonerated findings: 5
- Neutral findings: 1

## Accepted Findings

### FINDING_1: Bash 3.2 incompatibility in OOS shared include
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `declare -A` in `oos-disposition-shared.inc.bash` is Bash 4+; default macOS Bash 3.2 errors when the include is sourced, breaking the disposition gate and audit paths that depend on rejection counting. Static `lint-bash32` may not cover `*.inc.bash` if only `*.sh` is scanned, so the regression can slip past CI.
- **Suggested revision**: Replace associative-array deduping with Bash 3.2-safe counting (for example `sort -u` / `wc -l`), and/or extend `lint-bash32` globs to include dotted `.inc.bash` helpers; verify under Bash 3.2.


### FINDING_4: Inline-triage hits double-counted across audit artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `_audit_oos_inline_triage_hits` aggregates inline-triage counts from more than one artifact; duplicate lines across `codex-commit-message.txt` and `session-transcript.jsonl` can inflate `inline_count`, yielding audit pass skew versus what the gate would enforce on a single canonical source.
- **Suggested revision**: Deduplicate across sources or define a single canonical artifact and precedence rules in docs and implementation.


### FINDING_6: Accepted-markdown path errors can zero out obligations and pass
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Wrong CSV paths or missing `oos-accepted` files can yield `non_sec=0` and an unconditional pass, silently clearing obligations while the OOS pipeline assumed those inputs existed.
- **Suggested revision**: Fail closed when disposition is active but expected accepted files are missing or unreadable, or validate paths before treating the obligation set as empty.


### FINDING_7: `jq` errors in rejected-marker counting can abort whole audit under `set -e`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: A corrupt `oos-issues.ndjson` line can cause `jq` failure that aborts `audit-scan-run.sh` mid-registry, preventing later scan emissions.
- **Suggested revision**: Isolate parsing for this scan (treat bad lines as skip/partial with explicit reporting) without failing the entire run.


