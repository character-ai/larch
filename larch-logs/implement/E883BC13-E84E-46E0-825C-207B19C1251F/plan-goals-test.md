## Goal
Implement issue #3991: [IMPLEMENTING] auto-error-reporting: always file failure reports in the upstream larch repo (cross-repo filing + signature dedup).

## Implementation Plan
## Plan

## Approach

Implement Part 2 only: upstream filing and signature dedup for existing `/implement` stall recovery reports.

- Resolve the canonical upstream larch repo from `.claude-plugin/plugin.json` `repository`.
- Keep Tier A filing in the current larch repo through the existing `/larch:issue` path.
- Use a direct `gh issue create -R` helper for Tier B upstream filing.
- Add signature dedup before every create path.
- Bind each dedup pass to the same repo as its filing/comment path:
  - Tier A dedup searches the current `/larch:issue` filing repo.
  - Tier B dedup searches the resolved upstream larch repo.
- Split retry failure signatures from public report dedup signatures.
- Define one canonical `REPORT_DEDUP_SIGNATURE` seed grammar.
- Seed terminal-failure public dedup signatures only from:
  - `report_kind`
  - `failure_class`
  - `step`
  - `phase`
  - `safe_bail_token`
- Seed escalation-success public dedup signatures from the same fields plus:
  - `escalation_site`
  - `escalation_trigger`
- Do not include dispatcher, matched classifier, evidence digest, paths, branches, run IDs, raw state, raw logs, or `skill=implement` in Part 2 public report dedup seeds.
- Keep Tier A content and current-repo `/larch:issue` create path.
- Make Tier A lookup failure fail open, including missing marker during dedup-only.
- After Tier A exact-signature dedup returns `no-match` or `lookup-failed-open`, invoke `/larch:issue --input-file ... --no-dedup`.
- On confirmed duplicate with failed comment, fall back to manual print instead of creating a duplicate.
- Add a normalized Tier A dedup entrypoint in `stall-recovery-report.sh`.
- Prompt/runtime code must branch on `STALL_RECOVERY_REPORT_*`, not raw `FILE_FAILURE_REPORT_*`.
- Ensure composition steps do not emit branchable `STALL_RECOVERY_REPORT_STATUS`.
- Emit authoritative `STALL_RECOVERY_REPORT_STATUS` only from filing, dedup, dry-run, fallback, or skipped-operator-action steps.
- Preserve canonical `ISSUE_URL` and `ISSUE_NUMBER` persistence after successful Tier A `/larch:issue`.
- Keep dry-run local-only:
  - skip Tier A dedup and `/larch:issue`.
  - skip Tier B upstream resolver and cross-repo helper.
  - emit normalized `STALL_RECOVERY_REPORT_STATUS=dry-run`.
  - make no `gh` calls.
- Apply the Tier B safety boundary to dedup comments:
  - Tier B comments may use only pre-rendered bounded public slices.
  - Tier B comment assembly must reuse the existing Tier B sensitive-token rejection path.
  - Never pass raw root-cause or raw escalation ledger files to the Tier B comment path.
- Define Tier A post-create status and URL outputs.
- Update `/implement` Step 18a and 18a.5 runtime wiring.
- Document public upstream filing and public dedup comments for all Tier B `/implement` stall recovery reports.
- Defer all `/design` failure-reporting surfaces to Part 3.

## Files to modify/create

### NEW: scripts/resolve-upstream-larch-repo.sh

Parse `$PLUGIN_ROOT/.claude-plugin/plugin.json` with Python stdlib.

Behavior:

- Read `repository`.
- Accept GitHub HTTPS, SSH, `git+https`, and plain `OWNER/REPO` forms.
- Strip `.git`.
- Emit exactly `OWNER/REPO`.
- Reject missing, non-GitHub, malformed, newline, path traversal, or multi-value data.

Failure mode:

- Exit non-zero.
- Emit a short stderr diagnostic.
- Callers treat this as Tier B filing failure and fall back to chat-print.
- Do not guess `character-ai/larch`.

### NEW: scripts/resolve-upstream-larch-repo.md

Document:

- Metadata-based repo resolution decision.
- Why this handles repo renames better than a pinned constant.
- Failure mode: no cross-repo filing; print the composed sanitized report for manual filing.
- Stdout contract.

### NEW: scripts/test-resolve-upstream-larch-repo.sh

Cover:

- HTTPS repository URL.
- SSH repository URL.
- Plain `OWNER/REPO`.
- `.git` suffix.
- Missing `repository`.
- Non-GitHub URL rejection.
- Malformed owner or repo rejection.
- Newline injection rejection.

### NEW: scripts/test-resolve-upstream-larch-repo.md

Sibling contract doc for the harness above.

Point to `scripts/resolve-upstream-larch-repo.md` as primary.

### NEW: scripts/file-failure-report-cross-repo.sh

Add the shared filing and dedup helper.

Inputs:

