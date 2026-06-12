### FINDING_1: /design clarify rename still calls deleted helper
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-consumer-sweep, Codex-dyn-consumer-sweep
- **Severity**: important
- **Concern**: The /design clarify success path still instructs the orchestrator to run `scripts/tracking-issue-write.sh rename` after the plan deletes that helper, so clarify completion can fail at runtime despite other Python CLI cutovers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/design/SKILL.md to the consumer sweep and replace the embedded rename with python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename preserving RENAMED= parsing
  - From Codex-Arch: Add skills/design/SKILL.md to the plan and replace the direct helper command with python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename ...
  - From Cursor-Pragmatic: Add ### UPDATED: skills/design/SKILL.md to cut over that fence to python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename with the same RENAMED= parsing
  - From Codex-Pragmatic: Add skills/design/SKILL.md to the plan and change this command to python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py tracking-issue rename with the same args and best-effort RENAMED handling
  - From Cursor-dyn-consumer-sweep: Add ### UPDATED: skills/design/SKILL.md with the same python3 python/cli.py tracking-issue rename cut-over used in design-init-runparams.sh.
  - From Codex-dyn-consumer-sweep: Add UPDATED: skills/design/SKILL.md and replace the command with python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename while preserving the existing guards and best-effort RENAMED handling


### FINDING_2: CLI rename and append lack transient retry parity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Python rename and append-comment paths do not specify the same transient retry behavior that the retired shell helper applied around `gh issue edit` and `gh issue comment`, so cutover consumers can regress under flaky network or GitHub CLI failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Wire append_comment_main through the same with_transient_retry/_retry_gh pattern already used in upsert_marker_comment, or document and test equivalent retry on the CLI helper only.
  - From Cursor-Pragmatic: Specify in the CLI rename_main and append_comment_main sections that gh mutations use the same with_transient_retry pattern as existing upsert_marker_comment/_retry_gh


### FINDING_3: Read filter omits legacy implement-anchor comments
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Python read-mode filter plan omits the legacy `<!-- larch:implement-anchor v1 ` first-line skip contract, so migrated reads can reintroduce old internal anchor comments into task context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the legacy implement-anchor prefix to the Python skipped first-line marker set and include a focused pytest case for it
  - From Cursor-Pragmatic: Copy the full first-line skip set from scripts/tracking-issue-read.sh:427-436 (metadata, diagrams, plan, token-report, final-summary, implement-anchor) into the skipped-marker constants and pytest filter cases


### FINDING_4: Emergency preflight still references deleted shell prefix stripping
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The `/implement --emergency` title fallback still points to shell helper prefix-stripping logic that will be deleted, so emergency admission can halt or strip lifecycle prefixes incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update the preflight bullet to use the Python surface (for example python/cli.py issue title-eligibility or the same _LIFECYCLE_PREFIX_RE logic in tracking_issue.py) and add skills/implement/SKILL.md to the cutover list


### FINDING_5: Step 7a harness still depends on deleted summary helper
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Requirements, Codex-dyn-consumer-sweep
- **Severity**: important
- **Concern**: `test-step-7a.sh` still copies or asserts against `scripts/tracking-issue-summary.sh`, so deleting the helper can break `make test-step-7a`, `make lint`, or stale-reference checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ### UPDATED: skills/implement/scripts/test-step-7a.sh stubbing the python/cli.py tracking-issue upsert-summary command instead of copying scripts/tracking-issue-summary.sh
  - From Codex-Requirements: Add skills/implement/scripts/test-step-7a.sh to the plan, remove or replace the retired helper copy/chmod with Python diagrams helper dependencies only, and run make test-step-7a or required make lint
  - From Codex-dyn-consumer-sweep: Add UPDATED: skills/implement/scripts/test-step-7a.sh; remove the deleted-helper copy/chmod and replace the stale assertion literal with coverage around python/cli.py diagrams upsert


