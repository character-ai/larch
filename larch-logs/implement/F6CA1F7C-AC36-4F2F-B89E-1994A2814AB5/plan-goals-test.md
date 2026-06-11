## Goal
Implement issue #3926: [IMPLEMENTING] sh-to-py F3d: Issue wire core (plan-block, named-block, scope, untrusted, title, P3119)\n\nPartition piece 4 of 5 split from #3669..

## Implementation Plan
## Plan

### Goal

Port the issue-wire bash surface to `python/issue_wire.py`: plan-block, named-block, scope-paths, title helpers, untrusted blocks, and P3119 lint.

Expose the verbs through `python/cli.py`.

Cut over all live consumers named in scope and accepted findings before deleting the bash originals, harnesses, and `.md` siblings.

### Files to modify/create

### NEW: `python/issue_wire.py`

All migrated logic from the bash scripts:
- plan-block read/write/strip-body
- named-block write/delete
- scope-path extraction
- title eligibility, archival jq filter, brainstorm check, signal-marker insertion
- untrusted block emission
- P3119 fence-absence lint

**General CLI output contract:**
- KV entrypoints initialize quiet-mode with bash-parity argv0 names before emitting KVs.
- `plan-block read`, `plan-block write`, and `named-block write` emit machine-readable KVs with `logging_util.emit_kv`.
- `plan-block strip-body` is a raw stdout filter for success payloads.
- `plan-block strip-body` malformed paths initialize quiet-mode with a bash-parity argv0 name before emitting `MALFORMED=<token>` with `logging_util.emit_kv`.
- Raw stdout filters print only their payload to stdout.
- Raw stdout success filters do not call quiet initialization.
- `issue title-eligibility` prints its KV stream to stdout directly so command substitution captures it.
- `issue title-archival-jq`, `issue insert-signal-marker`, `untrusted redact-stream`, `untrusted xml-escape-attr`, and `untrusted file-block` do not route output through fd 3.
- `plan-block strip-body` emits `MALFORMED=<token>` to stdout on malformed input and exits 1.
- CLI failures are explicit.
- Do not add `|| true` around new command substitutions unless the old flow was fail-open.

**Title argument parsing contract:**
- Title-bearing CLIs accept both `--title VALUE` and `--title=VALUE`.
- `--title VALUE` treats the next token as title data even when it begins with `-` or `--`.
- Shell callsites that pass untrusted GitHub titles must use `--title="$TITLE_VAR"` to avoid option-like title ambiguity.
- Add at least one CLI and callsite-facing test for a leading-hyphen title.

**Shared issue validation contract:**
- `plan-block read`, `plan-block write`, and `named-block write` validate `--issue` as a positive decimal integer before any `gh` call.
- Invalid or zero issue values are usage-style failures with exit 1.
- Preserve the old stderr wording style for `--issue must be a positive integer`.

**Repo resolution contract for issue-body CLIs:**
- `plan-block read`, `plan-block write`, and `named-block write` accept optional `--repo`.
- If `--repo` is omitted, resolve the current repo with a bash-parity helper that shells out to `gh repo view --json nameWithOwner`.
- Do not use any `git remote origin` fallback for these CLIs.
- Omitted `--repo` must fail with `FAILED=true`, `ERROR=could not determine repo`, and exit 2 when `gh repo view` cannot resolve the repo.
- `plan-block read` preserves the legacy read contract:
  - missing repo resolution emits `FAILED=true`, `ERROR=could not determine repo`, exit 2.
  - explicit invalid repo values are not converted into a new `ERROR=invalid-repo` exit-1 path.
  - `gh issue view` failures, including failures caused by a bad repo slug, emit `FAILED=true`, `ERROR=<single-line redacted>`, exit 2.
- `plan-block write` and `named-block write` validate explicit and resolved repo slugs with the existing `gh.validate_repo_slug()` grammar.
- Preserve write failure KVs:
  - invalid repo: `FAILED=true`, `ERROR=invalid-repo`, exit 1.
  - could not determine repo: `FAILED=true`, `ERROR=could not determine repo`, exit 2.
  - gh failure: `FAILED=true`, `ERROR=<single-line redacted>`, exit 2.
  - content file not found: `FAILED=true`, `ERROR=content file not found: <path>`, exit 1.
  - redaction failure: `FAILED=true`, `ERROR=redaction:...`, exit 3.

**Plan-block / named-block section:**
- Marker regexes detect larch marker lines with bash-parity whitespace tolerance.
- Preserve current marker grammar tolerance for leading indentation, trailing whitespace, and internal whitespace inside marker comments.
- Parsing and stripping are marker-isolated:
  - `parse_named_block(body, "plan")` counts only `larch:plan` start/end markers.
  - `parse_named_block(body, "design-pause")` counts only `larch:design-pause` start/end markers.
  - unrelated `larch:*` markers are ignored.
  - issues containing both `plan` and `design-pause` blocks are valid.
- `parse_named_block(body: str, marker: str) -> tuple[str | None, str]`.
  - Returns `(inner, "")` on success.
  - Returns `(None, "")` when no requested markers are present.
  - Returns `(None, malformed_token)` on requested-marker parse error.
  - Malformed tokens: `multiple-start`, `multiple-end`, `start-without-end`, `end-without-start`, `end-before-start`.
- `strip_named_block(body: str, marker: str) -> tuple[str, str]`.
  - Removes only the requested block including markers.
  - Leaves other named blocks untouched.
  - Returns `(stripped, "")` on success.
  - With no requested markers, returns body unchanged.
- `compose_named_block(marker: str, inner: str) -> str`.
  - Strips trailing LF characters from `inner`, matching bash command substitution.
  - Emits canonical start, optional inner plus one LF, and canonical end plus one LF.
  - Does not add an extra blank line inside the named block.
- `named_block_write(runner: Runner, marker: str, issue: str, *, repo: str, content: str | None, delete: bool) -> dict`.
  - Allows only `plan` and `design-pause` markers.
  - Fetches body via `gh.issue_view_body`.
  - Strips trailing LF characters from the fetched current body before classify, compose, replace, remove, or absent-delete paths.
  - Classifies the current body for only the requested marker before composing.
  - If the current body has malformed requested markers, returns or raises a typed malformed result so the CLI emits `MALFORMED=<token>`, exits 1, and skips redaction and `gh issue edit`.
  - Upserts or deletes the requested named block.
  - Append semantics match bash exactly:
    - empty current body gets the block only.
    - non-empty current body gets `body + "\n\n" + block`.
  - Replace and remove preserve surrounding body bytes in the same line-oriented way as bash.
  - Delete of an absent block still follows bash parity:
    - compose the unchanged body after trailing-LF normalization.
    - redact the unchanged body.
    - run the retrying `gh issue edit` path.
    - emit `MODE=absent-noop`.
  - Redacts issue bodies through a Python secrets-only redactor that matches `scripts/redact-secrets.sh`.
  - Edits the issue body through a Python `gh` helper that writes the already-redacted body directly.
  - The edit helper bypasses any second redaction path such as `_fail_closed_redacted` or `_body_file_args`.
  - The edit helper preserves the current three-attempt transient retry envelope.
  - Returns `{"written": True, "mode": str, "markers_present": bool, "body_bytes": int}`.
  - Raises `ShipError` on gh or redaction failure.
