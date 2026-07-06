# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: architectural knowledge requiredness is not exported into self-validation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The implementer-side `jq` self-validation checks `env.ARCHITECTURAL_KNOWLEDGE_REQUIRED`, but the snapshot value is only written to `step2-architectural-knowledge.env`, not exported or passed into the `jq` invocation. That lets required acknowledgments slip through prompt-side validation and defer enforcement to dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Load snapshot before jq (source .env) or export ARCHITECTURAL_KNOWLEDGE_REQUIRED in launch-codex-implement / launch-cursor-implement when writing the snapshot
  - From cursor-specialist-edge-cases: Export required-ness into the implementer shell before jq (or copy snapshot into the Codex session dir) and drive jq via --arg; add a regression that jq fails when required and acknowledgment is absent
  - From codex-specialist-edge-cases: Add a concrete prelude that reads step2-architectural-knowledge.env and exports or passes the value to jq before validating complete and needs_qa.
  - From cursor-specialist-testing: Export ARCHITECTURAL_KNOWLEDGE_REQUIRED from step2-architectural-knowledge.env before jq (pin in scripts/test-prompt-template-invariants.sh) or set it in the implementer subprocess env in _ci_launcher; add a test covering jq with and without the env var.
  - From codex-specialist-testing: Change the self-validation snippet to load or prefix the snapshot value before `jq`, for example from `$IMPLEMENT_TMPDIR/step2-architectural-knowledge.env`, and add a prompt-template test that the shown command actually requires the acknowledgment when the snapshot is true.


### FINDING_4: snapshot write follows planted symlinks
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `_write_architectural_knowledge_snapshot` writes through `Path.write_text`, so a symlink planted at the snapshot path can redirect the write and truncate an arbitrary same-user file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Write the snapshot through larch.io.atomic_write with nofollow=True or an equivalent helper that rejects destination and temp symlinks before replace.
