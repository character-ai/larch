### FINDING_1: Launch-stderr temp files leak on signature failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When on-demand launch-stderr tail signature computation fails and the collector §3.8 loop `continue`s early, `mktemp` files matching `larch-launch-stderr-tail.*` are not removed. Repeated waterfall/collector runs with launcher stderr but unhashable tails can accumulate junk in `TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Collector integration harness gaps beyond same-signature dedup
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan/acceptance collector tests are largely missing: distinct dual-tail dedup, retry-path tail resolution, post-retry stale removal, launch-stderr surfacing, and byte-level stdout unchanged proof. Only same-signature dedup is pinned; over-aggressive dedup, wrong retry tail source, stale tails beside OK results, or accidental stdout leakage could regress without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_16: Stderr-tail render omits redact-tmpdir-paths.sh
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `render_failed_agent_stderr_tail` uses `redact-secrets.sh` only, omitting `redact-tmpdir-paths.sh` used at other publish boundaries. Codex/Cursor failure stderr containing operator home/repo or session tmpdir paths can surface verbatim to chat on FD 2 while other larch publish paths scrub paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Chain redact-tmpdir-paths.sh | redact-secrets.sh in render_failed_agent_stderr_tail; add harness path-redaction tests; document dual pipeline in lib-failed-agent-stderr-tail.md.


### FINDING_18: SECURITY.md not updated for stderr-tail trust boundary
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` was not updated for the new FD 2 stderr tail trust boundary despite AGENTS.md convention. Operators and auditors lack authoritative documentation of what is redacted, what is not, and where tails may appear (chat vs larch-logs).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add SECURITY.md section for failed-agent stderr tails: env var, redaction pipeline, failure-only semantics, dedup, and publish behavior.


### FINDING_19: Committed larch-logs stderr-tail artifacts and gitleaks blind spot
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New publishable `*.stderr-tail` artifacts can enter committed `larch-logs/` while gitleaks excludes that tree. A redaction miss on a stderr tail could commit sensitive material with no Layer 1/2 gitleaks backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Ensure dual redaction at publish; document gitleaks blind spot; treat run logs as sensitive regardless of redaction.


### FINDING_2: Stderr-tail emit runs under --summary-only collector calls
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: §3.8 stderr-tail emission runs for `--summary-only` collector calls used inside `dispatch-with-waterfall` `collect_phase`. Phase-1 codex failures can emit tails to chat even when phase-2/3 later succeeds, producing false alarms beside final OK slots in the transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Design plan-review collector does not surface stderr tails to chat
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` captures collector stdout only while nested quiet-init redirects stderr tails to quiet logs. `/design` plan-review slot failures produce `.stderr-tail` sidecars but dedup `larch_err` output lands in `larch-quiet-*.log`, not orchestrator chat—regression of #3119 visibility for design panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Tee collector stderr to parent FD 2 (mirror collect-findings.sh) or replay tail lines after successful collect


### FINDING_21: compose-collector-failure-log omits .stderr-tail dumps
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `compose-collector-failure-log.sh` still dumps only `.diag`, not `.stderr-tail`. Design Step 3 append-tool-failure logs lack redacted stderr tails even when sidecars exist; operators must grep tmpdir artifacts manually.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add dump_section for ${REVIEWER_FILE}.stderr-tail (and optionally .launch-stderr)


### FINDING_24: hook-anti-read-poll false positive on read verbs inside jq/grep literals
- **Reviewer(s)**: dyn-bash-cmd-parser-output.txt
- **Severity**: important
- **Concern**: `bash_has_read_verb` treats `cat`, `head`, `tail`, etc. as word-bounded tokens anywhere in the full Bash command string. A jq/awk program or grep alternation containing `"cat"` or `|cat|` (e.g. `jq 'select(.kind == "cat")' "$TASK_OUT"`) can match while `extract_task_output_token` also finds `tasks/...output`, incrementing the poll counter even though no read utility was invoked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-cmd-parser-output.txt: Gate on a stricter pattern (e.g. require a read verb only before the first `tasks/...output` match, or only in the segment after stripping single-quoted/double-quoted spans), and add harness cases for jq/grep literals that mention `cat` alongside a task-output path.


### FINDING_25: hook-anti-read-poll segment split lacks quote awareness
- **Reviewer(s)**: dyn-bash-cmd-parser-output.txt
- **Severity**: important
- **Concern**: `bash_line_task_output_poll_token` splits on the first `;`, `&&`, or `||` with no quote awareness. Metacharacters inside double-quoted strings or jq programs can produce garbage segments (false negatives for real polls) or spurious segments combining a read verb with a path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-cmd-parser-output.txt: Either document this as an intentional heuristic limit, or split only on unquoted operator boundaries (minimal state machine over `'`/`"`/`\"`), with harness cases for `";"` inside quotes and for pipelines where the task path appears only after a redirect on a later segment.


