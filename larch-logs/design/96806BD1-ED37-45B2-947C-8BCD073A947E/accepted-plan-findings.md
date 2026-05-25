### FINDING_1: Zero-judge `voting_result` vs `classify_result` / plan wording mismatch
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan ties per-row `voting_result` to main-agent / tally semantics while `classify_result` with `eligible_count<=0` yields `rejected`, so analytics can mislabel pending main-agent work, implementers may emit the wrong literal (e.g. `main-agent-vote-required` vs tally output), or conflate `voting_result` with `TALLY_PLAN_REVIEW_STATUS` instead of the tally cell schema.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define an explicit voting_result string for the 0-judge path (e.g. main-agent-vote-required or pending) and add a harness assertion; do not infer from classify_result(…, eligible=0) without documenting that semantic break from rejected
  - From Cursor-Arch: Choose an explicit voting_result string for the 0-judge path (distinct from normal rejected), document it in acceptance plus harness; do not claim current tally already emits those rows
  - From Cursor-Edge: State explicitly use classify_result 0 0 0 0 yielding rejected as the voting_result cell for zero-judge rows
  - From Cursor-Pragmatic: State explicitly that `voting_result` must equal `classify_result` output (zero votes, same `eligible_count`) not the `TALLY_PLAN_REVIEW_STATUS` string.
  - From Cursor-Requirements: Specify the exact voting_result string per row for main-agent-required rounds (e.g. empty reserved rejected literal or TALLY status mirror) and if using classify_result document that it yields rejected not main-agent-required

---


### FINDING_10: Parser axis-value casing contract contradicts lowercase stdout schema
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Cursor-Requirements
- **Severity**: latent
- **Concern**: Case-insensitive matching combined with “verbatim” / case-preserved wording conflicts with a lowercase-only emitted enum schema, allowing inputs like `SEVERITY=MAJOR` or `UNCERTAIN=FALSE` to go off-schema or behave inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Choose one contract: either require lowercase and treat other case as unrecognized, or accept case-insensitively and normalize every emitted PARSED_* value to the canonical lowercase enum
  - From Codex-Edge: Normalize every accepted axis value to the canonical lowercase enum before emit_kv, including UNCERTAIN true/false. Add parser fixtures for uppercase and mixed-case values.
  - From Codex-Pragmatic: Normalize axis values to lowercase after case-insensitive validation and document that emitted PARSED_* values always use the schema enums
  - From Cursor-Requirements: Choose one normative rule for axis value equality and mirror it in parse-judge-vote-and-rating.md and tests

---


### FINDING_11: Ballot block iteration order depends on shell glob ordering
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: Unsorted glob iteration can make TSV row order filesystem-dependent, breaking stable diffs across CI hosts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Sort block ids (FINDING then OOS numeric) before emitting classification rows

---


