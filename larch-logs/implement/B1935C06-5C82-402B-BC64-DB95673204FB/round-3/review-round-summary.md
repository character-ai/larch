# Review Round 3

- Mode: `diff`
- 12 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Tier A eligibility uses PLUGIN_ROOT instead of consumer working tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `tier_a_eligible` calls `is-larch-dev-clone` with `--working-tree-root "$PLUGIN_ROOT"`, not the consumer project tree. In consumer repos loaded from a local larch checkout, `report_surface` almost always selects `issue-input`; `compose-report` then rejects that surface on non-dev trees, teardown falls back to chat-print, and Tier B upstream filing may not run. The same mis-check can route full Tier A bodies to the wrong `--repo` destination instead of bounded Tier B filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Resolve working_tree_root like compose-report does; call tier_a_allowed on that path; use chat-print when Tier A is not allowed.
  - From codex-generic-output.txt: Base Tier A on the target working tree or resolved report repo being the larch dev repo, and fall back to Tier B unless both the project context and destination are validated as larch.


### FINDING_11: Fallback and operator-action sidecars never reach top chat on Gate-C publish path
- **Reviewer(s)**: dyn-design-reporting-output.txt, dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh --post-publish-only` runs the report gate and calls `print_report_gate_sidecars`, which prints `design-failure-chat-print.md` and `design-failure-operator-action-chat.md` after the summary body. On the Gate-C path those lines go to `design-publish.sh` stdout; `design-step5c.sh` captures that stream, parses only allowlisted KVs from `.design-publish-result.env`, then deletes the capture. Step 5c item 5 re-emits only `final-summary.md` from disk. Fallback and operator-action audit text written during publish therefore never reach top chat on normal publish outcomes (`approved`, `failed-publish`, `failed-plan-write`, etc.), despite plan requirements for operator visibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-reporting-output.txt: Extend Step 5c / Final summary handoff to also emit non-empty `design-failure-operator-action-chat.md` and `design-failure-chat-print.md` after the summary block (same content `print_report_gate_sidecars` would print).
  - From dyn-kv-cleanliness-output.txt: Keep embedded publish render file-only for the summary body (redirect render stdout to `/dev/null` or add a `--no-stdout` flag), and emit sidecars from the on-disk files in `design-step5c.sh` or prompt-side Step 5c item 5 after the verbatim `final-summary.md` emit.


### FINDING_12: Tier B dedup validation uses isolated mktemp tmpdir
- **Reviewer(s)**: dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: Tier B duplicate-comment validation passes an isolated `mktemp` directory as `--implement-tmpdir` instead of the report body's session tmpdir. Previously `validate-tier-b-public-file` used `body_dir`, so `build_sensitive_corpus_from_evidence` could scan `plan.txt`, `issue-body.txt`, `source-env.sh`, and related design artifacts during dedup. With the mktemp tmpdir, validation only sees the copied corpus file plus files absent from the empty directory, weakening dedup checks when the on-disk corpus is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tierb-safety-output.txt: Pass the real session tmpdir (e.g. `dirname "$body_file"`) to `reject_tier_b_comment_if_unsafe` / `validate-tier-b-public-file`, or copy the full bounded artifact set into the validator tmpdir. Keep corpus-copy only as a fallback, not the sole evidence source.


### FINDING_14: test-design-failure-report.sh coverage gaps
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The harness always sets `LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1`, so production `compose-report` status routing on consumer working trees is not exercised. CI can pass while consumer-repo production runs always hit `terminal-compose-failed` fallback due to mis-selected `issue-input` surface. Broader teardown-gate coverage stops at roughly five scenarios versus the plan's long acceptance list; missing branches include terminal-over-escalation precedence, Tier B sensitive-corpus rejection, panel-degradation escalation rules, invalid terminal state, and operator-action blocking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a non-legacy test with consumer CLAUDE_PROJECT_DIR and stubbed cross-repo helper asserting successful terminal or escalation filing.
  - From cursor-specialist-testing-output.txt: Add hermetic fixtures for each plan-listed branch in test-design-failure-report.sh.


### FINDING_15: test-design-publish.sh does not assert terminal staging on publish tmpdir
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-write and publish-failure terminal staging is not asserted on the actual `design-publish.sh` failure tmpdir. `stage_design_terminal_state` could break inside `design-publish` while the isolated stage-helper test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: After stubbed PLAN_BLOCK_RC=1 and PUBLISH_OK=false runs assert design-failure-terminal-state.env under the same DESIGN_TMPDIR.


### FINDING_16: test-design-step3-review.sh lacks runtime escalation/degradation checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Step 3 reporting harness is mostly static grep with no runtime ledger or non-terminal degradation checks. `step3_record_report_evidence` or `step3_stage_postplan_failed` could stop writing evidence without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add hermetic loop fixtures that stub record-escalation and assert ledger rows and absence of terminal state on panel degradation statuses.


### FINDING_19: test-render-final-summary.sh missing fallback chat-print sidecar case
- **Reviewer(s)**: dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: The plan requires a harness case that `fallback-print-required` prints `design-failure-chat-print.md` outside the summary body. The branch adds KV-isolation and operator-action sidecar coverage but no fallback chat-print case. A regression in `print_report_gate_sidecars` or `write_fallback_chat` on fallback paths would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-cleanliness-output.txt: Add a stubbed `design-failure-report.sh` path that writes `design-failure-chat-print.md`, run post-publish render, and assert the sidecar appears after the summary body in stdout while helper KVs remain in `design-failure-report.stdout.log`.


### FINDING_2: Tier A dedup-comment status dropped before handle_compose_outcome
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: When `dedup-tier-a-report` returns `dedup-comment`, `file_tier_a_after_compose` normalizes the dedup env but only appends to `COMPOSE_ENV` for `no-match` and `lookup-failed-open`. Terminal statuses like `dedup-comment` never reach `COMPOSE_ENV`, so `handle_compose_outcome` sees an empty status, writes fallback, and skips the run sentinel. Repeated teardown can post duplicate occurrence comments, violating at-most-one-report-per-run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: After normalizing `dedup_env`, append terminal statuses such as `dedup-comment`, `dry-run`, and `fallback-print-required` to `COMPOSE_ENV`; only create a new issue for `no-match` or the intended fail-open case.


### FINDING_20: design-step3-review.sh emits markdown warnings on stdout
- **Reviewer(s)**: dyn-kv-cleanliness-output.txt
- **Severity**: important
- **Concern**: The wrapper prints markdown `**⚠ Step 3: ...**` lines to stdout on allocation, env-read, and invalid-status paths, while the branch adds KV-only `SUMMARY_OUTCOME=failed-postplan` handling elsewhere. `test-design-step3-review.sh` only guards one specific postplan string, not the general KV-only contract. Orchestrators or fences that parse Step 3 Bash output as strict KV can mis-handle these lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-cleanliness-output.txt: Move operator-visible warnings to stderr (matching `design-step5c.sh`) or emit `WARN=<sanitized text>` KVs only; extend `test-design-step3-review.sh` to fail on any `**⚠` markdown in wrapper stdout.


### FINDING_4: populate_design_sensitive_corpus fails open
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: `populate_design_sensitive_corpus` ends with `|| true`, so a failed `populate-sensitive-corpus` leaves `design-failure-sensitive-corpus.env` empty or stale. First-time compose may still validate against the live tmpdir, but cross-repo dedup relies on the on-disk corpus file. Combined with weakened Tier B validator tmpdir isolation, unsafe `+1 occurrence` comments can pass validation without matching tokens from `plan.txt`, `issue-body.txt`, or `source-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed to fallback-print-required when populate fails; do not call compose-report without a fresh corpus file
  - From dyn-tierb-safety-output.txt: Treat populate failure as report degradation (fallback-print / skip filing), or fail closed before calling `file-failure-report-cross-repo.sh`. Only write the terminal/escalation sentinel after a successful populate when Tier B filing is intended.


### FINDING_6: design-publish.sh maps all failures to exit 2 publish-tail staging
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `fail()` always exits 2 via `publish_tail_fail` for all failure kinds, including argv validation and plan-validator failure. `design-step5c.sh` maps rc 2 to `failed-publish-tail` terminal staging and auto-filing, so validator/setup failures can file misleading publish-tail bugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reserve exit 2 for true publish-tail only; use distinct codes or stdout KVs for setup/validator failures; map those in step5c to skip or non-filing abort


### FINDING_7: Step 3 loop remaps tally-error/degraded-empty-collector to panel-failed before escalation recording
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After `run_step3_round_body`, when `body_rc` is non-zero and `LOOP_STATUS` is not already `panel-failed`, the loop sets `LOOP_STATUS=panel-failed` before `step3_loop_emit_envelope` records escalation evidence. An approved run after tally-error or degraded-empty-collector degradation can record the wrong trigger and produce escalation-success reports that omit or misstate the real degradation class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Preserve tally-error and degraded-empty-collector when already set; remap only for empty or unknown LOOP_STATUS