- CLI entries:
  - `plan_block_read_main`
  - `plan_block_write_main`
  - `plan_block_strip_body_main`
  - `named_block_write_main`

**Exact `plan-block read` CLI contract:**
- No plan markers:
  - truncate/create the output file empty.
  - stdout: `BLOCK_PRESENT=false`.
  - exit 0.
- Valid plan block:
  - write inner block content to the output file.
  - stdout: `BLOCK_PRESENT=true` and `OUTPUT=<path>`.
  - exit 0.
- Malformed requested markers:
  - truncate/create the output file empty.
  - stdout: `MALFORMED=<token>`.
  - exit 1.
- Invalid `--issue`:
  - usage-style stderr.
  - exit 1.
- Repo or gh failure:
  - stdout: `FAILED=true` and `ERROR=<single-line redacted>`.
  - exit 2.
  - Do not introduce `ERROR=invalid-repo` for this read path.

**Exact `plan-block write` and `named-block write` CLI contract:**
- `plan-block write` is the `named-block write --marker plan` compatibility surface.
- Success stdout:
  - `WRITTEN=true`
  - `MODE=appended|replaced|removed|absent-noop`
  - `MARKERS_PRESENT=true|false`
  - `BODY_BYTES=<n>`
  - exit 0.
- Malformed current body for the requested marker:
  - stdout: `MALFORMED=<token>`.
  - exit 1.
  - skip redaction and skip `gh issue edit`.
- Invalid `--issue`, unsupported marker, or mutually exclusive flags:
  - usage-style failure.
  - exit 1.
- Invalid repo:
  - stdout: `FAILED=true` and `ERROR=invalid-repo`.
  - exit 1.
- Missing repo resolution or gh failure:
  - stdout: `FAILED=true` and `ERROR=<single-line redacted>`.
  - exit 2.
- Redaction failure:
  - stdout: `FAILED=true` and `ERROR=redaction:...`.
  - exit 3.
- Delete on absent block still emits `WRITTEN=true`, `MODE=absent-noop`, `MARKERS_PRESENT=false`, and `BODY_BYTES=<n>`.
- Delete on absent block still redacts and calls the retrying issue edit helper.

**Exact `plan-block strip-body` CLI contract:**
- Flags: optional `--file PATH`, optional `--output PATH`.
- If `--file` is omitted, read input from stdin.
- No requested plan markers:
  - copy input to `--output`, or print to stdout when no output path is provided.
  - exit 0.
- Valid requested plan markers:
  - remove the block including marker lines.
  - write stripped body to `--output`, or stdout when no output path is provided.
  - exit 0.
- Malformed requested plan markers:
  - truncate/create `--output` empty when provided.
  - stdout: `MALFORMED=<token>`.
  - exit 1.

**Scope-path section:**
- `extract_scope_paths(plan_text: str) -> list[str]`.
  - Extracts the existing bash heredoc logic into a named function.
- `plan_scope_paths_main(argv)`.
  - Flags: required `--plan-file PATH`, optional `-z` or `--null`.
  - Fallback: `skills/design/SKILL.md` when no scope paths are found.
  - `-z` preserves nul-delimited output.
  - Missing `--plan-file` exits 2 with a stderr usage message.
  - Missing or unreadable plan files exit 2 with a stderr error.
  - Do not silently proceed with empty output on CLI input failure.

**Title section:**
- Constants:
  - `ARCHIVAL_JQ_FILTER`
  - `ARCHIVAL_REPORT_RE`
  - `LIFECYCLE_REJECT_RE`
  - `BRAINSTORM_RE`
- `ARCHIVAL_JQ_FILTER` is byte-compatible with `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER`.
- Leading whitespace is trimmed before all three title eligibility predicates.
- `LIFECYCLE_REJECT_RE` matches the bash token set exactly:
  - `^\[(IMPLEMENTING|DONE|DESIGNING|DESIGNED)\]`
  - case-insensitive.
  - `[STALLED]`, `[IN PROGRESS]`, and `[PLANNED]` are not lifecycle rejection tokens.
- `ARCHIVAL_REPORT_RE` matches the bash report-prefix behavior after leading whitespace trim.
- `BRAINSTORM_RE` matches the bash brainstorm leading-word behavior after leading whitespace trim.
- `title_lifecycle_reject_marker(title: str) -> str | None`.
  - Returns `[TOKEN]` or `None`.
  - Case-insensitive.
- `title_has_archival_report_prefix(title: str) -> bool`.
- `title_starts_with_brainstorm(title: str) -> bool`.
- `insert_signal_marker(title: str, marker: str) -> str`.
  - Matches the old bash helper exactly.
  - Scans the leading bracket-block sequence only to detect an existing exact marker.
  - Inserts after these exact lifecycle prefixes only: `[DESIGNING]`, `[DESIGNED]`, `[IMPLEMENTING]`, `[DONE]`, `[STALLED]`, `[IN PROGRESS]`, `[PLANNED]`.
  - Otherwise prepends `[marker] `.
  - Is idempotent when the same marker already appears in the leading bracket-block sequence.
- CLI entries:
  - `issue_title_eligibility_main`
  - `issue_title_archival_jq_main`
  - `issue_insert_signal_marker_main`
- `issue_title_eligibility_main` stdout:
  - `LIFECYCLE_REJECT=true/false`
  - `LIFECYCLE_MARKER=[TOKEN]` when true
  - `ARCHIVAL_REPORT=true/false`
  - `BRAINSTORM=true/false`
  - Always exits 0 when the CLI itself runs successfully.
- `issue_title_archival_jq_main` prints `ARCHIVAL_JQ_FILTER` to stdout.
- `issue_insert_signal_marker_main` prints the new title to stdout.

**Untrusted-block section:**
- `xml_escape_attr(text: str) -> str`.
  - Replaces `&`, `<`, `>`, and `"` with HTML entities.
- `redact_untrusted_stream(text: str) -> str`.
  - Applies `redact.redact(text)`.
  - Escapes `&`, `<`, and `>` for body context.
- `emit_untrusted_file_block(tag: str, path: Path) -> str`.
  - Reads the file.
  - Applies `redact_untrusted_stream`.
  - Wraps content in `<tag encoding="literal-redacted">\n...\n</tag>\n\n`.
- CLI entries:
  - `untrusted_file_block_main`
  - `untrusted_redact_stream_main`
  - `untrusted_xml_escape_attr_main`

