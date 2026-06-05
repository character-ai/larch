### FINDING_1: Plan-review denylist misses real top-level reviewer sidecars
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-producer-name-audit, Codex-dyn-producer-name-audit
- **Severity**: important
- **Concern**: The proposed top-level plan-review transcript denylist excludes raw `*-output*.txt` transcripts but still allows real sidecars for the same reviewer basenames, including structured `.txt.tsv` / `.txt.jsonl` files and producer stderr sidecars such as `.txt.launch-stderr` / `.txt.stderr-tail`. Because top-level design artifacts are default-allow, these per-reviewer non-canonical artifacts can still publish beside canonical aggregates like `findings.md` and `voting-tally.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the new plan-review transcript branch and tests/docs to exclude the same reviewer-output prefixes with `.tsv` and `.jsonl` sidecars, or explicitly justify keeping them as canonical artifacts.
  - From Cursor-Edge: Add the three plan-review prefixes with a `*-output*.txt.tsv` suffix to `design_artifact_excluded`, document them in `scripts/design-log-publish.md`, and pin with a top-level fixture plus deny-loop assertion in `scripts/test-design-log-publish.sh` (e.g. `codex-primary-plan-arch-output.txt.tsv`)
  - From Codex-Edge: Add the same cursor-plan-/codex-primary-plan-/claude-plan- anchored output*.txt exclusions for .tsv, .launch-stderr, and .stderr-tail, with deny fixtures for at least one static and one phased or dynamic basename.
  - From Codex-Innovation: Add narrowly anchored exclusions for the same plan-review prefixes with .txt.tsv and .txt.launch-stderr suffixes, plus matching fixtures/docs if the plan-review top level should only keep canonical aggregates
  - From Codex-Pragmatic: Add anchored deny patterns for those structured sidecars and add matching fixtures/assertions/docs; keep patterns prefix-scoped so findings-classification.tsv and other canonical TSVs still publish
  - From Cursor-dyn-producer-name-audit: Add `cursor-plan-*-output*.txt.tsv`, `codex-primary-plan-*-output*.txt.tsv`, and `claude-plan-*-output*.txt.tsv` to the new `design_artifact_excluded` branch (or one equivalent alternation) and pin at least one fixture per prefix in `scripts/test-design-log-publish.sh`
  - From Codex-dyn-producer-name-audit: Add prefix-anchored exclusions for *-output*.txt.launch-stderr and *-output*.txt.stderr-tail for the same three plan-review prefixes, plus matching test fixtures; keep unrelated artifacts untouched


### FINDING_2: Claude `.meta` / `.json` / `.cap-hit` exclusions appear to be dead patterns
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds Claude plan-review `.meta`, `.json`, and `.cap-hit` exclusions even though the generic Claude plan reviewer path appears to produce only `.done` plus caller-captured `.launch-stderr`, reintroducing fictional/dead denylist patterns and unnecessary SIMPLE-lane complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Keep claude-plan-*-output*.txt for the real transcript, but limit .meta .json and .cap-hit sidecar exclusions and tests to the cursor-plan and codex-primary-plan producers unless a real Claude producer for those suffixes is identified


### FINDING_3: Planned Codex `.json` fixture does not match a real producer basename
- **Reviewer(s)**: Codex-dyn-test-fixture-gap
- **Severity**: important
- **Concern**: The planned `codex-primary-plan-arch-output.txt.json` fixture appears fictional for the current producer path because Codex plan slots emit the `.txt` output while the `.json` sidecar copy comes from the Cursor launcher path. This could let tests pass without proving that a real `.json` sidecar basename is denied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-fixture-gap: Use a real `.json` fixture basename such as `cursor-plan-arch-output.txt.json` for the `.json` sidecar assertion, or document and omit the codex `.json` fixture if that deny pattern is only defensive.

