### [Plan Review] FINDING_7

### FINDING_7: Fixed script-rendered operator text is unmapped
- **Reviewer(s)**: Cursor-dyn-amendment-coverage, Codex-dyn-amendment-coverage
- **Severity**: latent
- **Concern**: Step 5 and Gate C/Step 3 preview prose are rendered by scripts such as `render-final-summary.sh` and `emit-design-plan-preview.sh`, but the plan names only composed-plan surfaces and does not amend or explicitly exempt these fixed operator-visible outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-amendment-coverage: Either explicitly exempt fixed structured script outputs from the readability lint contract, or add these scripts to the manifest with a narrow check that their operator-facing prose stays covered by the shared style source
  - From Codex-dyn-amendment-coverage: Either explicitly exempt fixed structured script outputs from the readability lint contract, or add these scripts to the manifest with a narrow check that their operator-facing prose stays covered by the shared style source


