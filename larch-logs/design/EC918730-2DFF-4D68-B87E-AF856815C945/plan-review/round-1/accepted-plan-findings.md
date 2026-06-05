### FINDING_1: Missing negative coverage for dynamic Codex prompt sidecars
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned dynamic Codex allow coverage does not add prompt-sidecar deny fixtures for dynamic Codex outputs, so an ordering regression could allow `.prompt` launcher prompts to be committed without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `dyn-api-contract-codex-output.txt.prompt` (and phased twin) to fixtures with `assert_not_file` mirroring the static Codex prompt checks


### FINDING_2: Missing `.cap-hit` coverage for dynamic Codex sidecars
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The test plan covers phased `.meta`/`.json` sidecars but not dynamic Codex `.cap-hit` sidecars, so an implementation could omit `.cap-hit` from the allow contract and still pass regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal .cap-hit fixture/assertion for the phased dynamic Codex case, and include unphased coverage too if no existing assertion covers it


### FINDING_3: Design-log raw-output boundary is overstated or unenforced
- **Reviewer(s)**: Codex-dyn-artifact-taxonomy, Codex-dyn-sidecar-boundary
- **Severity**: important
- **Concern**: The proposed design-log wording/fix appears to claim raw reviewer outputs are excluded, but the publisher still stages top-level design tmpdir files and plan-review dispatch writes raw Cursor/Codex outputs there. Either the policy must be scoped to `plan-review/round-N`, or the publisher and tests must actually exclude those top-level raw outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-artifact-taxonomy: Narrow the new comment/doc text to say plan-review/round-N excludes raw reviewer outputs and findings.md is canonical for that round snapshot. Do not claim all design-log raw reviewer outputs are excluded unless the plan also intentionally changes design-log-publish and its tests.
  - From Codex-dyn-sidecar-boundary: Either scope the plan wording to plan-review/round-N only, or add the real raw output patterns to design_artifact_excluded and pin them in scripts/test-design-log-publish.sh.