- `--repo OWNER/REPO`
- `--body-file PATH`
- `--title TITLE`, required for create paths
- `--dedup-only` for Tier A pre-pass use
- optional `--attempts-file PATH`
- optional `--escalation-ledger-file PATH`
- optional `--root-cause-file PATH`
- optional `--publication-tier tier-a|tier-b`
- optional `--dry-run`

Validation:

- Validate each supplied file as regular, readable, and non-symlink.
- Extract exact marker `<!-- larch-stall:signature=<64-hex> -->` from `--body-file`.
- For `--dedup-only`, missing marker emits `FILE_FAILURE_REPORT_STATUS=lookup-failed-open` and exits 0.
- For non-`--dedup-only`, missing marker emits `FILE_FAILURE_REPORT_STATUS=fallback-print-required` and exits 0.
- For create paths, reject missing or empty `--title` with fallback status.
- For `--publication-tier tier-b`, treat structured comment payload files as already bounded public slices.
- For `--publication-tier tier-b`, assemble the final comment body only from those bounded slices.
- For `--publication-tier tier-b`, run the assembled final comment body through the existing Tier B sensitive corpus and `sensitive_token_rejects_file` rejection path.
- For `--publication-tier tier-b`, fail with fallback status if the final comment body contains raw report body sections or disallowed sensitive-token evidence.
- Keep captured stderr redacted through `python3 python/cli.py redact secrets`.

Dedup flow:

1. Read all open issues from `--repo` with a paginated body-capable API call, for example `gh api --paginate "repos/$repo/issues?state=open&per_page=100"`.
2. Ignore pull requests in the returned issues.
3. Exact-match the marker in fetched issue bodies.
4. On match:
   - Build a temp comment body from structured inputs, not by reposting the full issue body.
   - First line: `+1 occurrence`.
   - Include this run's attempts table from `--attempts-file` when supplied.
   - Include escalation evidence from `--escalation-ledger-file` when supplied.
   - Include root-cause finding from `--root-cause-file` when supplied.
   - Use an explicit placeholder when an optional slice is absent.
   - For Tier B, accept only pre-rendered bounded public slices from the caller.
   - For Tier B, validate the final assembled comment with the existing Tier B sensitive-token rejection path before posting.
   - Post with `gh api repos/$repo/issues/$number/comments`.
   - Emit `FILE_FAILURE_REPORT_STATUS=dedup-comment`.
   - Emit `FILE_FAILURE_REPORT_URL=<comment html_url>`.
5. On no match and `--dedup-only`:
   - Emit `FILE_FAILURE_REPORT_STATUS=no-match`.
6. On lookup failure and `--dedup-only`:
   - Emit `FILE_FAILURE_REPORT_STATUS=lookup-failed-open`.
   - Emit `FILE_FAILURE_REPORT_FALLBACK_REASON=<token>`.
   - Exit 0 so Tier A callers continue to the existing `/larch:issue` path.
7. On no match without `--dedup-only`:
   - Create with `gh issue create -R "$repo" --title "$title" --body-file "$body_file"`.
   - Normalize the created issue URL.
   - Emit `FILE_FAILURE_REPORT_STATUS=filed`.
   - Emit `FILE_FAILURE_REPORT_URL=<issue-url>`.
8. On lookup, auth, network, comment, or create failure outside Tier A fail-open lookup:
   - Emit `FILE_FAILURE_REPORT_STATUS=fallback-print-required`.
   - Emit `FILE_FAILURE_REPORT_FALLBACK_REASON=<token>`.
   - Exit 0 so callers can print the already-sanitized report.
9. On `--dry-run`:
   - Validate inputs and marker rules.
   - Emit `FILE_FAILURE_REPORT_STATUS=dry-run`.
   - Make no `gh` calls.

### NEW: scripts/file-failure-report-cross-repo.md

Document:

- Signature dedup contract.
- All-open-issues body fetch requirement.
- Exact client-side marker match.
- Direct `gh issue create -R` rationale.
- `FILE_FAILURE_REPORT_STATUS=filed` as the create-success token.
- `--title` requirement for create paths.
- Structured comment payload inputs.
- `--publication-tier tier-b` public comment contract.
- Tier B dedup comments may include only bounded public slices.
- Tier B comment bodies reuse the existing Tier B sensitive-token rejection path before posting.
- Tier B callers must pass:
  - bounded attempts table.
  - allowlisted escalation summary with sanitized site and trigger rows only.
  - `stall-recovery-bounded-root-cause.md` or equivalent pre-rendered bounded root-cause slice.
- Tier B callers must not pass raw ledger TSV, raw root-cause files, full report bodies, raw logs, paths, branches, or run IDs as comment payloads.
- `--dedup-only` Tier A use.
- `FILE_FAILURE_REPORT_STATUS=no-match` on clean dedup miss.
- Tier A lookup-failure and marker-missing fail-open behavior.
- Fallback-print contract.
- Output KVs.
- URL semantics:
  - `FILE_FAILURE_REPORT_URL` may be an issue URL or comment URL depending on status.
  - Issue URL aliases are the caller's responsibility and must not be populated from comment URLs.
