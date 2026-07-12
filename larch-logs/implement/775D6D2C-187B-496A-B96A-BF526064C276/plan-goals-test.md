## Goal
Implement issue #6975: [IMPLEMENTING] bug-treadmill [FEATURE] learn-from-bugs: origin mining + regression-ratio headline.

## Implementation Plan
## Plan

## Approach

Extend the existing digest and prompt-driven report flow without adding a full report renderer. Add two narrow, deterministic seams:

1. **Origin extraction** runs during digest preparation from the normalized title plus an explicit, unsqueezed diagnostic allowlist before section caps are applied. Its section reader must preserve repeated headings, so every allowed `Root Cause` section contributes in document order.
2. **Zone resolution and the required origin headline** use small pure helpers so their query and report grammar receive executable coverage. The headline helper renders only the mandatory Section 2 preamble; clustering and proposal writing remain in the skill.

The report remains prompt-authored, but Step 4 must insert the generated headline verbatim and run a report-contract check before presenting the result. This makes origin counts, percentages, ratio, chain direction, headline ordering, and prose-only warning syntax testable without introducing a separate full-report renderer.

1. Classify each digest by origin.
   - Add a frozen origin value with `kind` and optional issue reference.
   - Compute origin from the normalized title plus the **unsqueezed** diagnostic input before `_pick_sections()` applies `_squeeze()` caps.
   - Use an origin-specific ordered diagnostic-section iterator rather than the dictionary-returning `_split_sections()` as the source of origin bodies. The iterator must preserve duplicate headings and yield each section body in original document order.
   - The body allowlist is exact:
     - every section whose normalized heading starts with `root cause`, including `root cause` and `root cause analysis`; and
     - the complete diagnostic prefix as `_freeform` only when section selection would use the `_freeform` fallback.
   - Exclude `summary`, `suggested fix`, `suggested fix(es)`, all other headings, and `_title_only` value text from origin body scanning. `_title_only` remains title-only classification.
   - Continue to use `diagnostic_prefix()` so appended `/design` plans never participate.
   - Treat a referenced origin marker as `regression`; treat bare `regression` as a regression without a reference.
   - Apply narrow, case-insensitive phrase heuristics for `spec-gap` and `new-code`; default to `unknown`.
   - Serialize the result as an additive `origin` object in every digest record.

2. Make the mandatory report headline deterministic while keeping report synthesis prompt-driven.
   - Add a pure origin-headline formatter over selected digest records.
   - Render all four origin kinds with raw counts, deterministic percentages, an explicit denominator, referenced regression chains, and the regression ratio.
   - Render a referenced residual as `#<origin> -> #<current bug>`.
   - Count bare regressions in the ratio but omit them from chains.
   - Treat self-references as suspect evidence: retain the regression count but emit a clearly labeled suspect self-chain rather than a normal causal chain.
   - Have `prepare` write the generated headline to a dedicated scratch artifact and emit its path as a `KEY=value` result. Step 4 reads and inserts that block first in Section 2 before cluster rows.
   - Add a pure report-contract validator for the generated headline placement and prose-only warning form. Step 4 validates `${RUN_DIR}/report.md` against the prepared digest and headline before printing it.
   - Do not attempt to mechanically classify proposal quality beyond the documented marker contract; the validator verifies that a marked prose-only cluster includes the required citations and mechanical-alternative line.

3. Expand the Step 4 report contract.
   - Require the generated origin headline before the root-cause cluster list.
   - Require cluster mechanisms caused by duplicated contracts, such as parallel parsers or copied field names, to name **single-sourcing** as the class-level fix.
   - Require a cluster whose only residual proposal is a guideline to include the exact marker `prose-only prevention: unlikely to stick`.
   - Require that marked cluster to cite #6746 and #6747 and name the nearest lint, hook, or invariant-test alternative, or explicitly state that no mechanical alternative exists.
   - Keep percentage and ratio denominators based on every selected digest record, including `unknown`.
   - Define zero-selected output as zero counts, no chains, explicit denominator `0`, and regression ratio `n/a (0/0)`.

