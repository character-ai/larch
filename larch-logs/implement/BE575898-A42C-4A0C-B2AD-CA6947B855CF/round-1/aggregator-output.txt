Merged overlapping reviewer items into a single structured list. Historical log nits are one `[OUT_OF_SCOPE]` bucket; the STALE_PHRASES / removed-POS_MARKERS concern is one latent integration item; fixture heredocs vs misleading comments stay separate because the fixes differ.

### FINDING_1: Quick-mode doc-sync self-test fixtures still use retired Step 5 wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: In [`scripts/test-quick-mode-docs-sync.sh`](scripts/test-quick-mode-docs-sync.sh) (notably around lines 284–304), self-test fixture heredocs still embed “Unified hard panel” / “hard review panel” style strings that are no longer `POS_MARKERS`, so the harness keeps deprecated vocabulary and widens repo greps without adding enforcement value.
- **Suggested revision**: Rewrite fixture heredocs to neutral Step 5 wording while preserving required positive marker substrings and exactly one deliberate stale phrase in `bad.md` (per harness design).

### FINDING_2: [OUT_OF_SCOPE] Historical implement run logs still use legacy unified hard panel phrasing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Under [`larch-logs/implement/EA494C39-F682-443C-82FD-E45AA1834936/round-1/`](larch-logs/implement/EA494C39-F682-443C-82FD-E45AA1834936/round-1/) (including `review-round-summary.md` and related artifacts), pre-existing markdown still repeats legacy “unified hard panel” wording. This is archival snapshot content, not introduced by the reviewed branch diff; it only adds grep noise and optional policy discussion.
- **Suggested revision**: No change required for the PR under review; any deliberate log or archival cleanup is a separate policy or follow-up task.

### FINDING_3: Stale-phrase table in quick-mode doc-sync harness doc still references unified + panel wording
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: In [`scripts/test-quick-mode-docs-sync.md`](scripts/test-quick-mode-docs-sync.md) (e.g. line 41), the stale-phrase documentation still says the simple review panel is superseded by unified `--panel hard`, which is inconsistent with removing “unified hard panel” style language from enforced docs. Harness behavior and markers are unaffected; this is documentation drift inside the test harness doc.
- **Suggested revision**: Reword that bullet to drop the “unified” label while still pointing at `--panel hard` and the intended migration story.

### FINDING_4: Self-test fixture comments overstate “every positive marker” vs actual fixture prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Comments in [`scripts/test-quick-mode-docs-sync.sh`](scripts/test-quick-mode-docs-sync.sh) (around lines 293–304) claim the bad file contains every positive marker while fixtures still include retired unified / hard-review phrases that are not in `POS_MARKERS`, which can mislead maintainers even though CI self-tests still pass.
- **Suggested revision**: Update comments to state that fixtures must include all `POS_MARKERS` strings plus exactly one stale phrase, and that additional legacy prose is optional or explicitly non-authoritative.

### FINDING_5: Retired Step 5 branding can return to public docs without failing the quick-mode doc-sync check
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: In [`scripts/test-quick-mode-docs-sync.sh`](scripts/test-quick-mode-docs-sync.sh) (roughly lines 82–96), two `POS_MARKERS` entries were removed without corresponding `STALE_PHRASES` (or equivalent) coverage. Editors could reintroduce deprecated Step 5 branding in `README.md` / `docs/*.md` while keeping the remaining technical anchors (five rounds, `--panel hard`, three-judge panel on round 1, six Cursor specialists), and CI would stay green—so enforcement no longer matches the apparent intent to retire those phrases from public docs.
- **Suggested revision**: Either extend `STALE_PHRASES` (and align self-test fixtures) for those retired phrases, add a focused grep-style guard for public doc surfaces, or explicitly document acceptance of reintroduction risk.

### FINDING_6: Positive anchors may no longer pin the human-facing “review panel” label in public Step 5 mirrors
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: With positive anchors narrowed to technical substrings only, public-facing narrative could drift away from the intended human label “review panel” (or whatever canonical substring the project agrees on) while still satisfying the remaining `POS_MARKERS`, weakening doc-sync as a guardrail for user-visible terminology.
- **Suggested revision**: Add the agreed canonical substring for the review panel label to `POS_MARKERS` and propagate it through sibling docs and mirrors the harness syncs, or document that narrative wording is intentionally unconstrained.

### FINDING_7: [OUT_OF_SCOPE] Plugin marketplace description still advertises deprecated unified hard panel wording
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [`/.claude-plugin/plugin.json`](.claude-plugin/plugin.json) (e.g. line 4) still uses the deprecated phrase “unified hard panel” for Step 5 in the marketplace-facing description, while the branch removes that terminology from README, skills docs, and SKILL Step 5 breadcrumbs—so consumers browsing or installing the plugin can see wording the rest of the distribution deliberately retired.
- **Suggested revision**: Treat as a follow-up (not required for the reviewed PR diff): rewrite the description to match the new review-panel terminology, and only add CI enforcement for that copy if the project wants the marketplace string owned by the same guards as in-repo docs.

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must **not** appear anywhere in this response.
