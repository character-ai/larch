### FINDING_2: Step 5 MAV still points at the old materiality gate
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Oos Pipeline Correctness
- **Severity**: blocking
- **Concern**: The mandatory `/implement` Step 5 main-agent-vote path still instructs backlog-relative materiality, so degraded MAV paths can reject legitimate OOS even after the rubric rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: skills/implement/references/step5-review-branches.md replacing impact-floor/concrete-trigger/issue-overhead/default-deny with the legitimacy rule from skills/shared/oos-acceptance-rubric.md
  - From Cursor-Innovation: ### UPDATED: skills/implement/references/step5-review-branches.md: replace materiality-gate MAV text with the same legitimacy rule as skills/shared/oos-acceptance-rubric.md; mirror in any implement SKILL cross-reference if needed
  - From Codex-Innovation: Add this reference to the plan’s UPDATED files and replace the materiality-gate sentence with the same legitimacy rule used by voter prompts.
  - From Cursor-Pragmatic: Add `### UPDATED: skills/implement/references/step5-review-branches.md` to the plan (and mirror the legitimacy wording used in `skills/design/SKILL.md` Step 3 MAV) so MAV OOS voting matches the rewritten `oos-acceptance-rubric.md`
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/references/step5-review-branches.md` with the same legitimacy wording used in the updated rubric and design MAV instructions
  - From Codex-Requirements: Add `### UPDATED: skills/implement/references/step5-review-branches.md` and replace the MAV OOS paragraph with the legitimacy rule; add or adjust a prompt expectation covering this reference.
  - From Cursor-dyn-Oos Pipeline Correctness: Add `### UPDATED: skills/implement/references/step5-review-branches.md` with the same legitimacy rule as `rendering.py` / `oos-acceptance-rubric.md`; keep parity with `skills/shared/voting-protocol.md:81`
  - From Cursor-dyn-Oos Pipeline Correctness: Expand the implement skill change to explicitly require `step5-review-branches.md` parity (or fold MAV instructions into the SKILL only if that file is retired)


### FINDING_3: Findings ledger judge text still rejects OOS on materiality
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Concern**: Ledger-injected judge guidance for later rounds still tells voters to say NO on OOS that fail the materiality gate, so the loosened legitimacy standard will be applied inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update judge-role ledger rules to legitimacy wording; adjust python/tests/review/test_findings_ledger.py expectations in the same change
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/review/findings_ledger.py` (and `python/tests/review/test_findings_ledger.py` expectations) to propagate the legitimacy rule in ledger judge text
  - From Cursor-dyn-Oos Pipeline Correctness: Add `### UPDATED: python/larch/review/findings_ledger.py` to replace materiality-gate NO guidance with the legitimacy standard (concrete/non-duplicate YES; style/noise/speculation NO)


### FINDING_4: Rejected-OOS audit parser misses legacy FINDING_N headings
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: blocking
- **Concern**: The rejected-OOS audit parser only matches one heading shape, so legacy `### FINDING_N: [OUT_OF_SCOPE]` blocks in `round-*/oos.md` will be omitted from the final audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: In the review_phase_detail rewrite parse both ### OOS_N: and ### FINDING_N: [OUT_OF_SCOPE] blocks from round-*/oos.md; filter security via voting.is_security_block_text; include only Result not accepted; add fixture coverage in python/tests/report/test_review_phase_detail.py for FINDING_N legacy rows
  - From Cursor-Innovation: Extend the audit block regex to accept both ### OOS_N: and ### FINDING_N: titles with [OUT_OF_SCOPE]/[OOS]; parse Result= from the Vote tally footer; skip security blocks and Result=accepted; add test_review_phase_detail fixtures with FINDING_N oos.md