**P3119 lint section:**
- `P3119_TOKENS: tuple[str, ...]`.
  - Builds the obfuscated token list through runtime string construction.
  - Does not place literal prohibited tokens in source.
- `lint_p3119_fence_absence(path: Path, label: str, *, ship_pr: bool = False) -> list[str]`.
  - Returns violation messages.
- `lint_p3119_main(argv)`.
  - CLI: `lint p3119-fence-absence PATH LABEL [--ship-pr]`.
  - Exit 0 when clean.
  - Exit 1 with violations to stderr.

### NEW: `python/test_issue_wire.py`

Pytest coverage for public functions and CLI entrypoints.

Key cases:
- `parse_named_block`: all 5 malformed tokens, clean extraction, absent markers, indented whitespace-tolerant markers, and marker isolation when plan and design-pause coexist.
- `strip_named_block`: malformed tokens, content before and after the block, whitespace-tolerant marker lines, and preservation of unrelated larch blocks.
- `compose_named_block`: strips trailing LF characters and emits one canonical newline before the end marker.
- `named_block_write`: append uses no separator for empty bodies and `\n\n` separator for non-empty bodies.
- `named_block_write`: fetched current bodies with trailing LF characters are normalized before classify, replace, remove, absent-delete, and `BODY_BYTES` calculation.
- `named_block_write`: plan and design-pause coexistence for write, replace, and delete.
- `plan-block read`: absent, present, malformed, invalid issue, missing repo resolution, invalid explicit repo through the legacy gh-failure path, and gh failure KVs and exit codes.
- `plan-block write` and `named-block write`: optional `--repo`, no-`--repo` success, no-`--repo` failure without origin fallback, invalid issue, invalid repo, retry behavior, success KVs, malformed-current-body `MALFORMED=` exit 1, and no edit on malformed bodies.
- `named-block write --delete`: absent marker still redacts and calls the retrying edit helper while emitting `MODE=absent-noop`.
- `named-block write`: uses the secrets-only issue-body redactor and passes already-redacted content to the gh edit helper without a second redaction pass.
- `plan-block strip-body`: file input, stdin input, success output, stdout mode, stdin-to-output mode, malformed `MALFORMED=` stdout, and output truncation.
- `extract_scope_paths`: section present, absent, backtick tokens, legacy path fallback, empty section, `-z` output, missing `--plan-file`, and unreadable plan file.
- Title functions: lifecycle reject tokens case-insensitive, exact reject token set, negative `[STALLED]`, archival, brainstorm, leading whitespace trimming, byte-compatible archival jq grammar, exact bash-compatible `insert_signal_marker` placement, and leading-hyphen titles.
- Untrusted: entity escaping, redaction plus escaping, file-block output structure including trailing double newline.
- P3119: clean file passes, each constructed token triggers a violation.
- CLI subprocess:
  - KV contracts for KV entrypoints.
  - Quiet-active parent captures `BLOCK_PRESENT` from `plan-block read` on stdout.
  - `plan-block strip-body` malformed paths emit `MALFORMED=` on stdout under quiet mode.
  - Raw stdout contracts for raw-output entrypoints.
  - Exit-code paths.
  - Command-substitution capture for `issue title-eligibility`.
  - `--title=-starts-with-hyphen` and split `--title -starts-with-hyphen` are parsed as title data.
- `named_block_write`:
  - Preserves three-attempt transient retry on issue body edit.
  - CLI emits redacted failure KVs for redaction or gh failures.

### UPDATED: `python/redact.py`

Add or expose an issue-body secrets-only redaction helper.
- Match `scripts/redact-secrets.sh` behavior for issue-wire body writes.
- Keep existing `redact.redact()` behavior unchanged for callers that need broader untrusted-content redaction.
- Make redaction failures explicit so issue-wire write CLIs can emit `FAILED=true`, `ERROR=redaction:...`, and exit 3.

### UPDATED: `python/gh.py`

Add `issue_view_body(runner: Runner, issue: str, *, repo: str) -> str`.
- Calls `gh issue view <issue> --repo <repo> --json body`.
- Parses JSON.
- Returns `""` when `body` is missing or null.
- Returns the body when it is a string.
- Raises `ShipError` for malformed JSON or non-string non-null `body`.
- Does not impose a new invalid-repo exit-1 contract on `plan-block read`; callers choose whether to prevalidate repo slugs.

Add a bash-parity repo resolver for issue-wire CLIs.
- Use `gh repo view --json nameWithOwner`.
- Return the `nameWithOwner` string when valid.
- Raise `ShipError` or return a typed failure when `gh repo view` cannot determine a repo.
- Do not fall back to `git remote origin`.
- Keep existing `resolve_repo()` behavior unchanged for other callers.

Add issue body edit support for named-block writes.
- Add `issue_edit_body_with_retry(...)` or extend the existing `issue_edit` surface.
- Accept already-redacted body content or an already-redacted body file.
- Bypass any second redaction path, including `_fail_closed_redacted` and `_body_file_args`.
- Run `gh issue edit <issue> --repo <repo> --body-file <file>`.
- Preserve the current three-attempt transient retry behavior from the shell path.
- Use the existing Python transient retry primitive if present.
- Raise `ShipError` after the final failed attempt.

Reuse existing repo helpers.
- Use `validate_repo_slug()` in write-path callers before invoking `gh`.
- Do not use origin-fallback repo resolution for plan/named-block omitted `--repo`.

### UPDATED: `python/cli.py`

Add registry entries for:
- `plan-block read`
- `plan-block write`
- `plan-block strip-body`
- `named-block write`
- `plan scope-paths`
- `issue title-eligibility`
- `issue title-archival-jq`
- `issue insert-signal-marker`
- `untrusted file-block`
- `untrusted redact-stream`
- `untrusted xml-escape-attr`
- `lint p3119-fence-absence`

### UPDATED: `python/rendering.py`

Replace the local untrusted block implementation with the shared issue-wire helpers.
- Delegate `_untrusted_file_block(tag, path)` to `issue_wire.emit_untrusted_file_block`.
- Keep rendered prompt bytes compatible for existing plan-review and voter paths.
- Do not add or structure-pin retired shell files `skills/design/scripts/render-plan-review-prompt.sh` or `skills/design/scripts/render-voter-prompt.sh`.

### UPDATED: `python/test_rendering.py`

Update or add coverage only if existing renderer tests pin untrusted block output.
- Expected output stays byte-compatible.
- Tests should prove renderer paths use the shared issue-wire escaping and redaction behavior.
- Do not add tests for retired render shell scripts.

### UPDATED: `skills/design/scripts/design-publish.sh`

Replace the `plan-block-write.sh` call:
```bash
python3 "$PLUGIN_ROOT/python/cli.py" named-block write \
  --marker plan --issue "$ISSUE" \
  --content-file "$DESIGN_TMPDIR/composed-plan.redacted.md" \
  ${ISSUE_WIRE_REPO:+--repo "$ISSUE_WIRE_REPO"}
```