### FINDING_12: `design-log-publish` plan-review staging: symlink safety, allowlist vs `render-cache`, enumeration, empty-tree semantics, and path canonicalization
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Cursor-dyn-publish-allowlist-safety, Codex-dyn-publish-allowlist-safety
- **Severity**: important
- **Concern**: Plan text may falsely equate plan-review staging to render-cache strictness; symlinked roots/files, prefix stripping, absolute-vs-relative matching, and “reject unexpected files” may be underspecified; empty `plan-review/` or missing rounds must not accidentally fail publish; `find` wording can be ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror render-cache checks reject symlinks for DESIGN_TMPDIR/plan-review before enumerating
  - From Codex-Edge: Mirror the render-cache hardening: reject plan-review if it is a symlink or not a directory, resolve a physical root, require regular non-symlink files, verify each staged path remains under the resolved root, and add publish harness cases for symlink root and symlink allowed file
  - From Cursor-Pragmatic: Spell out enumerate-and-validate steps (e.g. `find` under `plan-review` then require each file path match `plan-review/round-[0-9]+/findings-classification\\.tsv$` else `larch_err` + fail publish).
  - From Cursor-dyn-publish-allowlist-safety: Describe render-cache as full-tree staging with escape guard, and specify plan-review as the new strict allowlist (enumerate allowlisted paths plus explicit reject pass), or drop the equivalence claim
  - From Cursor-dyn-publish-allowlist-safety: Spell out a second `find` (or walk) under a resolved `plan-review` root and require every file path match `^plan-review/round-[0-9]+/findings-classification\\.tsv$` after relativization (or equivalent), else `larch_err` + `emit_publish_result false`
  - From Cursor-dyn-publish-allowlist-safety: State explicitly: empty `plan-review/`, no `round-*` dirs, or zero `findings-classification.tsv` matches is success (no `larch_err`); reserve errors for symlink wrong-type, path escape, or disallowed files present
  - From Cursor-dyn-publish-allowlist-safety: Mirror the render-cache block: resolve `plan_root=$(cd "$DESIGN_TMPDIR/plan-review" && pwd -P)`, reject symlink/wrong-type like lines 279-287, enumerate from `pr_root`, strip `${pr_root#/}` → `plan-review/...` or strip design tmpdir prefix consistently, validate each path stays under `pr_root` before `design_publish_stage_file "$f" "$RUN_DEST/$rel"`
  - From Cursor-dyn-publish-allowlist-safety: Replace glob wording with a normative `find` predicate (e.g. `-path` segments) and note `*` does not cross `/` in GNU find
  - From Codex-dyn-publish-allowlist-safety: Spell out the exact loop: resolve pr_root, find all regular files under it, derive rel relative to pr_root, allow only rel matching round-<positive-int>/findings-classification.tsv, stage to $RUN_DEST/plan-review/$rel, and larch_err plus emit_publish_result false for every other regular file
  - From Codex-dyn-publish-allowlist-safety: Add a test-design-log-publish.sh case that creates an empty plan-review directory, and preferably an empty plan-review/round-1 directory, then asserts publish succeeds and stages no plan-review files while still rejecting a later unexpected regular file

---


### FINDING_13: Duplicate ID lines: last match wins; new parser must stay consistent with `vote_for_id`
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Pragmatic
- **Severity**: latent
- **Concern**: `vote_for_id`-style scanning can make the last recognized matching line authoritative; if the new parser differs (first wins vs last wins), `v*_vote` can disagree with `voting_result` / classification rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document last-wins in parse-judge-vote-and-rating.md and assert in harness fixtures
  - From Codex-Edge: Specify and implement exact vote_for_id duplicate semantics in parse-judge-vote-and-rating.sh, preferably by updating parsed values on every matching anchored line. Add a fixture with duplicate FINDING_N lines.
  - From Cursor-Pragmatic: Document and test last-line-wins parity for repeated IDs in one voter file.

---


### FINDING_14: `reviewer_slots` semantics conflict: ballot attribution vs missing voter / harness expectations
- **Reviewer(s)**: Codex-Edge, Codex-dyn-schema-wire-consistency
- **Severity**: important
- **Concern**: The column may be interpreted as ballot proposer attribution, missing-slot signaling, or judge-panel slots, corrupting analytics without parse failure when panels are degraded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Split the concepts or rename the column before implementation. For example use finding_reviewers for reviewer_for_block output and separate voter slot columns/statuses if missing judges must be represented.
  - From Codex-dyn-schema-wire-consistency: Revise the plan/harness so reviewer_slots is derived from reviewer_for_block and remains stable regardless of missing voters; missing judges should only produce empty vN_* cells.

---


### FINDING_15: Skipped-tally / zero-findings paths omit per-round `findings-classification.tsv`
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: Early exits after `write_empty_review_artifacts` (or similar) can skip tally while Decision 2 / publish / acceptance expect a per-round `plan-review/round-N/findings-classification.tsv` (at least header-only) for uniformity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Header-only TSV write on those exits mkdir -p DESIGN_TMPDIR/plan-review/round-$ROUND_NUM and emit the 18-column header line or invoke tally-plan-review.sh with the empty ballot plus --findings-classification-out
  - From Codex-Innovation: Have write_empty_review_artifacts create plan-review/round-$ROUND_NUM/findings-classification.tsv with the 18-column header, or route the empty ballot through tally; update the SKILL.md skip-voting note and add a plan-review-loop harness case
  - From Cursor-Requirements: Either mkdir and write the header-only TSV alongside write_empty_review_artifacts before emit_loop_kvs or invoke tally-plan-review.sh on the empty ballot with new --findings-classification-out; extend test-plan-review-loop expectations accordingly
  - From Codex-Requirements: Update the zero-finding branch to create DESIGN_TMPDIR/plan-review/round-$ROUND_NUM and write the header-only TSV or invoke tally-plan-review.sh on the empty ballot with --findings-classification-out; add a plan-review-loop harness assertion for that artifact

