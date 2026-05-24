### FINDING_11: Retry prompt composition path lacks anchor assertion in harness (`scripts/test-dispatch-plan-voters.sh:63-65,151-174` vs `scripts/dispatch-plan-voters.sh:84-86`)
- **Reviewer(s)**: dyn-test-coverage-gaps-output.txt
- **Severity**: latent
- **Concern**: New anchor `grep -Fq` checks only healthy primary artifacts `codex-plan-voter-prompt.txt` and `cursor-plan-voter-prompt.txt` (`scripts/test-dispatch-plan-voters.sh:151-152`), while the absent-tools path already inspects `claude-plan-voter-prompt-retry.txt` for the retry header (`scripts/test-dispatch-plan-voters.sh:64`) and the `retry-waterfall` block exercises parse-rate retry without opening any `*-plan-voter-prompt-retry.txt` for the anchor (`scripts/test-dispatch-plan-voters.sh:159-174`). That leaves the retry prompt composition path unguarded even though `make_plan_voter_retry_prompt_file` is supposed to embed the full primary body after the prefix (`scripts/dispatch-plan-voters.sh:84-86`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-gaps-output.txt: **Suggested fix:** After line 64, assert the anchor in `$TMP/absent/claude-plan-voter-prompt-retry.txt`, and after the retry-waterfall section assert it in `$TMP/retry-waterfall/codex-plan-voter-prompt-retry.txt` (created when voter-2’s first pass is narrative-only), so regressions that drop `cat "$src_prompt_file"` or point `orig_prompt` at the wrong file fail the harness.