Preserve the existing `if !` wrapper and error handling.

Set `ISSUE_WIRE_REPO` only when:
- the operator supplied an explicit repo, or
- a gh-only resolver succeeded.

Do not pass a repo value that came from an origin-fallback resolver into plan/named-block issue-wire CLIs.

### UPDATED: `skills/design/scripts/test-design-publish.sh`

Cut over stubs, expectations, and structure assumptions from `plan-block-write.sh` to the Python CLI.
- Update all helper-path checks and copied-helper fixtures.
- Retarget expectations to the `named-block write --marker plan` Python CLI pattern.
- Add coverage that origin-fallback repo values are not passed to the issue-wire CLI.
- Preserve assertions for publish ordering, error handling, and body-file behavior.

### UPDATED: `scripts/design-pause-save.sh`

Replace the `named-block-write.sh --marker design-pause --content-file` call:
```bash
python3 "$SCRIPT_DIR/../python/cli.py" named-block write \
  --marker design-pause --content-file "$redacted_state_tmp" \
  --issue "$ISSUE" ${ISSUE_WIRE_REPO:+--repo "$ISSUE_WIRE_REPO"}
```

Set `ISSUE_WIRE_REPO` only when the repo was operator-supplied or resolved through a gh-only resolver.

Do not pass origin-fallback repo values into the issue-wire CLI.

### UPDATED: `scripts/design-pause-load.sh`

Replace the `named-block-write.sh --marker design-pause --delete` call:
```bash
python3 "$SCRIPT_DIR/../python/cli.py" named-block write \
  --marker design-pause --delete --issue "$ISSUE" ${ISSUE_WIRE_REPO:+--repo "$ISSUE_WIRE_REPO"}
```

Set `ISSUE_WIRE_REPO` only when the repo was operator-supplied or resolved through a gh-only resolver.

Do not pass origin-fallback repo values into the issue-wire CLI.

### UPDATED: `skills/design/scripts/test-design-pause-resume.sh`

Cut over the direct named-block writer harness usage.
- Remove the `NBW="$REPO_ROOT/scripts/named-block-write.sh"` dependency on the deleted helper.
- Remove or adjust the `-x "$NBW"` prerequisite check.
- Retarget direct NBW invocations to:
  ```bash
  python3 "$REPO_ROOT/python/cli.py" named-block write
  ```
- Add coverage that origin-fallback repo values are not passed to the issue-wire CLI.
- Preserve existing assertions for:
  - `MODE=`
  - `MALFORMED=`
  - success KVs
  - absent delete still reaches the edit path
  - pause save/load behavior
- If duplicated direct NBW cases are fully covered by `python/test_issue_wire.py`, remove only the duplicated direct-helper cases and keep pause/resume integration coverage.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`

Remove the `PLAN_BLOCK_STRIP_BODY_SH` variable.

First strip-body site:
- Preserve `LARCH_QUIET_DISABLE=1`.
- Preserve stdout capture to `strip_kv`.
- Preserve `MALFORMED=` awk parsing.
- Replace only the command:
```bash
LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" plan-block strip-body \
  --file "$ORIGINAL_FEATURE_FILE" --output "$stripped_tmp" >"$strip_kv" 2>"$strip_err"
```

Second strip-body site:
- Preserve `LARCH_QUIET_DISABLE=1`.
- Preserve existing failure handling.
```bash
if ! LARCH_QUIET_DISABLE=1 python3 "$PLUGIN_ROOT/python/cli.py" plan-block strip-body \
  --file "$ORIGINAL_FEATURE_FILE" --output "$_feature_context_base" >/dev/null; then
    ...
fi
```

Update diagnostic prefixes from the old script name only if needed.

### UPDATED: `skills/design/scripts/scout-plan-archetypes-wrapper.sh`

Replace the `extract-plan-scope-paths.sh` call:
```bash
python3 "$PLUGIN_ROOT/python/cli.py" plan scope-paths \
  --plan-file "$plan" >"${target}.tmp"
```

Preserve `set -e` propagation so missing or unreadable plan files fail non-zero.

### UPDATED: `skills/design/scripts/design-route.sh`

Remove:
```bash
source "$PLUGIN_ROOT/scripts/lib-title-eligibility.sh"
```

Replace the 3 bash function calls with one Python invocation plus KV parsing:
```bash
if ! _te_kv=$(python3 "$PLUGIN_ROOT/python/cli.py" issue title-eligibility --title="$ISSUE_TITLE"); then
    # preserve existing fail-closed cancel/error route
fi
```

Parse `LIFECYCLE_REJECT`, `LIFECYCLE_MARKER`, `ARCHIVAL_REPORT`, and `BRAINSTORM` from `_te_kv` using `awk -F=`.

Preserve the ordered routing table exactly:
1. `LIFECYCLE_REJECT=true`
   - `ROUTE=cancel-title-filter`
   - `TITLE_FILTER_REASON=lifecycle`
   - `TITLE_FILTER_MARKER="$LIFECYCLE_MARKER"`
   - call `emit_cancel_route_result`
2. Else `ARCHIVAL_REPORT=true`
   - `ROUTE=cancel-title-filter`
   - `TITLE_FILTER_REASON=archival`
   - call `emit_cancel_route_result`
3. Else `BRAINSTORM=true`
   - `BRAINSTORM_PREFIX=true`
   - continue to the re-entry guard.

Do not use `2>/dev/null || true`.

If the CLI fails, preserve fail-closed behavior by taking the existing cancel/error route instead of allowing managed titles through.

Add a fixture or harness case where `ISSUE_TITLE` begins with `-`.

### UPDATED: `skills/issue/scripts/list-issues.sh`

Remove:
```bash
source "$PLUGIN_ROOT/scripts/lib-title-eligibility.sh"
```

Remove the plugin-root detection or fallback probe keyed on `scripts/lib-title-eligibility.sh`.

Re-key plugin-root validation to a stable active surface, such as:
```bash
test -f "$PLUGIN_ROOT/python/cli.py"
```

Obtain the archival jq filter through the Python CLI with fail-open behavior:
```bash
if ! DEDUP_SKIP_PREFIX_FILTER=$(python3 "$PLUGIN_ROOT/python/cli.py" issue title-archival-jq); then
    emit_kv LIST_STATUS "failed"
    larch_err "WARN list-issues.sh: failed to load archival title filter"
    exit 0