- Security boundary:
  - Tier A callers may pass Tier A redacted payloads.
  - Tier B callers must pass only Tier B allowlisted output.
  - The helper validates and rejects unsafe final public Tier B comment bodies before posting.

### NEW: scripts/test-file-failure-report-cross-repo.md

Sibling contract doc for the harness below.

Point to `scripts/file-failure-report-cross-repo.md` as primary.

### NEW: scripts/test-file-failure-report-cross-repo.sh

Use PATH stubs for `gh`.

Cover:

- Creates issue with `gh issue create -R`.
- Create path passes `--title`.
- Create success emits `FILE_FAILURE_REPORT_STATUS=filed`.
- Dedup match posts one comment and skips create.
- Dedup comment uses structured attempts, escalation summary, and root-cause files.
- Dedup comment does not repost the full report body.
- Tier B publication mode accepts bounded public slices.
- Tier B publication mode rejects or falls back on raw full-body comment payloads.
- Tier B publication mode rejects comments caught by the existing sensitive-token rejection path.
- Dedup match after page 1 is found.
- Marker only present in issue body is found.
- Pull requests returned by the issues API are ignored.
- `--dedup-only` emits `no-match`.
- `--dedup-only` lookup failure emits `lookup-failed-open`.
- `--dedup-only` missing marker emits `lookup-failed-open`.
- Non-dedup missing marker emits `fallback-print-required`.
- Comment failure after confirmed duplicate falls back.
- Create failure falls back.
- Returned issue URLs normalize.
- Comment URLs remain comment URLs.
- Body symlink and missing body fail closed.
- Structured payload symlink and missing structured payload fail closed when supplied.
- Dry run makes no `gh` calls.

### UPDATED: skills/implement/scripts/stall-recovery-report.sh

Add report filing support with minimal core changes.

Changes:

- Keep existing `/implement` flags working.
- Keep existing Tier A and Tier B content allowlists.
- Keep the existing retry failure signature formula unchanged.
- Add a separate `REPORT_DEDUP_SIGNATURE` for the public HTML marker.
- Define canonical public report seed serialization:
  - grammar version line: `larch-stall-report-dedup-v1`
  - UTF-8 text input.
  - LF line endings.
  - field order fixed by report kind.
  - each field line encoded as `key<TAB>byte_length<TAB>value`.
  - missing optional values encoded as byte length `0` and empty value.
  - final newline included.
  - hash primitive: SHA-256 over the canonical bytes, emitted as lowercase 64-hex.
- For terminal-failure reports, canonical field order is:
  - `report_kind`
  - `failure_class`
  - `step`
  - `phase`
  - `safe_bail_token`
- For escalation-success reports, canonical field order is:
  - `report_kind`
  - `failure_class`
  - `step`
  - `phase`
  - `safe_bail_token`
  - `escalation_site`
  - `escalation_trigger`
- Read `escalation_site` and `escalation_trigger` from the same first ledger or fallback row used in the report title.
- Sanitize `escalation_site` and `escalation_trigger` with the same sanitizer used for the title before seed serialization.
- Keep `escalation_site` and `escalation_trigger` out of terminal-failure seeds.
- Exclude repo-specific or run-specific data from `REPORT_DEDUP_SIGNATURE`:
  - evidence digest
  - run IDs
  - paths
  - branches
  - raw state
  - raw logs
- Exclude dispatcher and matched classifier from `REPORT_DEDUP_SIGNATURE`.
- Do not include `skill=implement` in the Part 2 seed.
- Render the exact marker `<!-- larch-stall:signature=<hash> -->` into every Tier A and Tier B report body.
- For Tier A `issue-input`, place the marker immediately after the `###` title line so `/larch:issue` preserves it in the created issue body.
- For Tier B `chat-print`, include the marker near the top of the body.
- Treat the computed 64-hex `REPORT_DEDUP_SIGNATURE` as a report-safe machine field only for that exact HTML marker.
- Validate and redact the final Tier B body after inserting the marker, before passing it to the cross-repo helper.
- Emit structured comment payload files for Tier A:
  - attempts table
  - escalation ledger slice
  - root-cause finding
- Emit bounded public structured comment payload files for Tier B:
  - bounded attempts table
  - allowlisted escalation summary with sanitized site and trigger rows only
  - bounded root-cause finding, for example `stall-recovery-bounded-root-cause.md`
- Do not pass raw Tier A root-cause or raw ledger files to the Tier B comment path.
- Ensure `compose-report --surface issue-input` is composition-only and does not emit branchable `STALL_RECOVERY_REPORT_STATUS=printed`.

Add a helper output normalizer:

- Map `FILE_FAILURE_REPORT_STATUS=filed` to `STALL_RECOVERY_REPORT_STATUS=filed`.
- Map `FILE_FAILURE_REPORT_STATUS=dry-run` to `STALL_RECOVERY_REPORT_STATUS=dry-run`.
- Pass through `dedup-comment`, `no-match`, `fallback-print-required`, and `lookup-failed-open`.
- Map `FILE_FAILURE_REPORT_URL` to canonical `STALL_RECOVERY_REPORT_URL`.
- Emit `STALL_RECOVERY_REPORT_ISSUE_URL` only when the URL is an issue URL.
- Emit `STALL_RECOVERY_REPORT_ISSUE_NUMBER` only when parsed from an issue URL.
- Do not populate issue URL aliases from a dedup-comment URL.
- Prefer `STALL_RECOVERY_REPORT_URL` for new notices.

Add a Tier A dedup entrypoint, for example `dedup-tier-a-report`:

- Resolve the current filing repo with the same current-repo resolver used by the existing issue path.
- Call `scripts/file-failure-report-cross-repo.sh --dedup-only`.
- Pass `--publication-tier tier-a`.
- Pass Tier A structured comment payload files.
- Normalize helper output to `STALL_RECOVERY_REPORT_*`.
- Emit only normalized `STALL_RECOVERY_REPORT_*` KVs for prompt/runtime consumers.
- If current repo resolution fails, emit:
  - `STALL_RECOVERY_REPORT_STATUS=lookup-failed-open`
  - `STALL_RECOVERY_REPORT_FALLBACK_REASON=current-repo-unresolved`
- Make no `gh` calls when `DRY_RUN_DECISION=true` or `LARCH_STALL_RECOVERY_DRY_RUN=1`; emit `STALL_RECOVERY_REPORT_STATUS=dry-run`.

For Tier B `compose-report`:

- Render the sanitized artifact first.
- If dry-run is active:
  - skip upstream resolver.
  - skip cross-repo helper.
  - make no `gh` calls.
  - emit `DRY_RUN_DECISION=true`.
  - emit `STALL_RECOVERY_REPORT_STATUS=dry-run`.
  - keep local artifact-only behavior.
- Resolve upstream with `scripts/resolve-upstream-larch-repo.sh` only when dry-run is not active.
- On upstream resolver failure, emit:
  - `STALL_RECOVERY_REPORT_STATUS=fallback-print-required`
  - `STALL_RECOVERY_REPORT_FALLBACK_REASON=upstream-repo-unresolved`
  - preserve `stall-recovery-chat-print.md` for fallback printing.
- Call `scripts/file-failure-report-cross-repo.sh` with:
  - `--repo "$upstream_repo"`
  - `--body-file "$IMPLEMENT_TMPDIR/stall-recovery-chat-print.md"`
  - `--title "$report_title"`
  - `--publication-tier tier-b`
  - bounded public structured comment payload files
- Emit `STALL_RECOVERY_REPORT_STATUS=filed|dedup-comment|fallback-print-required|skipped_operator_action|dry-run`.
- Emit `STALL_RECOVERY_REPORT_URL` on filed or comment success.
- Keep `LARCH_STALL_RECOVERY_DRY_RUN=1` local-only.

For Tier A create flow:

- Keep `issue-input` and current `/larch:issue` flow.
- Prompt/runtime code calls the normalized `dedup-tier-a-report` entrypoint before `/larch:issue`.
- On `dedup-comment`, skip `/larch:issue`.
- On `no-match` or `lookup-failed-open`, continue to `/larch:issue --input-file ... --no-dedup`.
- On `fallback-print-required` after a confirmed duplicate comment failure, print the sanitized report instead of creating a duplicate.
- On `dry-run`, skip dedup and `/larch:issue`.
- After successful `/larch:issue` creation:
  - call existing `normalize-issue-env` or the equivalent folded writer.
  - persist canonical `ISSUE_URL` and `ISSUE_NUMBER`.
  - emit `STALL_RECOVERY_REPORT_STATUS=filed`.
  - emit `STALL_RECOVERY_REPORT_URL=<issue-url>`.
  - emit `STALL_RECOVERY_REPORT_ISSUE_URL=<issue-url>`.
  - emit `STALL_RECOVERY_REPORT_ISSUE_NUMBER=<number>` when parseable.

### UPDATED: skills/implement/scripts/stall-recovery-report.md

Update:

- Retry signature and public report dedup signature are separate.
- Public report marker uses `REPORT_DEDUP_SIGNATURE`.
- Canonical `REPORT_DEDUP_SIGNATURE` seed grammar:
  - version line `larch-stall-report-dedup-v1`.
  - fixed field order.
  - `key<TAB>byte_length<TAB>value` lines.
  - UTF-8 bytes.
  - LF endings.
  - final newline.
  - SHA-256 lowercase 64-hex output.
- Terminal-failure public report signature seed includes only:
  - `report_kind`
  - `failure_class`
  - `step`
  - `phase`
  - `safe_bail_token`
