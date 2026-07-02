## Plan

## Approach

Make a prose density pass only.

Preserve these byte-stable surfaces:

- ballot IDs: `FINDING_N:`, `OOS_N:`, headings, and vote-line examples.
- axis tokens: `CORRECTNESS`, `SEVERITY`, `QUALITY`, `UNCERTAIN`.
- severity values, quality values, correctness values, and YES/NO grammar.
- classification headers, scoring thresholds, and tally behavior descriptions.
- fenced examples and tables unless a prose sentence outside the grammar can shrink safely.

Use `NO_SKETCHES` guidance: draft and implement from direct repo inspection, not planning-panel agreement.

Keep the discussion constraints:

- Compress `skills/shared/voting-protocol.md`.
- Compress static prose blocks in `render_voter_main`.
- Do not edit `VOTER_ARCHETYPES`.
- Do not edit `skills/shared/review-acceptance-rubric.md` or `skills/shared/oos-acceptance-rubric.md`.
- If the OOS paragraph changes, sync all four parity sites.

## Files to modify/create

### UPDATED: skills/shared/voting-protocol.md

Compress prose paragraphs while preserving voting semantics.

Targets:

- Overview and ballot narrative.
- Voter prompt template prose.
- Severity floor wording.
- Panel and OOS sections.
- OOS reporting prose.

Keep code fences, tables, IDs, and vote examples byte-stable unless the text is plain prose and not parser-facing.

Shorten the canonical OOS voter rubric paragraph and keep its meaning:

- apply the OOS Acceptance Rubric.
- require backlog-relative materiality.
- keep impact floor, concrete trigger, issue-overhead test, and default-deny.
- treat remedies as informational.
- keep remedy choice with the future implementer.

### UPDATED: python/larch/rendering/rendering.py

Compress only static prose emitted by `render_voter_main`.

Edit these blocks:

- initial voter role and necessity guidance.
- severity floor.
- panel severity rubric.
- boilerplate anti-style and proposed-fix directives.
- OOS paragraph for `finding-only`.
- OOS paragraph for `finding-oos`.
- output-only directive text where it can shrink without changing parser expectations.

Do not edit:

- `VOTER_ARCHETYPES`.
- dispatch logic.
- parser grammar.
- argument parsing.
- calibration math.
- dynamic rubric loading.

Keep the runtime OOS paragraph semantically aligned with `skills/shared/voting-protocol.md`.

### UPDATED: skills/design/SKILL.md

Update only the Step 3 MAV OOS sentence if the canonical OOS wording changes.

Keep the same operational flow:

- cast one YES or NO.
- use panel proportionality.
- apply `skills/shared/oos-acceptance-rubric.md`.
- default-deny.
- ignore remedy preference.

### UPDATED: skills/implement/references/step5-review-branches.md

Update only the Step 5 MAV OOS paragraph if the canonical OOS wording changes.

Keep all command wiring and Step 5 resume behavior unchanged.

### UPDATED: python/tests/rendering/test_rendering.py

Update pinned substring assertions that depend on compressed `render_voter_main` prose.

Keep assertions for behavior-critical text:

- panel severity rubric exists.
- blocker, major, minor, nit, and uncertain meanings remain present.
- immediate action and output-only directives remain present.
- `VOTER_ARCHETYPES` lens assertions remain unchanged.

### MAY_UPDATE: python/skill-closure-baseline.json

Update only if the implementation chooses to ratchet the lower panel-tier baseline in this PR.

If changed, regenerate with `make regen-skill-closure-baseline` and commit the full generated file.

If not changed, still show the token reduction with `python3 python/cli.py skill-closure report` before and after the prose pass.

## Edge cases

- Do not reduce OOS wording so far that voters treat remedy disagreement as a NO reason.
- Do not blur in-scope necessity voting with OOS issue-worthiness voting.
- Do not remove the nit severity floor for in-scope findings.
- Do not alter neutral rescue or OOS scoring semantics.
- Do not change `[OUT_OF_SCOPE]` legacy behavior under `FINDING_N:`.
- Preserve the four-site OOS parity invariant when that paragraph changes.
- Avoid adding new prose that offsets the token savings.

## Failure modes

- A compressed sentence drops a required rubric boundary and changes voter behavior.
- A parser-facing token in a fence or output template changes and breaks vote parsing.
- A test assertion is weakened too much and stops guarding behavior-critical prompt text.
- `python/skill-closure-baseline.json` is regenerated without a real panel-tier reduction.
- OOS parity drifts between runtime voter text, `voting-protocol.md`, Step 3 MAV, and Step 5 MAV.

## Testing strategy

Run focused tests first:

```bash
python3 -m pytest python/tests/rendering/test_rendering.py
```

Run voting and tally tests that cover parser and classifier behavior:

```bash
python3 -m pytest python/tests/review/test_voting.py python/tests/review/test_findings_ledger.py
```

Check the panel-tier token count:

```bash
python3 python/cli.py skill-closure report
python3 python/cli.py lint skill-closure-growth --skill panel-tier
```

If `python/skill-closure-baseline.json` changes, run:

```bash
make regen-skill-closure-baseline
python3 python/cli.py lint skill-closure-growth
```

For markdown-only confidence, run relevant lint if dependencies are available:

```bash
python3 python/cli.py checks run-relevant
```

## Implementation notes

Prefer deletion and sentence folding over rewrites.

Review the diff with these checks:

- Search for changed grammar tokens: `FINDING_N`, `OOS_N`, `CORRECTNESS=`, `SEVERITY=`, `QUALITY=`, `UNCERTAIN=`.
- Compare the OOS paragraph across all four parity sites.
- Confirm `VOTER_ARCHETYPES` is unchanged.
- Confirm no acceptance rubric files changed.

## Acceptance

Run focused tests first:

```bash
python3 -m pytest python/tests/rendering/test_rendering.py
```

Run voting and tally tests that cover parser and classifier behavior:

```bash
python3 -m pytest python/tests/review/test_voting.py python/tests/review/test_findings_ledger.py
```

Check the panel-tier token count:

```bash
python3 python/cli.py skill-closure report
python3 python/cli.py lint skill-closure-growth --skill panel-tier
```

If `python/skill-closure-baseline.json` changes, run:

```bash
make regen-skill-closure-baseline
python3 python/cli.py lint skill-closure-growth
```

For markdown-only confidence, run relevant lint if dependencies are available:

```bash
python3 python/cli.py checks run-relevant
```

review_status: ok
rounds_completed: 1
diff_added: 20
diff_deleted: 95
mechanical_churn: false
diff_lines: 150