fi
```

Preserve existing `/issue` list and dedup behavior.

Update any local fixture or structure assertion that pinned `lib-title-eligibility.sh`.

### UPDATED: `scripts/launch-claude-subprocess.sh`

Remove:
```bash
source "$SCRIPT_DIR/lib-untrusted-block.sh"
```

Replace helper calls:
```bash
ctx_attr=$(printf '%s' "$ctx" | python3 "$SCRIPT_DIR/../python/cli.py" untrusted xml-escape-attr)
python3 "$SCRIPT_DIR/../python/cli.py" untrusted redact-stream <"$ctx"
```

Keep prompt structure byte-compatible.

### UPDATED: `skills/design/scripts/revise-plan-with-waterfall.sh`

Remove:
```bash
source "$REPO_ROOT/scripts/lib-untrusted-block.sh"
```

Replace the 3 untrusted file-block calls:
```bash
python3 "$REPO_ROOT/python/cli.py" untrusted file-block plan "$PLAN_FILE"
python3 "$REPO_ROOT/python/cli.py" untrusted file-block findings "$FINDINGS_FILE"
python3 "$REPO_ROOT/python/cli.py" untrusted file-block feature "$FEATURE_FILE"
```

### UPDATED: `skills/review/scripts/aggregate-findings.sh`

Remove the `lib-untrusted-block.sh` source and fallback check.

Replace the scope-anchor emission with:
```bash
python3 "$PLUGIN_ROOT/python/cli.py" untrusted file-block \
  plan_review_scope_anchor "$_scope_anchor_canon"
```

Preserve current failure handling.

### UPDATED: `scripts/check-recovery-paths-in-plan-scope.sh`

Replace the `extract-plan-scope-paths.sh` call with:
```bash
python3 "$SCRIPT_DIR/../python/cli.py" plan scope-paths \
  --plan-file "$PLAN_FILE" -z
```

Preserve the existing nul-file comparison contract.

Preserve `set -e` propagation so missing or unreadable plan files fail non-zero.

### UPDATED: `skills/design/SKILL.md`

Update all runtime references to deleted issue-wire helpers.

Required replacements:
- Clarify and publish prose that references `scripts/plan-block-write.sh` now points to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" named-block write --marker plan`.
- Scope-anchor prose that references `scripts/plan-block-strip-body.sh` now points to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-block strip-body`.
- Step 2b drafter subprocess fence removes the `source lib-untrusted-block.sh` line.
- Step 2b replaces all `larch_emit_untrusted_file_block` calls with:
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" untrusted file-block <tag> <path>
  ```
- Script catalog references to deleted helpers now name the Python CLI verbs.

Do not restyle unrelated skill prose.

### UPDATED: `skills/implement/SKILL.md`

Update every runtime reference to deleted issue-wire helpers.
- Preflight item 3 uses:
  ```bash
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-block read \
    --issue "$ISSUE" --output "$PLAN_FILE" ${REPO:+--repo "$REPO"}
  ```
- Preserve the existing forked-repo `--repo` behavior and failure gates.
- Protocol Directive Preflight prose, exit table, and error descriptions must reference the Python CLI, not `scripts/plan-block-read.sh`.
- Extracted Script Registry must not list deleted helper scripts or retired harnesses.
- Any mention of `test-plan-block.sh` must be removed or replaced with `python/test_issue_wire.py` and the relevant Makefile or pytest gate.
- Because `plan-block read` intentionally preserves the legacy invalid-repo-as-gh-failure path, do not add a new caller assumption that exit 1 only means invalid repo.

### UPDATED: `scripts/tracking-issue-write.sh`

Remove the title marker helper variable, helper existence check, and source block:
```bash
TITLE_MARKERS_HELPER=...
source "$TITLE_MARKERS_HELPER"
```

Replace `insert_signal_marker` with a guarded Python command substitution:
```bash
ERR_TMP=$(mktemp)
if ! NEW_TITLE=$(python3 "$SCRIPT_DIR/../python/cli.py" issue insert-signal-marker \
  --title="$CUR_TITLE_REDACTED" --marker "FALSE-POSITIVE" 2>"$ERR_TMP"); then
    ERR_CONTENT=$(cat "$ERR_TMP" 2>/dev/null || true)
    # emit FAILED=true and a redacted single-line ERROR using the existing failure-envelope helpers
    # exit with the existing helper-failure class before truncation or gh edit
fi
rm -f "$ERR_TMP"
```

Preserve:
- the `FAILED=true` and `ERROR=<single-line redacted>` stdout envelope on subprocess failure.
- the existing idempotent `MARKED=false` branch when the title is unchanged.
- truncation after marker insertion.
- gh edit retry behavior.

Add a marker test where the current title begins with `-`.

### UPDATED: `skills/design/scripts/test-plan-review-scope-anchor.sh`

Replace the direct `scripts/plan-block-strip-body.sh` execution with:
```bash
python3 "$REPO_ROOT/python/cli.py" plan-block strip-body \
  --file "$TMP/feature.md" --output "$TMP/anchor.txt"
```

Preserve the existing assertions.

### UPDATED: `scripts/test-design-structure.sh`

Update structure pins:
1. Remove `source lib-p3119-fence-absence.sh`.
2. Replace all `assert_p3119_family_b_fence_absent` calls with:
   ```bash
   python3 "$SCRIPT_DIR/../python/cli.py" lint p3119-fence-absence FILE LABEL || fail ...
   ```
3. Remove the `lib-untrusted-block.sh` file-existence check.
4. Simplify the `plan-review-loop.sh` OR-check to only `lib-scope-anchor-handoff`.
5. Update `launch-claude-subprocess.sh`, `revise-plan-with-waterfall.sh`, and `aggregate-findings.sh` checks to grep for the new untrusted CLI verbs.
6. Do not add checks for retired `render-plan-review-prompt.sh` or `render-voter-prompt.sh`.
7. If renderer structure is pinned, pin `python/rendering.py` to the shared issue-wire untrusted helper instead.
8. Change all `design-publish.sh` pins from `plan-block-write.sh` to the `named-block write` Python CLI pattern.
9. Retarget ordering and guard checks around `design-publish.sh` to the new Python CLI invocation.
10. Replace title helper function-name checks with an `issue title-eligibility` Python CLI check on `design-route.sh`.
11. Add pins for `list-issues.sh` using `issue title-archival-jq` with the fail-open wrapper.
12. Add pins for `list-issues.sh` plugin-root probing against `python/cli.py`, not deleted title helpers.
13. Add pins for `check-recovery-paths-in-plan-scope.sh` using `plan scope-paths -z`.
14. Add pins that `skills/design/SKILL.md` and `skills/implement/SKILL.md` no longer reference deleted helper paths.
15. Add a pin that `skills/design/scripts/test-plan-review-scope-anchor.sh` no longer invokes `plan-block-strip-body.sh`.
16. Add a pin that `skills/design/scripts/test-design-pause-resume.sh` no longer invokes `named-block-write.sh`.
17. Add or retarget pins for `skills/design/scripts/test-design-publish.sh`.

### UPDATED: `scripts/test-review-structure.sh`

Remove:
```bash
source lib-p3119-fence-absence.sh
```