4. Add `--zones`.
   - Parse one comma-separated value through Step 1.
   - Trim entries, reject an empty list and empty zone names, and preserve zone text as untrusted search data.
   - Translate zones through a tested pure resolver into one topical GitHub query using an explicit OR group: `--zones "design,implement"` becomes `[BUG] (design OR implement) in:title,body`.
   - Establish a single-source rule: `--search`, `--zones`, and verbal search text are mutually exclusive sources.
   - Reject `--zones` with `--search` and reject `--zones` with verbal search text before preparation. Preserve existing `--search` behavior when zones are absent.
   - Forward the resolved query through the existing `--search` preparation argument.
   - Do not change the `--file` contract or couple this skill to `/analyze-bugs`.

5. Keep public documentation, executable unit tests, and the structural harness aligned with the skill prompt.

## Files to modify/create

### UPDATED: python/larch/issue/learn_from_bugs.py

- Add a frozen `Origin` domain type with JSON shape:
  `{"kind": "regression|new-code|spec-gap|unknown", "ref": <int|null>}`.
- Add compiled, case-insensitive patterns for:
  - `introduced by #N`
  - `introduced by PR #N`
  - `incomplete fix of #N`
  - `persists after #N`
  - `residual of #N`
  - bare `regression`
- Support only the documented spacing variants for `PR` and issue references; tests will enumerate every supported form.
- Add an ordered, unsqueezed diagnostic-section iterator for origin extraction that:
  - operates on `diagnostic_prefix(body)`;
  - returns normalized heading and full body for each occurrence in source order;
  - preserves repeated headings instead of collapsing them into a mapping;
  - recognizes the same structural-section boundary semantics used by `_pick_sections()` when deciding whether `_freeform` fallback applies.
- Add an origin-input helper that:
  - normalizes the title after `[DONE]` removal;
  - reads full, unsqueezed bodies from every ordered section whose normalized heading begins with `root cause`;
  - uses the full prefix only for the same no-structured-section condition that yields `_freeform`;
  - never includes `summary`, `suggested fix`, `suggested fix(es)`, arbitrary sections, or `_title_only` value text.
- Invoke origin classification before `_pick_sections()` compresses retained sections. Persist the resulting `Origin` independently of the squeezed `sections` mapping.
- Define stable source order as normalized title first, then every allowed root-cause body in document order, including repeated root-cause headings, then `_freeform` fallback. When several referenced markers exist, use the first match in that order.
- Define deterministic precedence: referenced regression marker, bare regression marker, `spec-gap` phrase, `new-code` phrase, then `unknown`.
- Add narrow phrase sets:
  - `spec-gap`: `never designed`, `was never told`, `no handling for`;
  - `new-code`: `first time this path ran`, `newly added`.
- Add `origin` to `BugDigest` and `BugDigest.to_json()` without changing scan-state schema, filing state, issue selection, or historical artifacts.
- Update digest-size accounting to measure the serialized digest payload supplied to the model, including `origin`, rather than only `sections`, so `DIGEST_CHARS` and `DIGEST_TOKENS_EST` remain truthful.
- Add pure zone-resolution helpers that:
  - split and trim a comma-separated zone string;
  - reject empty values and empty elements with `LearnFromBugsError`;
  - render `[BUG] (<zone> OR <zone> ...) in:title,body`;
  - reject zones combined with explicit `--search` or a non-empty verbal-search indicator.
- Expose the resolver through a narrow CLI entry point that emits only `RESOLVED_SEARCH=<query>` for valid zone input. It must accept zone text through argv without shell evaluation.
- Add a pure `render_origin_headline()` helper that renders:
  - all four kinds in a fixed order;
  - count, one-decimal deterministic percentage, and `selected=<N>` denominator;
  - referenced chains in `#<origin> -> #<current>` direction;
  - a regression ratio based on all selected records;
  - explicit zero-selected and self-chain behavior.
