### OOS_1: [SCOPE-REDUCTION] Harness lists `round_runner.py` as a prompt-construction surface
- **Description**: [SCOPE-REDUCTION] Harness lists `round_runner.py` as a prompt-construction surface. Scenario: Round orchestration composes findings and env files; it does not assemble external-tool prompts or `claude_sub` prompt bodies. Adding it expands harness scope without guarding a Step 3/5 prefix path.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-50
- **Phase**: design



### OOS_2: [SCOPE-REDUCTION] Harness adds a non-prompt file
- **Description**: [SCOPE-REDUCTION] Harness adds a non-prompt file. Scenario: `round_runner.py` orchestrates rounds and delegates prompt rendering to other modules; it does not assemble external-tool prompts. Scanning it adds harness surface without advancing Step 3 or Step 5 prefix stability.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-60
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Harness lists round_runner.py as a prompt surface
- **Description**: [OUT_OF_SCOPE] Harness lists round_runner.py as a prompt surface. Scenario: `python/larch/review/round_runner.py` orchestrates round state and finding composition; it does not assemble external-tool prompts. Adding it to the cache-key file list expands harness scope without guarding a Step 3/5 instability source.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-cache-key-discipline.sh
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] Voter prompt assembly still interleaves dynamic ledger before ballot path
- **Description**: [OUT_OF_SCOPE] Voter prompt assembly still interleaves dynamic ledger before ballot path. Scenario: `render_voter_main` injects `_code_ledger_section` before the per-ballot `args.ballot_file` line, so growing ledgers can still invalidate the stable voting-instruction suffix on claude_sub voter calls in Step 5.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:1133-1200
- **Phase**: design



### OOS_5: Step 5 coder-fix prompt still embeds per-session paths mid-prompt
- **Description**: Step 5 coder-fix prompt still embeds per-session paths mid-prompt. Scenario: `_compose_coder_prompt` places `Read {findings_file}` and the session-directory line before the closing stable tail; that can reduce prefix reuse for `launch-claude-review-fix` `claude_sub` calls, but reviewer-volume `render specialist` fixes likely dominate Step 5 ratios and may satisfy acceptance without this change.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:356-380
- **Phase**: design



### OOS_6: round_runner.py listed without prompt construction
- **Description**: round_runner.py listed without prompt construction. Scenario: The harness expansion names `round_runner.py`, but the file only orchestrates review rounds and findings composition; it contains no prompt assembly strings or per-session path interpolation. Listing it adds maintenance surface without guarding prefix order.
- **Reviewer**: Cursor-dyn-Cache Prefix Reviewer
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-683
- **Phase**: design



