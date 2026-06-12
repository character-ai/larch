## Goal
Implement issue #3927: [IMPLEMENTING] sh-to-py F3e: Tracking-issue lifecycle (tracking-issue-read/write/summary)\n\nPartition piece 5 of 5 split from #3669..

## Implementation Plan
## Plan

### Approach

- Treat `NO_SKETCHES_CLASSIFIED_SIMPLE` as binding.
- Draft from direct repo inspection, not sketch agreement.
- Honor round-1 scope:
  - Implement all four `tracking-issue read` modes.
  - Cut over `skills/implement/scripts/step-0-bootstrap.sh`.
  - Cut over remaining live tracking lifecycle consumers.
  - Delete retired tracking issue shell helpers and harnesses.
- Preserve shell contracts:
  - `KEY=value` stdout on normal success paths.
  - exit `0` for success.
  - exit `1` for usage or validated content rejection.
  - exit `2` for `gh` failures.
  - exit `3` only for compose-time redaction failures where the old shell used it.
- Preserve stream parity:
  - `upsert-summary` success KVs go to stdout.
  - `upsert-summary` non-usage failure `FAILED=true` and `ERROR=` go to stderr.
  - `read` shell-level usage and validation failure envelopes go to stdout (`FAILED=true` and `ERROR=`).
  - `read` parser-level usage failures that Bash handled before `fail_usage`, such as missing option values, keep stderr-only usage diagnostics and no stdout envelope.
  - Other tracking write verbs keep stdout failure envelopes for envelope-producing validation, `gh`, and redaction failures.
  - Write-verb usage errors stay stderr-only and do not emit stdout failure envelopes.
- Initialize quiet routing at the start of every tracking-issue CLI main before any contract output.
- Keep existing public Python functions stable where possible.
  - Public `tracking_issue.rename(runner, issue, state, *, repo, current_title, cwd) -> str` keeps its current signature and string return type for `finalize.py` and other library callers.
  - Put shell-grade rename idempotency, redacted canonical comparison, prefix detection, truncation, and transient `gh issue edit` retry in a private shared rename core.
  - Public `rename()` delegates to that core with the supplied `current_title` and performs no second `gh` title fetch.
  - `rename_main` fetches the current title, calls the same core, and owns KV emission only.
- Add CLI-specific helpers when the shell CLI needs URLs, IDs, retry envelopes, `RENAMED=` details, or summary body composition that current public functions do not expose.
- Use `issue_wire.insert_signal_marker()` directly for false-positive marking.
- Use existing `gh.py`, `redact.py`, `retry.py`, `proc.Runner`, and `logging_util` seams.
- Do not retry `create-issue`.
  - It is not idempotent.
- Retry transient `gh issue comment` and `gh issue edit` failures for append, rename, false-positive, and summary upsert.
- Keep read mode 1 non-idempotent.
  - It must append the prompt before reading.
  - It must map delegated append failures to read exit `2`.
- Do not add or revive `scripts/upsert-diagrams-comment.sh`.
  - That helper is already retired.
  - Keep diagrams coverage to the existing Python rendering audit.

### UPDATED: python/tracking_issue.py

Add the missing tracking lifecycle surface.

- Add constants for:
  - read caps: body `8000`, comments `50`, total `100000`.
  - read cap override flag names:
    - `--max-body-chars`
    - `--max-comments`
    - `--max-total-chars`
  - lifecycle marker prefix.
  - managed lifecycle prefixes, including legacy `[IN PROGRESS]` and `[PLANNED]`.
  - skipped first-line marker prefixes copied exactly from the retired read helper, including:
    - metadata summary markers.
    - diagrams markers, with both `<!-- larch:diagrams v1 -->` and `<!-- larch:diagrams v1 runid=... -->` forms.
    - plan markers.
    - token-report markers.
    - final-summary markers and run-id variants.
    - legacy `<!-- larch:implement-anchor v1 ` markers.
  - issue read envelope preamble.
- Add a public `strip_lifecycle_prefix(title: str) -> str` helper:
  - strip exactly one managed or legacy lifecycle prefix at the start.
  - share the same prefix family used by rename.
  - leave stacked prefixes after the first intact.
  - use this helper from shared rename logic and prompt documentation.
  - do not use `issue title-eligibility` for prefix stripping.
- Add small result dataclasses or typed dicts for:
  - `read` output.
  - `create_issue` output.
  - shared rename core output (`renamed: bool`, `new_title: str`).
  - `mark_false_positive` output.
  - `upsert_summary` output.
- Add parser helpers:
  - numeric issue validation.
  - repo resolution through `gh.resolve_repo_gh_only`.
  - repo slug validation with `gh.validate_repo_slug`.
  - read out-dir validation.
  - read cap override parsing and validation with the same defaults as the retired shell helper.
  - marker-shape validation for `upsert-summary`.
  - body and content file reading with empty-body checks where shell required them.
  - fixed-token sentinel validation errors.
  - raw `KEY=value` emission.
  - lifecycle prefix stripping through `strip_lifecycle_prefix()`.
  - issuecomment URL parsing and `COMMENT_ID` derivation.
- Add a per-main exit-code table in code comments and tests:
  - `read_main`: exits `0`, `1`, or `2`; never `3`.
  - `create_issue_main`: exits `0`, `1`, `2`, or `3`.
  - `append_comment_main`: exits `0`, `1`, `2`, or `3`.
  - `rename_main`: exits `0`, `1`, `2`, or `3`.
  - `mark_false_positive_main`: exits `0`, `1`, `2`, or `3`.
  - `upsert_summary_main`: exits `0`, `1`, `2`, or `3`.