- Have `run_prepare()` write `origin-headline.md` alongside `digest.jsonl` and `coverage-index.json`, and return `ORIGIN_HEADLINE_PATH`.
- Add a pure `validate_report_contract()` helper used by a narrow CLI validation entry point. It must:
  - require the exact generated headline as the first content block in Step 4 Section 2, before cluster rows;
  - reject reversed or altered generated chains by comparing against the prepared headline;
  - validate every `prose-only prevention: unlikely to stick` marker has #6746, #6747, and either a named lint, hook, or invariant-test alternative or an explicit no-mechanical-alternative statement.
- Keep the validator scoped to the new deterministic contract; it must not reimplement model clustering or filing decisions.

### UPDATED: python/larch/cli.py

- Register the new `learn-from-bugs` zone-resolution CLI entry point.
- Register the report-contract validation entry point.
- Preserve all existing `learn-from-bugs prepare`, coverage-index, read-state, and write-state routing unchanged.

### UPDATED: python/tests/issue/test_learn_from_bugs.py

- Add parameterized referenced-marker extraction cases for every regex family, including capitalization and only the `PR` spacing variants the production regex supports.
- Assert every referenced marker yields `kind="regression"` with the expected integer reference.
- Add a bare-regression case with `ref=None`, a no-marker case that remains `unknown`, and focused heuristic cases for every required `spec-gap` and `new-code` phrase family.
- Assert precedence when text contains both a referenced regression marker and a heuristic phrase.
- Verify title-origin extraction and retained root-cause-origin extraction.
- Verify origin scanning uses the full unsqueezed root-cause body by placing a marker after `ROOT_CAUSE_CAP` and after `FREEFORM_CAP`.
- Add a repeated-root-cause fixture with a marker in the first `Root Cause` section and either no marker or a later competing marker in a second `Root Cause` section. Assert that both bodies are examined in source order and that the first allowed marker controls classification.
- Add explicit negative cases proving that a marker or heuristic phrase appearing only in:
  - `summary`,
  - `suggested fix`,
  - `suggested fix(es)`, or
  - `_title_only` fallback value text
  leaves origin `unknown` when the title and allowed diagnostic input have no marker.
- Add a `_freeform` fixture with a referenced marker and assert it classifies as a referenced regression.
- Verify marker text after the diagnostic-plan boundary does not affect origin.
- Extend digest JSON and `run_prepare` assertions to cover the additive `origin` object, `ORIGIN_HEADLINE_PATH`, and digest-size accounting over the complete serialized digest input.
- Use a `persists after #N` fixture to establish source and current issue numbers for the generated `#<origin> -> #<current>` chain.
- Add executable zone-resolution coverage for:
  - `design,implement` exact OR-group translation;
  - whitespace trimming;
  - empty input and empty comma elements;
  - conflict with explicit `--search`;
  - conflict with verbal search text;
  - zone text containing shell metacharacters being retained as literal query data.
- Add origin-headline fixture tests for all four kinds, counts, one-decimal percentages, explicit denominator, bare-regression ratio inclusion, chain direction, zero-selected output, rounding behavior, and suspect self-chain output.
- Add report-contract fixture tests that:
  - accept a report with the generated headline before cluster rows and a valid prose-only clause;
  - reject a headline after clusters, altered or reversed chain text, missing denominator or ratio, and a prose-only marker missing either citation or the required mechanical-alternative line.

### UPDATED: skills/learn-from-bugs/SKILL.md

- Add `--zones "a,b"` to frontmatter, the Contract, and Step 1 parsing.
- Document that `--search`, `--zones`, and verbal description are mutually exclusive search sources:
  - reject `--zones` plus `--search`;
  - reject `--zones` plus verbal search text;
  - preserve existing explicit-search, verbal-search, and default-search behavior when zones are absent.
- Specify trimming, validation, untrusted-data handling, explicit OR-group translation, and the exact example:
  `--zones "design,implement"` → `[BUG] (design OR implement) in:title,body`.
