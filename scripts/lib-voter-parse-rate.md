# lib-voter-parse-rate.sh

**Consumer**: `scripts/dispatch-code-voters.sh`, `scripts/dispatch-plan-voters.sh` (sourced library; not directly executed).

## Role

Shared **parse-rate** helpers for code-review and plan-review voter outputs: substantive vote-line checks (`check_voter_parse_rate`), one retry orchestration (`check_and_retry_voter_parse_rate`), retry prompt construction (`make_voter_retry_prompt_file`), and subprocess relaunch (`launch_voter_retry`).

## Environment contract

Callers set `LARCH_VPR_*` globals before invoking retry helpers (ballot path, tmpdir, id grammar `finding-only` vs `finding-oos`, retry prefix kind `code` vs `plan`, launcher plugin root, optional context argv). See source header comments in `lib-voter-parse-rate.sh`.

## Plan vs code ballots

`LARCH_VPR_RETRY_PREFIX_KIND=plan` selects the plan-ballot retry preamble (`FINDING_N:` / `OOS_N:` vote lines). `finding-oos` grammar counts both finding and OOS headings from the ballot when scoring judge errors.

The retry literals at the top of `lib-voter-parse-rate.sh` are the authoritative wording for retry prompts. `LARCH_VPR_RETRY_PREFIX_KIND` only selects between those constants; it does not define the line format. Both code and plan retry preambles require vote lines to carry `CORRECTNESS=`, `SEVERITY=`, `QUALITY=`, and `UNCERTAIN=` rating tokens.

Substantive parse-rate success is intentionally weaker than that retry ideal: any line that yields a parseable `PARSED_VOTE` (`YES`, `NO`, or `EXONERATE`) counts as substantive even when one or more rating axes are missing. The tally layer still records blank rating cells for partial rows, but the slot is no longer downgraded to `NOT_SUBSTANTIVE` solely because it omitted forensic metadata.

## Edit in sync

Update this file when changing parse-rate behavior, `dispatch-code-voters.sh`, `dispatch-plan-voters.sh`, or `scripts/test-dispatch-plan-voters.sh` / `scripts/test-dispatch-code-voters.sh` expectations.