- At the start of each CLI main:
  - call `logging_util.quiet_init(...)` before parsing emits contract output.
  - ensure success KVs use raw stdout, not quiet diagnostics.
  - ensure `upsert_summary_main` failure envelopes use diagnostic stderr routing.
  - preserve stderr-only usage errors for write verbs.
- Add read mode implementation:
  - `--sentinel PATH` standalone:
    - reject combined flags before side effects.
    - strip leading UTF-8 BOM only at file start.
    - match only column-0 `ISSUE_NUMBER=`, `RUN_ID=`, `ADOPTED=`.
    - first match wins.
    - strip only trailing `\r`.
    - validate non-empty `ISSUE_NUMBER` as digits.
    - validate non-empty `RUN_ID` as `[A-Za-z0-9._-]+`.
    - validate non-empty `ADOPTED` as exactly `true` or `false`.
    - accept empty `ADOPTED=` as unusable, not false.
    - emit `ISSUE_NUMBER=`, `RUN_ID=`, `ADOPTED=`.
  - `--prompt TEXT --out-dir PATH` and stdin `--out-dir PATH`:
    - validate explicit `--out-dir` exists and is a directory before writing `task.md`.
    - write prompt text to `<out-dir>/task.md`.
    - apply only `--max-total-chars`.
    - do not touch GitHub.
    - emit `ISSUE_NUMBER=`, `TASK_SOURCE=prompt`, `TASK_FILE=...`.
  - `--issue N --out-dir PATH [--repo OWNER/REPO]`:
    - validate explicit `--out-dir` exists and is a directory before writing `task.md`.
    - fetch issue body and comments.
    - wrap fetched content in `external_issue_body` and `external_issue_comment`.
    - filter summary, lifecycle, diagrams, plan, token-report, final-summary, and legacy implement-anchor comments by exact first-line marker patterns.
    - tolerate BOM and trailing `\r` in first-line matching.
    - preserve truncation markers inside content.
    - cap body, comments, and total task file.
    - emit `TASK_SOURCE=issue-only`.
  - `--issue N --prompt TEXT --out-dir PATH [--repo OWNER/REPO]`:
    - validate explicit `--out-dir` exists and is a directory before writing `task.md`.
    - delegate to the same shell-parity internal append helper used by `append_comment_main`.
    - preserve append retry behavior.
    - require parseable `COMMENT_ID` and `COMMENT_URL` recovery before fetching issue context.
    - if delegated append fails, emit `FAILED=true` and `ERROR=append-comment failed: ...` on stdout and exit `2`.
    - map delegated append validation, redaction, and `gh` failures to read exit `2`.
    - never propagate append-only exit `3` through `read_main`.
    - then fetch and render as above.
    - append operator prompt unwrapped at the end.
    - emit `TASK_SOURCE=issue-plus-prompt`.
- Wire `read_main` argparse for:
  - `--max-body-chars`
  - `--max-comments`
  - `--max-total-chars`
- Validate read cap overrides before side effects.
- Document `read_main` stream contract:
  - shell-level usage failures such as invalid flag combinations, non-numeric `--issue`, and missing required mode flags emit `FAILED=true` and `ERROR=usage:...` on stdout.
  - parser-level usage failures that the shell handled before `fail_usage`, such as missing option values, emit usage diagnostics on stderr with no stdout envelope.
  - non-usage validation failures use the stdout failure envelope.
- Add `create_issue`:
  - accept `--title`, `--body-file`, optional `--repo`.
  - resolve repo if omitted.
  - reject missing or empty body file.
  - compose outbound title and body.
  - redact tmpdir paths first.
  - redact secrets second.
  - fail closed with exit `3` on compose-time secret redaction failure.
  - do not retry `gh issue create`.
  - parse and emit `ISSUE_NUMBER=` and `ISSUE_URL=`.
  - fail if `gh` succeeds but emits no issue URL.
- Add CLI-specific append-comment helper:
  - keep existing `append_comment()` behavior stable for library callers.
  - share validation and body composition.
  - redact tmpdir paths first.
  - redact secrets second.
  - fail closed with exit `3` on compose-time secret redaction failure.
  - wrap `gh issue comment` in the same transient retry pattern used by existing marker-comment upserts.
  - require a parseable `#issuecomment-<id>` URL for success.
  - derive `COMMENT_ID` from the parsed URL.
  - if `gh issue comment` exits `0` but no parseable issuecomment URL is recovered, emit the stdout failure envelope and exit `2`.
  - expose an internal result/error form that `read --issue --prompt` can consume without leaking append-only exit codes.
  - preserve lifecycle marker charset and `--` rejection diagnostics.
- Add a private shared shell-parity rename core, for example `_rename_shell_parity` or `rename_with_details`:
  - accept `runner`, `issue`, `state`, `repo`, `current_title`, optional `cwd`.
  - redact the supplied current title before canonical comparison.
  - detect the current canonical lifecycle prefix family from the redacted current title.
  - rebuild the canonical current title from that detected prefix plus the stripped current title.
  - build the prospective new title with the requested lifecycle prefix plus `strip_lifecycle_prefix()` output.
  - preserve managed prefix under 256-character truncation.
  - redact tmpdir paths first.
  - redact secrets second.
  - truncate again after redaction.
  - compare the prospective redacted title against the redacted canonical current title before `gh issue edit`.
  - edit only when the canonical redacted title differs.
  - wrap `gh issue edit` in the same transient retry pattern used by existing marker-comment upserts.
  - return `renamed: bool` and `new_title: str`.
  - keep KV emission out of the shared core.
- Refactor public `rename()` as a stable adapter:
  - keep `rename(runner, issue, state, *, repo, current_title, cwd) -> str`.
  - delegate to the shared rename core with the supplied `current_title`.
  - do not perform a second `gh` title fetch inside public `rename()`.
  - return the final title string from the core result.
  - preserve existing `finalize.py` caller semantics.