- In Step 1, resolve zones through the new CLI helper and parse only its whole-line `RESOLVED_SEARCH=` output. Keep the final resolved search on the existing `RESOLVED_SEARCH` and `SEARCH_ARGS` route.
- In Step 2, parse `ORIGIN_HEADLINE_PATH` in addition to existing preparation output and abort if it is absent.
- Update Step 3’s digest schema description to include `origin.kind` and `origin.ref`.
- Document that origin classification is best-effort and is not verified historical attribution without checking cited issues and the repository.
- In Step 4, require reading `ORIGIN_HEADLINE_PATH` and inserting it verbatim as the first block of Section 2 before root-cause cluster rows.
- Specify the generated headline’s four origin counts, percentages, explicit denominator, referenced chain direction, regression ratio, zero-selected form, and self-chain warning.
- Require duplicated-contract clusters, including parallel parsers and copied field names, to name single-sourcing as the class-level prevention.
- Require the exact prose-only marker across proposal sections when a cluster has only a guideline residual, plus #6746 and #6747 citations and one line naming the nearest lint, hook, or invariant-test alternative or explicitly accepting that none exists.
- Require the Step 4 report-contract CLI validation to succeed before the report is printed, a durable marker is written, or filing-mode work begins.
- Preserve all filing-mode partitions, durable-marker ordering, and Step 5 approval gates.

### UPDATED: scripts/test-learn-from-bugs-structure.sh

- Extend frontmatter and Contract checks to pin `--zones`.
- Pin the exact zone translation example and both mutual-exclusion failures: zones plus `--search`, and zones plus verbal search text.
- Assert Step 1 uses the zone-resolution CLI result through `RESOLVED_SEARCH` and the existing `SEARCH_ARGS` preparation route.
- Assert Step 2 requires `ORIGIN_HEADLINE_PATH`.
- Assert Step 3 documents additive `origin.kind` / `origin.ref`, the explicit diagnostic allowlist, exclusion of summary and suggested-fix sections, repeated-root-cause handling in document order, and best-effort status.
- Assert Step 4 requires the generated headline before cluster rows, all four origin kinds, counts, percentages, denominator, chain direction, regression ratio, zero-selected behavior, and self-chain warning.
- Assert duplicated-contract clusters name single-sourcing as the class fix.
- Assert the exact prose-only marker, both backing issue citations, required mechanical-alternative line, and pre-print report-contract validation.
- Keep the existing `--file` routing, durable filing, and marker-order assertions unchanged.

### UPDATED: README.md

- Add `--zones "a,b"` to the skill catalog argument list.
- Concisely summarize zone-scoped mining, origin distribution, regression chains and ratio, and prose-only prevention warnings.
- State that origin attribution is best-effort.
- Avoid copying the full heuristic list or report grammar.

### UPDATED: docs/skills.md

- Add `--zones "a,b"` to `/learn-from-bugs` arguments.
- Document mutually exclusive search sources and the zone OR-query behavior.
- Document the generated origin headline, chain direction, regression-ratio denominator, best-effort classification, self-chain warning, and prose-only warning.
- Explain that zone names are a manual handoff from chronic-zone analysis rather than automatic `/analyze-bugs` coupling.
- Preserve existing filing-mode and untrusted-content documentation.

## Edge cases

- A referenced marker and a heuristic phrase occur together: the referenced regression wins.
- A bare `regression` has no trustworthy issue number: emit `ref: null`, omit it from chains, and include it in the regression ratio.
- Several referenced markers occur: use the first match in stable title-then-allowed-body order rather than inventing a multi-parent schema.
- Repeated root-cause headings remain independent allowed sources; inspect each full body in document order rather than retaining only the last body.
- A marker appears beyond a retained-section cap: classify it from the unsqueezed diagnostic text while retaining only capped text in `sections`.
- Marker text appears only in an appended `/design` plan: ignore it because extraction uses only the diagnostic prefix.
- Marker text appears only in `summary` or suggested-fix content: ignore it.
- A digest has no structured root-cause section: classify from title plus full `_freeform` fallback when applicable; a `_title_only` digest is title-only.
- There are no selected bugs: render zero counts, no chains, `selected=0`, and `n/a (0/0)` rather than dividing by zero.
- Percentages need not sum to exactly 100 after rounding: preserve raw counts, fixed one-decimal percentages, and the total denominator.
- A regression references its own issue number: retain classification and count it, but label the chain as suspect evidence.
- `--zones` contains whitespace: trim each name.
- `--zones` is empty, contains an empty comma element, is combined with `--search`, or is combined with verbal search text: stop with a clear argument error before preparation.
- Zone text contains shell metacharacters: treat it as argv data and emit it only through the resolver’s `KEY=value` contract.