Replace `assert_p3119_family_b_fence_absent` calls with the Python CLI equivalent.

Update any review aggregation pin from `lib-untrusted-block.sh` to `untrusted file-block`.

### UPDATED: `scripts/test-research-structure.sh`

Remove:
```bash
source lib-p3119-fence-absence.sh
```

Replace `assert_p3119_family_b_fence_absent` calls with the Python CLI equivalent.

### UPDATED: `scripts/test-legacy-title-prefix-literals-scope.sh`

Update legacy title-prefix literal allowlists.
- Drop deleted helper script paths.
- Allow deliberate literals in:
  - `python/issue_wire.py`
  - `python/test_issue_wire.py`
  - remaining active docs or scripts that intentionally mention `[PLANNED]`, `[IN PROGRESS]`, or lifecycle prefixes.
- Keep the test focused on preventing new literal sprawl.

### UPDATED: `.claude/rules/gh-body-file.md`

Retarget deleted helper references.
- Replace plan-block and named-block shell helper references with the Python CLI verbs.
- Preserve the rule’s body-file safety intent.
- Do not restyle unrelated rule prose.

### UPDATED: `AGENTS.md`

Retarget canonical-source references to deleted plan-block helper scripts.
- Replace helper paths with `python/cli.py` issue-wire verbs and `python/test_issue_wire.py`.
- Preserve repository guidance and existing style.

### UPDATED: `SECURITY.md`

Retarget issue-wire security guidance from deleted shell helpers to Python surfaces.
- Replace plan-block read/write references with:
  - `python3 python/cli.py plan-block read`
  - `python3 python/cli.py named-block write --marker plan`
- Document that named-block write paths redact issue bodies through the Python secrets-only redactor matching `scripts/redact-secrets.sh`.
- Document that issue-wire body edit helpers write already-redacted bodies directly and do not apply a second redaction pass.
- Document that omitted repo resolution for issue-wire body CLIs uses `gh repo view --json nameWithOwner`, not `git remote origin`.
- Preserve the existing security posture and do not restyle unrelated sections.

### UPDATED: `agent-lint.toml`

Update lint configuration references to deleted helpers.
- Remove or retarget entries that pin retired issue-wire bash files.
- Keep active lint coverage equivalent.

### UPDATED: `docs/issue-anchored-plan.md`

Update the normative wire-format docs for the Python issue-wire surface.
- Replace `scripts/plan-block-read.sh`, `scripts/plan-block-write.sh`, `scripts/plan-block-strip-body.sh`, and named-block helper references with Python CLI equivalents.
- Replace or remove wildcard references such as `scripts/plan-block-*.sh`.
- Preserve the live wire grammar and failure contracts.
- Add notes only where needed for bash-parity behavior:
  - read invalid repo remains a gh-failure path.
  - omitted repo resolution uses `gh repo view`, not origin fallback.
  - callers must not feed origin-fallback repos into plan/named-block issue-wire CLIs.
  - fetched current bodies strip trailing LF characters before write composition.
  - absent delete still redacts and edits.
  - issue body edit receives already-redacted content and does not re-redact.

### UPDATED: `docs/linting.md`

Update P3119 and retired-harness documentation.
- Replace `lib-p3119-fence-absence.sh` references with `python3 python/cli.py lint p3119-fence-absence`.
- Remove retired harness targets that are dropped from the Makefile.
- Point parity coverage to `python/test_issue_wire.py`.

### UPDATED: Additional harnesses, fixtures, and literal allowlists

Sweep and update test fixtures that still pin deleted helper paths.

Expected updates include:
- `skills/design/scripts/test-design-publish.sh` stubs and expectations for `named-block write`.
- `skills/design/scripts/test-design-pause-resume.sh` direct named-block writer calls and `MODE=` / `MALFORMED=` assertions.
- `scripts/test-dispatch-plan-voters.sh` stubs that copied `lib-untrusted-block.sh`.
- `skills/design/scripts/test-dispatch-plan-review-panel.sh` stubs that copied `lib-untrusted-block.sh`.
- Design-route fixtures that previously copied or sourced `lib-title-eligibility.sh`.
- List-issues fixtures that previously probed `lib-title-eligibility.sh`.
- `scripts/test-legacy-title-prefix-literals-scope.sh` allowlists.
- Any fixture calls to plan-block, named-block, title, scope, untrusted, or P3119 bash helpers.
- Any literal allowlist entries for deleted bash files.
- P3119 literal allowlists move to `python/issue_wire.py` and `python/test_issue_wire.py` where needed.

Use a safe stale-reference sweep before deletion:
```bash
git grep -n -E 'plan-block-[*][.]sh|plan-block-read[.]sh|plan-block-read[.]md|plan-block-write[.]sh|plan-block-write[.]md|plan-block-strip-body[.]sh|plan-block-strip-body[.]md|named-block-write[.]sh|named-block-write[.]md|extract-plan-scope-paths[.]sh|extract-plan-scope-paths[.]md|lib-title-markers[.]sh|lib-title-markers[.]md|lib-title-eligibility[.]sh|lib-title-eligibility[.]md|lib-untrusted-block[.]sh|lib-untrusted-block[.]md|lib-p3119-fence-absence[.]sh|test-plan-block[.]sh|test-plan-block[.]md|test-plan-block-strip-body[.]sh|test-plan-block-strip-body[.]md|test-lib-title-eligibility[.]sh|test-lib-title-eligibility[.]md|test-lib-title-markers[.]sh|test-extract-plan-scope-paths[.]sh|test-extract-plan-scope-paths[.]md' -- . ':(exclude)larch-logs/**'
```

Do not delete a helper until all live, test, fixture, doc, lint-config, security, and skill references are cut over or explicitly retired.

### UPDATED: `python/migrated-scripts.tsv`

Append entries tagged `#3926` for all deleted bash files and existing `.md` siblings.

Include every absorbed runtime helper and replaced harness:
- `scripts/plan-block-read.sh`
- `scripts/plan-block-read.md`
- `scripts/plan-block-write.sh`
- `scripts/plan-block-write.md`
- `scripts/plan-block-strip-body.sh`
- `scripts/plan-block-strip-body.md`
- `scripts/named-block-write.sh`
- `scripts/named-block-write.md`
- `scripts/extract-plan-scope-paths.sh`
- `scripts/extract-plan-scope-paths.md`
- `scripts/lib-title-markers.sh`
- `scripts/lib-title-markers.md`
- `scripts/lib-title-eligibility.sh`
- `scripts/lib-title-eligibility.md`
- `scripts/lib-untrusted-block.sh`
- `scripts/lib-untrusted-block.md`
- `scripts/lib-p3119-fence-absence.sh`
- `scripts/test-plan-block.sh`
- `scripts/test-plan-block.md`
- `scripts/test-plan-block-strip-body.sh`
- `scripts/test-plan-block-strip-body.md`
- `scripts/test-lib-title-eligibility.sh`
- `scripts/test-lib-title-eligibility.md`
- `scripts/test-lib-title-markers.sh`
- `scripts/test-extract-plan-scope-paths.sh`
- `scripts/test-extract-plan-scope-paths.md`