- Add `rename_main`:
  - fetch current title when the CLI path needs it.
  - call the shared rename core.
  - emit `RENAMED=true|false` and `NEW_TITLE=...` on stdout.
- Add `mark_false_positive`:
  - fetch current title.
  - redact tmpdir paths first.
  - redact secrets second.
  - call `issue_wire.insert_signal_marker(title, "FALSE-POSITIVE")`.
  - compare the marker insertion result against the redacted current title before truncation.
  - if unchanged, skip edit and emit `MARKED=false` with `NEW_TITLE=` set to the current redacted title.
  - only truncate the final title to 256 chars after detecting a newly inserted marker.
  - edit only when changed.
  - retry transient `gh issue edit` failures.
  - emit `MARKED=true|false` and `NEW_TITLE=...`.
- Add `upsert_summary_main`:
  - accept `--issue`, `--marker`, `--content-file`, optional `--repo`, optional `--comment-id`.
  - validate marker shape before GitHub calls.
  - validate repo before GitHub calls.
  - invalid repo exits `1` with `ERROR=invalid repo: expected OWNER/REPO`.
  - compose the marker comment body as `f"{marker}\n\n{content}"` to match `scripts/tracking-issue-summary.sh`.
  - do not route summary upserts through `upsert_marker_comment()` or `_upsert_marker_comment()` unchanged.
  - redact tmpdir paths first.
  - treat tmpdir redaction helper failure as best effort and preserve the original body.
  - redact secrets second.
  - fail closed with exit `3` on secret redaction failure.
  - reject duplicate marker comments when searching by marker.
  - let `--comment-id` bypass marker search and patch that exact comment.
  - retry transient `gh issue comment` and `gh api` patch failures.
  - on success, emit stdout fields:
    - `COMMENT_ID=`
    - `COMMENT_URL=`
    - `UPDATED=true|false`
  - on create success, preserve shell parity for empty `COMMENT_ID=` if the old helper could not recover an ID.
  - on non-usage failure, emit `FAILED=true` and `ERROR=` to stderr, not stdout.
  - on usage failure, keep stderr-only behavior.
- Add `main_*` entry points:
  - `read_main`
  - `create_issue_main`
  - `append_comment_main`
  - `rename_main`
  - `mark_false_positive_main`
  - `upsert_summary_main`
- Make each CLI main catch expected failures and emit the old envelope only for envelope-producing paths.
- Redact or replace `gh` stderr with a generic token-free error before surfacing it.

### UPDATED: python/cli.py

Register the new domain and verbs.

- Add:
  - `("tracking-issue", "read")`
  - `("tracking-issue", "create-issue")`
  - `("tracking-issue", "append-comment")`
  - `("tracking-issue", "rename")`
  - `("tracking-issue", "mark-false-positive")`
  - `("tracking-issue", "upsert-summary")`

### UPDATED: python/test_tracking_issue.py

Expand pytest coverage and replace shell harness parity.

- Add sentinel tests:
  - valid values.
  - missing file.
  - unreadable file where practical.
  - CRLF.
  - leading BOM.
  - indented keys ignored and emitted as empty values.
  - column-0-only parsing.
  - duplicate first-match wins.
  - invalid `ISSUE_NUMBER`, `RUN_ID`, and `ADOPTED` use fixed-token errors.
  - empty `ADOPTED` is accepted as unusable, not false.
  - combined `--sentinel` flags fail before side effects.
- Add read-mode tests:
  - prompt-only flag.
  - stdin mode through CLI main.
  - explicit `--out-dir` missing or non-directory fails before writing `task.md`.
  - issue-only body and comments.
  - issue-plus-prompt delegates append before fetch.
  - issue-plus-prompt uses the shell-parity append helper with retry and comment URL recovery.
  - issue-plus-prompt maps append validation, redaction, and `gh` failures to read exit `2`.
  - issue-plus-prompt emits `ERROR=append-comment failed: ...` on stdout for append failure.
  - issue-plus-prompt does not leak append exit `3`.
  - summary marker filters.
  - lifecycle marker filters.
  - diagrams marker filters for plain and run-id forms.
  - plan, token-report, and final-summary marker filters, including run-id variants.
  - legacy implement-anchor first-line filter.
  - `max-body-chars`, `max-comments`, and `max-total-chars` defaults and override flags.
  - invalid read cap override values fail before side effects.
  - malformed JSON from comments fails safely.
- Add lifecycle helper tests:
  - `strip_lifecycle_prefix()` strips exactly one managed prefix.
  - legacy `[IN PROGRESS]` and `[PLANNED]` strip.
  - stacked prefixes keep every prefix after the first.
  - titles without managed prefixes are unchanged.
- Add write tests:
  - `create-issue` success URL parsing.
  - create without URL fails.
  - create does not retry.
  - append emits `COMMENT_ID` and `COMMENT_URL`.
  - append retries transient `gh issue comment` failures.
  - append treats `gh issue comment` rc `0` without a parseable issuecomment URL as exit `2` with stdout failure envelope.
  - lifecycle marker rejection messages.
  - shared rename core redacts current title before canonical comparison.
  - shared rename core detects canonical prefixes from the redacted current title.
  - shared rename core compares prospective `NEW_TITLE` against the redacted canonical current title before editing.
  - shared rename core returns `renamed=false` without `gh issue edit` when a redactable current title is already canonical.
  - public `rename()` adapter delegates to the shared core with supplied `current_title` and returns the final title string.
  - rename retries transient `gh issue edit` failures.
  - rename idempotency with redacted canonical current title.
  - rename emits `NEW_TITLE=` on `RENAMED=true`.
  - rename emits `NEW_TITLE=` on `RENAMED=false`.
  - legacy prefix stripping.
  - stacked prefix leaves all but one prefix intact.
  - false-positive mark inserts after lifecycle prefix.
  - false-positive compares against the redacted current title before truncation.
  - false-positive already-marked titles emit `MARKED=false`, skip edit, and preserve the redacted current title in `NEW_TITLE=`.
  - false-positive truncates only after detecting a newly inserted marker.
  - false-positive retries transient edit failures.
  - outbound tmpdir redaction runs before secret redaction.
  - secret redaction failures exit `3` where shell did.
  - summary upsert composes posted and patched bodies as `marker\n\ncontent`.
  - summary upsert creates, patches, rejects duplicate marker comments, and honors `--comment-id`.
  - summary upsert emits `COMMENT_ID=`, `COMMENT_URL=`, and `UPDATED=` on create, patch, and `--comment-id` success paths.
  - summary upsert failures emit `FAILED=true` and `ERROR=` to stderr.
  - summary upsert validates marker shape.
  - summary upsert validates repo shape before GitHub calls.