### FINDING_5: Two-judge OOS acceptance thresholds are not specialized
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Concern**: The plan documents relaxed OOS acceptance thresholds for 2-judge panels, but the shared classifier still treats split 2-judge OOS ballots as neutral.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an OOS-only acceptance classifier with the required OOS thresholds, 1/1, 1+/2, 2+/3, and use it in code-review and plan-review tally only for OOS items. Keep in-scope finding thresholds unchanged unless the feature intentionally changes them too.
  - From Codex-Innovation: Add an OOS-specific threshold branch in both tally paths that accepts OOS at 1+/2 and 1/1 while leaving in-scope accept_finding unchanged; update tests for split 2-judge OOS acceptance.
  - From Codex-dyn-Oos Pipeline Correctness: Add a firm plan step for python/larch/review/voting.py or an OOS-specific classifier used by both tallies, with tests that one YES in a 2-judge OOS panel writes the accepted OOS artifact while non-OOS strict handling stays unchanged


### FINDING_6: Some review-core branches still skip real voter dispatch
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: Edge-case `/implement` branches still route to tally paths without dispatching real voter files, so OOS ballots can miss the panel entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Refactor validation-exhausted handling to use the same voter dispatch and tally setup as the normal branch, including voter files/tools and proposer map, before deciding accepted OOS.
  - From Cursor-Requirements: In the prune-only refactor, replace every `gate.remaining_count == 0` early return with a post-prune ballot-empty check on parsed `findings.md` blocks; only call `_zero_findings_branch` when zero blocks remain, and add/keep a pipeline test that an all-OOS ballot dispatches voters and produces non-empty `review-tally.env` / `oos-accepted-review.md` when thresholds pass


### FINDING_7: Security-tagged OOS can leak into public round oos.md
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Removing the pre-vote gate leaves security-tagged OOS on the public artifact path unless tally keeps them on a private sidecar or filters them before append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a firm `### UPDATED: python/larch/review/review_tally.py` step: when `security=True`, skip the public `oos.md` append (route to the existing local `security-oos-observations.md` / security sidecar contract instead), keep pool/accepted-sink holdback as today, add/extend `test_review_tally.py` to assert security text is absent from `oos.md`, and update `SECURITY.md` to describe post-vote holdback instead of pre-vote `oos-dropped-security-local.md`
  - From Codex-Pragmatic: Keep raw oos.md private and project a new sanitized rejected-OOS audit artifact built only from non-security rejected/neutral rows, or filter security before any oos.md projection; update SECURITY.md and tests to pin that public logs never contain security OOS
  - From Cursor-Requirements: Add an explicit tally step (e.g. in `review_tally.py`): when `security=True`, write to a session-local sidecar only and skip `oos.md`; update SECURITY.md to describe post-vote security routing instead of pre-vote dropped security


### FINDING_9: Run-log projection still hides the oos.md source file
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The repointed rejected-OOS audit reads `round-*/oos.md`, but that file is still deny-listed from round log projection, so committed run logs will not contain the source the new audit needs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Move `oos.md` from `_ROUND_ARTIFACT_DENY_GLOBS` into `_ROUND_ARTIFACT_ALLOW`, remove `oos-dropped-before-vote.md` from allow, and add a `test_run_logs.py` assertion that round flush includes `oos.md` after the security routing fix above


### FINDING_10: Aggregate pool promotion can file rejected review OOS
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The code-review aggregate pool still promotes rejected OOS into the accepted-review artifact, which can cause Step 9a.1 to file an item that did not meet the panel threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a firm `### UPDATED: python/larch/review/review_tally.py` step to disable aggregate-pool promotion for `/implement` review OOS, or restrict it to vote-accepted/main-agent accepted blocks only; keep the #6291 design aggregate pool and update the promotion tests.


