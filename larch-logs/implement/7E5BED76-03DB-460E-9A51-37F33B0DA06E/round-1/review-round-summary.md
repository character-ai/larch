# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Partial tokenization treats incomplete raw attribution as sole-finder eligible
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `raw_sole_finder_attribution` (`python/voting.py:459-460`) accepts a partial `tokenize_finding_reviewers` match as complete raw attribution. When `finding_reviewers` is a whitespace co-proposal (e.g. `"Cursor-Pragmatic Codex-Arch"`) but the corpus only knows one label (e.g. `--reviewer-labels Cursor-Pragmatic` with no other TSV seed for `Codex-Arch`), tokenization returns a single token, `tokens or comma_parts` never runs, and replay scoreboard / progress Top reviewers can add `+0.25` despite two raw reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Reject partial tokenization for bonus eligibility; only return tokens when they consume the full comma segment, and reserve comma fallback for zero-token cases.
  - From codex-specialist-edge-cases-output.txt: Reject partial tokenization for bonus eligibility, or require tokenization to consume the full comma segment before len(raw_reviewers)==1 can qualify


### FINDING_8: No-env replay tests can inherit `LARCH_UNIQUE_FINDER_BONUS` from caller environment
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After replay code started reading `LARCH_UNIQUE_FINDER_BONUS`, no-env tests can inherit the variable from the caller environment. Running e.g. `LARCH_UNIQUE_FINDER_BONUS=0.25 python3 -m pytest python/test_voting.py -k scoreboard_main_weights_classification_tsv` can fail because expected base scores become fractional bonus scores; similar no-env progress-report assertions can fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Clear LARCH_UNIQUE_FINDER_BONUS in no-env tests or in an autouse fixture, while keeping explicit active-bonus tests setting it themselves.