---


### FINDING_16: Degraded panels must not compact voter paths into wrong `v1`/`v2`/`v3` columns
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Sorting “available files” sequentially can shift tools left when a middle slot is missing (e.g. Codex absent but Cursor present lands in `v2` instead of `v3`), violating fixed-slot analytics conventions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make row assembly a fixed basename/tool map: claude->v1, codex->v2, cursor->v3, never compacting slots; add a harness for Codex missing with Cursor present
  - From Codex-Requirements: Map each parsed voter file to a fixed canonical slot by tool name or nominal filename, leave absent slots empty, and add a Codex-missing test case in addition to the Cursor-missing case

---


### FINDING_17: Parser soft-failure / exit-0 matrix incomplete for ID-matched lines with unrecognized vote tokens (and acceptance text gaps)
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-parser-exit-contract, Codex-dyn-parser-exit-contract
- **Severity**: important
- **Concern**: Contract bullets emphasize recognized votes or missing ID lines but omit the “ID matched, vote token unrecognized” case, risking non-zero exits under `set -euo pipefail` and tally abort vs `JUDGE_ERROR`-aligned empty `PARSED_VOTE` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document whether malformed lines yield empty PARSED_VOTE with exit 0 or a hard failure and add a harness case matching that contract
  - From Cursor-dyn-parser-exit-contract: Add an explicit (a)-(d) matrix to the parser contract and planned scripts/parse-judge-vote-and-rating.md: (d) exit 0 with empty PARSED_VOTE aligned to vote_for_id JUDGE_ERROR; tighten the PARSED_VOTE sentence to mean no recognized vote token for that id not merely missing line
  - From Cursor-dyn-parser-exit-contract: Mention case (d) explicitly in Acceptance next to exit 0 wording
  - From Codex-dyn-parser-exit-contract: Add an explicit four-case table to scripts/parse-judge-vote-and-rating.sh and .md plus harness coverage: missing args/unreadable nonzero with no PARSED_VOTE contract; no ID match exit 0 PARSED_VOTE empty; recognized token exit 0 PARSED_VOTE token; ID match with unrecognized token exit 0 PARSED_VOTE empty

---


### FINDING_18: Harness case 4 does not pin `UNCERTAIN=false` with another axis omitted (partial-row / uncertain propagation)
- **Reviewer(s)**: Cursor-dyn-parser-exit-contract, Codex-dyn-parser-exit-contract
- **Severity**: important
- **Concern**: The plan/harness text can allow an implementation that keys `PARSED_UNCERTAIN` off the `UNCERTAIN` token alone, contradicting the intended “false token + omitted axis still forces uncertain” edge behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-parser-exit-contract: Extend case 4 with an explicit fixture line shape (e.g. FINDING_2: YES ... UNCERTAIN=false with QUALITY omitted) and assert vN_uncertain true and vN_quality empty
  - From Codex-dyn-parser-exit-contract: Add a fixture such as FINDING_2: YES CORRECTNESS=true SEVERITY=major UNCERTAIN=false and assert PARSED_QUALITY empty, PARSED_UNCERTAIN=true, and TSV vN_uncertain=true

---


