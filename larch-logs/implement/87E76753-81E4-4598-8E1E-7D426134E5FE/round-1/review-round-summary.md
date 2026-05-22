# Review Round 1

- Mode: `diff`
- Accepted findings: 6
- Rejected findings: 0
- Exonerated findings: 3
- Neutral findings: 0

## Accepted Findings

### FINDING_1: aggregate-findings revision traceability is too weak to catch wrong or fabricated bullets
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Suggested-revision traceability does not reliably tie each merged bullet to the text that actually justified it. Matching uses a six-word prefix over the union of all input blocks for a slot (not a corpus scoped to the merged finding), so a bullet can match unrelated prose from the same reviewer, and merged bullets can still look traceable when only a shared prefix is real. Very short normalized revisions take a `window < 2` path that effectively auto-passes without a meaningful substring scan, so empty, trivial, or lightly edited fabricated tails can slip through. The check is advisory (stderr warnings, no strict fail by default), so these false negatives can still reach downstream steps. There is also a dead `out_slots` assignment tied to this path, signaling incomplete wiring rather than a functional guard.
- **Suggested revision**: Scope candidate input text per merged finding (explicit source linkage or a conservative overlap heuristic with `Reviewer(s)` / merge correspondence), require full normalized substring (or full bullet) against that scoped corpus per plan, remove the unconditional short-revision success path in favor of substring match or explicit untraceable warnings, consider optional strict failure for untraceable bullets, and drop or use `out_slots` while adding harness cases that lock the behavior.


### FINDING_2: Unknown From-slot labels skip traceability with no warning
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Slot labels on `From` lines that are absent from the input slot map are skipped silently, so typos or parser drift never surface as an advisory signal even though traceability is meant to catch aggregator mistakes.
- **Suggested revision**: Emit a stderr warning (and optionally fail in strict modes) when a `From` slot label cannot be resolved against the known slot map instead of `continue` without signal.


### FINDING_3: Multi-line suggested-revision bullets are dropped from parsing and validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: The bullet parser only retains single-line `From` bullets, so honest wrapped verbatim revisions never enter `suggested_revisions_bullets` and bypass traceability checks entirely.
- **Suggested revision**: Implement continuation-line parsing for revision bullets, or tighten the orchestrator contract and docs so revisions are strictly single-line and rejected otherwise.


### FINDING_5: Coder-facing prompt under-specifies Justification and legacy singular revision fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The coder prompt no longer explicitly tells coders to read `Justification` as supplementary untrusted context alongside `Concern`, so justification-bearing ballots may be applied from partial context. It also emphasizes plural `Suggested revisions` without naming the legacy singular `Suggested revision`, weakening clarity during transition.
- **Suggested revision**: Restore explicit guidance to treat `Justification` as non-editable context with `Concern`, and mention the legacy singular field in the same guidance so older ballots remain unambiguous.


### FINDING_7: New traceability behavior lacks dedicated harness coverage in CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Parsing, matching, multi-bullet output, untraceable-bullet warnings, and legacy `Suggested revision` compatibility are not asserted in automated tests, so regressions in `aggregate-findings.sh` can ship silently.
- **Suggested revision**: Add `aggregate-findings` harness fixtures covering traceable multi-bullet output, untraceable bullets, unknown slots, short revisions, and legacy singular compatibility, asserting stderr warning paths where applicable.


### FINDING_8: `ship-pr` can clear `OOS_PENDING` on pr-create resume without the OOS disposition gate
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Pending out-of-scope disposition state may be cleared without running the mechanical disposition check if an orchestrator or manual resume path skips the skill block and still reaches `ship-pr`, weakening the wire-up between gate and pending-state writer.
- **Suggested revision**: Ensure a single authoritative clearing path for `OOS_PENDING` that cannot run without `oos-disposition-gate.sh` (or equivalent), or restructure so `ship-pr` cannot clear pending until the gate has run.


