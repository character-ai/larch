## Goal
Implement issue #6159: [IMPLEMENTING] md-to-py-XII: density-pass the design plan-review generated prompt builders.

## Implementation Plan
## Plan

## Approach

`approach-synthesis.txt` is `NO_SKETCHES`, so draft from direct inspection. The approved outline binds scope.

Make a prose-only density pass over the design plan-review reviewer prompt builder. Keep all machine-parsed contract text byte-identical where tests or downstream parsers depend on it.

Do not touch:
- `render_voter_main`
- `_oos_proposal_instruction()` / `oos_proposal_instruction()`
- `_architectural_guidelines_review_section()`
- `_code_ledger_section()`
- implement-side specialist, voter, or aggregator prompt builders
- panel topology, dispatch, payload inclusion, or ratchets

Compress by replacing long prose with shorter equivalent instructions. Preserve exact anchors and vocab:
- `schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix`
- `{"no_issues_found": true}`
- `[OUT_OF_SCOPE]`
- `[SCOPE-REDUCTION]`
- `[ALREADY_ADDRESSED]`
- `in_scope`, `out_of_scope`
- `blocking`, `important`, `nit`, `latent`
- `code-quality`, `risk-integration`, `correctness`, `architecture`, `security`
- `<READABILITY_STYLE>` token behavior
- the unquoted, slash-separated `code-quality / risk-integration / correctness / architecture / security` enumeration, kept together (with `security`) on one grep-visible line — `.github/workflows/ci.yaml`'s "Assert focus-area enum includes 'security'" job greps `python/larch/rendering/rendering.py` for this exact substring; only the prefix wording around it may shorten
- `Acceptable TSV block example` and `Your response MUST begin with either the TSV header line` — both are pinned verbatim by `scripts/test-prompt-template-invariants.sh`'s plan-reviewer assertions, separate from and in addition to the `test_rendering.py` pytest assertions

## Files to modify/create

### UPDATED: python/larch/rendering/rendering.py

Compress only plan-review-owned text:
- `_PLAN_REVIEW_ROLES`
  - Shorten the four static role blurbs.
  - Keep each role's distinct lens:
    - architecture: maintainability, standards, patterns, boundaries, failures
    - innovation: assumptions, alternatives, stronger unconventional solutions
    - pragmatic: minimum scope, safety, regressions, recovery, races, corruption
    - requirements: goals, acceptance criteria, constraints, testing gaps
- `_plan_review_plan_directive()`
  - Shorten Cursor wording while preserving the `Cursor cannot read DESIGN_TMPDIR plan` behavior.
  - Keep `<larch_plan_under_review>` markers and inlined plan content.
  - Keep Codex path-reference behavior.
- `render_plan_review_main()`
  - Shorten `tier` without weakening the minimum-change instruction.
  - Shorten the feature scope anchor prose while preserving the heading and `[SCOPE-REDUCTION]` rule.
  - Shorten the response-start, post-PR framing, duplicate-check, OOS, and `[ALREADY_ADDRESSED]` prose. Leave the one line carrying the slash-separated focus-area enumeration and the two harness-pinned TSV/sentinel phrases listed above untouched (or reworded only outside the pinned substring).
  - Keep TSV header, row example, severity set, focus-area set, exact-tab rule, and sentinel literal unchanged.
  - Keep readability-style loading and fallback text unchanged unless shortening non-token prose around it is safe.
  - Leave payload-byte accounting unchanged.

### UPDATED: python/larch/review/plan_review_panel.py

Compress only `_GENERIC_CODEX_PLAN_REVIEW_ROLE`.

Keep:
- generic Codex slot creation
- `_slot_row()` fallback text
- dynamic scout body wrapping
- manifest fields
- payload sidecar threading
- model-role assignment
- dispatch and pruning behavior

### UPDATED: python/tests/rendering/test_rendering.py

Update tests only where they assert compressible prose substrings.

