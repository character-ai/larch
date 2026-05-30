### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:82-83	Collector dedup pass anchored at line ~852 is before the retry loop (section 3 starts ~854) and before sections 3.5–3.7 that rewrite RESULTS	Implementer inserts dedup after the first classification loop; retries/NS-retry/substantive passes still change STATUS afterward, so FD-2 tails can be missing, stale, or emitted for slots that later become OK	Place the dedup-emit pass immediately before section 4 (current ~1419), after section 3.7 completes; drop the ~852 anchor and cite the post-3.7 / pre-4 boundary explicitly
1	in_scope	important	correctness	plan.txt:84-85;scripts/collect-agent-results.sh:1164-1165	Collector dedup reads `${OUTPUT}.stderr-tail` from REVIEWER_FILE, but retry failure rows keep REVIEWER_FILE at ORIG_OUTPUT while `build_failure_reason` and `run-external-agent.sh` use `${ORIG_OUTPUT%.txt}-retry.txt`	After a retried failure, chat can show the first-attempt stderr tail while FAILURE_REASON describes the retry attempt (or skip the retry tail entirely if only `${RETRY_OUTPUT}.stderr-tail` exists)	Resolve tail path in the dedup pass: prefer `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present for failed slots, else `${REVIEWER_FILE}.stderr-tail`; extend `test-collect-agent-results.sh` with a retry-failure case

1. **[correctness]** `plan.txt:82-83` — The dedup-emit pass is described as running after the retry loop settles, but the line anchor `~852` is the end of the **first** results-classification loop. Section 3 (empty-output retry, ~854–1173), section 3.5 (substantive validation), section 3.6 (structured validation), and section 3.7 (NOT_SUBSTANTIVE retry) all run later and can change `RESULTS[]` / `STATUS`. Insert dedup immediately before section 4 (`# --- 4. Emit structured results ---`, ~1419), not near 852.

2. **[correctness]** `plan.txt:84-85` / `scripts/collect-agent-results.sh:1164-1165` — On retry failure the collector keeps `REVIEWER_FILE=$ORIG_OUTPUT` but builds `FAILURE_REASON` from `RETRY_OUTPUT` (`${ORIG_OUTPUT%.txt}-retry.txt`). `write_failed_agent_stderr_tail` in `run-external-agent.sh` writes to whichever `--output` was used, so the retry attempt’s tail lands on `${RETRY_OUTPUT}.stderr-tail`. The dedup pass as written only probes `${OUTPUT}.stderr-tail` derived from `REVIEWER_FILE`, so chat can surface the wrong root-cause tail or none. Resolve retry vs original sidecar in the dedup pass and cover it in the extended collector harness.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/collect-agent-results.sh:852-1419	Dedup-emit anchor contradicts “after retries settle”	Placing the pass near ~852 runs before §3 empty-output retry, §3.5–3.7 NS retry, and final `RESULTS[]` updates, so tails/dedup can reflect pre-retry state or miss retry-final failures	Insert the dedup pass immediately before `# --- 4. Emit structured results ---` (~1419), after §3.7; drop the ~852 anchor from the plan
1	in_scope	important	correctness	scripts/collect-agent-results.sh:1140-1166	Retry failure keeps `REVIEWER_FILE=$ORIG_OUTPUT` but `run-external-agent.sh` writes `${RETRY_OUTPUT}.stderr-tail`	Empty-output / transient retry that fails on `*-retry.txt` leaves agent stderr only on the retry basename; collector dedup reading `${REVIEWER_FILE}.stderr-tail` sees nothing or a stale first-pass tail	In dedup (and tests), resolve tail from `REVIEWER_FILE` with fallback to `${REVIEWER_FILE%.txt}-retry.txt.stderr-tail` when present, or copy retry tail onto the canonical output path in the retry-failure branch
1	in_scope	important	risk-integration	scripts/run-external-agent.sh:63-75; scripts/lint-fix-loop.sh:231-237; scripts/launch-codex-implement.sh:324-338	Stderr source list assumes `${OUTPUT}.sidecar` / `.diag` / output	Lint-fix-loop Codex uses `2>"$run_dir/codex.wrapper.log"`; implement launchers use caller `--sidecar-log`, not `${TRANSCRIPT}.sidecar`, so `write_failed_agent_stderr_tail` often sees only generic `.diag` and `emit_failed_agent_stderr_tail_raw` goes to the redirected log, not chat—contrary to the plan’s foreground-lane claim	Narrow the plan goal to review/collector batches (where `${OUTPUT}.sidecar` exists) or add a minimal explicit stderr-source hook at the choke point; do not claim lint-fix-loop/implement chat surfacing without launcher-path changes
1	in_scope	latent	correctness	scripts/run-external-agent.sh:140-141	Stale `${OUTPUT}.stderr-tail` not cleared in pre-launch `rm -f`	A later failure with empty/missing stderr can leave a prior `.stderr-tail`; collector dedup may re-emit an old redacted tail	Add `${OUTPUT_FILE}.stderr-tail` to the stale-artifact cleanup (and unlink in `write_failed_agent_stderr_tail` when render is empty/disabled)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-quiet-init-purity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-quiet-init-purity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-quiet-init-purity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-quiet-init-purity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-quiet-init-purity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-fd-routing-integrity-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-fd-routing-integrity-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:82-85 / scripts/collect-agent-results.sh:852-1418	Dedup-emit pass anchored at ~852 before retries/NS settle	Inserting dedup after the section-2 loop (~852) runs before section 3 empty-output retry and sections 3.5–3.7 NS retries; emits tails for slots later upgraded to OK and uses non-final STATUS	Move dedup immediately before section 4 (`# --- 4. Emit structured results ---`, ~1419); iterate `RESULTS[]`, parse `REVIEWER_FILE` per entry, and gate on final `STATUS`

