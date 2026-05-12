## Goal
Add `--run-id <ID>` to the Flags/Arguments section of all 22 plugin-exported skill SKILL.md files. No new behavior wiring (deferred to #1438).

## Implementation Plan
Mechanical one-line addition per skill SKILL.md flags section. Standard wording:
`- \`--run-id <ID>\`: Optional run identifier; when set, used as the run ID for this invocation instead of the auto-generated one. Default: empty (auto-generate).`

22 files: alias, block-issue, cleanup, compress-skill, create-skill, design, fix-issue, im, imaq, implement, imq, issue, report-tokens, research, review, set-up-forked-open-source-repo, show-skill, simplify-skill, skill-evolver, test-issue, umbrella, upgrade-larch.

## Test plan
Run `/relevant-checks` after all edits (pre-commit on modified files + agent-lint on full repo).