### FINDING_6: Outbound tracking compose paths miss tmpdir-path redaction parity
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-contract-parity
- **Severity**: important
- **Concern**: Python tracking issue compose paths only specify secrets redaction, but the retired shell paths redacted tmpdir paths before secrets. This can leak operator repo paths into GitHub titles or comments, and upsert-summary also needs its shell-compatible best-effort tmpdir then fail-closed secrets behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add tmpdir-paths then secrets redaction to create_issue, append-comment, rename, mark_false_positive, and upsert-summary compose paths; document the order in SECURITY.md as specified.
  - From Cursor-dyn-contract-parity: Specify upsert_summary_main body composition: best-effort tmpdir-paths (preserve body on helper failure), then fail-closed secrets redaction with exit 3 on compose-time failure, matching summary.sh ordering.


### FINDING_8: upsert-summary failure stream conflicts with existing consumers
- **Reviewer(s)**: Cursor-dyn-contract-parity
- **Severity**: important
- **Concern**: The universal `main_*` failure rule would emit `FAILED=true` and `ERROR=` through stdout, but the retired summary helper emitted failures on stderr. Existing consumers capture stdout and stderr separately and expect summary failures in the err file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-parity: Document upsert_summary_main as a carve-out: success KVs on stdout; failure FAILED/ERROR on stderr to match summary.sh. Do not route upsert-summary failures through stdout emit_kv unless every stderr-capturing consumer is updated in the same change.


### FINDING_9: upsert-summary success stdout fields are under-specified
- **Reviewer(s)**: Cursor-dyn-contract-parity, Codex-dyn-contract-parity
- **Severity**: important
- **Concern**: The Python plan does not fully enumerate the upsert-summary success key-value stdout contract. Consumers rely on `COMMENT_ID`, `COMMENT_URL`, and `UPDATED`, so the CLI could omit required fields while still appearing to satisfy the written plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-parity: Under upsert_summary_main, explicitly emit COMMENT_ID= (empty on create), COMMENT_URL=, and UPDATED=true|false on stdout for every success path, matching the shell contract.
  - From Codex-dyn-contract-parity: Spell out upsert_summary_main success fields COMMENT_ID, COMMENT_URL, and UPDATED. Add concrete create, patch, and --comment-id tests that assert each emitted field


### FINDING_10: Per-verb exit-code parity is not pinned
- **Reviewer(s)**: Cursor-dyn-contract-parity, Codex-dyn-contract-parity
- **Severity**: important
- **Concern**: The plan gives a generic exit-code matrix but does not bind exit codes to each CLI main. This can lose shell parity where read never exits 3, write exits 3 for compose-time redaction, and upsert-summary exits 3 for redaction helper failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-parity: Add a per-main_* exit-code table in the tracking_issue.py section mirroring each shell script header, including read_main max exit 2 and upsert_summary_main exit 3 on redaction failure.
  - From Codex-dyn-contract-parity: Add a compact main_* exit-code table and pytest cases that assert 0/1/2/3 where applicable: read_main 0/1/2 only, write mains 0/1/2/3, upsert_summary_main 0/1/2/3


### FINDING_11: design-publish cutover omits NEW_TITLE parsing parity
- **Reviewer(s)**: Cursor-dyn-contract-parity
- **Severity**: important
- **Concern**: `design-publish` admission logic depends on parsing `NEW_TITLE=` when `RENAMED=false`. The cutover only mentions idempotent `RENAMED=false` handling, so it can break the existing success predicate for already-designed titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-parity: Cutover bullet: keep parsing NEW_TITLE= from rename stdout; add a pytest rename case asserting NEW_TITLE= is emitted on both RENAMED=true and RENAMED=false paths.


### FINDING_12: upsert-summary validation gates are missing
- **Reviewer(s)**: Cursor-dyn-contract-parity
- **Severity**: important
- **Concern**: The upsert-summary CLI spec does not require the retired shell helper’s marker-shape validation or `OWNER/REPO` validation before GitHub calls, so invalid inputs can change behavior and exit envelopes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-parity: Add upsert_summary_main validation: marker must match shell pattern; invalid repo exit 1 with ERROR=invalid repo: expected OWNER/REPO; pytest parity for invalid marker and invalid repo.




