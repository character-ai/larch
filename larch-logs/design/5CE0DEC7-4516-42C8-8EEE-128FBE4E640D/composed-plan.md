## Plan

### Approach

- Treat this as **retirement**, not a fresh port.
- Keep `python/file_oos.py` and `python/cli.py oos issue-cap` as the canonical runtime.
- Do **not** add a new module.
- Do **not** reconcile Python output to the deleted Bash helper beyond the accepted fixture behaviors below.
- Make the required output-string change in `file_oos.py`: remove the retired `skills/implement/scripts/oos-issue-cap.sh` path from the rollup `**Description**`.
- Close behavioral gaps in `issue_cap` / `issue_cap_main` so migrated Bash fixtures pass: missing-input fail-closed, same input/output rejection, stale output cleanup on failure, in-place failure input preservation.
- Delete the orphaned Bash helper, Python sub-helper, Bash harness, and their sibling contract docs.
- Migrate **all** unique `test-oos-issue-cap.sh` fixture coverage into `python/test_file_oos.py` (including excerpt-helper cases via `_excerpt_from_body` / `_excerpt_max_chars`).
- **Keep** `make test-oos-issue-cap` (already pytest-backed); update its docs row only.
- Remove retired path entries from `scripts/residual-bash-paths.txt` and `agent-lint.toml`; add retired paths to `python/migrated-scripts.tsv` with `#4968`.
- Repoint prose to `python/cli.py oos issue-cap` and `python/file_oos.py`.

### Files to modify/create

### UPDATED: python/file_oos.py

- Change the rollup `**Description**` string so it no longer names `skills/implement/scripts/oos-issue-cap.sh`; prefer wording like `rolled up by the per-run OOS issue cap`.
- At the start of `issue_cap`, require `input_file.is_file()`; raise `FileNotFoundError` (or equivalent `ValueError` with message `input file not found: …`) when the path is missing so `issue_cap_main` returns non-zero and creates no output.
- When `--output` is provided and resolves to the same real path as `--input-file`, reject with a non-zero error (`--input-file and --output resolve to the same path`); omit `--output` for in-place rewrite.
- On failure after `--output` was provided, delete any partially written output file (mirror Bash `cleanup_on_exit` stale-output behavior).
- On in-place failure, leave the input file byte-unchanged.
- Preserve existing cap math, excerpt semantics, file-ref extraction, heading renumbering, and env knob names unless a listed fixture requires a targeted fix.
- Invalid `OOS_ISSUES_PER_RUN_CAP` / `OOS_ISSUE_CAP_EXCERPT_MAX` should continue to raise with `must be a positive integer` wording; align CLI exit code with migrated invalid-env fixtures (Bash used `2`; return `2` from `issue_cap_main` for env validation failures if tests assert that).

### UPDATED: python/test_file_oos.py

- Migrate the full `skills/implement/scripts/test-oos-issue-cap.sh` fixture list into pytest under `-k issue_cap`, covering at least:
  - default cap exceeded
  - explicit cap exceeded
  - under-cap pass-through
  - equal-count pass-through
  - `cap=1` total rollup
  - empty input
  - invalid `OOS_ISSUES_PER_RUN_CAP` (zero, non-numeric, negative, empty)
  - invalid `OOS_ISSUE_CAP_EXCERPT_MAX` (zero, non-numeric, empty)
  - malformed OOS blocks with and without body content
  - in-place rewrite
  - heading renumbering
  - parser/heading parity mismatch
  - non-OOS input rejection
  - missing input file (non-zero, no output created)
  - stale output deleted on failure
  - in-place failure preserves input bytes
  - same input/output path rejected
  - UTF-8 truncation without replacement characters and with ellipsis
  - markdown normalization in aggregate bullets
  - file reference preservation after excerpt cutoff
  - excerpt max validation (zero, non-numeric, negative) via Python excerpt helpers
- Invoke `python/cli.py oos issue-cap` (or `issue_cap_main`) for CLI-path cases; call excerpt helpers directly for former `oos-issue-cap-excerpt.py` cases.
- Add small helpers only as needed; avoid retired-path literals in fixtures.
- Land migrated tests **before** deleting the Bash harness files.

### UPDATED: python/migrated-scripts.tsv

- Append all six retired paths with `#4968`:
  - `skills/implement/scripts/oos-issue-cap.sh`
  - `skills/implement/scripts/oos-issue-cap.md`
  - `skills/implement/scripts/oos-issue-cap-excerpt.py`
  - `skills/implement/scripts/oos-issue-cap-excerpt.md`
  - `skills/implement/scripts/test-oos-issue-cap.sh`
  - `skills/implement/scripts/test-oos-issue-cap.md`

### UPDATED: scripts/residual-bash-paths.txt

