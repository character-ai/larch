### [Plan Review] FINDING_1

### FINDING_1: `prepare` writes ledger only after `gh` snapshot
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `prepare` appends `ledger-pending.tsv` only after the open-issue snapshot. A transient `gh`/API failure aborts before that write and before orchestrator `finalize`+`record`, so deterministic pre-verification drops (0-YES, OOS, near-duplicate, cap-exceeded, security-sensitive, etc.) leave no durable ledger row. The next run repeats log scans and can re-enter up to 100 verifications, breaking idempotency and the acceptance criterion that a second pass files nothing new.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `prepare`, write `ledger-pending.tsv` for all gh-independent drops (0-YES, schema-unsupported, ambiguous round, oos-deferred, ledger-duplicate, near-duplicate, cap-exceeded, security-sensitive) before the open-issue query. On snapshot failure emit `VERIFY_COUNT=0` plus paths and require the SKILL to still run `finalize`+`record` so those rows commit; exit non-zero only after `record`.
  - From Cursor-Innovation: Reorder `prepare`: append `ledger-pending.tsv` for all deterministic pre-verification dispositions (everything except open-issue-overlap) before the open-issue query; run the snapshot only after that durable write, or split append into pre-gh and post-gh phases.
  - From Cursor-Requirements: Write deterministic pre-verification drops to `ledger-pending.tsv` before the open-issue snapshot (or always flush already-computed drop rows on snapshot failure). Keep open-issue-overlap drops after a successful snapshot only.


### [Plan Review] FINDING_2

### FINDING_2: No fail-closed gate when both external reviewers are unavailable
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Unlike peer skills (`/design`, `/review`, `/research`), the workflow never probes reviewer binaries or runs `agent degraded-tools-gate`. `prepare` can emit `VERIFY_COUNT>0` and the orchestrator fires up to 100 doomed `launch-review` calls instead of aborting once with a clear operator message, wasting cost and producing noisy `LAUNCH_FAILURES` without durable per-candidate ledger rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Have `prepare` emit `CODEX_BINARY_FOUND`, `CURSOR_BINARY_FOUND`, and `VERIFY_TOOL`. Before the verification loop, if `VERIFY_COUNT>0` and both binaries are missing, skip launches, print a both-down abort breadcrumb, still run `finalize`+`record` for prepare-owned drops, and exit non-zero (mirror `degraded-both-down-hard-fail` posture).
  - From Cursor-Innovation: In `prepare`, probe `CODEX_BINARY_FOUND` / `CURSOR_BINARY_FOUND` (or reuse session-style probes), emit those KVs, and fail closed with a single operator-visible error when both are false before emitting verification prompts; mirror the degraded-tools posture from `skills/shared/external-reviewers.md`.
  - From Cursor-Requirements: In `prepare`, probe `CODEX_BINARY_FOUND`/`CURSOR_BINARY_FOUND` (or reuse `agent check-reviewers`). When both are false and survivors exist, fail closed before emitting verification prompts (emit `VERIFY_COUNT=0` plus a explicit `BOTH_EXTERNAL_REVIEWERS_DOWN=true` row) rather than scheduling doomed launches.


### [Plan Review] FINDING_3

### FINDING_3: Parsed `REPO_ROOT` not bound to verification launches
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: `prepare` emits `REPO_ROOT` for demotion probes, but step 4 calls `agent launch-review` without `cd` to that root. `launch-review` resolves the repo from orchestrator CWD (`OUTER_LAUNCHER_WORKDIR` / `_resolve_review_codex_workdir`), so a mis-rooted or nested-git session verifies against the wrong tree, dirty-tree baselines diverge, and `bind_verifier_location` can pass on unrelated files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap each verification launch in `cd "<parsed REPO_ROOT>" && python3 ... agent launch-review ...` (or an equivalent wrapper-owned `cd`), and add a harness assertion that SKILL.md mandates using parsed `REPO_ROOT` before every launch.
  - From Cursor-Innovation: Wrap each verification launch in `cd "<parsed REPO_ROOT>" && ... agent launch-review ...`, or extend `launch-review` with an explicit consumer-repo workdir and pass `REPO_ROOT` from `prepare`.
  - From Cursor-Requirements: Wrap each verification launch in `cd "$REPO_ROOT" && ...` (or add a documented `--workdir "$REPO_ROOT"` path if `launch-review` gains one). Unit-test that demotion probes and verification share the same resolved root.