- Escalation-success public report signature seed includes only:
  - `report_kind`
  - `failure_class`
  - `step`
  - `phase`
  - `safe_bail_token`
  - sanitized `escalation_site`
  - sanitized `escalation_trigger`
- Public report signature seed excludes dispatcher, matched classifier, repo-specific evidence, and run-specific evidence.
- Part 2 intentionally omits `skill=implement`; skill-aware hashing is deferred to Part 3.
- Signature marker contract.
- Tier A marker placement after the `###` title line.
- Tier A dedup repo is the same repo that `/larch:issue` will file into.
- Tier B dedup repo is the resolved upstream larch repo.
- Tier B final-body validation after marker insertion.
- Tier B dedup comments reuse the existing Tier B sensitive-token rejection path.
- Tier B now files upstream instead of chat-printing on success.
- Tier B passes the composed title to the cross-repo helper.
- Tier B passes only bounded public structured comment payload files to the cross-repo helper.
- Tier B comment payloads must not use raw root-cause files, raw escalation ledgers, full report bodies, raw logs, paths, branches, or run IDs.
- Structured comment payload files are the mechanical contract for `+1 occurrence` comments.
- Helper status normalization includes `no-match` and `dry-run`.
- `STALL_RECOVERY_REPORT_URL` is canonical for new notices.
- `STALL_RECOVERY_REPORT_ISSUE_URL` remains a compatibility alias for issue URLs only.
- Dedup-comment success uses only `STALL_RECOVERY_REPORT_URL` when the URL points to a comment.
- Tier A dedup is exposed through a normalized `STALL_RECOVERY_REPORT_*` entrypoint.
- Tier A successful `/larch:issue` creation emits `filed` and issue URL KVs.
- Tier A successful `/larch:issue` creation preserves canonical `ISSUE_URL` and `ISSUE_NUMBER` persistence through `normalize-issue-env` or equivalent writer.
- After Tier A signature dedup returns `no-match` or `lookup-failed-open`, `/larch:issue` must be called with `--no-dedup`.
- The `--no-dedup` rule prevents semantic dedup from hiding a new exact-signature occurrence.
- Tier A `issue-input` composition is not an authoritative filing status and must not emit branchable `STALL_RECOVERY_REPORT_STATUS=printed`.
- Dry-run is local-only and emits `STALL_RECOVERY_REPORT_STATUS=dry-run`.
- Dry-run skips Tier A dedup, `/larch:issue`, upstream resolver, and cross-repo helper.
- Upstream resolver failure emits normalized `STALL_RECOVERY_REPORT_STATUS=fallback-print-required`.
- Tier B success notification shape:
  - `**ℹ /implement stall report filed: <github-url>**`
  - `**ℹ /implement stall report +1 comment: <github-url>**`
- Fallback keeps the current full chat-print behavior.
- Canonical repo resolution choice and failure mode.
- Tier A dedup lookup failure and marker-missing are fail-open to the existing `/larch:issue --no-dedup` create path.

### UPDATED: skills/implement/references/stall-recovery.md

Update Step 18a and 18a.5:

- Tier A:
  - compose the `issue-input` artifact.
  - treat compose output as artifact metadata only, not as authoritative filing status.
  - if `DRY_RUN_DECISION=true`, skip dedup and `/larch:issue`, then write the terminal sentinel with `STALL_RECOVERY_REPORT_STATUS=dry-run`.
  - call the normalized `stall-recovery-report.sh dedup-tier-a-report` entrypoint.
  - branch only on `STALL_RECOVERY_REPORT_STATUS`.
  - pass Tier A structured comment payload files through the entrypoint.
  - on `dedup-comment`, skip create and write the terminal sentinel.
  - on `no-match` or `lookup-failed-open`, continue to `/larch:issue --input-file ... --no-dedup`.
  - on confirmed duplicate with comment failure, print fallback report and write the terminal sentinel.
  - after successful `/larch:issue`, call `normalize-issue-env` or equivalent writer before writing `stall-recovery-terminal-report.env`.
  - after successful `/larch:issue`, persist canonical `ISSUE_URL` and `ISSUE_NUMBER`.
  - after successful `/larch:issue`, normalize and emit `STALL_RECOVERY_REPORT_STATUS=filed`.
  - populate `STALL_RECOVERY_REPORT_URL`, `STALL_RECOVERY_REPORT_ISSUE_URL`, and `STALL_RECOVERY_REPORT_ISSUE_NUMBER` from the created issue URL.
- Tier B:
  - call `compose-report --surface chat-print`.
  - if `DRY_RUN_DECISION=true`, skip upstream resolver and cross-repo helper.
  - resolve upstream larch repo inside the report composer only when dry-run is not active.
  - pass the composed title to the cross-repo helper.
  - pass only bounded public comment payload files to the cross-repo helper.
  - dedup and file/comment against the resolved upstream repo.
  - on upstream resolver failure, receive normalized `STALL_RECOVERY_REPORT_STATUS=fallback-print-required`.
  - on `filed` or `dedup-comment`, print only the short notice.
  - on `fallback-print-required`, print `stall-recovery-chat-print.md`.
  - on `dry-run`, keep local-artifact-only behavior.
  - on `skipped_operator_action`, keep the local sentinel and do not file.