### FINDING_1: `.claude/rules/gh-body-file.md` still references deleted tracking-issue shell scripts
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The F3e cutover deletes `tracking-issue-{read,write,summary}.sh`, but `.claude/rules/gh-body-file.md` still lists those retired paths in `paths:` frontmatter and body guidance. The planned stale-reference grep/sweep does not cover `.claude/rules/`, while `lint-retired-scripts` scans tracked files broadly. After merge, editing `SECURITY.md` or other matched paths can inject reminders citing missing scripts; `make lint` can fail with no prior grep hit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `.claude/rules/gh-body-file.md` to the cutover/sweep (replace paths with `python/tracking_issue.py` / `python/cli.py tracking-issue …`) and include `.claude/rules/` in the final grep
  - From Cursor-Requirements: Extend the stale-reference grep and failure-mode sweep to include `.claude/rules/` (at minimum `gh-body-file.md`) and retarget those `paths:` entries to the Python CLI surfaces
  - From Codex-Requirements: Add .claude/rules/gh-body-file.md to the plan. Replace retired tracking helper paths with python/tracking_issue.py and include .claude/rules in the stale-reference grep


### FINDING_2: `/implement --emergency` empty-body title fallback cannot use `issue title-eligibility`
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Preflight emergency title fallback must strip one lifecycle prefix from the issue title when the body is empty. The plan (or migrated SKILL prose) points at `issue title-eligibility`, which emits eligibility KVs (`LIFECYCLE_REJECT`, `ARCHIVAL_REPORT`, `BRAINSTORM`) and does not emit a prefix-stripped title. After `tracking-issue-write.sh` / `strip_one_lifecycle_prefix` is deleted, empty-body `--emergency` runs cannot derive a correct fallback plan and may retain managed or legacy lifecycle prefixes (`[DESIGNING]`, `[DESIGNED]`, `[IMPLEMENTING]`, etc.) in plan text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Revise the plan to replace the deleted helper reference with the exact one-prefix strip behavior from python/tracking_issue.py, including the managed and legacy prefix list; do not use issue title-eligibility as the stripping executable unless it is changed to emit the stripped title with the same prefix family
  - From Cursor-Innovation: Replace the executable fallback with a documented strip rule shared with `tracking_issue._LIFECYCLE_PREFIX_RE` (add a small public `strip_lifecycle_prefix(title) -> str` helper in `python/tracking_issue.py` and reference it from SKILL prose), or add an explicit `tracking-issue strip-lifecycle-prefix` verb; do not use `issue title-eligibility` for stripping
  - From Cursor-Pragmatic: Document the exact strip-one-prefix rule (reuse tracking_issue._LIFECYCLE_PREFIX_RE / shared helper from rename_main) in the SKILL text, or add a minimal CLI strip verb; do not reference title-eligibility for stripping


### FINDING_3: Missing pytest parity for gh-stderr redaction before `ERROR=`
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan deletes `scripts/test-tracking-issue-write.sh`, which pins fail-closed gh error redaction (token scrubbing and truncation fallback). The replacement pytest list covers compose-time redaction failures only. A Python CLI port could surface raw gh stderr containing secrets in `ERROR=` while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add one or two python/test_tracking_issue.py CLI-main failure tests with runner stderr containing a token and a redaction-truncation fallback case. Assert ERROR omits raw stderr or uses generic token-free text.