Do not add a `lib-p3119-fence-absence.md` row unless that file exists.

### UPDATED: `Makefile`

Remove retired harness targets from:
- `.PHONY`
- shard assignments
- target rule definitions

Targets to drop:
- `test-plan-block`
- `test-plan-block-strip-body`
- `test-lib-title-eligibility`
- `test-lib-title-markers`
- `test-extract-plan-scope-paths`

If additional deleted harness targets are discovered during the stale-reference sweep, remove those in the same pattern.

Do not drop `test-design-pause-resume`; cut it over to the Python CLI.

### UPDATED: `scripts/relevant-checks.sh`

Remove `scripts/lib-untrusted-block.sh|` from the case arm.

Keep `scripts/lib-scope-anchor-handoff.sh`.

Add or adjust patterns so changes to these files run the relevant Python and structure checks:
- `python/issue_wire.py`
- `python/test_issue_wire.py`
- `python/redact.py`
- `python/gh.py`
- `python/rendering.py`
- `python/test_rendering.py`
- affected skill scripts
- affected structure harnesses
- `.claude/rules/gh-body-file.md`
- `AGENTS.md`
- `SECURITY.md`
- `agent-lint.toml`
- `docs/issue-anchored-plan.md`
- `docs/linting.md`
- `skills/design/scripts/test-design-publish.sh`
- `skills/design/scripts/test-plan-review-scope-anchor.sh`
- `skills/design/scripts/test-design-pause-resume.sh`
- `scripts/test-legacy-title-prefix-literals-scope.sh`

### Deleted files

Delete only after all cutovers and stale-reference sweep pass.

Deleted files:
- `scripts/plan-block-read.sh`
- `scripts/plan-block-read.md`
- `scripts/plan-block-write.sh`
- `scripts/plan-block-write.md`
- `scripts/plan-block-strip-body.sh`
- `scripts/plan-block-strip-body.md`
- `scripts/named-block-write.sh`
- `scripts/named-block-write.md`
- `scripts/extract-plan-scope-paths.sh`
- `scripts/extract-plan-scope-paths.md`
- `scripts/lib-title-markers.sh`
- `scripts/lib-title-markers.md`
- `scripts/lib-title-eligibility.sh`
- `scripts/lib-title-eligibility.md`
- `scripts/lib-untrusted-block.sh`
- `scripts/lib-untrusted-block.md`
- `scripts/lib-p3119-fence-absence.sh`
- `scripts/test-plan-block.sh`
- `scripts/test-plan-block.md`
- `scripts/test-plan-block-strip-body.sh`
- `scripts/test-plan-block-strip-body.md`
- `scripts/test-lib-title-eligibility.sh`
- `scripts/test-lib-title-eligibility.md`
- `scripts/test-lib-title-markers.sh`
- `scripts/test-extract-plan-scope-paths.sh`
- `scripts/test-extract-plan-scope-paths.md`

### Approach

1. Implement `python/issue_wire.py` using stdlib-only code.
2. Use `gh.issue_view_body()` and the new retry-preserving body edit helper for network operations.
3. Add and use a bash-parity `gh repo view` resolver for optional `--repo` behavior in plan/named-block CLIs.
4. Preserve `plan-block read` repo failure compatibility by not adding an `invalid-repo` exit-1 path there.
5. Use `gh.validate_repo_slug()` for write-path repo validation.
6. Validate positive integer `--issue` for plan-block read, plan-block write, and named-block write before any gh call.
7. Use marker-isolated parse and strip helpers with bash-parity whitespace tolerance so different larch named blocks can coexist.
8. Normalize fetched current issue bodies by stripping trailing LF characters in the named-block write path before composition.
9. Preserve absent-delete side effects by redacting and editing even when mode is `absent-noop`.
10. Add or expose a Python secrets-only redactor matching `scripts/redact-secrets.sh` for issue body writes.
11. Ensure the retrying gh issue edit helper writes already-redacted body content directly and does not re-redact.
12. Write `python/test_issue_wire.py` for function parity, CLI contracts, quiet-mode KV behavior, raw stdout behavior, redaction, repo fallback prevention, retry behavior, stdin strip-body behavior, write KVs, malformed write bodies, exact title grammar, leading-hyphen titles, marker coexistence, trailing-LF body parity, absent-delete edit behavior, and scope-path failure modes.
13. Register all CLI verbs in `python/cli.py`.
14. Cut over all runtime consumers:
   - design publish
   - design pause save/load
   - plan review loop
   - scout plan archetypes
   - design route
   - issue list
   - launch Claude subprocess
   - revise plan with waterfall
   - aggregate findings
   - recovery scope checker
   - tracking issue write
15. Ensure plan/named-block callsites pass `--repo` only for operator-supplied repos or gh-only resolved repos.
16. Cut over `python/rendering.py` to reuse issue-wire untrusted helpers for active renderer paths.
17. Cut over runtime skill instructions in `skills/design/SKILL.md` and all implement runtime references in `skills/implement/SKILL.md`.
18. Update `SECURITY.md`, docs, rules, lint config, structure harnesses, shell fixtures, copied helper fixtures, and literal allowlists.
19. Cut over `skills/design/scripts/test-design-pause-resume.sh`.
20. Cut over `skills/design/scripts/test-design-publish.sh`.
21. Run the safe stale-reference sweep, including `plan-block-[*][.]sh`, before deleting helpers.
22. Delete absorbed bash helpers and replaced harnesses.
23. Update `python/migrated-scripts.tsv`, `Makefile`, and `scripts/relevant-checks.sh`.
24. Run parity and lint gates.

### Non-targets

- Do not create or edit retired shell scripts:
  - `skills/design/scripts/render-plan-review-prompt.sh`
  - `skills/design/scripts/render-voter-prompt.sh`
- Do not add structure pins for those retired files.
- Use `python/rendering.py` for active renderer untrusted-block behavior.

### Edge cases