1. **correctness** — `plan.txt:82-85` / `scripts/collect-agent-results.sh:852-1418`: The plan requires dedup after retries are final (line 82) but pins insertion to “after line ~852”, which is the end of the first validation loop and **before** section 3 retry (starts ~854) and sections 3.5–3.7. Cases like `test-collect-agent-results.sh` C_T1/C_T4 (transient failure → retry → `STATUS=OK`) would still get a failure stderr tail on FD 2. **Revision:** insert dedup only after section 3.7 completes, immediately before stdout emission (~1419).

2. **correctness** — `plan.txt:84-85`: The dedup pass refers to `${OUTPUT}.stderr-tail`, but `OUTPUT` is only the section-2 loop variable; after retries, `RESULTS` may point at `*-retry.txt` paths. A post-loop dedup that reuses bare `OUTPUT` would read the wrong sidecar (typically the last slot). **Revision:** name the path from each entry’s `REVIEWER_FILE=` field when opening `.stderr-tail`.

**FD-2 routing (no finding):** `emit_failed_agent_stderr_tail_raw` is specified as plain `printf >&2` in a non-quiet script; collector dedup uses `larch_err`, which routes to original stderr (FD 4 under quiet init, not contract FD 3). None of these paths use `emit`/`emit_kv`.

**Fence + `larch_err` (exonerated):** `larch_err` does not add timestamps or script prefixes; line-by-line calls preserve fence lines. Per-line streaming redaction may re-run on already-redacted tail content; plan treats that as idempotent.

**Stdout harness (exonerated):** The “stdout RESULTS … byte-unchanged” check is specified in the proposed `scripts/test-collect-agent-results.sh` extension (plan testing strategy ~165-167), not in `test-lib-failed-agent-stderr-tail.sh` (unit scope only). Failure modes ~151 is satisfied by that extension; it does not yet spell `cmp`/golden-file mechanics, but “byte-unchanged” is enough for implementers.

**Claude double surface (exonerated):** `launch-claude-review.sh` ~173-178 full stderr re-emit stays; plan ~104-105 and ~169 explicitly keep it additive alongside `${OUTPUT}.stderr-tail` and collector dedup. Operators may see full stderr at launch time plus a bounded tail in the collector log—accepted by the plan.