### FINDING_4: Stream-placement pytest coverage incomplete for all tracking-issue CLI verbs
- **Reviewer(s)**: Cursor-dyn-stream-placement-parity, Codex-dyn-stream-placement-parity
- **Severity**: important
- **Concern**: Deleted shell helpers pin stdout vs stderr contracts for all six verbs. The plan's pytest expansion specifies stream-placement assertions only for `upsert-summary` failures. `read`, `create-issue`, `append-comment`, `rename`, and `mark-false-positive` lack stdout/stderr separation tests despite approach requiring stdout failure envelopes for non-upsert verbs. Callers (`implement-bootstrap.sh`, `design-publish.sh`) capture `FAILED=` / `ERROR=` from stdout only; regressions that move failure envelopes to stderr would break production callers without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stream-placement-parity: Add minimal subprocess/capfd tests per write/read main: success KVs on stdout; exit 1/2/3 failures emit FAILED=true and ERROR= on stdout and not stderr; mirror test_issue_wire.py plan-block stdout patterns and retiring test-tracking-issue-read-sentinel.sh stdout failure cases
  - From Codex-dyn-stream-placement-parity: Add explicit cli.main or main-function tests in python/test_tracking_issue.py for each verb that capture stdout and stderr separately. Assert success KVs are on stdout, read and write-helper failure envelopes stay on stdout, and upsert-summary failure envelopes stay on stderr.




### FINDING_2: Ship-pr cutover uses cwd-relative Python path
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed `ship-pr.sh` cutover can fail outside the plugin repository because it uses `python3 python/cli.py` instead of resolving the CLI through the plugin root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename, preserving existing repo args and failure recording
  - From Codex-Requirements: Use `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue rename` in both `--repo` and ambient-repo branches, and preserve the existing failure-recording behavior.


### FINDING_3: Migration-history allowance can still fail retired-script lint
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan allows retired script path literals in migration-history text even though `lint-retired-scripts` still scans those tracked files and can fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove the migration-history allowance, or record F3e without full retired repo-relative path literals outside python/migrated-scripts.tsv


### FINDING_4: Rename CLI needs shell idempotency parity
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned `rename_main` behavior may spuriously rename issues unless it ports the shell helper’s redaction, canonical-prefix detection, and canonical-title comparison algorithm.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Port tracking-issue-write.sh rename idempotency from scripts/tracking-issue-write.sh:465-491: redact current title, detect CUR_CANON_PREFIXES from the redacted title, rebuild CUR_TITLE_CANONICAL, compare to prospective NEW_TITLE before gh issue edit


### FINDING_5: Tracking CLI mains need quiet routing initialization
- **Reviewer(s)**: Codex-Pragmatic, Cursor-dyn-stream-placement-parity
- **Severity**: important
- **Concern**: Missing `quiet_init` in tracking-issue CLI entry points can route stdout or stderr contract output to the wrong stream under inherited quiet environments, breaking command substitution captures and redirected failure handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add logging_util.quiet_init at the start of each tracking-issue main before any KEY=value emission, or explicitly use raw stdout only. Add one quiet-env capture regression for a representative tracking-issue verb.
  - From Cursor-dyn-stream-placement-parity: Add logging_util.quiet_init(argv0="tracking-issue-summary.sh") at upsert_summary_main entry; emit FAILED=true and ERROR= only via diagnostic() (never emit_kv); add a subprocess test mirroring python/test_issue_wire.py inherited-quiet cases that asserts failure lines land on the redirected stderr fd when parent quiet env is set


### FINDING_6: Write-verb usage errors must preserve stderr-only behavior
- **Reviewer(s)**: Codex-dyn-stream-placement-parity
- **Severity**: important
- **Concern**: The plan may incorrectly add stdout `FAILED=true` or `ERROR=` envelopes to usage-error paths that the retired write helper handled as stderr-only exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stream-placement-parity: Narrow the plan and tests: keep stdout FAILED=true and ERROR= for current envelope-producing validation, gh, and redaction failures, but preserve stderr-only usage behavior for write-verb usage errors unless the implementation deliberately documents a breaking contract change.


