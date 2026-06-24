## Goal
Implement issue #5270: [IMPLEMENTING] md-to-py-V: slim plan-review.md (drop rendered-string dupes + dead loop prose).

## Implementation Plan
## Plan

## Approach

- Surgical docs-only reduction to `skills/design/references/plan-review.md` and four ancillary files.
- No Python behavior changes.
- Replace Competition notice blockquote and Voter prompts section with one-line pointers to the runtime render verbs.
- Compress three loop-internal sections (`## Collecting External Reviewer Results`, `## Voting Panel launch-order and tally`, `## Finalize Plan Review` prose) to short notes, keeping the semantic-dedup rule, voter line format, and byte-preserved FINDING_N / OOS templates.
- Also compress `## Ballot file handling` to remove stale Write-tool instruction (loop-internal in loop mode); keep MAV-relevant ballot interpretation fact.
- Update Consumer / Contract / When-to-load preamble to accurately reflect what the orchestrator consumes.
- Update SKILL.md Step 3 normative-source description to drop `the Competition notice blockquote` and `reviewer prompts` and `ballot handling`.
- Update `review-acceptance-rubric.md`, `oos-acceptance-rubric.md`, and `voting-protocol.md` sync-note comment to remove stale plan-review.md claims.

## Files to modify/create

### UPDATED: skills/design/references/plan-review.md

- Revise Consumer / Contract / When-to-load preamble to list only orchestrator-consumed surfaces (dedup rules, templates, MAV, post-driver interpretation).
- Replace `## Competition notice` blockquote with compact pointer: plan-review prompts rendered by `python/cli.py render plan-review`; competition scoring in `voting-protocol.md`; competition notice text not part of plan-review output.
- Keep `Style requirements for finding text and OOS Descriptions: <READABILITY_STYLE>.` unchanged.
- In `## Claude Code Reviewer Subagent archetype`, remove "Append the Competition notice blockquote above" instruction; replace with note that competition notice is not part of plan-review prompt output.
- Replace `## Voter prompts` long prompt strings with pointer to `python/cli.py render voter`.
- Compress `## Ballot file handling`: state rebuild / proposer-map write / validation / rewrite are loop-internal; no orchestrator Write-tool path in loop mode; MAV obtains BALLOT_PATH from wrapper, not from orchestrator ballot authoring.
- Compress `## Collecting External Reviewer Results`: loop-internal note + keep semantic dedup rules (in-scope, OOS, in-scope-wins).
- Compress `## Voting Panel launch-order and tally`: loop-internal note + keep voter line format block + point thresholds/scoreboard at `voting-protocol.md` + post-driver tally interpretation guidance.
- Compress `## Finalize Plan Review` prose: loop-internal note + post-driver artifact reading guidance + keep byte-preserved FINDING_N and OOS templates unchanged.
- Do not edit: `Track Rejected Plan Review Findings`, `Single-pass review`, `Deferred main-agent adjudication`, `Related: decomposition panel`.

### UPDATED: skills/design/SKILL.md

- Step 3 mandatory-read sentence: remove `the Competition notice blockquote`, `reviewer prompts`, and `ballot handling` from the plan-review.md normative-source list; cite `python/cli.py render plan-review` and `python/cli.py render voter` as prompt-body authorities.

### UPDATED: skills/shared/review-acceptance-rubric.md

- Update `plan-review.md` pointer: no longer embeds voter instructions + competition notice; points to runtime renderers; keeps structural plan-review contracts.

### UPDATED: skills/shared/oos-acceptance-rubric.md

- Update `plan-review.md` pointer: no longer embeds OOS voter instructions; points to `python/cli.py render voter`.

### UPDATED: skills/shared/voting-protocol.md

- Revise HTML sync-note comment (line 81): drop `plan-review.md (Voter 1)` from sync list; name `python/cli.py render voter` as canonical runtime emitter; note OOS paragraph parity across remaining MAV surfaces is manual; drop retired harness claim.

## Edge cases

- Byte-preserved templates (FINDING_N, OOS) stay exactly as-is.
- Semantic dedup rules kept verbatim or near-verbatim.
- `<READABILITY_STYLE>` line preserved (lint-enforced).
- `design-step3-mav.sh --phase pre` string kept in Deferred MAV section (test-pinned).
- MAV section untouched.

## Testing strategy

- `make test-prompt-template-invariants`
- `make test-design-step3-mav`
- `make test-step3-orchestrator-fence`
- `make test-effort-prose`
- `make lint`

## Acceptance

Plan review completed 4 rounds with zero findings accepted (degraded panel). Gate C approved.

diff_lines: 163

## Test plan
(no test plan section in plan-file)