**Codex/cursor double surface (exonerated):** Foreground `run-external-agent.sh` raw tail emit vs collector `larch_err` resurface is intentional per plan approach ~126-128 (#3119 background case); not equivalent to the claude launcher duplicate.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-fd-routing-integrity-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-fd-routing-integrity-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-sidecar-lifecycle-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-sidecar-lifecycle-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/launch-claude-subprocess.sh:222 scripts/launch-claude-review.sh:180-182	Claude slot writes .done before parent can write .stderr-tail	wait-for-reviewers unblocks on subprocess .done while launch-claude-review still runs post-rc work; collector dedup can skip a missing sidecar for real failures	Write .stderr-tail in launch-claude-subprocess.sh immediately before .done (source ${OUTPUT}.stderr), or defer .done until the parent finishes the tail write
2	in_scope	important	correctness	scripts/launch-claude-review.sh:154-163 plan:launch-claude-review	Planned tail source is wrapper stderr not CLI stderr	Plan calls write_failed_agent_stderr_tail on SUBPROCESS_STDERR (launch-claude-subprocess.sh redirect); agent failures live in ${OUTPUT}.stderr from subprocess	Use first non-empty of ${OUTPUT}.stderr then SUBPROCESS_STDERR (mirror run-external-agent source order)
3	in_scope	important	correctness	scripts/collect-agent-results.sh:852 scripts/collect-agent-results.sh:1417-1419	Plan line anchor places dedup before retry/validation	Dedup after ~852 runs before section 3 retries and 3.5/NS paths; stderr-tail and STATUS are not final	Insert dedup immediately before section 4 emit (~1417), after all retry and validation blocks
4	in_scope	important	correctness	scripts/run-external-agent.sh:141 plan:run-external-agent	Startup cleanup omits stale .stderr-tail	Second failure with empty stderr leaves prior .stderr-tail; dedup can emit wrong tail for a new failure	Add ${OUTPUT_FILE}.stderr-tail to the line 141 rm -f list
5	in_scope	important	correctness	scripts/collect-agent-results.sh:1164-1165 plan:collect-agent-results	Dedup path not aligned with retry artifact layout	Retry also failed keeps REVIEWER_FILE=ORIG_OUTPUT but run-external-agent writes ${ORIG}-retry.stderr-tail; dedup on REVIEWER_FILE misses the tail	Resolve tail path from retry output when ${ORIG%.txt}-retry.stderr-tail exists (same path build_failure_reason uses for retry .diag)

1. **correctness** — `scripts/launch-claude-subprocess.sh:222`, `scripts/launch-claude-review.sh:180-182`: `launch-claude-subprocess.sh` writes `${OUTPUT_CANON}.done` before the parent returns. `collect-agent-results.sh` waits only on `.done` sentinels (`scripts/collect-agent-results.sh:291-308`), so the dedup pass can run while `launch-claude-review.sh` has not yet written `.stderr-tail`. **Revision:** write the sidecar in `launch-claude-subprocess.sh` before line 222, or do not publish `.done` until the parent finishes the tail write.

2. **correctness** — `scripts/launch-claude-review.sh:154-163` (plan § launch-claude-review): The plan sources `SUBPROCESS_STDERR` (wrapper redirect). CLI stderr is `${OUTPUT}.stderr` (`scripts/launch-claude-subprocess.sh:215`). **Revision:** prefer `${OUTPUT}.stderr`, then wrapper capture.

3. **correctness** — `scripts/collect-agent-results.sh:852` vs `1417-1419` (plan § collect-agent-results): Anchor “after line ~852” is the end of the first results loop, before retries (`854+`) and substantive/NS work (`1175+`). **Revision:** place dedup immediately before section 4 (`# --- 4. Emit structured results ---`).

4. **correctness** — `scripts/run-external-agent.sh:141` (plan § run-external-agent): Stale-clear lists `.diag` but not `.stderr-tail`. Empty stderr on a later failure leaves an old sidecar. **Revision:** add `${OUTPUT_FILE}.stderr-tail` to the startup `rm -f` list.

5. **correctness** — `scripts/collect-agent-results.sh:1164-1165` (plan § collect-agent-results): Retry failure keeps `REVIEWER_FILE=$ORIG_OUTPUT` while `run-external-agent.sh` writes `${ORIG}-retry.stderr-tail`. **Revision:** resolve tail from the retry output path when present.

**Exonerated (plan-consistent):** `run-external-agent.sh` writes failure artifacts before `exit`, then the EXIT trap writes `.done` (`149-155`, `289-308`) — no race for codex/cursor. `design-log-publish.sh:259` excludes `*.sidecar`, `*.done`, `*.diag`, etc.; `*.stderr-tail` is not matched, so the publish claim holds. Atomic `mktemp`+`mv` in the proposed lib is fine if stale files are cleared at runner start (finding 4).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-sidecar-lifecycle-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-sidecar-lifecycle-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/lib-failed-agent-stderr-tail.sh:33-34 (planned)	Byte-cap pipeline uses tail | redact | head -c under caller pipefail	When stderr exceeds 5 KB, head -c closes the pipe early; tail/redact get SIGPIPE; with set -o pipefail (run-external-agent.sh:61, collect-agent-results.sh:57, launch-claude-subprocess.sh:4) render/write can return non-zero or abort before .stderr-tail is written — the #3119 background case loses tails exactly when they are largest	Truncate without a failing pipeline: spool tail|redact to a temp file then head -c from the file, or wrap the pipeline with set +o pipefail / || true per scripts/lib-cursor-launcher-common.sh:282-294; assert non-zero exit_code still writes .stderr-tail in test-lib-failed-agent-stderr-tail.sh
2	in_scope	important	architecture	scripts/launch-claude-subprocess.md:10-11	Plan updates launch-claude-subprocess.sh ordering but not its sibling contract	launch-claude-subprocess.md still says .done is written only after output promotion; post-change behavior writes ${OUTPUT}.stderr-tail before .done on failure — doc/harness drift and script-md-siblings violation	Add ### UPDATED: scripts/launch-claude-subprocess.md documenting pre-.done .stderr-tail write, harness pointer, and edit-in-sync with lib-failed-agent-stderr-tail.sh

1. **correctness** — `scripts/lib-failed-agent-stderr-tail.sh:33-34` (planned): Proposed `render_failed_agent_stderr_tail` uses `tail -n <N> "$source_file" | redact-secrets.sh | head -c 5120`. Callers run `set -o pipefail` (`run-external-agent.sh:61`, `collect-agent-results.sh:57`, `launch-claude-subprocess.sh:4`). `scripts/test-pipe-sigpipe-safety.sh` documents that `producer | head` fails under pipefail when the producer outlives `head`. Large stderr hits the byte cap often; the pipeline can exit 141 and skip `.stderr-tail` creation on the failure paths that matter most. **Revision:** spool-then-truncate, or `set +o pipefail` / `|| true` around the cap step (see `lib-cursor-launcher-common.sh:282-294`).

2. **architecture** — `scripts/launch-claude-subprocess.md:10-11`: The plan changes `launch-claude-subprocess.sh` to write `${OUTPUT_CANON}.stderr-tail` before `${OUTPUT_CANON}.done` on failure but does not list `launch-claude-subprocess.md`, while other touched scripts get `.md` updates. The current contract says `.done` follows output promotion only. **Revision:** add `### UPDATED: scripts/launch-claude-subprocess.md` for pre-`.done` sidecar write and harness cross-refs.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-innovation-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-innovation-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-innovation-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-quiet-fd-routing-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-quiet-fd-routing-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-quiet-fd-routing-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-quiet-fd-routing-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-quiet-fd-routing-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-collector-dedup-alignment-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-collector-dedup-alignment-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-collector-dedup-alignment-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-collector-dedup-alignment-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-collector-dedup-alignment-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-collector-dedup-alignment-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-collector-dedup-alignment-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-collector-dedup-alignment-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-collector-dedup-alignment-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-collector-dedup-alignment-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-source-selection-mapping-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-source-selection-mapping-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/run-external-agent.sh:250-265,289-299	Proposed stderr source order `.sidecar` → `.diag` → `OUTPUT_FILE` is mode-blind; FAILED/TIMED_OUT always append a non-empty wrapper line to `${OUTPUT_FILE}.diag` before selection	`--capture-stdout` merges agent stderr into `OUTPUT_FILE` (`run-external-agent.sh:229-232`, `run-external-agent.md:23-24`) but `.diag` is still populated on every non-zero/timeout exit (`:263`, `:299`), so the second candidate wins and tails show wrapper text instead of merged agent stderr — contradicts the plan’s `--capture-stdout` merged-mode claim (`plan.txt:77-78`)	Branch on in-scope `CAPTURE_STDOUT` / `CAPTURE_STDOUT_ONLY`: e.g. merged → prefer non-empty `OUTPUT_FILE` before `.diag`; stdout-only → `.diag` before `OUTPUT`; default review → keep `.sidecar` first
1	in_scope	important	risk-integration	skills/review/scripts/collect-findings.sh:206-221	Collector dedup is planned via `larch_err` in `collect-agent-results.sh`, but `/review` captures all collector stderr into `collect-agent-results.log` and only replays that log when the collector exits non-zero	Review launches discard launcher stderr (`scripts/dispatch-with-waterfall.sh:269,284` `2>&1` to `/dev/null`), so `emit_failed_agent_stderr_tail_raw` never reaches chat; on `collector_rc=0` the dedup pass’s `larch_err` tails stay in the log file and never surface — the main `/review` batch path misses issue #3202 chat delivery	Minimum fix: after a successful collector run, scan failed slots for `.stderr-tail` and emit (or replay dedup lines from the log) via `larch_err`; or stop redirecting collector stderr to only a file on the review path

## Findings

1. **[correctness]** `scripts/run-external-agent.sh:250-265,289-299` — The plan’s uniform `.sidecar` → `.diag` → `OUTPUT_FILE` pick does not match where stderr actually lives per capture mode. Default codex/cursor review (stderr in `${OUTPUT}.sidecar` via `launch-review.sh:542`, `966`) is fine when the sidecar is non-empty. `--capture-stdout-only` puts agent stderr in `.diag` (`run-external-agent.sh:207-216`) and also works when the sidecar is empty. `--capture-stdout` merges stderr into `OUTPUT_FILE` (`229-232`), but both FAILED and TIMED_OUT always append wrapper text to `.diag` first (`263`, `299`), so `.diag` is almost always non-empty and blocks the merged file — the plan’s merged-mode coverage claim is wrong for voters, dialectic judges, and other direct `--capture-stdout` callers.

2. **[risk-integration]** `skills/review/scripts/collect-findings.sh:206-221` — The collector dedup pass is the right batch choke point, but `/review` wires it so FD 2 does not reach the operator on success: `collect-agent-results.sh` stderr goes to `collect-agent-results.log`, and lines are replayed with `larch_err` only when `collector_rc -ne 0`. Review slot launches are backgrounded with stderr discarded (`dispatch-with-waterfall.sh:269,284`), so `run-external-agent.sh` raw `>&2` tails are lost before collection. The plan does not update `collect-findings.sh`, so the proposed change may not deliver stderr tails to chat on the primary `/review` path even when `.stderr-tail` sidecars are written correctly.

## Claude lane (no finding)

Claude reviewer/voter runs use `launch-claude-review.sh` → `launch-claude-subprocess.sh`, not `run-external-agent.sh` (`launch-claude-subprocess.sh:198-215` writes `${OUTPUT_CANON}.stderr`). The plan’s separate pre-`.done` write from that file (`plan.txt:111-116,146-147`) matches the bypass; run-external-agent source order is irrelevant for that lane.

## TIMED_OUT vs FAILED (exonerated)

Both paths in `run-external-agent.sh` only append wrapper diagnostics to `.diag`; neither writes `.sidecar` (launchers own the sidecar). TIMED_OUT can leave `.sidecar` empty or unflushed after `kill` while `.diag` still gets a timeout line — same selection runs on both branches, so behavior is consistent but often degrades to wrapper-only text; the plan’s “empty/missing source” edge case partially covers this without claiming file parity.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-source-selection-mapping-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-source-selection-mapping-output.txt.diag)

  ```