### FINDING_7: Stale-reference sweep misses bare helper tokens
- **Reviewer(s)**: Cursor-dyn-consumer-cutover-sweep
- **Severity**: important
- **Concern**: The terminal stale-reference grep only matches `.sh` filenames, so harness stubs and assertions using bare retired helper names can survive the cutover undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-consumer-cutover-sweep: Broaden the sweep regex to also match bare helper tokens (e.g. `tracking-issue-write`, `tracking-issue-summary`, `tracking-issue-read`) or explicitly require retargeting all assertion/stub log strings in the listed harness `UPDATED` sections


### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:197
- **Concern**: [SCOPE-REDUCTION] Sentinel pytest spec says leading whitespace is ignored but the retired helper requires column-0 keys only. Scenario: Implementing leading-whitespace stripping or tolerant key matching would diverge from scripts/tracking-issue-read.sh:240-241 and scripts/test-tracking-issue-read-sentinel.sh:298-299 where indented ISSUE_NUMBER= lines are treated as absent
- **Proposed resolution**: Rephrase the sentinel test bullet to pin column-0-only parsing: indented keys emit empty values; keep BOM and trailing CRLF tests separate


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:199
- **Concern**: [SCOPE-REDUCTION] Emergency title fallback still points at deleted shell strip_one_lifecycle_prefix with no mechanical Python call. Scenario: After scripts/tracking-issue-write.sh is deleted, --emergency preflight has no callable strip helper; an orchestrator can improvise wrong prefix handling and write a bad plan-from-issue.txt
- **Proposed resolution**: Add one explicit preflight invocation pattern in the plan (for example python3 -c "from tracking_issue import strip_lifecycle_prefix; print(strip_lifecycle_prefix(sys.argv[1]))" "$title") and update SKILL.md to reference that call, not the retired shell helper name


### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:355-363
- **Concern**: [SCOPE-REDUCTION] Plan cuts over scripts/upsert-diagrams-comment.sh but that path is absent; diagrams already go through python/cli.py diagrams upsert / python/rendering.py. Scenario: Implementers may add a new shell wrapper or duplicate upsert logic hunting a file that no longer exists
- **Proposed resolution**: Drop the scripts/upsert-diagrams-comment.sh section; keep only the python/rendering.py audit confirming existing upsert_marker_comment usage


### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/tracking_issue.py:44-73
- **Concern**: [SCOPE-REDUCTION] Plan adds a separate rename_main with shell-grade idempotency while keeping rename() on a weaker raw-title early return. Scenario: Shell rename compares redacted canonical titles (scripts/tracking-issue-write.sh:465-491); library rename() returns early on new_title == current_title before redaction, so CLI and library paths can diverge and pytest can green-light the wrong semantics
- **Proposed resolution**: Implement shell parity once in shared rename logic (canonical redacted compare, retry, KV emission in rename_main only) and have rename_main call that core instead of a parallel implementation


### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:355-363
- **Concern**: [SCOPE-REDUCTION] Plan lists `### UPDATED: scripts/upsert-diagrams-comment.sh` but that helper is already retired. Scenario: `python/migrated-scripts.tsv` records `scripts/upsert-diagrams-comment.sh` as migrated under #3675 and the file is absent from the repo; F3e cutover work would target a dead path outside the live tracking-issue shell surface
- **Proposed resolution**: Drop the `upsert-diagrams-comment.sh` subsection. Keep only the existing `python/rendering.py` audit (diagrams already go through `tracking_issue.upsert_marker_comment` / `python/cli.py diagrams upsert`)




### FINDING_1: Public rename wrapper must share shell-parity core
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The CLI rename path can gain shell parity while the public `tracking_issue.rename()` path keeps different idempotency, fetching, or return behavior. This can regress `finalize.py` callers or create divergent tracking titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add one bullet: public rename(runner, issue, state, *, repo, current_title, cwd) delegates to the shared core using the supplied current_title (no second gh fetch). Drop or amend the outline non-goal that blocks changing rename()
  - From Cursor-Pragmatic: Refactor so public rename() delegates to the same shared rename core as rename_main (fetch/compare/edit/retry logic shared; KV emission stays in rename_main only); add a direct unit test that a redactable current title yields RENAMED=false without gh edit
  - From Codex-Pragmatic: Keep tracking_issue.rename(runner, issue, state, repo=..., current_title=..., cwd=...) -> str as a compatibility wrapper, and put CLI details in a new private core or rename_with_details helper.