- `is-larch-dev-clone` selects content tier only.
- It no longer decides whether any public report is filed.
- New prompt logic must branch on canonical `STALL_RECOVERY_REPORT_STATUS`.
- New prompt notices must prefer `STALL_RECOVERY_REPORT_URL`.
- Issue URL aliases must not be read for dedup-comment URLs.

### UPDATED: skills/implement/SKILL.md

Wire the runtime prompt to the new filing contract.

Update Step 18a and Step 18a.5 so:

- Tier A resolves the current `/larch:issue` filing repo inside the normalized dedup entrypoint.
- Tier A uses `stall-recovery-report.sh dedup-tier-a-report`, not the raw cross-repo helper.
- Tier A branches on `STALL_RECOVERY_REPORT_STATUS`.
- Tier A treats compose output as non-authoritative and does not branch on `printed`.
- Tier A passes structured comment payload files to the dedup entrypoint.
- Only `dedup-comment` skips `/larch:issue`.
- `no-match` and `lookup-failed-open` continue to `/larch:issue --input-file ... --no-dedup`.
- Confirmed duplicate plus comment failure prints the sanitized fallback instead of creating a duplicate.
- Successful Tier A `/larch:issue` creation calls `normalize-issue-env` or equivalent writer before sentinel persistence.
- Successful Tier A `/larch:issue` creation emits `filed` status and issue URL KVs.
- Tier B compose-report files or comments upstream.
- Tier B passes `--title "$report_title"` to the cross-repo helper.
- Tier B passes only bounded public comment payload files to the cross-repo helper.
- Tier B success prints only the short filed/comment notice.
- Tier B fallback prints the sanitized artifact.
- Dry-run gates both tiers before any dedup, resolver, `/larch:issue`, or `gh` work.
- Dry-run emits `STALL_RECOVERY_REPORT_STATUS=dry-run`.
- `filed`, `dedup-comment`, `fallback-print-required`, `dry-run`, and `skipped_operator_action` each complete the selected terminal path before sentinel writes.
- Notices use `STALL_RECOVERY_REPORT_URL`.
- Issue URL aliases are used only for issue URLs, not comment URLs.

### UPDATED: skills/implement/scripts/test-stall-recovery-report.sh

Add cases for:

- Signature marker in Tier A and Tier B artifacts.
- Tier A marker survives the parsed `/larch:issue` input body.
- Public marker uses `REPORT_DEDUP_SIGNATURE`, not the retry failure signature.
- One golden-vector assertion for canonical `REPORT_DEDUP_SIGNATURE` seed serialization and SHA-256 output.
- Terminal-failure public marker seed is stable across repo paths, branches, run IDs, evidence digest changes, dispatcher changes, and matched-classifier changes.
- Escalation-success public marker changes when sanitized `escalation_site` changes.
- Escalation-success public marker changes when sanitized `escalation_trigger` changes.
- Terminal-failure public marker does not include escalation site or trigger.
- Part 2 seed does not include `skill=implement`.
- Tier A issue-input composition does not emit branchable `STALL_RECOVERY_REPORT_STATUS=printed`.
- Tier B validates/redacts the final body after marker insertion.
- Tier B comment payload validation reuses the existing sensitive-token rejection path.
- Tier B calls upstream resolver and cross-repo filer when not dry-run.
- Tier B skips upstream resolver and cross-repo filer during dry-run.
- Tier B passes the composed title to the cross-repo filer.
- Tier B passes bounded public structured comment payload files to the cross-repo filer.
- Tier B does not pass raw root-cause or raw ledger files to the cross-repo filer.
- Tier B upstream resolver failure emits `STALL_RECOVERY_REPORT_STATUS=fallback-print-required`.
- Tier B create success emits `filed` status and URL.
- Tier B dedup emits comment status and URL.
- Helper output maps `no-match` to `STALL_RECOVERY_REPORT_STATUS=no-match`.
- Helper output maps `dry-run` to `STALL_RECOVERY_REPORT_STATUS=dry-run`.
- Helper output maps to `STALL_RECOVERY_REPORT_STATUS`, `STALL_RECOVERY_REPORT_URL`, and issue URL compatibility keys.
- Dedup-comment URL does not populate `STALL_RECOVERY_REPORT_ISSUE_URL` or `STALL_RECOVERY_REPORT_ISSUE_NUMBER`.
- Tier B filing failure emits fallback status and preserves chat-print artifact.
- Tier A dedup-only invokes the normalized entrypoint with the current `/larch:issue` filing repo.
- Tier A dedup-only hit skips later create path.
- Tier A dedup-only no-match continues to `/larch:issue --no-dedup`.
- Tier A dedup-only lookup failure continues to `/larch:issue --no-dedup`.
- Tier A dedup-only missing marker continues to `/larch:issue --no-dedup`.
- Tier A successful `/larch:issue` creation calls `normalize-issue-env` or equivalent writer.
- Tier A successful `/larch:issue` creation preserves canonical `ISSUE_URL` and `ISSUE_NUMBER`.
- Tier A successful `/larch:issue` creation emits `filed` status and issue URL KVs.
- Tier A dedup does not call the upstream resolver.
- Tier A dry-run skips dedup and `/larch:issue`.
- Dry-run does not call `gh` on either tier.

