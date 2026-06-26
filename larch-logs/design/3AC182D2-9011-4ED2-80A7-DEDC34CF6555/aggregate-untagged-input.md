### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:317-336
- **Concern**: `prepare` still appends `ledger-pending.tsv` only after the open-issue snapshot; gh failure aborts before that write and before orchestrator `finalize`+`record`. Scenario: A transient `gh` failure after 0-YES/OOS/cap/near-duplicate work drops every deterministic disposition with no durable ledger row. The next run repeats log scans and can re-enter up to 100 verifications, breaking the acceptance criterion that a second pass files nothing new.
- **Proposed resolution**: In `prepare`, write `ledger-pending.tsv` for all gh-independent drops (0-YES, schema-unsupported, ambiguous round, oos-deferred, ledger-duplicate, near-duplicate, cap-exceeded, security-sensitive) before the open-issue query. On snapshot failure emit `VERIFY_COUNT=0` plus paths and require the SKILL to still run `finalize`+`record` so those rows commit; exit non-zero only after `record`.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/rejected-analysis/SKILL.md:104-129
- **Concern**: No fail-closed gate when both Codex and Cursor are unavailable. Scenario: Unlike `/design`, `/review`, and `/research`, the workflow never probes binaries or runs `agent degraded-tools-gate`. `prepare` can emit `VERIFY_COUNT>0` and the orchestrator fires up to 100 doomed `launch-review` calls instead of aborting once with a clear operator message.
- **Proposed resolution**: Have `prepare` emit `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, and `VERIFY_TOOL`. Before the verification loop, if `VERIFY_COUNT>0` and both binaries are missing, skip launches, print a both-down abort breadcrumb, still run `finalize`+`record` for prepare-owned drops, and exit non-zero (mirror `degraded-both-down-hard-fail` posture).

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/rejected-analysis/SKILL.md:108-118
- **Concern**: Parsed `REPO_ROOT` is never bound to verification launches. Scenario: `prepare` emits `REPO_ROOT` for `git log` demotion, but step 4 calls `agent launch-review` without `cd` to that root. `launch-review` resolves the repo from orchestrator CWD (`OUTER_LAUNCHER_WORKDIR` in `python/agents.py`), so a mis-rooted session verifies against the wrong tree, dirty-tree baselines diverge, and `bind_verifier_location` can still pass on unrelated files.
- **Proposed resolution**: Wrap each verification launch in `cd "<parsed REPO_ROOT>" && python3 ... agent launch-review ...` (or an equivalent wrapper-owned `cd`), and add a harness assertion that SKILL.md mandates using parsed `REPO_ROOT` before every launch.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/rejected_analysis.py:262-267
- **Concern**: In-scope/OOS filter reimplements `voting.classification_row_is_oos` without the parsed TSV header. Scenario: `analyze_issues` routes OOS rows through `voting.classification_row_is_oos(raw, header=prep.header)` (`python/analyze_issues.py:2523`). The plan uses ad hoc `scope=oos` / `out_of_scope` string checks on dict rows. That can drift from header-aware routing (compact layouts without a `scope` column, `FINDING_N` rows with `scope=oos`) and let deferred OOS rows reach verification despite the v1 exclusion requirement.
- **Proposed resolution**: Replace the hand-rolled filter with `voting.classification_row_is_oos(row, header=prep.header)` plus an explicit `out_of_scope` drop when the `scope` column exists; unit-test a `FINDING_N` + `scope=oos` fixture.

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/rejected_analysis.py:384-385
- **Concern**: Voter-calibration sidecar schema is unspecified. Scenario: The issue requires verdicts in a form `/voter-calibration` can consume. The plan only says write/append `larch-logs/rejected-analysis-verdicts.tsv` rows with no frozen columns or dedupe key, so reruns can append duplicate calibration labels and no downstream parser has a stable contract.
- **Proposed resolution**: Freeze sidecar columns (`schema_version`, `finding_hash`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `verification_status`, `file_path`, `triaged_at`) and dedupe on `(finding_hash, verification_status)` before append; document the contract in `docs/run-logs.md` and add a unit test for idempotent append. ### 1. `prepare` ledger ordering on gh failure (correctness) The plan still sequences open-issue snapshot before the single `ledger-pending.tsv` append (`plan.txt:329-334`). A failed snapshot aborts `prepare` with no durable rows and no orchestrator path to `record`, so deterministic drops repeat on rerun. Split gh-independent ledger writes before the snapshot and keep `finalize`+`record` on that path. ### 2. Both-down external reviewer gate (risk-integration) Step 4 launches verifiers with no session probe or `degraded-tools-gate` (`plan.txt:104-129`). Peer skills gate at Step 0. When both binaries are missing, the skill should fail closed before the verification loop, not after up to 100 fast launcher failures. ### 3. `REPO_ROOT` not bound to launches (correctness) `REPO_ROOT` is parsed from `prepare` but never used to root `launch-review`. Launcher dirty-tree and file reads use orchestrator CWD. Require `cd` to parsed `REPO_ROOT` before each verification fence. ### 4. OOS filter should reuse `classification_row_is_oos` (architecture) The proposed filter at `plan.txt:262-267` duplicates logic that `analyze_issues` already centralizes with header awareness. Call `voting.classification_row_is_oos` with the prep header to avoid drift on committed classification TSV layouts. ### 5. Voter-calibration sidecar needs a frozen schema (completeness) Issue scope requires consumable verdict labels for `/voter-calibration`. The plan emits a sidecar without column contract or dedupe rules. Freeze schema and idempotent append semantics before claiming the sibling-skill integration goal.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py
- **Concern**: extractors miss the repo's common markdown-bulleted Location and Concern forms. Scenario: The current code-review prose uses `- **Location**:` and `- **Concern**:` bullets, and some locations are directory-only or bare repo paths, as shown in `python/test_plan_review.py:1378-1398`, `python/test_plan_review.py:2325-2333`, and `python/test_redact.py:324-340`; without normalizing those shapes, `file_path` or `concern` will go empty or carry markdown, collapsing unrelated findings under one hash.
- **Proposed resolution**: Strip the bullet and bold prefix before matching `Location` and `Concern`, and accept plain repo-relative paths without a `:line` suffix

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rejected_analysis.py
- **Concern**: path selection depends on mutable repo_root existence. Scenario: extract_target_path prefers the first normalized path that exists under `repo_root`, so the same finding can hash differently after an unrelated merge creates or removes one of the candidate paths; that defeats the ledger backstop and allows duplicates on rerun.
- **Proposed resolution**: Choose the hash path from stable text order or a frozen TSV field only, and reserve repo-root existence checks for stale/verifier binding, not for the hash key

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/rejected-analysis/SKILL.md:105-334
- **Concern**: `prepare` still writes `ledger-pending.tsv` only after the open-issue snapshot. Scenario: `prepare` applies 0-YES, OOS, near-duplicate, cap, and security drops, then calls `gh` at line 330 and fail-closes on snapshot failure before the line 334 `ledger-pending` append. A transient `gh`/API outage aborts with no durable rows for those deterministic drops. The next run repeats log scans, can re-verify near-duplicate siblings and cap-exceeded candidates, and weakens the acceptance criterion that incremental reruns do not redo expensive work.
- **Proposed resolution**: Reorder `prepare`: append `ledger-pending.tsv` for all deterministic pre-verification dispositions (everything except open-issue-overlap) before the open-issue query; run the snapshot only after that durable write, or split append into pre-gh and post-gh phases.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/rejected-analysis/SKILL.md:108-129
- **Concern**: No fail-closed gate when both Codex and Cursor are unavailable. Scenario: Unlike `/design` and `/implement`, the plan never probes reviewer binaries or calls `agent degraded-tools-gate`. `prepare` can still emit `VERIFY_COUNT>0`, and the orchestrator fires up to 100 `launch-review` calls that fail immediately, then exits with `LAUNCH_FAILURES>0` and no per-candidate ledger rows. That violates the issue's cost-discipline requirement and produces a noisy failure instead of one clear abort.
- **Proposed resolution**: In `prepare`, probe `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` (or reuse session-style probes), emit those KVs, and fail closed with a single operator-visible error when both are false before emitting verification prompts; mirror the degraded-tools posture from `skills/shared/external-reviewers.md`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/rejected-analysis/SKILL.md:108-118
- **Concern**: Verification launches do not bind `REPO_ROOT` to the reviewer workspace. Scenario: `prepare` emits `REPO_ROOT`, but the verification Bash fence calls `agent launch-review` without `cd "$REPO_ROOT"` and `launch-review` has no `--workdir` flag; it resolves the tree from orchestrator CWD / `CLAUDE_PROJECT_DIR` via `_resolve_review_codex_workdir`. In nested-git or mis-rooted sessions, verifiers read the wrong tree, return `confirmed`/`stale` against unrelated code, and auto-filing creates incorrect issues; `${OUTPUT}.dirty-tree` may also compare the wrong baseline.
- **Proposed resolution**: Wrap each verification launch in `cd "<parsed REPO_ROOT>" && ... agent launch-review ...`, or extend `launch-review` with an explicit consumer-repo workdir and pass `REPO_ROOT` from `prepare`.

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:384-385
- **Concern**: Voter-calibration sidecar schema is unspecified despite issue requirement. Scenario: The issue requires verdicts in a form `/voter-calibration` can consume. The plan only says `record` will write/append voter-verdict sidecar rows and names `larch-logs/rejected-analysis-verdicts.tsv`, but never freezes column order, required fields, or dedupe key. `/voter-calibration` today reads classification TSVs only; without a frozen contract, second runs can append duplicate labels and the sibling skill cannot parse the feed.
- **Proposed resolution**: Freeze a versioned TSV schema in `python/rejected_analysis.py` (for example `schema_version`, `finding_hash`, `file_path`, `line_hint`, `verdict`, `confirmed_but_rejected`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `triaged_at`) and document the dedupe key (`finding_hash`); add a unit test that a second `record` does not duplicate rows.

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:42-55
- **Concern**: Extractor misses the bulletized Concern/Location forms used by current logs. Scenario: Current code-review logs use `- **Concern**:` and `- **Location**:` bullets. The planned extractor would return empty concern/path for those rows, so distinct findings collapse onto the same hash and reruns can suppress or re-file the wrong item.
- **Proposed resolution**: Teach the extractor to parse the bulletized `- **Concern**:` and `- **Location**:` / `- **File**:` shapes already present in committed logs, or reuse the same parser that normalizes existing review artifacts before hashing.

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:57-59
- **Concern**: Path tie-break depends on whether a candidate path exists in the current checkout. Scenario: A later merge that adds or deletes one of several candidate paths changes which path exists under `repo_root`, so the same finding hashes differently on a rerun and the ledger backstop stops matching.
- **Proposed resolution**: Make path selection depend only on a stable textual rule, or persist the chosen file path from prepare; do not consult live file existence when computing the hash key.

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: plan.txt:337-350
- **Concern**: Launch-failed and parse-failed verdicts are not durably staged for finalize. Scenario: A transient launcher outage, parse failure, or location mismatch leaves no durable per-candidate status. Finalize cannot tell a retryable failure from a successful launch that never ingested, so it will misledger or strand candidates.
- **Proposed resolution**: Persist a status row for every candidate on every ingest outcome, not just dirty-tree and confirmed verdicts, and have finalize read that durable status file instead of inferring missing rows as verification-failed.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:42-72
- **Concern**: `extract_concern` may return empty but `compute_finding_hash` still hashes `file_path` plus empty `concern`. Scenario: Multiple distinct rejected findings on the same file with no `### FINDING_N:` title and no `what:`/`Concern:` line share one `finding_hash` and `(file_path, concern_hash)` near-dedup key. One survivor is verified/filed; siblings are ledger-suppressed or skipped on rerun, so real defects can be dropped or mis-attributed.
- **Proposed resolution**: In `prepare`, after `extract_concern`, drop and ledger `dismissed:unidentifiable-concern` when normalized `concern` is empty (even if `file_path` is set). Unit-test two same-file rows with empty concern do not collapse.

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/rejected_analysis.py:219-221
- **Concern**: Issue requires verdict sidecar rows `/voter-calibration` can consume, but the plan only names `VERDICT_SIDECAR` and says "write/append" without a frozen column schema or dedupe key. Scenario: `record` can append incompatible rows across runs; `/voter-calibration` today reads classification TSVs only, so the promised false-negative feed has no parse contract or consumer hook. The integration goal in the issue is only partially delivered.
- **Proposed resolution**: Freeze `schema_version`, exact TSV header (e.g. `finding_hash`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `verify_status`, `file_path`, `line_hint`, `triaged_at`), sanitization rules, and dedupe key (`finding_hash` plus `triaged_at` or append-only-once). Document in `docs/run-logs.md` and assert header stability in `python/test_rejected_analysis.py`.

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:225-230
- **Concern**: extract_target_path depends on current repo existence before hashing. Scenario: The same finding mentions two repo paths. If one exists on run A and the other exists on run B after a rename or later merge, the chosen file_path and finding_hash can change, so reruns bypass the ledger and re-file the same defect.
- **Proposed resolution**: Make path selection stable from the finding text alone. Use repo existence only after hashing, for stale or verification decisions.

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:337-350
- **Concern**: launch-failed verdicts have no durable per-candidate status, so finalize cannot keep them retryable. Scenario: A launcher exits non-zero for one candidate while others succeed. The plan records only aggregate LAUNCH_FAILURES and appends no launch-failed stub, so finalize will treat the missing ingest row like verification-failed and permanently ledger a retryable failure.
- **Proposed resolution**: Persist a per-candidate launch-failed status row or sidecar, and have finalize and record exclude those hashes from the missing-ingest fallback.

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:329-335
- **Concern**: `prepare` writes `ledger-pending.tsv` only after the open-issue snapshot, which fail-closes on `gh`/API errors. Scenario: The `prepare` verb orders work as: read ledger, query open issues with fail-closed abort, then append `ledger-pending.tsv` for all deterministic pre-verification drops (0-YES, OOS-deferred, cap-exceeded, near-duplicate, security-sensitive, etc.). A transient `gh` failure after cheap filtering but before that append exits with no durable rows. The next rerun repeats log scans and can re-enter up to 100 verifications, violating the acceptance criterion that a second window pass files nothing new and weakening cost discipline.
- **Proposed resolution**: Write deterministic pre-verification drops to `ledger-pending.tsv` before the open-issue snapshot (or always flush already-computed drop rows on snapshot failure). Keep open-issue-overlap drops after a successful snapshot only.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/rejected-analysis/SKILL.md:108-118
- **Concern**: No fail-closed gate when both Codex and Cursor binaries are unavailable. Scenario: Unlike `/design`, `/review`, and `/research`, the skill has no session probe or `agent degraded-tools-gate`. `prepare` can still emit `VERIFY_COUNT>0` and the orchestrator fires up to 100 doomed `agent launch-review` calls that fail fast, leaving candidates unledgered and the run exiting with `LAUNCH_FAILURES>0` instead of aborting once with a clear operator message.
- **Proposed resolution**: In `prepare`, probe `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` (or reuse `agent check-reviewers`). When both are false and survivors exist, fail closed before emitting verification prompts (emit `VERIFY_COUNT=0` plus a explicit `BOTH_EXTERNAL_REVIEWERS_DOWN=true` row) rather than scheduling doomed launches.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/rejected-analysis/SKILL.md:108-118
- **Concern**: Verification launches do not bind `REPO_ROOT` to `agent launch-review` workdir. Scenario: `prepare` emits `REPO_ROOT` for `git log` demotion probes, but the verification Bash fence calls `agent launch-review` without `cd "$REPO_ROOT"` (or equivalent). `launch-review` resolves the repo via orchestrator CWD / `_resolve_review_codex_workdir(Path.cwd())`, which can diverge from `REPO_ROOT` in nested-git or mis-rooted sessions. Agents read the wrong tree, `bind_verifier_location` can still pass on coincidental path strings, and `${OUTPUT}.dirty-tree` compares the wrong baseline.
- **Proposed resolution**: Wrap each verification launch in `cd "$REPO_ROOT" && ...` (or add a documented `--workdir "$REPO_ROOT"` path if `launch-review` gains one). Unit-test that demotion probes and verification share the same resolved root.

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:384-385
- **Concern**: Voter-calibration sidecar schema and dedupe key are unspecified. Scenario: Issue scope requires emitting per-finding verify verdicts in a form `/voter-calibration` can consume. The plan only says `record` will write/append `larch-logs/rejected-analysis-verdicts.tsv` with sanitized cells; it never freezes columns, `schema_version`, or a dedupe key. Append-without-merge can duplicate rows across reruns, and `/voter-calibration` has no parse contract today.
- **Proposed resolution**: Freeze a minimal TSV schema (e.g. `schema_version`, `finding_hash`, `verdict`, `file_path`, `line_hint`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `triaged_at`) in `python/rejected_analysis.py` and `docs/run-logs.md`; merge-append by `finding_hash` in `record`; add a unit test that a second run does not duplicate sidecar rows.

### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rejected_analysis.py:359-360
- **Concern**: Clustering heuristic for subsystem-coherent issues is unspecified. Scenario: Acceptance requires filed issues to be subsystem-coherent and size-capped. `finalize` only says cluster by subsystem/file area deterministically with a per-issue cap (e.g. 5) but does not define the grouping rule (directory depth, path-prefix merge/split, or anti-bundling across unrelated roots). Tests only assert that clustering happens, not coherence, so implementers can bundle unrelated surfaces into one issue.
- **Proposed resolution**: Specify one deterministic rule (e.g. group by first two repo-relative path segments, never merge clusters whose top-level directory differs, split any cluster above the cap by lexicographic file order) and add a fixture test that unrelated paths never share a batch index.