- Add quiet-routing tests:
  - each tracking-issue main calls quiet initialization before contract output.
  - representative success KVs still land on stdout under inherited quiet environment.
  - `upsert-summary` failure lines land on redirected stderr under inherited quiet environment.
  - quiet diagnostics never swallow or reroute `KEY=value` stdout.
- Add usage-stream tests:
  - write-verb usage errors emit usage diagnostics on stderr only.
  - write-verb usage errors do not emit `FAILED=true` or `ERROR=` to stdout.
  - `read` shell-level usage errors emit `FAILED=true` and `ERROR=usage:...` on stdout with empty stderr.
  - `read` parser-level missing option value cases emit stderr usage diagnostics with no stdout envelope.
  - `read` invalid flag combination and non-numeric `--issue` coverage.
  - envelope-producing validation errors still use the old failure envelope stream.
- Add `gh` stderr sanitization tests:
  - runner stderr containing a token-shaped value does not appear in `ERROR=`.
  - redaction or truncation fallback uses generic token-free text.
  - token-shaped stderr is not copied to stdout or stderr envelopes.
- Add stream-placement parity tests for all six verbs with three rows per verb:
  - success: success KVs on stdout, no failure envelope.
  - usage:
    - `read` shell-level usage: stdout `FAILED=true` and `ERROR=usage:...`.
    - `read` parser-level missing option values: stderr usage only, no stdout failure envelope.
    - write verbs: stderr-only usage diagnostics, no stdout failure envelope.
  - non-usage:
    - `read`, `create-issue`, `append-comment`, `rename`, and `mark-false-positive`: stdout `FAILED=true` and `ERROR=...`.
    - `upsert-summary`: stderr `FAILED=true` and `ERROR=...`.
  - cover representative exit `1`, exit `2`, and exit `3` paths.
- Add exit-code parity tests:
  - `read_main` uses only `0`, `1`, and `2`.
  - write mains use `3` only for compose-time redaction failures.
  - `upsert_summary_main` uses `3` for redaction failure.
- Add CLI registry smoke tests through `cli.main()` for all six verbs.

### UPDATED: skills/design/SKILL.md

Cut over the clarify success rename path.

- Replace the embedded `scripts/tracking-issue-write.sh rename` command with:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename ...`
- Preserve existing guards.
- Preserve best-effort behavior.
- Preserve `RENAMED=` parsing.
- Preserve `NEW_TITLE=` parsing if the prompt checks already-designed or clarified titles.
- Update helper-name text in warnings only where it names the retired shell helper.

### UPDATED: skills/design/scripts/design-init-runparams.sh

Cut over the `[DESIGNING]` rename.

- Replace `scripts/tracking-issue-write.sh rename` with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename ...`
- Keep `RENAMED=` parsing unchanged.
- Keep warning behavior unchanged except helper name text.
- Parse `NEW_TITLE=` if the existing success predicate needs it.

### UPDATED: skills/design/scripts/design-publish.sh

Cut over the `[DESIGNED]` rename path.

- Replace helper invocation with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename ...`
- Preserve best-effort behavior.
- Preserve `RENAMED=false` idempotent success.
- Preserve parsing of `NEW_TITLE=` when `RENAMED=false`.
- Update warning text that tells operators what command to run manually.

### UPDATED: skills/design/scripts/design-publish.md

Retarget the design publish contract.

- Replace retired helper references with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename ...`
- Preserve ordering and best-effort contract text.
- Remove bare retired helper names unless the lint manifest explicitly permits them.

### UPDATED: skills/design/scripts/render-final-summary.sh

Cut over final-summary comment upserts.

- Replace `tracking-issue-summary.sh upsert-summary` with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Pass `--issue`, `--marker`, `--content-file`, optional `--repo`, and optional `--comment-id`.
- Keep stdout file and stderr file handling stable.
- Expect success fields on stdout.
- Expect failure `FAILED=true` and `ERROR=` in the stderr file.

### UPDATED: skills/implement/SKILL.md

Cut over emergency title fallback references and tracking summary references.

- Replace `/implement --emergency` preflight references to deleted shell prefix-stripping logic.
- Document the exact fallback title rule:
  - use the same prefix family as `python/tracking_issue.py`.
  - strip exactly one managed or legacy lifecycle prefix.
  - keep any stacked prefix after the first.
  - preserve the rest of the title byte-for-byte except for the one stripped prefix.
- Reference `tracking_issue.strip_lifecycle_prefix()` as the source of truth for this behavior.
- Add the explicit callable preflight pattern:
  - `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" python3 -c 'import sys; from tracking_issue import strip_lifecycle_prefix; print(strip_lifecycle_prefix(sys.argv[1]))' "$title"`
- Do not point the fallback at `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" issue title-eligibility`.
  - That verb reports eligibility only.
  - It does not emit a prefix-stripped title.