- Named-block marker allowlist: `plan` and `design-pause` only.
- Unsupported markers emit the same failure style as the old script.
- Positive integer `--issue` validation rejects `0`, empty, and non-decimal values before any gh call.
- Omitted repo resolution for plan/named-block CLIs uses `gh repo view` only, with no origin fallback.
- Plan/named-block callsites do not pass origin-fallback repo values into issue-wire CLIs.
- `plan-block read` invalid repo values surface as legacy gh failures, not `ERROR=invalid-repo`.
- Marker lines preserve bash whitespace tolerance for indentation, trailing whitespace, and internal comment whitespace.
- `strip_named_block` with no requested markers returns the body unchanged.
- `parse_named_block` and `strip_named_block` ignore unrelated `larch:*` markers.
- Plan and design-pause blocks can coexist without false malformed results.
- `compose_named_block` strips trailing LF characters from content before wrapping.
- `named_block_write` strips trailing LF characters from fetched current issue bodies before classify and compose.
- Named-block append uses exactly `\n\n` between a non-empty existing body and the new block.
- Current-body malformed requested markers in write paths emit `MALFORMED=<token>`, exit 1, and do not edit.
- Delete of an absent block emits `MODE=absent-noop` but still redacts and edits the body.
- Issue body writes use a secrets-only redactor matching `scripts/redact-secrets.sh`.
- Issue body edit helper does not re-redact already-redacted content.
- `gh.issue_view_body` treats missing or null body as `""`.
- `extract_scope_paths` with an empty scope section returns `["skills/design/SKILL.md"]`.
- `plan scope-paths -z` preserves nul-delimited output for recovery checks.
- `plan scope-paths` missing or unreadable files exit 2 and write errors to stderr.
- `plan-block strip-body` reads stdin when `--file` is omitted.
- `plan-block strip-body` malformed failures emit `MALFORMED=` to stdout on exit 1.
- KV-producing issue-body CLIs preserve stdout capture even when quiet mode is active in the parent.
- `emit_untrusted_file_block` trailing double newline matches bash exactly.
- Title eligibility trims leading whitespace before lifecycle, archival, and brainstorm predicates.
- Title-bearing CLIs and callsites handle titles beginning with `-`.
- `title_lifecycle_reject_marker` is case-insensitive and only rejects `[IMPLEMENTING]`, `[DONE]`, `[DESIGNING]`, and `[DESIGNED]`.
- `insert_signal_marker` matches the exact bash placement rules.
- P3119 tokens are built at runtime to avoid literal tokens in source.
- Raw-output CLIs write to stdout directly and do not lose output through quiet fd-3 handling.
- `design-route.sh` title-eligibility failure fails closed.
- `design-route.sh` preserves ordered lifecycle, archival, then brainstorm routing.
- `list-issues.sh` archival jq filter failure fails open with `LIST_STATUS=failed` and exit 0.
- `list-issues.sh` plugin-root detection does not rely on deleted title helper files.
- `tracking-issue-write.sh mark-false-positive` preserves the `FAILED=true` and `ERROR=` envelope if marker insertion subprocess fails.
- Named-block issue edits retry transient GitHub failures three times.

### Failure modes

1. Invalid `--issue` in plan/named-block issue-body CLIs: usage-style stderr, exit 1, and no gh call.
2. Omitted `--repo` when `gh repo view` cannot resolve: exit 2 with `FAILED=true ERROR=could not determine repo`.
3. `gh issue view` failure in `plan_block_read_main`: exit 2 with `FAILED=true ERROR=<redacted>`, matching the bash contract.
4. Invalid repo in `plan_block_read_main`: do not emit `ERROR=invalid-repo`; let the legacy gh failure path emit `FAILED=true ERROR=<redacted>` and exit 2.
5. Invalid repo slug in write CLIs: exit 1 with `FAILED=true ERROR=invalid-repo`.
6. Malformed plan block in `plan_block_read_main`: exit 1 with `MALFORMED=<token>` and empty output file.
7. Malformed current body in `plan_block_write_main` or `named_block_write_main`: exit 1 with `MALFORMED=<token>` and no edit.
8. Malformed plan block in `plan_block_strip_body_main`: exit 1 with `MALFORMED=<token>` on stdout.
9. Missing `--plan-file` or unreadable plan file in `plan_scope_paths_main`: exit 2 with stderr.
10. Redaction failure in `named_block_write`: `ShipError` leads to `FAILED=true ERROR=redaction:...` and exit 3.
11. Issue body edit transient failure, including absent-delete edit: retry three times before surfacing `ShipError`.
12. Title eligibility CLI failure in `design-route.sh`: route to the existing error/cancel path, not a managed-title pass-through.
13. Archival jq CLI failure in `list-issues.sh`: emit `LIST_STATUS=failed`, warn on stderr, and exit 0.
14. Signal-marker subprocess failure in `tracking-issue-write.sh`: emit `FAILED=true ERROR=<redacted single-line stderr>` and exit before truncation or gh edit.
15. Consumer script error paths are preserved. Existing `if !` wrappers and KV parsers remain.

### Testing strategy

- `python/test_issue_wire.py` covers all public functions and CLI entrypoints.
- `python/test_rendering.py` covers renderer untrusted-block parity if renderer tests already pin this behavior.
- Existing bash harnesses run as parity gates before their Makefile targets are dropped.
- `make test-design-structure test-review-structure test-research-structure` verifies structure pin updates.
- Run `skills/design/scripts/test-plan-review-scope-anchor.sh` after its cutover.
- Run `skills/design/scripts/test-design-pause-resume.sh` after its cutover.
- Update and run affected fixture harnesses, including `skills/design/scripts/test-design-publish.sh`.
- Add or update tests for:
  - quiet-mode KV stdout capture for issue-body KV CLIs.
  - no-`--repo` success and failure paths with no origin fallback.
  - callsites not passing origin-fallback repo values into issue-wire CLIs.
  - positive integer issue validation.
  - plan-block read invalid repo preserving gh-failure style.
  - null or missing issue body.
  - whitespace-tolerant marker parsing.
  - marker isolation for plan plus design-pause coexistence.
  - named-block append blank-line separator.
  - fetched current-body trailing-LF parity.
  - write-path success KVs.
  - write-path malformed current bodies with no edit.
  - secrets-only issue-body redaction.
  - no second redaction in the retrying issue edit helper.
  - absent-delete `MODE=absent-noop` still redacts and edits.
  - `plan-block strip-body` stdin mode.
  - `plan-block strip-body` malformed stdout capture.
  - `plan scope-paths` missing and unreadable file failures.
  - `list-issues.sh` plugin-root probing against `python/cli.py`.
  - `list-issues.sh` fail-open archival filter failure.
  - exact title eligibility grammar and leading whitespace trimming.
  - leading-hyphen title handling for title CLIs and shell callsites.
  - exact `insert_signal_marker` bash behavior.
  - `tracking-issue-write.sh` marker subprocess failure envelope.
- `make lint-retired-scripts` confirms no lingering references after `python/migrated-scripts.tsv` is updated.
- Final gate:
  ```bash
  make lint
  make py-lint
  make py-test
  ```

diff_added: 1585
diff_deleted: 1395
diff_lines: 2980


## Acceptance

- `python/issue_wire.py` importable; all CLI verbs registered in `python/cli.py`.
- All named consumers cut over to Python CLI; no script sources a deleted bash helper.
- All 28 bash files deleted; stale-reference sweep passes (`make lint-retired-scripts`).
- `make lint + py-lint + py-test` green.

## Test plan
(no test plan section in plan-file)
