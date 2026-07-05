### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Ndjson duplicate guard still uses the wrong hash contract (FINDING_9 incomplete). Scenario: Step 8 guideline rows are committed by `run_log_flush._render_execution_issues_batch`, which hashes each redacted `- ` chunk with `run_log_batch._normalize_body_for_hash` and stores that as `source_sha256`. The plan hashes only `--note-file` text with a copy of `execution_issues.normalize_body_for_hash` and substring-matches `source_sha256`. That cannot match real rows when Warnings already has other bullets (9694D21F) or when the two normalizers diverge on trailing newlines. The ndjson guard will miss and re-append.
- **Proposed resolution**: Define the md entry text first (bullet lines as flushed). For ndjson, redact with the same `redact` helper, normalize with `run_log_batch._normalize_body_for_hash`, sha256 per `_execution_issue_chunk`, and treat a hit in `$IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson` as `duplicate`. Reuse `structured_body_dedupe_keys` / `_existing_execution_issue_keys` if simpler. Do not compare raw draft-file sha to section-level rows.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Concern**: Md Warnings dedup must split entries the same way flush does. Scenario: The plan says scan `### Warnings` for a matching normalized hash but does not define entry boundaries. `run_log_flush._execution_issue_chunks` splits on top-level `- ` lines. Whole-section or raw-file hashing will not match per-bullet flush rows or miss duplicates when other warnings share the section.
- **Proposed resolution**: Specify that the helper splits the Warnings body with the same chunk rules as `_execution_issue_chunks`, hashes each candidate chunk with the pre-push contract above, and skips append when any chunk hash or dedupe key already exists in md or ndjson.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: RUN_ID and log_root resolution are unspecified. Scenario: The plan says check ndjson when `RUN_ID` is available via env or arg, but the CLI surface lists only `--implement-tmpdir` and `--note-file`. Without reading `LARCH_RUN_ID` from `session-env.sh` / `parent-issue.md` (as `step_7a` does) and resolving log root to `$IMPLEMENT_TMPDIR/larch-logs`, the secondary guard is skipped silently and post-flush Step 8 re-append can still repopulate md.
- **Proposed resolution**: Resolve `run_id` from session artifacts when env is unset; resolve batch path to `implement_tmpdir / "larch-logs" / "implement" / run_id / "execution-issues.ndjson"`; exit 2 only for missing tmpdir, not missing run_id.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:Approach
- **Concern**: Append-only scope does not satisfy acceptance criterion 2 for the documented duplicate mode. Scenario: The issue requires at most one guideline note per run in committed ndjson. 9694D21F shows identical `source_sha256` rows from `pre-push refresh` and `post-transcript refresh` without a second Step 8 append. The helper only blocks re-append after flush; it cannot stop `_render_execution_issues_batch` from writing duplicate rows when the same md is flushed twice.
- **Proposed resolution**: Keep the helper for post-flush re-emission, but add a minimal flush-side fix in `run_log_flush.py` so `_render_execution_issues_batch` does not append rows whose `structured_body_dedupe_keys` are already in the batch, or document that acceptance criterion 2 remains unmet.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14-17
- **Concern**: Dedup hash still does not match committed run-log source_sha256. Scenario: The duplicate committed rows are produced by the pre-push/post-transcript run-log renderer, which hashes redacted bullet chunks with the no-trailing-newline normalizer in python/larch/report/run_log_batch.py:366-374 via python/larch/report/run_log_flush.py:135-137. The plan copies python/larch/issue/execution_issues.py:35-45 and hashes the whole note with a trailing newline, so an existing ndjson row for the same guideline bullet can be missed and the at-most-once criterion remains broken.
- **Proposed resolution**: Make append_deviation_note compute and check the same hash unit the committed renderer writes: split the Warnings note into the same bullet chunks, normalize without adding a trailing newline, and compare those source_sha256 values against the run batch. Update the ndjson duplicate test to seed that committed hash shape.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Dedup hash must follow run_log_flush redact+normalize contract; copying execution_issues.normalize_body_for_hash is incomplete vs accepted FINDING_3. Scenario: Pre-push/post-transcript flush computes source_sha256 from _redact_batch_payload(body) then run_log_batch._normalize_body_for_hash; execution_issues.normalize_body_for_hash also differs on trailing newline. Ndb substring lookup and md hash compare against raw --note-file will miss real duplicates and allow re-append, failing acceptance #2
- **Proposed resolution**: Copy run_log_batch._normalize_body_for_hash byte-for-byte; apply _redact_batch_payload to the formatted Warnings entry before hashing; add test that seeds ndjson via _render_execution_issues_batch and proves append-deviation-note returns duplicate

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Md dedup must chunk Warnings the same way flush does, not hash the draft file in isolation. Scenario: Plan hashes --note-file text directly, but flush emits one ndjson row per _execution_issue_chunks chunk under Warnings; multi-bullet drafts get per-chunk source_sha256. Whole-file hashing mis-dedupes or blocks valid appends
- **Proposed resolution**: Specify the exact markdown entry written under ### Warnings; before insert, walk existing Warnings chunks, redact+normalize each, and compare to the candidate chunk hash(es) using the same chunking rules as run_log_flush

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Ndb path and RUN_ID resolution are underspecified in the helper contract. Scenario: Plan references larch-logs/implement/$RUN_ID/ without anchoring to implement_tmpdir and gives no RUN_ID reader; CLI lists only --implement-tmpdir and --note-file. Secondary guard is skipped whenever RUN_ID is unset, so post-flush re-emission can still duplicate committed rows
- **Proposed resolution**: Resolve RUN_ID from parent-issue.md, session-env.sh, or LARCH_RUN_ID; read implement_tmpdir/larch-logs/implement/RUN_ID/execution-issues.ndjson; cover missing-RUN_ID skip and ndjson-hit duplicate in tests

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-23
- **Concern**: Prior ndjson-dedup fix remains incomplete because the planned Step 8 call has no --run-id and the new CLI options do not define one, yet the plan allows the ndjson guard to skip when RUN_ID is absent.. Scenario: The helper can run with only IMPLEMENT_TMPDIR and --note-file, miss an existing $IMPLEMENT_TMPDIR/larch-logs/implement/<run>/execution-issues.ndjson row, append the same deviation back to execution-issues.md after a refresh, and let a later flush commit the duplicate source_sha256, violating the at-most-once acceptance criterion.
- **Proposed resolution**: Resolve the run id inside the helper from --run-id or from IMPLEMENT_TMPDIR artifacts such as parent-issue.md, session-id, or session-env.sh/LARCH_RUN_ID, and check $IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson before writing; keep skip behavior only when no run id can be recovered.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Ndjson duplicate guard still uses the wrong hash contract versus ship pre-push flush. Scenario: The plan hashes raw --note-file with a copied execution_issues.normalize_body_for_hash and compares that to row source_sha256. Pre-push/post-transcript refreshes in python/larch/report/run_log_flush.py redact each warning chunk, normalize with run_log_batch._normalize_body_for_hash, and dedupe via structured_body_dedupe_keys. After Step 7a clears execution-issues.md or on a Step 8 relaunch, the secondary ndjson check can miss an already-committed guideline row and accept criterion 2 still fails.
- **Proposed resolution**: Build the exact warning entry the helper will write, redact it like run_log_flush, and treat duplicate when its structured_body_dedupe_keys overlap _existing_execution_issue_keys(batch) or existing Warnings bullets; do not compare raw note-file source_sha256 alone.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:append_deviation_note_main
- **Concern**: RUN_ID lookup for the ndjson guard is unspecified. Scenario: The plan says RUN_ID comes from env or arg, but append_deviation_note_main only documents --implement-tmpdir and --note-file. Step 8 prompt-side fences do not export RUN_ID, so the ndjson path will usually be skipped and only md dedup will run.
- **Proposed resolution**: Resolve RUN_ID from $IMPLEMENT_TMPDIR/parent-issue.md with session-id fallback, matching execution_issues.refresh_execution_issues, before reading larch-logs/implement/$RUN_ID/execution-issues.ndjson. ### 1. **correctness** — Ndjson dedup must match flush dedupe keys, not raw note SHA The plan adds an ndjson secondary guard (addressing accepted FINDING_9), but it still compares `sha256(normalize_body_for_hash(note_file))` to `source_sha256` in committed rows. Ship pre-push refresh does not use that contract: `run_log_flush._render_execution_issues_batch` redacts each warning chunk, normalizes with `run_log_batch._normalize_body_for_hash`, and dedupes with `structured_body_dedupe_keys` / `_existing_execution_issue_keys`. After Step 7a clears `execution-issues.md`, a second Step 8 guidelines-assessment can re-append the same deviation. The ndjson guard will not recognize the earlier row, so the note can land in committed `execution-issues.ndjson` twice. Acceptance criterion 2 is not met. **Suggested revision:** After formatting the warning entry for md, compute dedupe keys the same way `run_log_flush` does (redacted bullet chunks + `structured_body_dedupe_keys`). Return `duplicate` when those keys overlap existing ndjson rows or equivalent Warnings bullets in md. Drop the raw note-file `source_sha256` probe. ### 2. **correctness** — Specify RUN_ID resolution from tmpdir sentinels The helper only documents `--implement-tmpdir` and `--note-file`, while the plan says RUN_ID may come from "env or arg" without defining the arg. Step 8 orchestration does not reliably export RUN_ID into the environment. Without reading `$IMPLEMENT_TMPDIR/parent-issue.md` (and `session-id` fallback, as in `execution_issues.refresh_execution_issues`), the ndjson guard will usually be skipped. Dedup then depends only on md text, which is empty after a successful Step 7a flush. **Suggested revision:** Pin RUN_ID resolution to `parent-issue.md` / `session-id` under `--implement-tmpdir`, and document that contract in the helper and tests.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:13-17
- **Concern**: [PRIOR_FIX_INCOMPLETE] The planned ndjson dedup hash copies python/larch/issue/execution_issues.py, but the duplicate committed rows are emitted by run-log refresh, whose hash normalizer in python/larch/report/run_log_batch.py has different trailing-newline semantics.. Scenario: If a guideline warning already exists in execution-issues.ndjson from the refresh path, the helper can compute a different source_sha256, miss the existing row, and re-append the same note, failing the at-most-once committed ndjson criterion.
- **Proposed resolution**: Compute the helper's ndjson dedup hash with the exact normalizer used by the committed execution-issues refresh path, or centralize one shared lower-layer normalizer used by both paths; seed the ndjson duplicate test with that refresh-path hash.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Ndjson secondary dedup must mirror flush body-key contract, not note-file source_sha256 equality. Scenario: Committed rows are deduped in run_log_flush via _redact_batch_payload, run_log_batch._normalize_body_for_hash, and exec_issue_detail.structured_body_dedupe_keys (see test_execution_issues_batch_dedupes_repeated_warning_events). The plan hashes the raw note with a local execution_issues.normalize_body_for_hash copy and substring-matches source_sha256. That misses existing rows whose source_sha256 used redacted bodies or combined Warnings chunks, so a post-flush Step 8 re-entry can re-append and re-commit the same guideline text despite acceptance criterion 2.
- **Proposed resolution**: Before writing, redact the formatted Warnings entry, derive structured_body_dedupe_keys for category Warnings, and treat duplicate when keys are a subset of _existing_execution_issue_keys parsed from $IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson (same contract as run_log_flush.py).

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py
- **Concern**: Md Warnings dedup must be per-entry, not whole-section hash scan. Scenario: The plan says to scan ### Warnings for a matching normalized hash but does not define how to split bullets or format the appended entry. Flush emits one ndjson row per _execution_issue_chunks chunk; a section-level hash diverges whenever other Warnings bullets coexist, so md dedup can miss an identical guideline line already present.
- **Proposed resolution**: Split the formatted Warnings entry with the same chunk rules as run_log_flush._execution_issue_chunks, compute structured_body_dedupe_keys per chunk, and skip append when any chunk key already exists in the Warnings section text or ndjson batch.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Concern**: Specify how the note file becomes a Warnings entry before hashing. Scenario: The helper reads architectural-guideline-assessment-draft.md wholesale; present.md still only says append deviation notes under Warnings without entry shape. Hash and body-key dedup depend on the exact md lines (leading - bullets, prefixes). Format drift between draft, md, and flushed ndjson defeats both dedup guards.
- **Proposed resolution**: Document one entry shape in present.md (e.g. prepend each draft line under ### Warnings as - lines, or wrap once as - **Architectural guidelines**: …) and have append-deviation-note emit that exact text before dedup.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-23
- **Concern**: Ndjson duplicate guard has no reliable run-id or temp log-root source. Scenario: The plan promises a source_sha256 check when RUN_ID is available, but append_deviation_note has no run_id parameter, the CLI options omit --run-id, and the prompt call passes only --implement-tmpdir and --note-file. If RUN_ID is only in ship-pr-state.sh or LARCH_RUN_ID/session env, or if the helper checks repo-root larch-logs instead of $IMPLEMENT_TMPDIR/larch-logs, it skips the ndjson guard and can append a guideline note whose source_sha256 already exists in the run batch.
- **Proposed resolution**: Add --run-id to the helper CLI and prompt call, default it from RUN_ID/LARCH_RUN_ID or ship-pr-state.sh, validate it, and check $IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID/execution-issues.ndjson.