- Replace Invariant #2 and other tracking summary command examples with explicit Python CLI forms:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Do not reintroduce deleted shell helpers.

### UPDATED: skills/implement/references/summary-comment-template.md

Retarget the summary comment contract.

- Replace retired summary helper examples with:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Preserve marker shape and body framing requirements.
- Preserve `COMMENT_ID=`, `COMMENT_URL=`, and `UPDATED=` parsing guidance.
- Preserve failure envelope guidance on stderr.

### UPDATED: scripts/implement-bootstrap.sh

Cut over tracking lifecycle calls.

- Replace rename to implementing with:
  - `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue rename ...`
- Replace both `--sentinel` reads with:
  - `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue read --sentinel ...`
- Replace plan summary upsert with:
  - `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue upsert-summary ...`
- Keep existing tmpdir stdout and stderr capture paths unless tests require updated names.
- For summary upsert, keep stdout and stderr captures separate.
- Update `--tool` labels and warning text to the new CLI command.

### UPDATED: skills/implement/scripts/step-0-bootstrap.sh

Cut over the sentinel read.

- Replace `tracking-issue-read.sh --sentinel` with:
  - `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue read --sentinel ...`
- Preserve fallback behavior when the sentinel is unusable.
- Preserve empty `ADOPTED=` semantics.

### UPDATED: scripts/implement-finalize.sh

Cut over Step 18 rename.

- Replace `tracking-issue-write.sh rename` with:
  - `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue rename ...`
- Preserve best-effort stalled and done rename behavior.
- Update warning text only where it names the retired helper.
- Preserve `RENAMED=` and `NEW_TITLE=` parsing where present.

### UPDATED: scripts/implement-finalize.md

Retarget the finalize contract.

- Replace retired rename helper examples with:
  - `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue rename ...`
- Preserve best-effort and failure recording contract text.
- Remove bare retired helper names unless the lint manifest explicitly permits them.

### UPDATED: scripts/ship-pr.sh

Cut over postmerge done rename.

