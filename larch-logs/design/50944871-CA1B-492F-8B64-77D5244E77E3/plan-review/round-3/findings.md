### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:202-218
- **Concern**: Proposed denylist omits full .stderr sidecars for plan-review outputs. Scenario: Claude generic review and phase3 Claude fallback write ${output}.stderr; the proposed design-log-publish branch skips transcripts, .launch-stderr, and .stderr-tail but would still stage the full stderr sidecar into larch-logs/design
- **Proposed resolution**: Add .stderr arms for cursor-plan-*-output*.txt.stderr, codex-primary-plan-*-output*.txt.stderr, and claude-plan-*-output*.txt.stderr; add matching publish tests and docs entries

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:39-48
- **Concern**: Plan changes a committed run-log publication boundary but omits SECURITY.md. Scenario: The repo instruction requires SECURITY.md updates for security-relevant behavior changes; excluding raw plan-review reviewer transcripts and sidecars changes what potentially prompt-bearing reviewer output can reach committed larch-logs
- **Proposed resolution**: Add a narrow SECURITY.md note near the raw events exclusion documenting that design-log-publish also excludes plan-review raw reviewer outputs and listed sidecars, with findings.md/voting-tally.md as canonical artifacts

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:39-42
- **Concern**: Plan omits SECURITY.md update for changed design-log publication boundary. Scenario: After the PR, SECURITY.md still documents raw event-stream exclusion but not the new raw plan-review transcript exclusion, despite AGENTS.md requiring SECURITY.md updates for security-relevant behavior changes
- **Proposed resolution**: Add one concise SECURITY.md sentence near the raw event-stream note documenting that design-log-publish keeps raw plan-review reviewer transcripts and sidecars session-local while publishing canonical findings and voting artifacts only

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh (planned fixtures from plan.txt:13-26)
- **Concern**: Planned publish test omits sidecars required by the new exclusion contract. Scenario: The plan requires excluding claude-plan-*-output*.txt.jsonl and cursor/codex .stderr-tail sidecars, but the fixture list does not assert those cases; an implementation could pass the planned tests while leaking claude-plan-generic-output.txt.jsonl or codex-primary-plan-arch-output-phase3.txt.stderr-tail into larch-logs/design/<run-id>/
- **Proposed resolution**: Add deny-list fixtures and assertions for claude-plan-generic-output.txt.jsonl and at least one cursor/codex .stderr-tail phased output such as codex-primary-plan-arch-output-phase3.txt.stderr-tail

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-producer-filename-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11-14; skills/design/scripts/dispatch-plan-review-panel.sh:181-196,214-228; scripts/launch-review.sh:547-550,1129-1159
- **Concern**: Plan groups .json sidecars under both cursor-plan-* and codex-primary-plan-* even though only Cursor writes ${OUTPUT}.json; Codex writes ${OUTPUT}.events.jsonl instead. Scenario: Codex-primary .json deny arm would be a new dead pattern, contradicting the producer-backed minimum-change goal and the plan's own test note to avoid codex-primary-plan-arch-output.txt.json
- **Proposed resolution**: Split the proposed sidecar globs so .json applies only to cursor-plan-*-output*.txt.json; keep codex-primary-plan-* to .meta .cap-hit .tsv .launch-stderr and .stderr-tail, with .events.jsonl left to the existing suffix glob

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-sidecar-suffix-scope
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/design-log-publish.sh:294-308; skills/design/scripts/dispatch-plan-review-panel.sh:190-196; scripts/launch-review.sh:547-650; scripts/launch-review.sh:1129-1150
- **Concern**: Proposed cursor/codex sidecar branch still includes a dead codex-primary .json arm. Scenario: Plan-review Codex outputs are named codex-primary-plan-*-output.txt, but the Codex launcher writes .events.jsonl and .meta and the collector writes .tsv; only the Cursor path copies raw JSON to ${OUTPUT}.json. A codex-primary-plan-*-output*.txt.json deny/doc pattern would reintroduce a no-producer suffix.
- **Proposed resolution**: Split the sidecar list so .json applies only to cursor-plan-*-output*.txt.json; keep codex-primary-plan-* to .meta .cap-hit .tsv .launch-stderr and .stderr-tail.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-fixture-assertion-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:460-520
- **Concern**: Plan deny-list adds cursor/codex `.stderr-tail` and `.launch-stderr` (plan.txt:11-13) but happy-path fixture inventory omits paired setup+assert basenames for those suffixes on the codex arm and for `.meta`/`.cap-hit`/`.stderr-tail` on the cursor arm. Scenario: Implementer can typo or drop one vendor glob arm; harness still passes because only `cursor-plan-arch-output.txt.launch-stderr`, `codex-primary-plan-arch-output.txt.meta`, and `codex-primary-plan-arch-output.txt.cap-hit` are listed while committed runs also emit `codex-primary-plan-arch-output.txt.launch-stderr`, `codex-primary-plan-arch-output.txt.stderr-tail`, `cursor-plan-arch-output.txt.meta`, `cursor-plan-arch-output.txt.cap-hit`, and `cursor-plan-arch-output.txt.stderr-tail`
- **Proposed resolution**: Add one setup+deny-loop pair per missing producer-backed suffix: `codex-primary-plan-arch-output.txt.launch-stderr`, `codex-primary-plan-arch-output.txt.stderr-tail`, `cursor-plan-arch-output.txt.meta`, `cursor-plan-arch-output.txt.cap-hit`, `cursor-plan-arch-output.txt.stderr-tail` (keep existing cursor `.json`/`.tsv`/`.launch-stderr` and codex `.meta`/`.cap-hit`/`.tsv` entries)

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-fixture-assertion-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:14,25-26; scripts/collect-agent-results.sh:1284-1289
- **Concern**: Plan adds a claude-plan .jsonl deny pattern but omits the matching test fixture/assertion. Scenario: collect-agent-results writes unknown-tool structured sidecars as REVIEWER_FILE.jsonl, so claude-plan-generic-output.txt.jsonl can leak if the implementation misses that arm and the proposed test still passes
- **Proposed resolution**: Add claude-plan-generic-output.txt.jsonl to both the setup fixture block and the deny-list assertion loop