### UPDATED: docs/configuration-and-permissions.md

Add a consumer-facing note for auto failure reports.

Cover:

- All Tier B `/implement` stall recovery reports file to the public upstream larch repo when filing succeeds.
- This includes terminal-failure reports and escalation-success reports.
- Consumer and forked runs use the operator's current `gh` GitHub identity.
- Tier B content rules are the safety boundary for public cross-repo publication.
- Tier B `+1 occurrence` comments use the same public safety boundary as Tier B issue bodies.
- Tier B comments include only bounded public attempts, sanitized escalation site/trigger summary, and bounded root-cause findings.
- Tier B comments are checked by the same sensitive-token rejection path used for Tier B publication.
- If upstream resolution, auth, or network access fails, larch prints the sanitized report for manual filing.
- Larch dev clones still use the current larch repo path.

### UPDATED: SECURITY.md

Update Stall recovery sanitization section:

- Tier B consumer and forked `/implement` stall recovery reports now file to the public upstream larch repo.
- This includes terminal-failure reports and escalation-success reports.
- The issue or comment is created under the operator's current GitHub identity.
- Tier B content rules are the safety boundary for cross-repo publication.
- Tier B dedup comments are public and must use the same bounded-content safety boundary as Tier B issue bodies.
- Tier B dedup comments are checked by the same sensitive-token rejection path used for Tier B publication.
- Tier B dedup comments may include only bounded public attempts, sanitized escalation site/trigger summary, and bounded root-cause findings.
- Tier B dedup comments must not include raw ledgers, raw root-cause files, full report bodies, raw logs, paths, branches, or run IDs.
- If upstream resolution, auth, or network fails, larch prints the sanitized report for manual filing.
- Residual risk remains bounded by the existing Tier B heuristic validation.
- Tier A successful filing still preserves canonical `ISSUE_URL` and `ISSUE_NUMBER` environment persistence.
- `/design` public filing is not part of this change and remains deferred to Part 3.

### UPDATED: Makefile

Add harness targets:

- `test-resolve-upstream-larch-repo`
- `test-file-failure-report-cross-repo`

Thread them into the relevant harness group near related shell tests.

### UPDATED: agent-lint.toml

Add new test harnesses or generated wrapper docs to the same exclude class used by comparable test scripts, if the dead-script rule requires it.

## Deferred to Part 3

Do not change these in this PR:

- `skills/design/SKILL.md`
- `skills/design/scripts/design-step3-review.sh`
- `skills/design/scripts/design-step5c.sh`
- `skills/design/scripts/design-step6-prelude.sh`
- `skills/design/scripts/design-step6-cleanup.sh`
- any new `skills/design/scripts/design-failure-report.*`
- any new `skills/design/references/design-failure-surface.md`
- any `/design` failure-report tests
- public `--skill design` or `--artifact-prefix design-failure` profile work in the shared stall core
- skill-aware public report signature hashing

## Edge cases

- **Plugin metadata missing or malformed:** do not guess `character-ai/larch`; emit normalized fallback status and fall back to printing the sanitized Tier B report.
- **Dry-run:** keep local-artifact-only behavior and make no resolver, dedup, `/larch:issue`, or `gh` calls.
- **Tier A repo target:** dedup searches the same current repo that `/larch:issue` will file into.
- **Tier A caller contract:** runtime code consumes normalized `STALL_RECOVERY_REPORT_*` output from the Tier A dedup entrypoint.
- **Tier A composition:** compose output is artifact metadata only and must not emit authoritative filing status.
- **Tier A semantic dedup:** after signature `no-match` or `lookup-failed-open`, call `/larch:issue --no-dedup`.
- **Tier A canonical issue env:** after successful `/larch:issue`, persist canonical `ISSUE_URL` and `ISSUE_NUMBER` before writing terminal report env.
- **Tier B repo target:** dedup, comment, and create all target the resolved upstream larch repo.
- **Tier B comment safety:** comments use bounded public slices only, never raw Tier A artifacts.
- **Tier B sensitive-token rejection:** final Tier B comment bodies reuse the existing sensitive-token rejection path.
- **Duplicate search returns broad matches:** require exact marker match in fetched issue body before commenting.
- **Duplicate appears after page 1:** paginated issue-body fetch must still find it.
- **Terminal-failure repo-specific evidence changes:** public report marker remains stable when only paths, branches, run IDs, evidence digests, dispatcher, or matched classifier change.
- **Escalation-success handoffs differ:** public report marker changes when sanitized escalation site or trigger differs.
- **Dedup lookup fails for Tier A:** continue to the existing `/larch:issue --no-dedup` create path.
- **Missing marker during Tier A dedup-only:** continue to the existing `/larch:issue --no-dedup` create path.
- **Comment creation fails after confirmed duplicate:** fall back to manual print instead of creating a duplicate.
- **Tier A duplicate:** comment `+1 occurrence` and skip `/larch:issue`.
- **Tier A no duplicate:** keep `/larch:issue --input-file ... --no-dedup`.
- **Tier A create success:** emit `filed` status and issue URL KVs.
- **Tier B success:** do not print the full report body.
- **Tier B failure:** print the already-sanitized report body.
- **Tier B marker validation:** validate/redact the final body containing the exact marker.
- **Operator-action root cause:** write local sentinel and skip public filing.
- **URL KVs:** use `STALL_RECOVERY_REPORT_URL` for new notices and keep issue URL aliases for issue URLs only.