- Replace legacy bash rename with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename ...`
- Use the plugin-root-resolved CLI in both `--repo` and ambient-repo branches.
- Do not use cwd-relative `python3 python/cli.py`.
- Preserve `--repo` behavior.
- Preserve failure recording phase and exit handling.
- Preserve `RENAMED=` and `NEW_TITLE=` parsing where present.

### UPDATED: skills/implement/scripts/post-tracking-issue.sh

Cut over metadata summary upsert.

- Replace `tracking-issue-summary.sh` with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Preserve marker shape.
- Preserve output parsing.
- Expect success fields on stdout and failure envelope on stderr.

### UPDATED: skills/implement/scripts/refresh-execution-issues.sh

Cut over execution-issues summary upsert.

- Replace `tracking-issue-summary.sh` with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Preserve output and error files.
- Preserve best-effort warning behavior.
- Expect success fields on stdout and failure envelope on stderr.

### UPDATED: skills/implement/scripts/write-final-report.sh

Cut over final-summary and token/report upserts.

- Replace `tracking-issue-summary.sh` with:
  - `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary ...`
- Preserve comment-only and full-report modes.
- Preserve `COMMENT_ID`, `COMMENT_URL`, and `UPDATED` parsing.
- Expect failure envelope on stderr.

### UPDATED: python/rendering.py

Audit only.

- Confirm diagrams already use `tracking_issue.upsert_marker_comment` or the live Python diagrams upsert path.
- Do not add a shell wrapper for diagrams.
- Do not target absent `scripts/upsert-diagrams-comment.sh`.

### UPDATED: scripts/test-implement-finalize.sh

Update stubs and assertions.

- Stub `python/cli.py tracking-issue rename` instead of `tracking-issue-write.sh`.
- Keep failure warning assertions aligned with the new helper label.
- Preserve `RENAMED=` and `NEW_TITLE=` cases where covered.

### UPDATED: scripts/test-step0b-router-flag-recovery.sh

Update design rename stubs.

- Stub `python/cli.py tracking-issue rename`.
- Update expected warning text where it names `tracking-issue-write.sh`.
- Remove or retarget bare `tracking-issue-write` assertion tokens.

### UPDATED: skills/design/scripts/test-design-publish.sh

Update publish rename stubs.

- Stub the Python CLI command.
- Preserve ordering assertions:
  - plan write.
  - diagrams upsert.
  - rename.
  - log publish.
- Assert `NEW_TITLE=` is parsed when `RENAMED=false`.
- Remove or retarget bare retired-helper assertion tokens.

### UPDATED: skills/implement/scripts/test-implement-bootstrap.sh

Update tracking read, rename, and summary stubs.

- Stub `python/cli.py tracking-issue read --sentinel`.
- Stub `python/cli.py tracking-issue rename`.
- Stub `python/cli.py tracking-issue upsert-summary`.
- Preserve branch coverage for resume and adopt paths.
- Preserve separate stdout and stderr capture assertions for summary upsert.
- Remove or retarget bare retired-helper assertion tokens.

### UPDATED: skills/implement/scripts/test-post-tracking-issue.sh

Update summary helper stubs.

- Stub the Python CLI.
- Preserve metadata marker and `POSTED=` behavior assertions.
- Preserve stderr failure assertions.
- Remove or retarget bare `tracking-issue-summary` assertion tokens.

### UPDATED: skills/implement/scripts/test-refresh-execution-issues.sh

Update summary helper stubs.

- Stub the Python CLI.
- Preserve warning and no-op behavior tests.
- Preserve stderr failure assertions.
- Remove or retarget bare `tracking-issue-summary` assertion tokens.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

Update final-report helper stubs.

- Stub `tracking-issue upsert-summary`.
- Preserve comment URL and update-state assertions.
- Preserve `COMMENT_ID`, `COMMENT_URL`, and `UPDATED` parsing.
- Remove or retarget bare retired-helper assertion tokens.

### UPDATED: skills/implement/scripts/test-step-7a.sh

Remove the deleted summary-helper dependency.

- Stop copying or chmodding `scripts/tracking-issue-summary.sh`.
- Stub the Python CLI path used for summary or diagrams upserts.
- Remove stale assertions that depend on retired helper literals, including bare helper tokens.
- Preserve Step 7a coverage for diagrams and tracking comment behavior.

### UPDATED: skills/implement/scripts/test-step-18b-final-report.sh

Update integration stubs.

- Stub the Python CLI summary command in plugin fixtures.
- Preserve final-report state assertions.
- Remove or retarget bare retired-helper assertion tokens.

### UPDATED: scripts/test-legacy-title-prefix-literals-scope.sh

Retarget the literal-scope check.

- Remove retired shell helper paths.
- Keep coverage for lifecycle prefix literals in `python/tracking_issue.py` and tests.
- Keep coverage for prompt references that intentionally name `tracking_issue.strip_lifecycle_prefix()` behavior.
- Assert `issue title-eligibility` is not cited as the emergency prefix-stripping implementation.
- Assert bare retired helper tokens are absent outside approved manifest rows.

### UPDATED: Makefile

Remove retired shell harness targets.

- Remove `test-tracking-issue-write`.
- Remove `test-tracking-issue-summary`.
- Remove `test-tracking-issue-read-sentinel`.
- Remove those targets from `.PHONY`.
- Remove them from `test-harnesses-*` shards.
- Rely on `python/test_tracking_issue.py` under `py-test`.
- Ensure `test-step-7a` remains runnable after deleted-helper removal.

### UPDATED: python/migrated-scripts.tsv

Add retired rows for:

- `scripts/tracking-issue-read.sh`
- `scripts/tracking-issue-read.md`
- `scripts/test-tracking-issue-read-sentinel.sh`
- `scripts/test-tracking-issue-read-sentinel.md`
- `scripts/tracking-issue-write.sh`
- `scripts/tracking-issue-write.md`
- `scripts/test-tracking-issue-write.sh`
- `scripts/test-tracking-issue-write.md`
- `scripts/tracking-issue-summary.sh`
- `scripts/tracking-issue-summary.md`
- `scripts/test-tracking-issue-summary.sh`
- `scripts/test-tracking-issue-summary.md`

Use the current issue number from the implementation context.

### UPDATED: agent-lint.toml

Remove stale exclusions for retired helper and harness paths.

- Delete entries for retired tracking issue scripts and docs.
- Remove comments that say these scripts are intentionally dead.
- Keep unrelated Makefile-only harness exclusions.

### UPDATED: .gitleaks.toml

Update allowlist text and paths.

- Remove retired `tracking-issue-write` shell helper and retired harness/doc paths.
- Add `python/tracking_issue.py` and `python/test_tracking_issue.py` only if token-shaped test fixtures require path allowlisting.
- Prefer narrower test fixture strings before adding path allowlists.

### UPDATED: .claude/rules/gh-body-file.md

Retarget deleted helper references.

- Replace retired helper paths in frontmatter `paths:` entries with live Python surfaces where path-trigger coverage is still needed:
  - `python/tracking_issue.py`
  - `python/cli.py`
  - relevant live consumers that compose GitHub bodies.
- Replace body guidance that names:
  - `scripts/tracking-issue-read.sh`
  - `scripts/tracking-issue-write.sh`
  - `scripts/tracking-issue-summary.sh`
- Use `python3 python/cli.py tracking-issue ...` examples in prose.
- Preserve the body-file safety guidance.
- Preserve path-trigger behavior for security-relevant tracking issue writes.

### UPDATED: SECURITY.md

Update the tracking caps, failure streams, and redaction section.

- Rename shell helper sections to the Python CLI surface.
- Document `tracking-issue read` caps, cap override flags, and untrusted GitHub wrapping.
- Document `tracking-issue read --out-dir` validation before `task.md` writes.
- Document sentinel fixed-token error messages.
- Document column-0-only sentinel key parsing.
- Document that `tracking-issue read` shell-level usage and non-usage failures use the stdout failure envelope.
- Document that parser-level missing option values remain stderr-only.
- Document `read --issue --prompt` append delegation, `append-comment failed:` errors, and exit `2` failure mapping.
- Document outbound redaction order:
  - tmpdir paths first.
  - secrets second.
- Document best-effort tmpdir redaction for summary upsert.
- Document fail-closed secret redaction for create, append, rename, mark-false-positive, and upsert-summary.
- Document false-positive idempotency before truncation.
- Document that `create-issue` is not retried.
- Document transient retry for append, rename, false-positive, and summary mutations.
- Document `upsert-summary` failure envelope on stderr.
- Document write-verb usage errors as stderr-only.
- Document summary upsert body composition as `marker` plus blank line plus content.
- Remove statements that tracking lifecycle writes still route through retired shell helpers.

### UPDATED: AGENTS.md

Update canonical sources.

- Replace references to retired tracking shell helpers with:
  - `python/tracking_issue.py`
  - `python/test_tracking_issue.py`
  - `python/cli.py tracking-issue ...`
- Keep `docs/issue-anchored-plan.md` as the normative wire spec.

### UPDATED: docs/issue-anchored-plan.md

Sweep references.

- Replace helper names with `python3 python/cli.py tracking-issue ...`.
- Preserve wire-format descriptions and marker literals.
- Preserve the first-line skip marker contract, including legacy implement-anchor comments.
- Preserve explicit skip marker families for metadata, diagrams, plan, token-report, and final-summary comments.
- Reference `tracking_issue.strip_lifecycle_prefix()` only where the document describes title prefix stripping.
- Do not preserve full retired helper path literals outside historical context that lint explicitly permits.

### UPDATED: docs/python-migration.md

Record the F3e completion.

- Add the tracking-issue lifecycle checklist note.
- Do not add full retired repo-relative path literals outside `python/migrated-scripts.tsv`.
- Ensure `lint-retired-scripts` guidance covers the new manifest entries.
- Mention summary failure stream parity if the doc lists CLI contract differences.
- Mention write-verb usage errors remain stderr-only if the doc lists CLI contract differences.
- Mention `read` shell-level usage failures use stdout envelopes if the doc lists CLI contract differences.
- Mention `read` parser-level missing option values remain stderr-only if the doc lists CLI contract differences.

### REWRITTEN: scripts/tracking-issue-read.sh

Delete this retired shell helper after all consumers and tests use the Python CLI.

### REWRITTEN: scripts/tracking-issue-read.md

Delete this retired shell contract after moving any still-useful contract text into tests or docs.

### REWRITTEN: scripts/test-tracking-issue-read-sentinel.sh

Delete this retired harness after pytest covers the sentinel branch.

### REWRITTEN: scripts/test-tracking-issue-read-sentinel.md

Delete this retired harness contract.

### REWRITTEN: scripts/tracking-issue-write.sh

Delete this retired shell helper after all consumers and tests use the Python CLI.

### REWRITTEN: scripts/tracking-issue-write.md

Delete this retired shell contract after preserving needed behavior in Python tests and docs.

### REWRITTEN: scripts/test-tracking-issue-write.sh

Delete this retired harness after pytest covers writer parity.

### REWRITTEN: scripts/test-tracking-issue-write.md

Delete this retired harness contract.

### REWRITTEN: scripts/tracking-issue-summary.sh

Delete this retired shell helper after all summary upserts use the Python CLI.

### REWRITTEN: scripts/tracking-issue-summary.md

Delete this retired shell contract after preserving needed behavior in Python tests and docs.

### REWRITTEN: scripts/test-tracking-issue-summary.sh

Delete this retired harness after pytest covers summary upsert parity.

### REWRITTEN: scripts/test-tracking-issue-summary.md

Delete this retired harness contract.

### Edge cases

- `--sentinel` must reject any combined flags before side effects.
- Empty sentinel values must emit empty fields and succeed.
- Malformed sentinel values must not echo attacker bytes.
- Sentinel keys must match only at column 0.
- Indented sentinel keys must be treated as absent.
- Leading BOM is stripped only at file start for sentinel parsing.
- Non-sentinel read modes must validate `--out-dir` exists and is a directory before writing outputs.
- Read cap overrides must be parsed and validated before side effects.
- Comment first-line matching must tolerate BOM and trailing `\r`.
- Legacy implement-anchor comments must not enter task context.
- Metadata, diagrams, plan, token-report, and final-summary marker comments must not enter task context.
- `--issue --prompt` duplicates prompt comments on retry by design.
- `--issue --prompt` append failures must surface as read stdout envelopes with `append-comment failed:` and exit `2`.
- Prompt-only mode must not touch GitHub.
- Issue comments may contain tabs, literal `\n`, multiline bodies, or invalid JSON.
- Total task file cap must not split XML-like close tags in a way that breaks downstream readers more than the shell already did.
- Multiple marker comments must fail closed for summary upsert.
- `--comment-id` bypasses marker search and patches that exact comment.
- Summary upsert bodies must preserve the blank line between marker and content.
- Rename must not corrupt stacked prefixes beyond stripping the first managed prefix.
- Rename idempotency must compare redacted canonical current and prospective titles.
- False-positive idempotency must compare the inserted-marker result to the redacted current title before truncation.
- Public `rename()` must remain a string-returning adapter over the shared core for `finalize.py`.
- Emergency empty-body fallback must call `tracking_issue.strip_lifecycle_prefix()` directly and must not use `issue title-eligibility` as a prefix stripper.
- Redaction can change title length, so truncate again after redaction.
- `create-issue` success without a parseable issue URL is a failure.
- Append-comment success without a parseable issuecomment URL is a failure.
- Stderr from `gh` must be redacted or replaced with a generic token-free error.
- Summary upsert failures must stay in stderr-captured files for existing consumers.
- Non-summary tracking verb non-usage failure envelopes must stay on stdout for existing consumers.
- `read` shell-level usage failures must stay on stdout for existing consumers.
- `read` parser-level missing option value failures must stay stderr-only for shell parity.
- Write-verb usage errors must stay stderr-only.
- Inherited quiet environments must not reroute contract KVs or failure envelopes.

### Failure modes

- A shell consumer may still call a deleted helper.
  - Mitigate with final grep over `scripts/`, `skills/`, `.claude/rules/`, `docs/`, `Makefile`, `AGENTS.md`, `SECURITY.md`, `agent-lint.toml`, and `.gitleaks.toml`.
- A docs-only contract may still name a retired helper or bare `tracking-issue` command instead of explicit Python CLI invocation.
  - Mitigate with targeted greps over `skills/**/*.md`, `scripts/**/*.md`, and `docs/`.
- A harness may keep bare retired helper tokens in stubs or assertions.
  - Mitigate with a stale-reference regex that matches both `.sh` filenames and bare helper names.
- `.claude/rules/gh-body-file.md` may still inject reminders that cite deleted helper paths.
  - Mitigate by retargeting its frontmatter and body guidance, then include `.claude/rules/` in stale-reference grep.
- `skills/design/SKILL.md` may still embed the deleted clarify rename command.
  - Mitigate with the same stale-reference sweep.
- `/implement --emergency` may still reference deleted shell prefix stripping or `issue title-eligibility`.
  - Mitigate with a targeted grep for title eligibility and prefix stripping references.
- `scripts/ship-pr.sh` may use cwd-relative `python3 python/cli.py`.
  - Mitigate by requiring `"$PLUGIN_ROOT/python/cli.py"` in all ship-pr branches.
- Public `rename()` and CLI rename may diverge.
  - Mitigate with one shared rename core, a stable public adapter, and direct tests for both paths.
- `read --issue --prompt` may propagate append exit `3` or lose the `append-comment failed:` prefix.
  - Mitigate with delegated append failure mapping tests.
- `read` may write `task.md` before validating `--out-dir`.
  - Mitigate with side-effect tests for missing and non-directory output paths.
- `read` may port an incomplete skip-marker list.
  - Mitigate with one representative test row per first-line marker family.
- `mark-false-positive` may truncate already-marked titles.
  - Mitigate with idempotency tests that assert no edit and unchanged redacted title.
- CLI wrappers may raise uncaught `ShipError` and lose the expected envelope.
  - Add tests through `cli.main()`.
- CLI failures may move `FAILED=true` and `ERROR=` to the wrong stream.
  - Add three-row stream-placement tests for every tracking-issue verb.
- `read` parser-level missing option values may incorrectly gain stdout failure envelopes.
  - Add parser-level missing-value usage tests.
- Usage errors may incorrectly gain stdout failure envelopes on write verbs.
  - Add write-verb usage-stream tests.
- Quiet routing may move contract output under inherited quiet environments.
  - Add inherited-quiet subprocess tests.
- `gh` stderr may leak secrets through `ERROR=`.
  - Add sanitized stderr and truncation fallback tests.
- Read mode may change task file bytes.
  - Pin representative golden substrings, markers, caps, and filters.
- Summary upsert may duplicate marker lines or drop the blank-line framing.
  - Test exact posted and patched body first line and the following blank line.
- Summary upsert failure output may move from stderr to stdout.
  - Test captured stream placement.
- Append-comment may report success with empty URL fields.
  - Test rc `0` without parseable issuecomment URL as exit `2`.
- Retired script manifest may flag test fixtures if stubs contain literal retired paths.
  - Build fixture paths indirectly or update manifest guidance.
- Migration-history prose may trip retired-script lint if it uses full retired repo-relative paths.
  - Keep full retired path literals only in `python/migrated-scripts.tsv`.
- Gitleaks may fail if token-shaped fixtures move from shell tests to Python tests.
  - Prefer safer fixture tokens before adding allowlists.

### Testing strategy

- Run targeted Python tests:
  - `cd python && python3 -m pytest test_tracking_issue.py -q`
  - `cd python && python3 -m pytest test_issue_wire.py -q`
- Run affected shell harnesses after stub updates:
  - `make test-design-publish`
  - `make test-implement-bootstrap`
  - `make test-implement-finalize`
  - `make test-post-tracking-issue`
  - `make test-refresh-execution-issues`
  - `make test-write-final-report`
  - `make test-step-7a`
  - `make test-step-18b-final-report`
  - `make test-step0b-router-flag-recovery`
  - `make test-legacy-title-prefix-literals-scope`
- Run migration and stale-reference checks:
  - `make lint-retired-scripts`
  - `grep -R "tracking-issue-read\(\.sh\)\?\|tracking-issue-write\(\.sh\)\?\|tracking-issue-summary\(\.sh\)\?" -n scripts skills .claude/rules docs Makefile AGENTS.md SECURITY.md agent-lint.toml .gitleaks.toml`
  - `grep -R "implement-anchor\|title-eligibility\|prefix-stripping\|strip_lifecycle_prefix" -n skills docs python scripts .claude/rules`
  - `grep -R "tracking-issue upsert-summary\|tracking-issue read\|tracking-issue rename" -n skills scripts docs .claude/rules | grep -v "python3 .*python/cli.py" || true`
  - classify only `python/migrated-scripts.tsv` retired rows as allowed full retired path hits.
- Run required final gates:
  - `make py-lint`
  - `make py-test`
  - `make lint`
  - `bash scripts/relevant-checks.sh`


## Acceptance

Panel findings incorporated (8 accepted):

- **FINDING_1**: Validate `--out-dir` existence before writing `task.md` on all non-sentinel read paths.
- **FINDING_2**: `read --issue --prompt` delegates to the append path, maps delegated append failures to exit `2`, and never propagates exit `3`.
- **FINDING_3**: `mark-false-positive` compares marker insertion against the redacted pre-truncation title; emits `MARKED=false` and skips edit when unchanged.
- **FINDING_5**: `read_main` wires `--max-body-chars`, `--max-comments`, `--max-total-chars` flags with the same defaults as the shell helper.
- **FINDING_6**: UPDATED entries added for `skills/implement/SKILL.md` Invariant #2, `skills/implement/references/summary-comment-template.md`, `skills/design/scripts/design-publish.md`, and `scripts/implement-finalize.md`; all consumer cutover instructions use the explicit `python3 .../python/cli.py tracking-issue` form.
- **FINDING_7**: `make lint` promoted to required final gate alongside `make py-lint` and `make py-test`.
- **FINDING_8**: Read usage stream contract and tests narrowed to shell-parity `fail_usage` cases; missing-option-value cases use stderr-only / no-stdout-envelope parity.
- **FINDING_9** `[SCOPE-REDUCTION]`: Summary skip list pinned to the exact first-line patterns from `scripts/tracking-issue-read.sh:427-434` (both `<!-- larch:diagrams v1 -->` and `<!-- larch:diagrams v1 runid=... -->` forms, plus all other marker families); one representative test row per pattern added.

diff_added: 1340
diff_deleted: 1490
diff_lines: 2830

## Test plan
(no test plan section in plan-file)
