### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-307; scripts/collect-agent-results.sh:1285-1289
- **Concern**: The proposed denylist omits structured reviewer sidecars (`*.txt.tsv` and Claude/unknown `*.txt.jsonl`).. Scenario: Plan-review collection writes sidecars such as `cursor-plan-arch-output.txt.tsv` and `claude-plan-generic-output.txt.jsonl`; after the proposed change the raw `.txt` transcript is skipped but these per-reviewer sidecars still publish at the top level, so the top-level gate still does not match the round-N canonical-artifact policy.
- **Proposed resolution**: Extend the new plan-review transcript branch and tests/docs to exclude the same reviewer-output prefixes with `.tsv` and `.jsonl` sidecars, or explicitly justify keeping them as canonical artifacts.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-309
- **Concern**: Top-level denylist omits structured reviewer sidecars. Scenario: `collect-agent-results.sh` writes `${REVIEWER_FILE}.tsv` for every successful Cursor/Codex plan-review slot (`scripts/collect-agent-results.sh:1285`); round-N excludes these via the allowlist catch-all but the proposed patterns only deny `*-output*.txt` plus `.meta`/`.json`/`.cap-hit`. Thousands of `cursor-plan-*-output.txt.tsv` / `codex-primary-plan-*-output.txt.tsv` files are already committed under `larch-logs/design/<run-id>/`, so publish still leaks per-reviewer raw findings after the PR while `findings.md` is documented as canonical
- **Proposed resolution**: Add the three plan-review prefixes with a `*-output*.txt.tsv` suffix to `design_artifact_excluded`, document them in `scripts/design-log-publish.md`, and pin with a top-level fixture plus deny-loop assertion in `scripts/test-design-log-publish.sh` (e.g. `codex-primary-plan-arch-output.txt.tsv`)

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:303-308
- **Concern**: Planned denylist omits real per-reviewer sidecars. Scenario: collect-agent-results.sh writes reviewer .tsv sidecars, dispatch writes .launch-stderr, and failed agents can write .stderr-tail; after the proposed .txt/.meta/.json/.cap-hit exclusions, files like cursor-plan-arch-output.txt.tsv or codex-primary-plan-arch-output.txt.stderr-tail still publish even though findings.md and voting-tally.md are canonical.
- **Proposed resolution**: Add the same cursor-plan-/codex-primary-plan-/claude-plan- anchored output*.txt exclusions for .tsv, .launch-stderr, and .stderr-tail, with deny fixtures for at least one static and one phased or dynamic basename.

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-308
- **Concern**: Plan omits generated .tsv and .launch-stderr plan-review sidecars from the new top-level deny branch. Scenario: collect-agent-results.sh writes ${REVIEWER_FILE}.tsv and dispatch writes ${output}.launch-stderr, so files like cursor-plan-arch-output.txt.tsv and cursor-plan-arch-output.txt.launch-stderr still publish after the raw .txt transcript is excluded
- **Proposed resolution**: Add narrowly anchored exclusions for the same plan-review prefixes with .txt.tsv and .txt.launch-stderr suffixes, plus matching fixtures/docs if the plan-review top level should only keep canonical aggregates

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:294-306; scripts/collect-agent-results.sh:1285
- **Concern**: The proposed transcript denylist omits structured reviewer sidecars such as cursor-plan-*-output*.txt.tsv / codex-primary-plan-*-output*.txt.tsv and Claude generic .tsv/.jsonl sidecars. Scenario: The collector writes these beside successful plan-review outputs; because design-log-publish is default-allow for top-level files, the raw .txt would be skipped but per-reviewer structured findings would still be committed at larch-logs/design/<run-id>/, leaving non-canonical plan-review output at the top level
- **Proposed resolution**: Add anchored deny patterns for those structured sidecars and add matching fixtures/assertions/docs; keep patterns prefix-scoped so findings-classification.tsv and other canonical TSVs still publish

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/scripts/dispatch-plan-review-panel.sh:97-124; scripts/launch-claude-review.sh:217-218
- **Concern**: The plan adds claude-plan .meta .json and .cap-hit exclusions even though the generic Claude plan reviewer is launched through launch-claude-review.sh, which only writes .done here plus caller-captured .launch-stderr, not those launch-review.sh sidecars. Scenario: This reintroduces the same dead-pattern/fictional-fixture class the issue explicitly says to remove, adding unnecessary denylist complexity in a SIMPLE lane
- **Proposed resolution**: Keep claude-plan-*-output*.txt for the real transcript, but limit .meta .json and .cap-hit sidecar exclusions and tests to the cursor-plan and codex-primary-plan producers unless a real Claude producer for those suffixes is identified

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-producer-name-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:1285-1292; skills/design/scripts/dispatch-plan-review-panel.sh:136-138; scripts/test-design-log-publish.sh:22-27
- **Concern**: Proposed deny patterns omit structured reviewer `.tsv` sidecars (`<reviewer-output>.tsv`). Scenario: After the PR, `cursor-plan-*-output.txt.tsv` and `codex-primary-plan-*-output.txt.tsv` (and `claude-plan-generic-output.txt.tsv` from both-down dispatch) still pass `design_artifact_excluded` and get copied to `larch-logs/design/<run-id>/`; committed logs already contain thousands of these files
- **Proposed resolution**: Add `cursor-plan-*-output*.txt.tsv`, `codex-primary-plan-*-output*.txt.tsv`, and `claude-plan-*-output*.txt.tsv` to the new `design_artifact_excluded` branch (or one equivalent alternation) and pin at least one fixture per prefix in `scripts/test-design-log-publish.sh`

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-producer-name-audit
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:303-308; scripts/dispatch-with-waterfall.sh:223-255; skills/design/scripts/dispatch-plan-review-panel.sh:97-124; scripts/run-external-agent.sh:324-342; scripts/launch-claude-review.sh:200-218
- **Concern**: The proposed exclusion set misses producer-emitted .launch-stderr and .stderr-tail sidecars for the same plan-review output basenames. Scenario: Even after excluding cursor-plan-*-output*.txt, codex-primary-plan-*-output*.txt, claude-plan-*-output*.txt, and .meta/.json/.cap-hit sidecars, design-log publish will still stage cursor-plan-arch-output.txt.launch-stderr or claude-plan-generic-output.txt.stderr-tail at the top level because the current denylist lacks those suffixes
- **Proposed resolution**: Add prefix-anchored exclusions for *-output*.txt.launch-stderr and *-output*.txt.stderr-tail for the same three plan-review prefixes, plus matching test fixtures; keep unrelated artifacts untouched

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-test-fixture-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:24
- **Concern**: The planned `codex-primary-plan-arch-output.txt.json` fixture appears fictional for the current producer path: codex plan slots emit `codex-primary-plan-<arch>-output.txt` in `skills/design/scripts/dispatch-plan-review-panel.sh:191-196`, while the `.json` sidecar copy is produced by the Cursor launcher path in `scripts/launch-review.sh:1130-1150`, not the Codex path.. Scenario: This would replace one fictional fixture with another, so the test could pass without proving a real `.json` sidecar producer basename is denied.
- **Proposed resolution**: Use a real `.json` fixture basename such as `cursor-plan-arch-output.txt.json` for the `.json` sidecar assertion, or document and omit the codex `.json` fixture if that deny pattern is only defensive.
