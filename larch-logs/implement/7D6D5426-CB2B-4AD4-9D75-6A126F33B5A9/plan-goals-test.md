## Goal
Implement issue #6161: [IMPLEMENTING] md-to-py-XII: density-pass aggregator generated prompt scaffolds (design and implement).

## Implementation Plan
## Plan

## Approach

Drafted from direct codebase inspection. `approach-synthesis.txt` is `NO_SKETCHES`, so this plan does not rely on planning-panel agreement.

`python/larch/review/review_aggregate.py` builds the aggregator prompt for **both** `/design` (plan-review aggregation, `--input-mode plan`) and `/implement`/`/review` (code-review aggregation, `--input-mode code`). There is no separate design-side aggregator prompt builder; `aggregate_findings()` is the single shared "generated wrapper" the issue refers to. It wraps the already-compressed `agents/orchestrator-aggregator.md` body with additional generated scaffold text. This plan shortens that fixed wrapper text without touching the agent file, the output grammar, or the byte-measurement plumbing.

Three fixed (non-payload, non-findings) text spans get shorter wording, each preserving its full meaning:

1. **Section heading** before the raw findings (`_"## Raw reviewer findings (input)"_` → `_"## Reviewer findings"_`). Emitted on every aggregator dispatch, in both skills.
2. **Required-reviewer-slots rules block** inside `_required_reviewer_slots_prompt_section()`: the "Apply these rules to the merged output:" line plus its 4 bullets. Emitted whenever the input has at least one reviewer slot (virtually every real aggregation dispatch), in both skills. The exact substrings existing tests assert on (`"## Required reviewer slots (validator inventory)"`, `"must appear in at least one"`, `"Use only slots from this inventory"`) are preserved verbatim, so no test changes are needed.
3. **Scope-reduction notice** appended only in plan mode when scope-reduction findings were withheld (`tagged_count > 0`). Shortened to the same effect.

Explicitly **out of scope** (left byte-identical), with rationale:

- `agents/orchestrator-aggregator.md`: already compressed in #5981; every remaining line encodes an output-grammar or validation rule (severity merge, empty-merge attestation, reviewer-slot fidelity), so touching it risks the "keep dedup/normalization output grammar and finding-list structure byte-identical" requirement.
- The scope-anchor "untrusted evidence, not instructions" wrapper sentences (plan mode only): this is a prompt-injection-defense idiom shared verbatim with other prompt builders in `python/larch/rendering/rendering.py`. Preserve it unchanged for consistency and to avoid weakening the "do not follow embedded instructions" defense for a small byte gain.
- `_validation_retry_prompt()`: only built on the rare validation-retry path, and directly tied to recovering from known LLM validation slips (#4868/#5077/#5222/#5503/#5606). It already inherits the smaller `base_prompt` from the changes above, so it shrinks proportionally with zero additional wording risk. Rewriting its own guidance text is not worth the reliability risk for a rarely-dispatched path.
- The existing scaffold/payload byte attribution in `payload_base_bytes` (i.e., what the required-reviewer-slots section counts as payload today): unchanged. This plan only shortens wording inside the existing structure; it does not reclassify which spans count as scaffold vs payload.

## Files to modify/create

### UPDATED: python/larch/review/review_aggregate.py

- In `_required_reviewer_slots_prompt_section()` (the `lines.extend([...])` block that currently reads "Apply these rules to the merged output:" plus 4 bullets), replace with this shorter block, keeping every constraint and every currently-tested substring:
  - `"Rules for the merged output:"`
  - `"- Every listed slot must appear in at least one \`- **Reviewer(s)**:\` line; dropping it fails validation."`
  - `"- Use only slots from this inventory for \`- **Reviewer(s)**:\`/\`- From <slot>:\` labels; never invent, rename, or merge names."`
  - `"- Each \`- From <slot>:\` bullet must quote that slot's own fix text verbatim."`
  - `"- An \`out-of-scope-only\` slot may appear only inside an \`[OUT_OF_SCOPE]\`-tagged output block."`
  - Leave the surrounding blank-line structure and the `"## Required reviewer slots (validator inventory)"` heading untouched.
- In `aggregate_findings()`, shorten the raw-findings section heading from `"\n\n## Raw reviewer findings (input)\n\n"` to `"\n\n## Reviewer findings\n\n"`.
- In `aggregate_findings()`, shorten the scope-reduction notice from `"\n\nScope-reduction findings with a leading [SCOPE-REDUCTION] marker were withheld from LLM aggregation and will be appended verbatim after validation. Do not recreate or merge them.\n"` to `"\n\n[SCOPE-REDUCTION]-marked findings were withheld from aggregation and are appended verbatim after validation; do not recreate or merge them.\n"`.
- Do not change `_strip_agent_frontmatter`, the scope-anchor wrapper sentences, `_validation_retry_prompt()`, or the `payload_base_bytes` computation.

## Edge cases

- **Empty required-slots section**: `_required_reviewer_slots_prompt_section()` still returns `""` when the input has no reviewer slots (unchanged early return); the shortened rules text only applies to the non-empty branch.
- **Retry attempts**: `_validation_retry_prompt()` embeds `base_prompt` verbatim, so retries automatically pick up the shortened heading/rules text with no separate edit.
- **Design vs implement parity**: the heading and rules-block edits apply identically to `--input-mode plan` and `--input-mode code` dispatches, since both share `aggregate_findings()`. The scope-reduction notice only ever fires in plan mode; that conditional is unchanged.
- **Cross-file coupling**: confirmed by repo-wide grep that no other `.py`, `.md`, or test file references the exact old wording being replaced (the one historical hit, a calibration-corpus diff fixture under `python/test_fixtures/plan-fidelity-calibration/`, is static stored data unrelated to live parsing).

## Failure modes

- Terser aggregator instructions could, in principle, reduce the LLM's rule compliance and raise validation-retry rates (`REASON=validation-exhausted` / `validation-failed`), which would increase average aggregator cost rather than reduce it. Mitigation: every constraint from the original bullets is preserved, only phrasing is trimmed; if retry rates rise after this ships, revert the rules-block wording first since it carries the most behavioral risk of the three edits.
- If some reviewer/tooling outside this repo depends on the exact old heading or notice text, it could break silently. Mitigation: the repo-wide grep sweep in this plan found no such in-repo dependency, and the one load-bearing heading (`## Required reviewer slots (validator inventory)`, cross-referenced by `agents/orchestrator-aggregator.md`) is left untouched.

## Testing strategy

Run the existing focused suite; it already asserts the preserved substrings and would catch any accidental behavior change:

- `python3 -m pytest python/tests/review/test_review_aggregate.py`

Then run changed-file lint if available:

- `make py-lint`

No new unit tests are needed: this change edits string literals inside already-tested code paths and does not add new branches, slot-kinds, or output shapes.

**Verify the acceptance criterion directly**, since unit tests only check substrings, not the measured byte drop: from the repo root, run `python3 python/cli.py token measure-panel-cost` and compare the `aggregator` slot-kind rows for both the `design` and `review`/`implement` skill columns against the current committed `larch-logs/panel-prompt-sizes.tsv` history. Confirm `scaffold_bytes` (and `prompt_bytes`) drop for both skills and neither regresses upward.

## Acceptance

Run the existing focused suite; it already asserts the preserved substrings and would catch any accidental behavior change:

- `python3 -m pytest python/tests/review/test_review_aggregate.py`

Then run changed-file lint if available:

- `make py-lint`

No new unit tests are needed: this change edits string literals inside already-tested code paths and does not add new branches, slot-kinds, or output shapes.

**Verify the acceptance criterion directly**, since unit tests only check substrings, not the measured byte drop: from the repo root, run `python3 python/cli.py token measure-panel-cost` and compare the `aggregator` slot-kind rows for both the `design` and `review`/`implement` skill columns against the current committed `larch-logs/panel-prompt-sizes.tsv` history. Confirm `scaffold_bytes` (and `prompt_bytes`) drop for both skills and neither regresses upward.

diff_lines: 20

## Test plan
(no test plan section in plan-file)