### FINDING_2: Upsert-summary body must preserve blank-line framing
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Reusing `upsert_marker_comment` unchanged can compose summary bodies as `marker\ncontent` instead of the shell-compatible `marker\n\ncontent`, causing byte-parity drift for existing summary comments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Implement upsert_summary_main with the shell body shape (marker, blank line, content), best-effort tmpdir redaction, then secret redaction. Do not route summary upserts through upsert_marker_comment unchanged.
  - From Cursor-Requirements: Specify in `upsert_summary_main` that composed bodies use `f"{marker}\n\n{content}"` (matching `scripts/tracking-issue-summary.sh:98`) and add a pytest asserting the posted/patched body shape


### FINDING_3: Append-comment success must require parseable issuecomment URL
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: If `gh issue comment` exits 0 without a parseable `#issuecomment` URL, the Python port can report success with empty `COMMENT_ID` or `COMMENT_URL`, unlike the shell helper which exits 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Require a parseable issuecomment URL for append-comment success, derive COMMENT_ID from it, and add a test for the no-URL rc0 failure envelope


### FINDING_4: Read usage errors must keep stdout failure envelope
- **Reviewer(s)**: Cursor-dyn-stream-contract, Codex-dyn-stream-contract
- **Severity**: important
- **Concern**: Planned stream-placement tests can miss the `tracking-issue read` usage path. The shell read helper emits usage failures as stdout `FAILED=true` and `ERROR=usage:…`, unlike write-verb usage failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stream-contract: Add read usage-stream tests: invalid flag combination and non-numeric --issue must emit FAILED/ERROR=usage: on stdout with empty stderr; document the same in the read_main plan section.
  - From Cursor-dyn-stream-contract: Extend the six-verb stream matrix to three rows per verb (success / usage / non-usage). For read, assert usage and non-usage both use stdout FAILED; for upsert-summary, assert all failure classes use stderr FAILED.
  - From Codex-dyn-stream-contract: Add a read usage row to the parity table/tests and state in `read_main` that usage and invalid-combination errors use the old stdout failure envelope, unlike write-verb usage errors


### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:138-153; python/finalize.py:430-441
- **Concern**: [SCOPE-REDUCTION] Rename plan risks changing the existing public tracking_issue.rename API. Scenario: The plan moves fetch/idempotency/result details into shared rename logic, but python/finalize.py still calls tracking_issue.rename(..., current_title=...) and expects the existing string-returning behavior. Changing that signature or return type would regress the live Python finalize path.
- **Proposed resolution**: Keep tracking_issue.rename(runner, issue, state, repo, current_title, cwd) as a stable adapter returning the new title string. Put shell-parity logic in a private core, and let rename_main fetch the title and emit RENAMED/NEW_TITLE from that core.


### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:24-27,138-153; python/finalize.py:435
- **Concern**: [SCOPE-REDUCTION] Plan replaces existing public rename behavior despite the approved non-goal to leave existing Python functions unchanged. Scenario: tracking_issue.rename already has Python callers such as finalize; changing shared behavior expands the blast radius beyond the CLI cutover and can affect default Python finalize paths
- **Proposed resolution**: Keep the existing public rename function stable, and put shell-parity RENAMED/NEW_TITLE behavior in a CLI-specific wrapper or a new helper that does not change existing caller semantics




### FINDING_1: Validate read `--out-dir` before writing outputs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Read modes need shell-parity validation that explicit `--out-dir` exists and is a directory before writing `task.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin an out-dir existence check for every non-`--sentinel` read path before writing `task.md`, with the same stdout failure envelope and exit `1`