## Failure modes

- `gh` unauthenticated or offline: helper emits fallback status for Tier B; caller prints report.
- `gh` lookup unavailable during Tier A dedup-only: normalized entrypoint emits fail-open status; caller continues to `/larch:issue --no-dedup`.
- Missing signature marker during Tier A dedup-only: normalized entrypoint emits fail-open status; caller continues to `/larch:issue --no-dedup`.
- Missing signature marker during Tier B filing: helper emits fallback status; caller prints report.
- `gh` lookup unavailable during Tier B filing: helper emits fallback status; caller prints report.
- Comment payload input invalid on confirmed duplicate: helper emits fallback status; caller prints report.
- Tier B comment payload fails bounded-public validation: helper emits fallback status; caller prints report.
- Tier B comment payload fails existing sensitive-token rejection: helper emits fallback status; caller prints report.
- Report body rejected by Tier B sensitive-token validation: composition fails closed; caller preserves tmpdir.
- Upstream resolver fails: Tier B composer emits normalized fallback status and caller prints the sanitized report for manual filing.
- Current repo resolver fails for Tier A dedup: normalized entrypoint emits `lookup-failed-open` and caller continues to `/larch:issue --no-dedup`.
- Tier A `/larch:issue` succeeds but issue env normalization fails: surface the failure and do not claim canonical `ISSUE_URL` or `ISSUE_NUMBER` persistence.

## Testing strategy

Run focused harnesses:

```bash
bash scripts/test-resolve-upstream-larch-repo.sh
bash scripts/test-file-failure-report-cross-repo.sh
bash skills/implement/scripts/test-stall-recovery-report.sh
```

Then run repo-relevant checks:

```bash
bash scripts/relevant-checks.sh
```

## Estimated churn

diff_added: 910
diff_deleted: 110
mechanical_churn: moderate
diff_lines: 1020

## Acceptance

- `scripts/resolve-upstream-larch-repo.sh` parses `.claude-plugin/plugin.json`, normalizes to `OWNER/REPO`, rejects malformed/non-GitHub/path-traversal inputs, exits non-zero on failure.
- `scripts/file-failure-report-cross-repo.sh` extracts `larch-stall:signature` marker, runs paginated `gh api` lookup (skipping pull requests), posts a `+1 occurrence` comment on signature match, creates a new issue on no-match, emits `fallback-print-required` on any failure.
- Tier B `compose-report` resolves upstream repo, calls the cross-repo helper, emits a short filed notice on success, falls back to full chat-print on helper failure.
- Tier A `compose-report` calls the cross-repo helper in `--dedup-only` mode first; on `dedup-comment` skips `/larch:issue`; on `no-match`/`lookup-failed-open` invokes `/larch:issue --input-file --no-dedup`.
- `STALL_RECOVERY_REPORT_STATUS` is the authoritative status variable for prompt/runtime branching; `FILE_FAILURE_REPORT_STATUS` is internal to the cross-repo helper.
- Dry-run mode makes no `gh` calls and emits `STALL_RECOVERY_REPORT_STATUS=dry-run`.
- Tier B comment assembly is validated against the Tier B sensitive-token rejection path before posting.
- `REPORT_DEDUP_SIGNATURE` is seeded only from the canonical fields (report_kind, failure_class, step, phase, safe_bail_token, plus escalation_site/trigger for escalation-success).
- All new harnesses pass (test-resolve-upstream-larch-repo.sh, test-file-failure-report-cross-repo.sh, updated test-stall-recovery-report.sh).
- `bash scripts/relevant-checks.sh` passes with no new failures.
- SECURITY.md updated to document consumer GitHub identity, Tier B content boundary, and filing-failure fallback.

diff_lines: 1020

## Test plan
(no test plan section in plan-file)
