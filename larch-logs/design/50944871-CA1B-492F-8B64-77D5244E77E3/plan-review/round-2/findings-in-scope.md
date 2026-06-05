### FINDING_1: Generic Claude plan-review sidecars remain publishable
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-producer-names, Codex-dyn-producer-names, Cursor-dyn-artifact-policy, Codex-dyn-artifact-policy, Codex-dyn-fixture-realism
- **Severity**: important
- **Concern**: The proposed denylist treats `claude-plan-*` as transcript-only and/or claims `.launch-stderr` is already excluded, but the both-externals-down generic Claude path can write sidecars such as `claude-plan-generic-output.txt.launch-stderr`, `.tsv`, `.stderr-tail`, and possibly collector `.jsonl`. Those artifacts would still pass the default-allow top-level design-log staging path, leaving raw reviewer outputs committed beside canonical outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add claude-plan-*-output*.txt.tsv plus claude-plan-*-output*.txt.launch-stderr (and .stderr-tail if failures are in scope) to design_artifact_excluded and test-design-log-publish.sh deny fixtures; correct the plan prose that says launch-stderr is already covered
  - From Codex-Arch: Extend the new claude-plan exclusion to actual generic sidecars such as claude-plan-*-output*.txt.tsv and claude-plan-*-output*.txt.launch-stderr, and add matching test-design-log-publish fixtures/assertions
  - From Codex-Edge: Include the real claude-plan-*-output*.txt sidecar suffixes in the new exclusion branch and add fixtures for at least .launch-stderr plus the structured sidecar path used by the generic reviewer.
  - From Codex-Innovation: Extend the new design_artifact_excluded branch, docs, and test fixtures to exclude at least claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv. Include claude .jsonl too if keeping collector-supported generic structured sidecars covered.
  - From Codex-Pragmatic: Add claude-plan-*-output*.txt.launch-stderr to the new deny branch and add a test fixture asserting claude-plan-generic-output.txt.launch-stderr is absent
  - From Cursor-Requirements, Codex-Requirements: Add claude-plan-*-output*.txt.tsv / .launch-stderr / .stderr-tail (or equivalent anchored arms) to design_artifact_excluded, document in design-log-publish.md, and pin with claude-plan-generic-output.txt.tsv and .launch-stderr fixtures in test-design-log-publish.sh
  - From Cursor-dyn-producer-names: Extend top-level deny patterns (and test-design-log-publish.sh fixtures/assertions) to exclude claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv; drop the incorrect already-covered-by-existing-globs claim in plan.txt
  - From Codex-dyn-producer-names: Add only the producer-backed claude-plan sidecar globs to the proposed branch and fixtures: claude-plan-*-output*.txt.launch-stderr, .stderr-tail, .tsv, and .jsonl
  - From Cursor-dyn-artifact-policy: Add claude-plan-*-output*.txt.launch-stderr and claude-plan-*-output*.txt.tsv (and .stderr-tail if produced) to the new design_artifact_excluded branch; extend test-design-log-publish.sh deny assertions; correct design-log-publish.md and lib-design-round-artifacts.md prose that says launch-stderr is already covered
  - From Codex-dyn-artifact-policy: Extend the proposed top-level plan-review exclusion, docs, and tests to cover real Claude generic sidecars at minimum claude-plan-*-output*.txt.launch-stderr, .stderr-tail, and the structured .tsv/.jsonl sidecar shape, or remove the false transcript-only claim.
  - From Codex-dyn-fixture-realism: Extend the planned branch and fixtures/assertions to exclude claude-plan-*-output*.txt.tsv and claude-plan-*-output*.txt.launch-stderr; include stderr-tail too if failed Claude reviewer tails are in scope

### FINDING_2: Cursor/codex `.jsonl` exclusions lack producer evidence
- **Reviewer(s)**: Codex-dyn-producer-names
- **Severity**: latent
- **Concern**: The proposed `cursor-plan-*` and `codex-primary-plan-*` `.jsonl` exclusions appear to add dead denylist scope: current structured validation writes `.tsv` for cursor/codex, while Codex JSONL uses `.events.jsonl`, already covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-producer-names: Drop cursor/codex .jsonl from the new sidecar list unless a real producer is added; keep existing *.events.jsonl coverage and use .jsonl only for the claude/unknown collector path if covered

### FINDING_3: Producer-name exclusions may unintentionally affect render-cache staging
- **Reviewer(s)**: Codex-dyn-artifact-policy
- **Severity**: latent
- **Concern**: Adding producer-name transcript patterns inside `design_artifact_excluded` changes both top-level staging and render-cache staging, despite the plan being motivated by top-level plan-review artifacts and render-cache documentation describing only suffix-deny behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-artifact-policy: Keep the new producer-name transcript exclusion on the maxdepth-1 top-level staging path, or pass a context flag so render-cache keeps its current suffix-only exclusion contract unless the plan explicitly documents and tests that broader policy change.

### FINDING_4: Cursor `.tsv` sidecar fixture is missing
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: important
- **Concern**: Planned deny fixtures cover codex `.tsv` sidecars but omit `cursor-plan-arch-output.txt.tsv`, so an implementation could typo or omit the cursor sidecar alternation while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fixture-realism: Add cursor-plan-arch-output.txt.tsv to the fixture-creation block and deny-list assertion loop alongside codex-primary-plan-arch-output.txt.tsv

### FINDING_5: Cursor phased transcript fixture is missing
- **Reviewer(s)**: Cursor-dyn-fixture-realism
- **Severity**: nit
- **Concern**: Phased transcript deny coverage pins only the codex phase-2 artifact, even though `cursor-plan-arch-output-phase2.txt` is also a real top-level producer/leak shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-fixture-realism: Add cursor-plan-arch-output-phase2.txt to the new transcript fixtures and deny-loop assertions