### FINDING_11: Oversized accepted OOS bodies can create multiple public issues
- **Reviewer(s)**: Codex-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Concern**: The one-unifying-issue rule can still be broken by GitHub body-size splitting, which turns one accepted OOS rollup into multiple public issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Oos Pipeline Correctness: Update the plan to preserve the exactly-one public issue invariant after GitHub body-size handling, for example by filing one summarized issue with full details kept in run logs, and add coverage for an oversized accepted OOS rollup yielding one public payload


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-Oos Pipeline Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:497-518,526-558,668-671,1012-1029,1258-1282; python/larch/review/plan_review_tally.py:882-888; python/larch/design/design_oos.py:176-208
- **Concern**: [SCOPE-REDUCTION] The retained aggregate OOS promotion pool can file rejected OOS. Scenario: The plan keeps the aggregate pool as-is, but both review and design paths add non-security OOS artifacts to the pool before checking accepted status; later promotion appends pool blocks into oos-accepted-review.md or oos-accepted-design.md when severity triggers fire, so a voted-rejected OOS can become public-filed instead of audit-only
- **Proposed resolution**: Change the plan to remove aggregate promotion from accepted filing sinks, or constrain the pool to vote-accepted OOS only; keep rejected and neutral OOS only in oos.md and the rejected-OOS audit


### FINDING_2: Oversized OOS rollups still split into multiple public issues
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The shared OOS filer still splits oversized accepted rollups into multiple public GitHub issues, so a single capped batch can produce `(part N/M)` bodies and more than one `[OOS]` issue instead of exactly one unifying issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote oos_filer.py from MAY_UPDATE to UPDATED: on oversize rollup emit one summarized public body (full text stays in run logs) and file a single create-one call; retire or gate multi-part splitting for capped OOS batches; add/adjust tests in test_oos_filer.py (and test_file_oos.py only if issue-cap output changes)
  - From Codex-Arch: Make oos_filer.py a firm update. Replace splitting with one under-limit summarized body that points to full run-log details, and test exactly one create-one call for oversized OOS
  - From Cursor-Innovation: Promote oos_filer.py from `MAY_UPDATE` to firm `### UPDATED:`: when `OOS_ISSUES_PER_RUN_CAP=1`, replace multi-part splitting with one summarized public body (full detail stays in run logs), and add `test_oos_filer.py` coverage that an oversized post-cap combined payload yields exactly one `create-one` call / one sentinel URL.
  - From Codex-Innovation: Add an explicit plan step for `oos_filer.py` to replace body splitting with one summarized or truncated public body plus run-log details, and cover the oversized path in `test_oos_filer.py`.
  - From Cursor-Pragmatic: Add an UPDATED design_oos.py step: after cap=1 rollup, stamp every source OOS block in oos-accepted-design.md with the single filed URL (or port the implement stable-id mapping); extend test_design_oos.py to assert all rollup sources carry Filed URL and skip re-file on rerun
  - From Codex-Requirements: Promote oos_filer.py from MAY_UPDATE to UPDATED. Replace body splitting with one summarized or truncated public body plus run-log details, and cover the oversized path in test_oos_filer.py.


### FINDING_4: Security-tagged OOS can leak into public artifacts
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: blocking
- **Concern**: Security-tagged OOS that are rejected or neutral can still be appended to public oos.md / oos_chunks, so security prose can leak into committed or projected public artifacts instead of staying in a private sidecar path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Route every security OOS outcome in plan_review_tally.py to a private sidecar and exclude it from oos.md, oos-accepted-design.md, and the aggregate pool. Add the matching design tally test
  - From Codex-Innovation: Add an explicit plan step for plan_review_tally to keep every security-tagged OOS out of oos_chunks, oos_accepted_chunks, and oos_pool_chunks, preserving it only in a local security sidecar or private disposition path, and cover rejected/neutral design security OOS.


### FINDING_5: Security sidecar blocks non-security OOS filing
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: When a security sidecar is present, oos_filer returns early before reading accepted files, so a separate accepted non-security OOS never gets filed into the unifying public issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Make oos_filer.py a firm UPDATED file. File accepted non-security blocks while keeping security blocks private and keeping the checkpoint blocked until private disposition, or explicitly rerun oos file after the sidecar is cleared. Add a mixed security plus non-security test.