### FINDING_2: Retry-prefix edit sites mis-anchored (plan vs `VOTER_PARSE_RATE_RETRY_PREFIX_*` globals)
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan points implementers at the wrong region (e.g. near the `LARCH_VPR_RETRY_PREFIX_KIND` branch ~186) while the literal retry strings live in top-of-file `VOTER_PARSE_RATE_RETRY_PREFIX_PLAN` / `VOTER_PARSE_RATE_RETRY_PREFIX_CODE`, risking missed updates and review drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Revise the plan to name the top-of-file prefix constants (lines 10-12) as the single source of truth for retry wording updates
  - From Cursor-Arch: Name the prefix constants at scripts/lib-voter-parse-rate.sh:10-12 as the required edit sites in the plan
  - From Cursor-Innovation: Point the plan and tasks at scripts/lib-voter-parse-rate.sh:10-12 for the prefix literals plus a note that make_voter_retry_prompt_file only selects among them
  - From Cursor-Pragmatic: Cite lines 10-12 (or variable names) as the edit site for plan/code retry strings.

---


### FINDING_20: `tally-plan-review.sh` usage text omits new `--findings-classification-out` flag
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Concern**: Direct operators miss the new optional argument and default path behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend usage() output alongside the new case branch in getopts parsing

---


### FINDING_3: Default nested `findings-classification.tsv` path may lack parent directories
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `tally-plan-review.sh` may only `mkdir -p` `$DESIGN_TMPDIR` while the default nested output `plan-review/round-1/findings-classification.tsv` needs parent dirs; direct tally or harness runs without `plan-review-loop` pre-creating dirs can fail under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify mkdir -p on the parent of the default output path inside tally before redirect (mirror plan-review-loop mkdir for explicit --out)
  - From Cursor-Arch: Require mkdir -p for the default output directory inside tally-plan-review.sh before writing the TSV
  - From Cursor-Edge: Require mkdir -p dirname of final TSV inside tally-plan-review.sh (not only plan-review-loop.sh)
  - From Cursor-Pragmatic: Add `mkdir -p` for the default output dirname inside `tally-plan-review.sh` (and keep loop-side `mkdir -p` for explicit `--findings-classification-out`).

---


### FINDING_5: Unescaped or unsanitized judge-supplied axis / vote text in TSV cells
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: Tabs or newlines (and broadly voter-sourced tokens) in axis names/values or other fields can break TSV columns, inject extra logical rows for naive consumers, or corrupt committed logs; some plan text only called out `reviewer_slots` while other voter-derived columns remain underspecified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan to require tab/newline stripping or replacement in all TSV cells sourced from voter files (axes and votes) before write, with a harness case if feasible
  - From Cursor-Arch: Specify tab newline normalization for all voter-sourced TSV fields and add a harness case where practical
  - From Cursor-Edge: Strip or replace tabs and newlines in each parsed axis value before TSV write same as reviewer_slots rule
  - From Cursor-Requirements: Define normalization or rejection rules for all vN_* cells sourced from voter files before writing TSV rows

---


### FINDING_7: Section header says three additive changes but lists four items
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-parser-exit-contract
- **Severity**: nit
- **Concern**: Heading/checklist mismatch causes readers to mis-estimate scope and reviewers to miss a required delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rename the heading to four changes or merge items for accurate checklist parity

---


