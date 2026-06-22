### OOS_2: [OUT_OF_SCOPE] Stale complexity-baseline rows for parse_argv_main
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: After the `design_argv.py` refactor, baseline rows still grandfather inflated metrics for `parse_argv_main` (e.g. PLR0915 metric 68) even though live audit likely no longer reports that symbol. Re-bloating `parse_argv_main` below those stale ceilings would not trip the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Re-run the audit generator and drop obsolete `design_argv.py` / `parse_argv_main` rows when simplifying the module.


### OOS_3: [OUT_OF_SCOPE] Missing symlink-escape test for aggregator/findings pair
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: #5038 adds a `_within_run_dir` guard on `findings.md` in `delete_identical_aggregator`, but there is no symlink-escape test for the aggregator/findings pair (unlike dyn-prompts, transcripts, tally, breadcrumbs).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a case where `aggregator-output.txt` is in-tree and `findings.md` is an escaping symlink; assert the external target is not read or deleted.