### [Plan Review] FINDING_4

### FINDING_4: In-scope/OOS filter duplicates header-aware routing
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The in-scope/OOS filter reimplements `voting.classification_row_is_oos` without the parsed TSV header. Ad hoc `scope=oos` / `out_of_scope` string checks on dict rows can drift from header-aware routing used elsewhere (e.g. `analyze_issues`), including compact layouts without a `scope` column and `FINDING_N` rows with `scope=oos`, letting deferred OOS rows reach verification despite the v1 exclusion requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the hand-rolled filter with `voting.classification_row_is_oos(row, header=prep.header)` plus an explicit `out_of_scope` drop when the `scope` column exists; unit-test a `FINDING_N` + `scope=oos` fixture.


### [Plan Review] FINDING_5

### FINDING_5: Voter-calibration sidecar schema and dedupe contract unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The issue requires per-finding verify verdicts in a form `/voter-calibration` can consume, but the plan only names `larch-logs/rejected-analysis-verdicts.tsv` and says write/append with no frozen columns, `schema_version`, or dedupe key. Reruns can append duplicate calibration labels and no downstream parser has a stable contract; `/voter-calibration` today reads classification TSVs only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Freeze sidecar columns (`schema_version`, `finding_hash`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `verification_status`, `file_path`, `triaged_at`) and dedupe on `(finding_hash, verification_status)` before append; document the contract in `docs/run-logs.md` and add a unit test for idempotent append.
  - From Cursor-Innovation: Freeze a versioned TSV schema in `python/rejected_analysis.py` (for example `schema_version`, `finding_hash`, `file_path`, `line_hint`, `verdict`, `confirmed_but_rejected`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `triaged_at`) and document the dedupe key (`finding_hash`); add a unit test that a second `record` does not duplicate rows.
  - From Cursor-Pragmatic: Freeze `schema_version`, exact TSV header (e.g. `finding_hash`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `verify_status`, `file_path`, `line_hint`, `triaged_at`), sanitization rules, and dedupe key (`finding_hash` plus `triaged_at` or append-only-once). Document in `docs/run-logs.md` and assert header stability in `python/test_rejected_analysis.py`.
  - From Cursor-Requirements: Freeze a minimal TSV schema (e.g. `schema_version`, `finding_hash`, `verdict`, `file_path`, `line_hint`, `source_skill`, `run_id`, `round_num`, `dissenting_slots`, `triaged_at`) in `python/rejected_analysis.py` and `docs/run-logs.md`; merge-append by `finding_hash` in `record`; add a unit test that a second run does not duplicate sidecar rows.


### [Plan Review] FINDING_9

### FINDING_9: Empty `concern` still participates in hash and near-dedup
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `extract_concern` may return empty but `compute_finding_hash` still hashes `file_path` plus empty `concern`. Multiple distinct rejected findings on the same file with no identifiable concern share one `finding_hash` and `(file_path, concern_hash)` near-dedup key, so one survivor is verified/filed and siblings are ledger-suppressed or skipped on rerun.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `prepare`, after `extract_concern`, drop and ledger `dismissed:unidentifiable-concern` when normalized `concern` is empty (even if `file_path` is set). Unit-test two same-file rows with empty concern do not collapse.


### [Plan Review] FINDING_10

### FINDING_10: Subsystem clustering heuristic is unspecified
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Acceptance requires filed issues to be subsystem-coherent and size-capped, but `finalize` only says cluster by subsystem/file area deterministically with a per-issue cap without defining the grouping rule (directory depth, path-prefix merge/split, anti-bundling across unrelated roots). Tests can assert clustering happens without enforcing coherence, so implementers may bundle unrelated surfaces into one issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Specify one deterministic rule (e.g. group by first two repo-relative path segments, never merge clusters whose top-level directory differs, split any cluster above the cap by lexicographic file order) and add a fixture test that unrelated paths never share a batch index.


