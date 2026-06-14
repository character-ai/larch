### OOS_1: [OUT_OF_SCOPE] risk-integration — prose vs structured `blocking` severity mismatch (pre-existing)
- **Reviewer(s)**: dyn-structured-severity-output.txt
- **Severity**: latent
- **Concern**: Pre-rendered specialist bodies allow `blocking` in TSV `severity` but prose format still lists only `**Important**` / `**Nit**` / `**Latent**` (`agents/pre-rendered/reviewer-correctness-body.txt:51`). `python/review_and_fix.py:34-38` `_HIGH_RE` also does not treat `**Blocking**` as high severity. That mismatch is outside the `research_eval.py` change.


### OOS_2: [OUT_OF_SCOPE] code-quality — `blocking` severity missing from canonical prompt surfaces
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-doc-contract-output.txt, dyn-structured-severity-output.txt
- **Severity**: latent
- **Concern**: `python/research_eval.py` now accepts `blocking`, matching `agents/reviewer-*.md` and pre-rendered reviewer bodies, but canonical prompt surfaces still document only `important`/`nit`/`latent` (`skills/shared/reviewer-templates.md:204`, `python/rendering.py:1136`, `agents/code-reviewer.md:161`). Plan explicitly forbade prompt edits or intentionally left canonical-template drift unchanged; validator/prompt mismatch can remain for templates that omit `blocking`. Pre-existing drift outside this commit; not introduced by `68e6aadd8`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align rendering prompt severity list in a follow-up if plan-review structured output should accept `blocking`.


