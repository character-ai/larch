### FINDING_1: Full `.stderr` plan-review sidecars can still be published
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The proposed design-log-publish denylist excludes some transcript and sidecar forms, but omits full `.stderr` sidecars for plan-review outputs. Claude generic review and phase3 Claude fallback can write `${output}.stderr`, which could still be staged into committed `larch-logs/design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add .stderr arms for cursor-plan-*-output*.txt.stderr, codex-primary-plan-*-output*.txt.stderr, and claude-plan-*-output*.txt.stderr; add matching publish tests and docs entries

### FINDING_2: SECURITY.md does not document the new publication boundary
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan changes the security-relevant design-log publication boundary by keeping raw plan-review reviewer transcripts and sidecars out of committed logs, but does not update `SECURITY.md` as required by repository instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a narrow SECURITY.md note near the raw events exclusion documenting that design-log-publish also excludes plan-review raw reviewer outputs and listed sidecars, with findings.md/voting-tally.md as canonical artifacts
  - From Codex-Pragmatic: Add one concise SECURITY.md sentence near the raw event-stream note documenting that design-log-publish keeps raw plan-review reviewer transcripts and sidecars session-local while publishing canonical findings and voting artifacts only

### FINDING_3: Publish tests do not cover all planned sidecar exclusions
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-fixture-assertion-gap, Codex-dyn-fixture-assertion-gap
- **Severity**: important
- **Concern**: The planned `scripts/test-design-log-publish.sh` fixtures and assertions omit several sidecar names that the exclusion contract requires. An implementation could miss or typo denylist arms for Claude `.jsonl`, cursor/codex `.stderr-tail`, `.launch-stderr`, `.meta`, or `.cap-hit` files while still passing the proposed tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add deny-list fixtures and assertions for claude-plan-generic-output.txt.jsonl and at least one cursor/codex .stderr-tail phased output such as codex-primary-plan-arch-output-phase3.txt.stderr-tail
  - From Cursor-dyn-fixture-assertion-gap: Add one setup+deny-loop pair per missing producer-backed suffix: `codex-primary-plan-arch-output.txt.launch-stderr`, `codex-primary-plan-arch-output.txt.stderr-tail`, `cursor-plan-arch-output.txt.meta`, `cursor-plan-arch-output.txt.cap-hit`, `cursor-plan-arch-output.txt.stderr-tail` (keep existing cursor `.json`/`.tsv`/`.launch-stderr` and codex `.meta`/`.cap-hit`/`.tsv` entries)
  - From Codex-dyn-fixture-assertion-gap: Add claude-plan-generic-output.txt.jsonl to both the setup fixture block and the deny-list assertion loop

### FINDING_4: Codex `.json` deny pattern is producer-dead
- **Reviewer(s)**: Codex-dyn-producer-filename-parity, Codex-dyn-sidecar-suffix-scope
- **Severity**: important
- **Concern**: The proposed sidecar globs apply `.json` to both cursor and codex plan-review outputs, but only Cursor writes `${OUTPUT}.json`; Codex writes `.events.jsonl` plus other sidecars. A `codex-primary-plan-*-output*.txt.json` deny pattern would be dead and contradict the producer-backed minimum-change goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-producer-filename-parity: Split the proposed sidecar globs so .json applies only to cursor-plan-*-output*.txt.json; keep codex-primary-plan-* to .meta .cap-hit .tsv .launch-stderr and .stderr-tail, with .events.jsonl left to the existing suffix glob
  - From Codex-dyn-sidecar-suffix-scope: Split the sidecar list so .json applies only to cursor-plan-*-output*.txt.json; keep codex-primary-plan-* to .meta .cap-hit .tsv .launch-stderr and .stderr-tail.
