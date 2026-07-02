## Goal
Implement issue #6029: [IMPLEMENTING] [BUG] #5975 latent: closure classifier index=0 and sentence-clause edge defects.

## Implementation Plan
## Summary

Two latent defects in the closure-growth classifier shipped by #5975 / PR #6009, plus one conscious coverage descope. None is observable with today's SKILL.md content (grep-verified during the audit), but each silently corrupts eager/conditional classification once a matching line shape appears in a skill file.

## Original report

From the 2026-07-02 post-merge audit of #5975 / PR #6009 at 63ed17f18. The index defect is exactly that run's FINDING_1 (which subsumed 5 raw reviewer findings), voted neutral 1-2 and left unfixed; the descope is that run's OOS_2. 0 OOS filed, so neither has tracking.

## Reproduction scenario

- Index defect: author a SKILL.md line that combines a narrow directive phrase with an un-prefixed "Read ... completely" clause, or a line with a conditional marker before the narrow phrase; run `python3 python/cli.py lint skill-closure-growth` and compare classification against intent.
- Sentence-clause defect: a directive line with no prior ". " sentence boundary; the extracted clause drops the line's first character.

## Expected behavior

Directive matches carry their real line index so dedup and conditional detection see correct positions; sentence clauses never clip characters; design's Step-0 shared references either participate in the eager ratchet or the asymmetry is documented.

## Observed behavior

All latent at 63ed17f18; no current line in the three gated SKILL.md files combines the trigger shapes (verified by grep during the audit).

## Root cause analysis

- python/larch/lint/lint_skill_closure_growth.py:311: `_narrow_directive_matches` hardcodes index=0 for narrow matches. When shapes co-occur on one line: the READ_COMPLETELY dedup (line 328, `existing.index <= match.start()`) suppresses every un-prefixed read-completely clause co-located with a narrow match (closure under-count), and `_line_is_conditional(line, 0)` receives an empty prefix and whole-line suffix, so mid-line conditional markers before the narrow phrase are ignored (over-count, fail-closed direction) while a "(when ...)" or "(if ...)" parenthetical anywhere on the line flips it conditional (under-count).
- lint_skill_closure_growth.py:292: `_sentence_clause` off-by-one: when `rfind(". ", ...)` misses, the result is -1 plus 2 equals 1, and the floor is applied before the addition, so the clause starts at column 1 and drops the first character. Cosmetic today because paths occur after the directive word and a clipped leading backtick still bare-matches.
- Descope: skills/design/SKILL.md:97,110 reference session-setup-output.md and external-reviewers.md with the same phrase shapes the eager matchers target, but the matchers are review-scoped, so these always-loaded design files stay outside design's eager ratchet.

## Evidence

- Code reads at 63ed17f18: lint_skill_closure_growth.py lines 292, 311, 328.
- Run log larch-logs/implement/BDBC0129-E265-4215-83EA-AE921949D08C: FINDING_1 neutral 1-2; OOS_2 descope record.

## Affected files

- python/larch/lint/lint_skill_closure_growth.py.
- python/tests/lint/ closure-growth tests: regression fixtures.
- skills/design/SKILL.md (only if the descope is closed by widening matcher scope).

## Suggested fix(es)

- Pass `match.start()` as the directive index.
- Compute the sentence-clause start so the zero floor applies after the +2 adjustment.
- Either widen the eager matchers to design's Step-0 shared references or record the asymmetry in the lint baseline documentation.
- Add fixtures: co-located directive plus narrow match; mid-line conditional before a narrow phrase; no-prior-sentence clause extraction.

## Open questions

None identified.

## Test plan
(no test plan section in plan-file)