### FINDING_26: hook-anti-read-poll misses multiline read without backslash continuation
- **Reviewer(s)**: dyn-bash-cmd-parser-output.txt
- **Severity**: important
- **Concern**: `bash_normalize_cmd` only joins backslash–newline continuations. A read verb on one physical line and `tasks/<id>.output` on the next without `\` is evaluated as two lines; neither line satisfies both predicates, so multiline polls of that shape are never counted (false negative).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-cmd-parser-output.txt: After normalization, if a line is only a read verb (or ends with one) and the next line yields a task-output token, treat them as one logical segment; add a harness case for `cat` newline `tasks/foo.output` without a trailing backslash.


### FINDING_27: HOME metacharacters in signature sed break or skew dedup
- **Reviewer(s)**: dyn-signature-dedup-output.txt
- **Severity**: important
- **Concern**: Session-path normalization builds a `sed -E` regex from `home_cache="${HOME:-}/.cache/larch/sessions"` with only `/` escaped. Other `sed` metacharacters in `HOME` (notably `#`, the pattern delimiter) can break `s#…#<path>#g`; with `pipefail` in the collector, a failing pipeline makes `failed_agent_stderr_signature` exit non-zero, §3.8 treats that as “no signature” and `continue`s—suppressing the first (and only) full tail for that slot. Unescaped `.` in usernames widens ERE matches and increases false “identical failure” dedup. There is no guard to fall back to `cksum` on partially normalized text when `sed` fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-signature-dedup-output.txt: Do not embed `HOME` in a dynamic `sed` regex. Prefer a fixed, delimiter-safe substitution (e.g. `printf '%s\n' "$norm" | sed "s|$(printf '%s' "$home_cache" | sed 's/[[\.*^$[]/\\&/g')|[^[:space:]]*|<path>|g"` with a tested escaper, or a non-regex path strip such as a small `awk`/bash loop using literal prefix match). Add harness cases with `HOME` containing `.` and `#` (and assert dedup still emits the first tail).
  - From dyn-signature-dedup-output.txt: Wrap the `home_cache` normalization in `set +o pipefail` / `|| true` (mirroring `render_failed_agent_stderr_tail:75-77`) or check `sed`’s exit status and continue to `cksum` on the pre-home `norm` so a bad `HOME` only weakens dedup, never suppresses the first tail.


### FINDING_3: Missing harness for collect-findings stderr tee on successful collect
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `collect-findings.sh` tees collector stderr to parent FD 2, but `test-collect-findings.sh` has no case asserting fenced tail/suppression lines on wrapper FD 2 when `collector_rc=0` and failed external slots exist (plan FINDING_3). A tee/process-substitution regression could silence `/review` failure tails in chat while `/design` panel paths still work, with CI staying green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Incomplete test-run-external-agent harness for stderr-tail boundary
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Planned wrapper-level cases are largely missing: mode-aware source selection order (sidecar vs diag vs output), `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` disable, stale `.stderr-tail` cleanup before launch, `TIMED_OUT` tailing, and disable-on-success. Only partial coverage (e.g. single `--capture-stdout` failure) exists; production regressions at the `run-external-agent.sh` boundary would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: CHANGELOG 47.0.4 omits #3202 stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Release notes for 47.0.4 document polling only, not failed-agent stderr surfacing. Operators installing that release miss `LARCH_FAILED_AGENT_STDERR_TAIL_LINES`, dedup, timeout clamp, and failure-tail behavior documented elsewhere in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: NS-retry CURSOR_EMPTY_RESPONSE leaves stale ORIG_OUTPUT.stderr-tail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sentinel-ordering-output.txt, dyn-bash-cmd-parser-output.txt
- **Severity**: important
- **Concern**: NS-retry success paths that land in `CURSOR_EMPTY_RESPONSE` keep `REVIEWER_FILE=$ORIG_OUTPUT` but only remove `${ORIG_OUTPUT}.stderr-tail` in plain-`OK` branches, unlike transient-retry (line 1157) which removes the tail for both `OK` and `CURSOR_EMPTY_RESPONSE`. After an original failure writes `.stderr-tail`, an NS retry that succeeds with a degraded sentinel leaves the pre-retry tail; §3.8 does not skip `CURSOR_EMPTY_RESPONSE` and can emit stale failure stderr to FD 2 (and may publish a stale sidecar) even though the slot recovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-sentinel-ordering-output.txt: Mirror the transient-retry pattern: after any successful NS retry (both structured and substantive paths), unconditionally `rm -f "${ORIG_OUTPUT}.stderr-tail"` regardless of whether the final status is `OK` or `CURSOR_EMPTY_RESPONSE`; optionally add a harness case where an original failure sidecar plus NS-retry `CURSOR_EMPTY_RESPONSE` must not emit the stale tail.
  - From dyn-bash-cmd-parser-output.txt: Extend stale-tail removal to every NS-retry / transient-retry terminal success class you do not want treated as a hard failure (at minimum `CURSOR_EMPTY_RESPONSE`), or add those statuses to the dedup skip list when `EXIT_CODE=0`.