## Failure modes

- Over-broad regexes can classify ordinary uses of “introduced” or “after” as regressions: anchor patterns to the required phrases and `#N` syntax.
- Dictionary-based section parsing can silently discard earlier duplicate root-cause sections: use the origin-specific ordered iterator and test a marker in the first duplicate section.
- Scanning retained digest sections can both miss late markers and consume unrelated summary or fix prose: classify before squeezing from the explicit diagnostic allowlist only.
- Heuristic prose can produce false positives: keep the phrase list small, document best-effort behavior, and retain `unknown` as the default.
- Prompt-only report requirements can drift: generate the mandatory headline, validate the completed report contract, and pin prompt grammar in the structural harness.
- Reversing chain direction misstates causality: generate and validate earlier-reference-left, current-issue-right chains.
- Treating percentages as the source of truth hides rounding errors: always render counts and the selected-record denominator.
- A guideline can be accompanied by vague mechanical prose to evade the warning: require a named lint, hook, or invariant test, or explicit acceptance that none exists.
- Zone translation can accidentally narrow results with implicit AND terms: require the explicit OR group and cover it in executable tests.
- Zones and explicit search can silently compete: reject every multi-source combination before calling prepare.

## Testing strategy

Run only tests and linters covering changed files:

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py`
- `bash scripts/test-learn-from-bugs-structure.sh`
- `python3 -m ruff check python/larch/cli.py python/larch/issue/learn_from_bugs.py python/tests/issue/test_learn_from_bugs.py`
- Run the repository’s documented Python type-check target scoped to the changed Python files if it accepts file arguments.
- Run the documented Markdown lint against `README.md`, `docs/skills.md`, and `skills/learn-from-bugs/SKILL.md`.
- Run `make test-learn-from-bugs-structure` as the Makefile-level confirmation.
- Inspect a prepared JSONL fixture and `origin-headline.md` fixture to confirm the exact additive origin shape and mandatory headline grammar.
- Run the report-contract fixture with unknown, new-code, spec-gap, referenced regression, bare regression, and self-referencing regression records. Confirm headline ordering, counts, percentages, denominator, ratio, chain direction, and prose-only validation behavior.
- Confirm a fixture containing repeated `Root Cause` headings classifies a marker from the first heading and observes document-order precedence across all allowed root-cause bodies.
- Confirm existing `--search`, verbal-description, default-search, `--file`, and `-s` behavior remains unchanged.

## Acceptance

Run only tests and linters covering changed files:

- `python3 -m pytest python/tests/issue/test_learn_from_bugs.py`
- `bash scripts/test-learn-from-bugs-structure.sh`
- `python3 -m ruff check python/larch/cli.py python/larch/issue/learn_from_bugs.py python/tests/issue/test_learn_from_bugs.py`
- Run the repository’s documented Python type-check target scoped to the changed Python files if it accepts file arguments.
- Run the documented Markdown lint against `README.md`, `docs/skills.md`, and `skills/learn-from-bugs/SKILL.md`.
- Run `make test-learn-from-bugs-structure` as the Makefile-level confirmation.
- Inspect a prepared JSONL fixture and `origin-headline.md` fixture to confirm the exact additive origin shape and mandatory headline grammar.
- Run the report-contract fixture with unknown, new-code, spec-gap, referenced regression, bare regression, and self-referencing regression records. Confirm headline ordering, counts, percentages, denominator, ratio, chain direction, and prose-only validation behavior.
- Confirm a fixture containing repeated `Root Cause` headings classifies a marker from the first heading and observes document-order precedence across all allowed root-cause bodies.
- Confirm existing `--search`, verbal-description, default-search, `--file`, and `-s` behavior remains unchanged.

oversize_override: operator
diff_lines: 477

## Test plan
(no test plan section in plan-file)