Keep or add assertions for protocol and anchor invariants:
- Cursor still inlines plan content and keeps `<larch_plan_under_review>`.
- Codex still references the plan path and does not inline plan content.
- TSV header remains exact.
- schema version `1` and non-counter warning remain present.
- focus-area allowlist remains exact, including the unquoted slash-separated enumeration with `security` on the same line.
- OOS cap helper text remains present through the shared helper.
- scope anchor heading still precedes architectural guidelines.
- architectural-guidelines untrusted warning remains separate from the scope anchor.
- dynamic body-file substitution still inherits the full scaffold.

### MAY_UPDATE: python/tests/review/test_plan_review_panel.py

Change only if a shortened prompt changes existing exact prose expectations in this file.

Do not change fallback prompt expectations unless `_slot_row()` changes, which is out of scope. Keep tests that guard dynamic scaffold inheritance, render-failure fallback, and payload-byte threading.

## Edge cases

- Cursor slots must still receive the full plan body inline because Cursor cannot read the design tmpdir plan path.
- Codex slots must still receive the plan path only.
- Dynamic scout reviewers must still get their body text as the role line plus the same scaffold.
- The scope anchor and architectural guidelines must remain separate blocks.
- The prompt may include untrusted feature text, plan text, and architectural guidelines. Keep all wording that tells reviewers to treat those blocks as evidence, not instructions.
- A shortened no-issues instruction must still prevent preambles and trailing prose.
- `.github/workflows/ci.yaml` greps `rendering.py` for the unquoted slash-separated focus-area enumeration and fails the build if `security` is not on that matched line; do not reformat that enumeration into bullets, backticks, or a reordered/renamed list.
- `scripts/test-prompt-template-invariants.sh` (wired into `make test-prompt-template-invariants`, CI shard `test-harnesses-3`) does a live `render plan-review` smoke and asserts several exact substrings independent of the pytest suite; a change that passes `test_rendering.py` can still fail this harness.

## Failure modes

- A compressed sentence may accidentally change a parser contract or accepted value set.
- Removing too much response-start guidance may lower plan-review parse rate.
- Changing shared helpers would collide with sibling density-pass issues.
- Payload-byte sidecars could drift if any payload inclusion path changes. Avoid such changes.
- Reformatting the focus-area enumeration line or the two harness-pinned phrases would pass pytest but fail CI's enum grep job or `test-prompt-template-invariants.sh`.

## Testing strategy

Run focused unit tests:
- `python -m pytest python/tests/rendering/test_rendering.py -q`
- `python -m pytest python/tests/review/test_plan_review_panel.py -q`

Run the prompt-template invariants harness (catches exact-substring pins outside pytest):
- `make test-prompt-template-invariants`

Run lint for changed Python files:
- `python3 python/cli.py checks run-relevant`

For acceptance, after implementation, run one live `/design` path that reaches plan review and inspect the committed `panel-prompt-sizes.tsv`:
- verify plan-review slots show lower `scaffold_bytes` than the pre-change baseline for comparable payloads
- verify `payload_bytes` still accounts for Cursor plan content, feature text, dynamic body text when marked payload, and ledger text
- verify parse rate and structured finding handling do not regress
- do not raise any ratchet

## Acceptance

Run focused unit tests:
- `python -m pytest python/tests/rendering/test_rendering.py -q`
- `python -m pytest python/tests/review/test_plan_review_panel.py -q`

Run the prompt-template invariants harness (catches exact-substring pins outside pytest):
- `make test-prompt-template-invariants`

Run lint for changed Python files:
- `python3 python/cli.py checks run-relevant`

For acceptance, after implementation, run one live `/design` path that reaches plan review and inspect the committed `panel-prompt-sizes.tsv`:
- verify plan-review slots show lower `scaffold_bytes` than the pre-change baseline for comparable payloads
- verify `payload_bytes` still accounts for Cursor plan content, feature text, dynamic body text when marked payload, and ledger text
- verify parse rate and structured finding handling do not regress
- do not raise any ratchet

diff_lines: 130

## Test plan
(no test plan section in plan-file)