- Remove `skills/implement/scripts/test-oos-issue-cap.sh`.

### UPDATED: agent-lint.toml

- Remove the four G004 allowlist entries for `test-oos-issue-cap.{sh,md}` and `oos-issue-cap-excerpt.{py,md}`.
- Delete or rewrite adjacent comment lines so no retired full path or basename remains outside `python/migrated-scripts.tsv`.
- No replacement entries needed; `python/test_file_oos.py` remains reachable via `skills/implement/SKILL.md`.

### UPDATED: docs/linting.md

- **Keep** the `make test-oos-issue-cap` row and `test-harnesses-12` wiring.
- Rewrite the row to describe pytest-backed coverage (`python3 -m pytest python/test_file_oos.py -q -k issue_cap`) instead of the deleted Bash harness paths.
- Keep `test-oos-file-conflict-deps` unchanged.

### UPDATED: docs/configuration-and-permissions.md

- Repoint `OOS_ISSUES_PER_RUN_CAP` and `OOS_ISSUE_CAP_EXCERPT_MAX` prose from the Bash helper to `python/cli.py oos issue-cap` / `python/file_oos.py`.
- Prefer non-zero failure wording over Bash-specific exit-code wording unless tests pin a specific code.
- Keep the warning string unchanged unless fixture migration requires a synchronized prose update.

### UPDATED: skills/implement/SKILL.md

- Remove machine-reachability references to `skills/implement/scripts/oos-issue-cap.sh`.
- Repoint the cap contract sentence from the deleted `.md` file to `python/cli.py oos issue-cap` and `python/file_oos.py`.
- Keep `python/test_file_oos.py` and `make test-oos-issue-cap` as harness references.

### UPDATED: skills/design/SKILL.md

- Replace the parenthetical `oos-issue-cap.sh` failure reference with `python/cli.py oos issue-cap`.
- Do not change Step 5b control flow.

## Files to delete

- `skills/implement/scripts/oos-issue-cap.sh`
- `skills/implement/scripts/oos-issue-cap.md`
- `skills/implement/scripts/oos-issue-cap-excerpt.py`
- `skills/implement/scripts/oos-issue-cap-excerpt.md`
- `skills/implement/scripts/test-oos-issue-cap.sh`
- `skills/implement/scripts/test-oos-issue-cap.md`

## Edge cases

- Missing `--input-file` must fail closed with non-zero exit and no output file created.
- Explicit `--output` equal to `--input-file` must be rejected; in-place rewrite omits `--output`.
- Failure after `--output` is set must remove a stale output file if one was created.
- In-place failure must preserve input bytes.
- Invalid env tests isolate env with `monkeypatch`.
- UTF-8 tests assert no U+FFFD replacement character and an ellipsis when truncated.
- Retired paths may remain only in `python/migrated-scripts.tsv`.

## Failure modes

- `make lint-retired-scripts` fails if retired paths remain in docs, skills, `agent-lint.toml`, or runtime strings.
- Deleting Bash harness files before pytest migration lands drops focused `issue_cap` CI coverage even though `make test-oos-issue-cap` already invokes pytest.
- Pytest under-constrains behavior if fixtures are dropped instead of migrated.

## Testing strategy

- Land `python/test_file_oos.py` `issue_cap` coverage first; confirm `make test-oos-issue-cap` passes.
- Run `cd python && python3 -m pytest test_file_oos.py -q -k 'issue_cap'`.
- Run `make py-test`.
- Run `make py-lint`.
- Run `make lint-retired-scripts`.
- Run `make lint`.

## Acceptance

- `python/test_file_oos.py` covers the full migrated `test-oos-issue-cap.sh` fixture set under `-k issue_cap`; `make test-oos-issue-cap`, `make py-test`, and `make py-lint` pass.
- UTF-8-safe excerpt truncation preserved (no U+FFFD replacement char; ellipsis on overflow). `issue_cap` runtime output is unchanged except the rollup `**Description**` string no longer names the retired `oos-issue-cap.sh` path.
- New safety behaviors hold: missing input fails closed with no output created; `--output` equal to `--input-file` rejected; stale output removed on failure; in-place failure preserves input bytes.
- The six retired files are deleted, recorded in `python/migrated-scripts.tsv` with `#4968`, and removed from `scripts/residual-bash-paths.txt` and `agent-lint.toml`.
- Prose in `skills/implement/SKILL.md`, `skills/design/SKILL.md`, `docs/configuration-and-permissions.md`, and `docs/linting.md` points at `python/cli.py oos issue-cap` / `python/file_oos.py`, not the retired Bash paths.
- `make lint-retired-scripts` and `make lint` are clean.

review_status: complete
rounds_completed: 2
diff_added: 240
diff_deleted: 920
mechanical_churn: false
diff_lines: 1160
