# lib-voter-parse-rate.sh

**Consumer**: `scripts/dispatch-code-voters.sh`, `scripts/dispatch-plan-voters.sh` (sourced library; not directly executed).

## Role

Shared **parse-rate** helpers for code-review and plan-review voter outputs: substantive vote-line checks (`check_voter_parse_rate`), one retry orchestration (`check_and_retry_voter_parse_rate`), retry prompt construction (`make_voter_retry_prompt_file`), and subprocess relaunch (`launch_voter_retry`).

## Environment contract

Callers set `LARCH_VPR_*` globals before invoking retry helpers (ballot path, tmpdir, id grammar `finding-only` vs `finding-oos`, retry prefix kind `code` vs `plan`, launcher plugin root, optional context argv). See source header comments in `lib-voter-parse-rate.sh`.

## Plan vs code ballots

`LARCH_VPR_RETRY_PREFIX_KIND=plan` selects the plan-ballot retry preamble (`FINDING_N:` / `OOS_N:` vote lines). `finding-oos` grammar counts both finding and OOS headings from the ballot when scoring judge errors.

The retry literals near the top of `lib-voter-parse-rate.sh`
(`VOTER_PARSE_RATE_RETRY_PREFIX_CODE` and
`VOTER_PARSE_RATE_RETRY_PREFIX_PLAN`) are the normative source for retry
wording. `LARCH_VPR_RETRY_PREFIX_KIND` only selects between those literals.
Both retry prompts require the extended line shape: vote token first, then
lowercase forensic axes (`CORRECTNESS`, `SEVERITY`, `QUALITY`, `UNCERTAIN`).
Axis tokens must appear before any optional `-- reason` delimiter because the
parser ignores axis-looking text after that delimiter.

## Edit in sync

Update this file when changing parse-rate behavior, `dispatch-code-voters.sh`, `dispatch-plan-voters.sh`, or `scripts/test-dispatch-plan-voters.sh` / `scripts/test-dispatch-code-voters.sh` expectations.
