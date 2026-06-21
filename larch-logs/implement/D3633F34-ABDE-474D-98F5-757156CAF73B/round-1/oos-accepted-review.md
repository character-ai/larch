### OOS_1: [OUT_OF_SCOPE] Classification-replay surfaces omit unique-finder bonus
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scoreboard-contract-output.txt
- **Severity**: latent
- **Concern**: When `LARCH_UNIQUE_FINDER_BONUS` is enabled, live tally scoreboards (`plan_review_tally.py`, `review_tally.py`) apply the bonus into printed `Score`, but classification-replay paths do not. `_scoreboard_points_from_classification()` (used by `python/cli.py voting scoreboard --findings-classification-file`) and `progress_report._top_reviewers_from_classification()` award only base accepted weights and never read `unique_finder_bonus_from_env()`. Replay scoreboards and run-summary Top reviewers can disagree with live `voting-tally.md` whenever the knob is on. The feature is experimental, off by default, and the plan scoped `plan_review_tally.py` and `review_tally.py` only; replay divergence predates or widens only when the env var is enabled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document that replay surfaces exclude the experimental bonus, or thread `unique_finder_bonus_from_env()` into those paths if parity is required.


