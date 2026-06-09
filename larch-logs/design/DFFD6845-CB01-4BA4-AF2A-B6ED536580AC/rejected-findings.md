### [Plan Review] FINDING_3

### FINDING_3: Add verifiable Acceptance criteria
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan has a testing strategy but lacks a `## Acceptance` section with checkable completion criteria, including the required side-effect-free Fable probe and key deliverables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `## Acceptance` listing concrete checks: Step 2b produces `plan.txt` via drafter or eligible inline fallback; Voter 1 resolves `LARCH_VOTER_MODEL` default `claude-fable-5` through `launch-claude-review.sh` for `/design` and `/review`; fallback reviewer dispatches use `claude-sonnet-4-6` with no `claude-opus-4-7` pins; pre-merge stdin probe exit 0 for `claude --model claude-fable-5` (per verify-external-tool-invocations); `make test-launch-claude-drafter` and expanded `test-launch-claude-review` pass; `bash scripts/relevant-checks.sh` passes


### [Plan Review] FINDING_4

### FINDING_4: Constrain drafter tmpdir and repo-root grants
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned drafter launcher accepts write and read roots but does not explicitly require the existing design-tmpdir allowlist or constrain the repo-root read grant. A bad invocation could write outside allowed design session roots or expose an arbitrary directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add launch-claude-drafter.sh requirements to source scripts/lib-design-tmpdir.sh and run larch_design_tmpdir_validate before any write/read under --design-tmpdir; also constrain --repo-root to the actual current repo/worktree root used by /design, and add harness cases for rejected disallowed design tmpdirs and broad/non-repo read roots


### [Plan Review] FINDING_5

### FINDING_5: Make drafter CLI argv probe a committed source of truth
- **Reviewer(s)**: Cursor-dyn-cli-allowlist-contract
- **Severity**: important
- **Concern**: The planned drafter harness can pass with substring assertions against a stubbed CLI without proving production argv matches the native `claude` CLI shape, risking an unrecognized or ignored allowlist in real use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cli-allowlist-contract: Add one committed fixture (e.g. scripts/fixtures/claude-drafter-native-argv.json) populated by the mandatory pre-merge probe; launch-claude-drafter.sh must assemble CMD_JSON from it; test-launch-claude-drafter.sh must jq-compare the written CMD_JSON= line to the same fixture byte-for-byte (not grep fragments)