### FINDING_8: Strict `*-vote-output.txt` inference vs waterfall phases, retries, stubs, and `voter-main-agent.txt`
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-schema-wire-consistency, Codex-dyn-schema-wire-consistency
- **Severity**: important
- **Concern**: Deriving tool/slot identity only from `*-vote-output.txt` basenames conflicts with phase2/phase3 outputs, retry filenames, fallback paths where basename does not match the actual tool, `voter-main-agent.txt`, and harness/stub names (`vstub*.txt`, `v1.txt`, etc.), causing hard errors, wrong-column placement, or silent mis-attribution in degraded panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Normalize known phase suffixes before deriving the slot, or pass explicit voter slot metadata into tally-plan-review.sh; define the main-agent voter mapping explicitly, and add harness cases for phase2/phase3 paths plus voter-main-agent.txt
  - From Codex-Edge: Do not infer voter identity solely from basename. Carry tool and slot metadata from dispatch-plan-voters into tally, or redefine v1/v2/v3 as fixed voter slots with explicit tool/status metadata. Add tests for phase2, phase3, and retry output paths.
  - From Codex-Pragmatic: Pass slot/tool metadata to tally or normalize phase/retry suffixes and map by fixed voter slot; add a fallback-path harness case
  - From Cursor-Innovation: Rename stub and harness voter fixtures to claude-vote-output.txt codex-vote-output.txt cursor-vote-output.txt or document a deliberate escape hatch for non-production callers
  - From Codex-Innovation: Define a synthetic main-agent handling path before making filename validation strict, or change the fallback rerun to pass a supported slot/tool mapping; add a harness for the rerun after TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
  - From Cursor-Pragmatic: Exempt `voter-main-agent.txt` (define vN mapping), relax strictness for non-panel files, or explicitly list SKILL + all tally harnesses to rename to `claude-vote-output.txt`/`codex-vote-output.txt`/`cursor-vote-output.txt` and update SKILL instructions.
  - From Cursor-dyn-schema-wire-consistency: Append a dedicated harness case (and expected stderr or exit contract) alongside the nine cases already listed
  - From Cursor-dyn-schema-wire-consistency: Extend the UPDATED `test-tally-plan-review.sh` bullet to rename all voter fixtures to the canonical `*-vote-output.txt` basenames (or document an explicit exception path for tests)
  - From Cursor-dyn-schema-wire-consistency: Update the stub `dispatch-plan-voters.sh` heredoc to write `claude-vote-output.txt` / `codex-vote-output.txt` / `cursor-vote-output.txt` (or document overriding `LARCH_PLAN_REVIEW_TALLY_SH` with a stub whenever filenames are non-canonical)
  - From Codex-dyn-schema-wire-consistency: Map v1/v2/v3 by voter slot identity, not only exact basename. Accept canonical slot prefixes with optional -phase2/-phase3 suffixes, or pass slot metadata alongside paths. Add harness fixtures for phase2/phase3 paths and for a truly malformed filename that must error.
  - From Codex-dyn-schema-wire-consistency: Pass voter tool metadata or the plan-voter slot manifest into tally, or define vN as slot identity instead of actual tool; add fallback phase2 and phase3 fixtures

---


### FINDING_9: `script-md-siblings` contract updates missing or incomplete for touched scripts and contracts
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Cursor-Pragmatic, Cursor-Innovation, Cursor-Requirements, Codex-dyn-publish-allowlist-safety
- **Severity**: important
- **Concern**: The plan changes multiple shell primaries and workflows but omits or understates required sibling `.md` updates (and related docs like `SKILL.md` / loop contract docs), risking stale CLI/artifact/prompt/publish contracts and doc-lint drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add UPDATED entries and concrete edits for the affected sibling .md files, including new argv, TSV artifact paths/schema, publish allowlist behavior, prompt line shape, retry prefix line shape, and harness coverage
  - From Codex-Pragmatic: Omitting updates drifts authoritative contracts and can fail doc lint expectations; add `tally-plan-review.md`, `render-voter-prompt.md`, `lib-voter-parse-rate.md`, `design-log-publish.md` to the change list.
  - From Codex-Requirements: Add tally-plan-review.md and skills/design/SKILL.md to Files to modify with concrete sections to refresh for the new TSV path and voter line shape
  - From Cursor-Pragmatic: Omitting updates drifts authoritative contracts and can fail doc lint expectations; add `tally-plan-review.md`, `render-voter-prompt.md`, `lib-voter-parse-rate.md`, `design-log-publish.md` to the change list.
  - From Cursor-Innovation: Add UPDATED scripts/lib-voter-parse-rate.md mirroring new axis-aware retry contract beside scripts/lib-voter-parse-rate.sh edits
  - From Cursor-Requirements: Include plan-review-loop.md in the PR touch list whenever empty-findings tally behavior changes
  - From Codex-dyn-publish-allowlist-safety: Add an UPDATED scripts/design-log-publish.md section documenting the plan-review/round-<N>/findings-classification.tsv staging path, reject-on-unexpected behavior, empty plan-review directory success semantics, and test coverage

---


