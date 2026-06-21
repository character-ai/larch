### OOS_6: [OUT_OF_SCOPE] Legacy Combined into #N regex matches incidental body prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: latent
- **Concern**: `has_combined_away_marker` applies the legacy `\bCombined\s+into\s+#\d+\b` regex to issue body text as well as comments. Issue discussion that mentions "Combined into #99" without an actual combine close comment can dock incorrectly to combined-away.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict matching to close-comment context or require larch combined-away marker for high-confidence docking.
  - From cursor-specialist-edge-cases-output.txt: Match legacy combined-away text only in normalized comments, not arbitrary body prose.
  - From dyn-oos-reconciler-output.txt: Restrict legacy combined-away detection to normalized comment bodies (and keep the explicit `larch:combined-away` marker in body/comments if desired), not free-form issue description text.


### OOS_7: [OUT_OF_SCOPE] Bulk gh issue list failure still emits success report with zero issues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `run_main` converts a total `gh issue list` failure into a warning and still returns success after rendering the normal report from `issues=[]`. If both expanded and fallback fetches fail due to auth, network, or repo errors, `/analyze-issues run` reports `Analyzed 0 issues` with exit 0 instead of failing, which can make operators trust an empty analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document WARN path or skip empty-issue sections when bulk fetch failed.
  - From codex-generic-output.txt: Preserve the old non-zero exit when `fetch_main` fails after its retry; only degrade optional field availability, not the entire issue dump fetch.