### FINDING_2: Preserve shell-parity append delegation and failure mapping in issue-plus-prompt reads
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `read --issue --prompt` must use the shell-parity append path, preserve the `append-comment failed:` prefix, require comment URL recovery, and map delegated append failures to read exit `2` rather than leaking append-only exits such as `3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When internal append fails in `--issue --prompt`, emit `ERROR=append-comment failed: ...` on stdout before exit `2`
  - From Cursor-Innovation: Delegate mode 1 to the same internal helper used by append_comment_main (retry plus COMMENT_ID/COMMENT_URL parse plus exit 2 on rc 0 without URL) before fetching issue context
  - From Cursor-Pragmatic: In read_main --issue --prompt, catch append helper redaction/validation failures and emit the same stdout FAILED envelope with exit 2; never propagate exit 3 through read.


### FINDING_3: Preserve false-positive idempotency before truncation
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: `mark-false-positive` must compare marker insertion against the redacted current title before truncation or editing, so already-marked titles remain no-ops and do not lose title text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After `insert_signal_marker`, compare against the redacted pre-marker title; emit `MARKED=false` and skip edit on equality
  - From Codex-Pragmatic: Compare insert_signal_marker output to the redacted current title before truncation. If unchanged, emit MARKED=false and NEW_TITLE as the current redacted title. Only truncate and edit when a marker was newly inserted.


### FINDING_5: Specify read cap override flags on `read_main`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan tests read cap overrides but does not specify `read_main` argparse wiring for `--max-body-chars`, `--max-comments`, and `--max-total-chars`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add those three optional flags to `read_main` with the same defaults and validation as the shell helper


### FINDING_6: Retarget all consumer cutover docs and scripts to the explicit Python CLI
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Consumer cutover instructions and runtime references may leave stale deleted-script names or bare `tracking-issue` invocations instead of the explicit `python3 .../python/cli.py tracking-issue ...` form.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add explicit UPDATED entries for skills/implement/SKILL.md Invariant #2 and skills/implement/references/summary-comment-template.md (and sibling contracts like skills/design/scripts/design-publish.md, scripts/implement-finalize.md) retargeting to python3 …/python/cli.py tracking-issue upsert-summary.
  - From Cursor-Requirements: Align every consumer subsection with the explicit forms used elsewhere, e.g. `python3 "$PLUGIN_ROOT/python/cli.py" tracking-issue upsert-summary …` and `python3 "$SCRIPT_DIR/../python/cli.py" tracking-issue read --sentinel …`.


### FINDING_7: Require `make lint` as a final gate
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The feature definition of done requires `make lint`, `make py-lint`, and `make py-test`, but the plan makes `make lint` optional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make make lint a required final gate alongside make py-lint and make py-test.


### FINDING_8: Keep read usage stream tests aligned with actual shell behavior
- **Reviewer(s)**: Codex-dyn-stream-parity
- **Severity**: important
- **Concern**: The read usage stream contract should not claim a stdout `FAILED=true` / `ERROR=usage` envelope for invalid invocations that Bash currently exits before `fail_usage`, such as missing option values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stream-parity: Narrow the read stream contract and tests to the shell-parity cases that actually use fail_usage, or explicitly add missing-value cases as stderr/no-stdout parity cases instead of stdout-envelope cases.


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tracking_issue.py:read_main
- **Concern**: [SCOPE-REDUCTION] Read-mode summary skip list is underspecified versus shell. Scenario: Plan names marker families in prose but does not pin the exact first-line patterns from scripts/tracking-issue-read.sh (metadata/diagrams/plan/token-report/final-summary runid variants plus legacy implement-anchor). A partial port can leave summary comments in task.md and break the feedback-loop guard on issue and issue-plus-prompt reads
- **Proposed resolution**: Add an explicit constant list matching scripts/tracking-issue-read.sh:427-434 (both <!-- larch:diagrams v1 --> and <!-- larch:diagrams v1 runid=… --> forms) and test one representative row per pattern



