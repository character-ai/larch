Here is the normalized structured finding list. In-scope items were merged where they described the same risk or the same code path; out-of-scope inputs stay separate with `[OUT_OF_SCOPE]` preserved on the heading.

### FINDING_1: Revision traceability relies on a weak six-word prefix heuristic
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: In `revision_traceable_in_blocks` (and related advisory traceability), a six-word normalized prefix can match unrelated prose in the same scoped block, so a fabricated or paraphrased bullet whose head collides with common text can pass without a full normalized substring match—undermining verbatim-trace intent and risking false passes or noisy diagnostics on odd punctuation or large inputs.
- **Suggested revision**: Prefer full normalized substring matching for `From:`-slot bullets (or isolate any prefix fallback behind an explicit legacy/opt-in path); add a regression where prefix matches but full normalized text does not; optionally add a strict full-string-only mode if policy requires it.

### FINDING_2: `compose_coder_prompt` diverges from the plan’s shape, length, and emphasis
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The coder prompt is one long `printf` with many clauses (higher token load), emphasizes “substantive issue behind” revisions versus the plan’s informational framing, risks treating quoted multi-reviewer bullets as ambiguous between hard constraints and hints, and may reference multi-reviewer bullets even when absent; the plan called for a minimal additive sentence but the change rewrote the whole directive—so regressions in wording could ship without dispatch harness pins.
- **Suggested revision**: Shorten and align wording with the plan (informational revisions, minimal change, clear status of bullets), prefer the minimal additive edit or document the broader rewrite as the canonical contract, and add stable `grep -Fq` pins on generated coder prompt text in `test-review-and-fix.sh` (or equivalent) alongside voter-style coverage.

### FINDING_3: Suggested-revisions sub-list parsing can drop or truncate content
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `suggested_revisions_bullets` can silently ignore lines between the “Suggested revisions” header and the first `From:` bullet; sub-list termination keyed on top-level heading patterns can cut off early when verbatim fix text contains lines resembling field headings (for example a line like `- **Concern**:`), hiding suffix content from advisory scans.
- **Suggested revision**: Warn or fail validation on unexpected pre-`From` lines; narrow end-of-sub-list detection with real structural boundaries (or document forbidden patterns inside verbatim fixes) and add fixtures/tests for those shapes.

### FINDING_4: [OUT_OF_SCOPE] Stale bundled-review note on `oos-disposition-shared.inc.bash`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Latent worry from bundled review JSONL about `declare -A`; the shipped helper is described as not using associative arrays and using `sort -u` dedup—noise for the voting feature, not a current code defect.
- **Suggested revision**: Triage using current tree and logs; no change required for this feature if final implementation matches the described behavior.

### FINDING_5: Verbatim multi-reviewer revision bullets enlarge untrusted prompt surface
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Verbatim bullets increase model-supplied prose in voter/coder prompts; a compromised or mistaken reviewer could embed instruction-like content that never touches tracked files but still influences later models if downstream prompts are not robust.
- **Suggested revision**: Strengthen untrusted-data framing, add per-bullet size limits, or apply a narrow deterministic sanitizer in voter/coder prompt construction while preserving traceability goals; align with guidance in [agents/orchestrator-aggregator.md](agents/orchestrator-aggregator.md) as appropriate.

### FINDING_6: OOS disposition gate may run without authoritative `--oos-issues-ndjson`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: When session id is empty and no ndjson is discovered under `larch-logs/implement`, the gate may omit `--oos-issues-ndjson` while still evaluating other signals—risking divergence from combined-evidence intent for NDJSON-only filed URLs or rejected-OOS markers.
- **Suggested revision**: Persist the authoritative `oos-issues.ndjson` path from the issue pipeline and fail closed when non-security OOS blocks exist but that path is missing, instead of running the gate without the flag.

### FINDING_7: `From:` bullet parsing splits slot labels on the first colon
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Regex/split behavior can mis-split slot vs revision body when slot labels contain `:`, skewing traceability warnings.
- **Suggested revision**: Constrain slot grammar, split on a reserved delimiter (for example last colon with a fixed prefix), or document unsupported labels and add coverage.

### FINDING_8: Voting doc YES vs NO rows use asymmetric problem-vs-fix framing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The YES row still reads like “accept finding and implement it” while NO reframes around problems and informational fixes, inviting inconsistent voter mental models within one table.
- **Suggested revision**: Reword YES/EXONERATE rows to parallel the problem-vs-fix semantics used for NO.

### FINDING_9: [OUT_OF_SCOPE] Reviewer templates vs singular “Suggested revision”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Template-driven reviewers may still prefer legacy singular “Suggested revision” until templates/agents are synced; not attributed to this branch’s functional change set.
- **Suggested revision**: Regenerate or edit [skills/shared/reviewer-templates.md](skills/shared/reviewer-templates.md) (and derived agents) when end-to-end consistency is required.

### FINDING_10: Plan fidelity vs diff surface (unrelated bundled changes)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The stated implementation plan lists five files, but the branch diff bundles unrelated areas (ship-pr, lint-bash32, Makefile, changelog, plugin, audit-runs, large `larch-logs`, etc.), increasing merge risk and review burden without traceability.
- **Suggested revision**: Split unrelated work into separate PRs or expand the plan so every changed area is explicitly in scope.

### FINDING_11: Revision trace scoping uses reviewer-line intersection semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Traceability scopes using merged `Reviewer(s)` ∩ input `Reviewer(s)` rather than strictly “input blocks for that slot” as written in the plan; rare merges could yield empty intersection and spurious untraceable warnings (or strict failures) even when text exists in the slot’s input block.
- **Suggested revision**: Align implementation with plan wording or update the plan to document intersection semantics; add a regression fixture if a realistic merge shape is at risk.

### FINDING_12: Diff-only review cannot attest `/relevant-checks` execution
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Reviewers cannot verify local `/relevant-checks` from artifacts alone.
- **Suggested revision**: Record checks in the PR body and rely on visible CI status for reviewers.

---

This aggregation produced twelve distinct `### FINDING_N:` blocks (with duplicates merged), so the `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line must **not** appear.
