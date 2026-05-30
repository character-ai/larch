### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

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

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-design-log-publish.sh:1038-1057	Ancestor-race coverage is underspecified relative to the existing leaf-race harness	The plan says to mirror the render-cache symlink-race block, but that block uses make_find_symlink_race_stub to replace the enumerated file with a symlink at find -type f time, which exercises the existing [[ -L "$f" ]] leaf guard—not design_publish_ancestor_within_root. Copying it verbatim can leave the new helper untested while CI stays green.	Extend make_find_symlink_race_stub (or add a sibling) so find -type l stays clean, find -type f still lists render-cache/sub/file.txt, and the stub swaps the intermediate sub directory to an outside symlink (not the leaf file). Assert PUBLISH_OK=false and prefer matching the new ancestor error substring.

1. **[correctness]** `scripts/test-design-log-publish.sh:1038-1057` — The proposed ancestor-directory TOCTOU test must not reuse the current leaf-race stub behavior unchanged. `make_find_symlink_race_stub` replaces `RACE_FIND_PATH` with a symlink at `find -type f` time, which the per-file `[[ -L "$f" ]]` check already covers. Item A’s new guard needs a stub that turns an intermediate directory (e.g. `render-cache/sub`) into an escape symlink after a clean `find -type l` scan but before staging, or the new helper can ship without regression coverage.

[OUT_OF_SCOPE] `scripts/design-log-publish.sh:527-531` — Item A adds the ancestor guard to the pause-only `.completed` loop but the testing strategy only mandates render-cache (and optional plan-review) harness cases; a `.completed` ancestor-race case would mirror the same stub pattern if pause publish hardening must stay symmetric.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

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

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-stale-line-refs-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-stale-line-refs-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-stale-line-refs-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-stale-line-refs-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-stale-line-refs-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-stale-line-refs-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-stale-line-refs-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-stale-line-refs-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-stale-line-refs-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-stale-line-refs-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-relay-audit-gap-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-relay-audit-gap-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-relay-audit-gap-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-relay-audit-gap-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-design-log-publish.sh:74-76	Plan-review ancestor harness layout uses `plan-review/round-1/sub/...`	`rel` like `round-1/sub/file` fails the plan-review allowlist (`unexpected path under plan-review`) before the new ancestor guard runs, so the case never exercises `design_publish_ancestor_within_root` and the required `plan-review ancestor became a symlink` substring assertion will not match	Use an allowlisted file directly under `round-1` (e.g. `findings-classification.tsv`) and set `ANCESTOR_RACE_PARENT` to the physical `round-1` directory (same pattern as render-cache `sub/`, but without a disallowed extra path segment)
2	in_scope	important	correctness	scripts/test-design-log-publish.sh:70-76	Ancestor cases must assert `larch_err` text that is emitted only on stderr	Adjacent leaf-race blocks capture stdout with `2>/dev/null`, so copying that wrapper cannot satisfy the plan’s required ancestor-specific stderr substring and risks a stdout-only `PUBLISH_OK=false` check	Capture stderr explicitly (e.g. merge `2>&1` into a variable or use a separate `2>` file) and assert the ancestor message there; do not reuse the stdout-only `2>/dev/null` pattern from the leaf-race cases

1. **[correctness]** `scripts/test-design-log-publish.sh:74-76` — The proposed plan-review ancestor race layout (`plan-review/round-1/sub/...`) conflicts with the publish allowlist in `scripts/design-log-publish.sh` (only `round-<N>/<basename>` or `round-<N>/revise/<basename>` are accepted). The case will fail earlier with “unexpected path under plan-review,” not the new ancestor guard. **Revision:** mirror the render-cache stub but swap `ANCESTOR_RACE_PARENT` to the physical `round-1` directory and keep the enumerated file allowlisted (e.g. `round-1/findings-classification.tsv`).

2. **[correctness]** `scripts/test-design-log-publish.sh:70-76` — New ancestor tests must prove the new `larch_err` strings, which go to stderr via `larch_err`; existing leaf-race neighbors discard stderr (`2>/dev/null`). **Revision:** capture stderr (or combined output) when asserting the ancestor-specific substring; do not copy the stdout-only capture from lines ~972–975 / ~1053–1056.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-design-log-publish.sh (plan §53-76)	Proposed plan-review ancestor-race layout uses `plan-review/round-1/sub/...`	That path fails the existing allowlist at `scripts/design-log-publish.sh:392-414` with `unexpected path under plan-review` before the new `design_publish_ancestor_within_root` call, so the harness cannot hit the required `plan-review ancestor became a symlink before staging` substring and may be misread as a guard bug	Use an allowlisted artifact (e.g. `round-1/findings-classification.tsv` or `round-1/revise/codex-output.txt`) and set `ANCESTOR_RACE_PARENT` to the physical `round-1` or `round-1/revise` directory swapped at `-type f` time (mirror render-cache `sub/` pattern without extra path segments)

1. **[correctness]** `scripts/test-design-log-publish.sh` (plan §53–76): The proposed **plan-review ancestor-directory race** case uses `plan-review/round-1/sub/...`. Current publish logic only allows `round-<N>/<basename>` or `round-<N>/revise/<basename>` (see ```392:414:scripts/design-log-publish.sh```). A nested `sub/` path is rejected earlier with `unexpected path under plan-review`, so the new ancestor guard is never exercised and the case cannot satisfy its own required `plan-review ancestor became a symlink before staging` assertion. **Suggested revision:** Use an allowlisted file (e.g. `round-1/findings-classification.tsv`) and parent-swap `round-1` (or `round-1/revise`) via `ANCESTOR_RACE_PARENT`, analogous to the render-cache `sub/` harness.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:74-76 scripts/design-log-publish.sh:392-414	Plan-review ancestor harness uses `round-1/sub/...` layout	`rel` fails the plan-review allowlist (`unexpected path under plan-review`) before `design_publish_ancestor_within_root` runs, so the new assertion on `plan-review ancestor became a symlink before staging` never exercises Item A	Use an allowlisted path such as `plan-review/round-1/findings-classification.tsv` and set `ANCESTOR_RACE_PARENT` to the physical `round-1` directory under `pr_root` (mirror render-cache `sub/` swap, without an extra `sub/` segment)
1. **[correctness]** `plan.txt:74-76`, `scripts/design-log-publish.sh:392-414` — The proposed plan-review ancestor-directory race case uses `plan-review/round-1/sub/...`. That `rel` does not match the `round-<N>/revise/...` or `round-<N>/<single-segment-artifact>` patterns; publish fails with `unexpected path under plan-review` before the new ancestor guard runs. The harness cannot validate Item A on the plan-review subtree as written.

   **Suggested revision:** Mirror the render-cache layout without violating the allowlist: e.g. `plan-review/round-1/findings-classification.tsv`, `ANCESTOR_RACE_PARENT` = physical `round-1` under resolved `pr_root`, swap that directory in `make_find_ancestor_race_stub` at `-type f`, assert `plan-review ancestor became a symlink before staging`.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-design-log-publish.sh:74-76	Plan-review ancestor harness layout uses `plan-review/round-1/sub/...`	That path fails the existing allowlist (`round-N/<file>` only) at `scripts/design-log-publish.sh:410-413` with `unexpected path under plan-review`, so the new guard is never exercised and the case can fail for the wrong reason	Use an allowlisted file directly under `round-1` (e.g. `findings-classification.tsv`); set `ANCESTOR_RACE_PARENT` to the physical `round-1` dir and `ANCESTOR_RACE_PATH` to that file (same stub pattern as render-cache `sub/`)
1	in_scope	important	risk-integration	scripts/test-design-log-publish.sh:70-76	Ancestor cases require a distinct `larch_err` substring but the plan does not say how to capture stderr	Sibling blocks redirect with `2>/dev/null` and only assert `PUBLISH_OK=false` on stdout; the ancestor message would be dropped and the anti-false-green substring check would not run	Capture publish with merged `2>&1` (or stderr kept) and assert the ancestor-specific substring in that capture; document this in the test `.md` block

**1. [correctness]** `scripts/test-design-log-publish.sh` (plan lines 74–76): The proposed plan-review ancestor layout `plan-review/round-1/sub/...` does not match publish allowlisting. Only `round-<N>/<allowlisted-file>` or `round-<N>/revise/<allowlisted-file>` are accepted (`scripts/design-log-publish.sh:392-413`). A nested `sub/` path is rejected before the new `design_publish_ancestor_within_root` call.

**2. [risk-integration]** `scripts/test-design-log-publish.sh` (plan lines 70–76): The plan requires asserting ancestor-specific `larch_err` text to avoid false greens, but existing race harnesses discard stderr (`2>/dev/null`) and only check stdout for `PUBLISH_OK=false`. Without an explicit capture strategy, the new substring assertions cannot work as specified.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/design-log-publish.sh:391-414	Plan-review ancestor harness uses `round-1/sub/...` layout	`rel` like `round-1/sub/file` fails the plan-review allowlist with `unexpected path under plan-review` before `design_publish_ancestor_within_root` runs, so the case cannot exercise the new guard	Use an allowlisted artifact directly under `round-1/` (e.g. `round-1/findings-classification.tsv`) and set `ANCESTOR_RACE_PARENT` to the `round-1` directory (mirror the existing intermediate-symlink layout at `scripts/test-design-log-publish.sh:929-937`, not a nested `sub/` segment)
2	in_scope	important	correctness	scripts/test-design-log-publish.sh:972-976	Ancestor cases require `larch_err` substring asserts but plan does not fix capture	Adjacent leaf-race blocks discard stderr via `2>/dev/null`; ancestor messages are emitted only on stderr (`design-log-publish.sh` contract), so `PUBLISH_OK=false`-only capture yields a false-green harness even if the guard is missing	Specify merged capture for ancestor blocks only (e.g. `out=$(... 2>&1)` or a dedicated `*_err` file) and assert the ancestor-specific substring there; keep stdout `PUBLISH_OK=false` check

1. **correctness** — `scripts/design-log-publish.sh:391-414` (proposed test in plan Item A): The plan-review ancestor-directory race case is laid out as `plan-review/round-1/sub/...`. The publish allowlist only accepts `round-<N>/<artifact>` or `round-<N>/revise/<artifact>`; any `round-1/sub/...` path is rejected earlier with `unexpected path under plan-review`. The harness cannot reach the new ancestor guard. Revise the case to swap the `round-1` parent directory around an allowlisted file directly under `round-1/` (same shape as the existing intermediate-symlink test, without a `sub/` segment).

2. **correctness** — `scripts/test-design-log-publish.sh:972-976` (proposed harness): Item A and the failure-modes section require asserting ancestor-specific `larch_err` text, not `PUBLISH_OK=false` alone. Neighboring symlink-race blocks capture publish output with `2>/dev/null`, which drops stderr where `larch_err` is written under `LARCH_QUIET_DISABLE=1`. Without an explicit `2>&1` (or stderr file) capture in the plan, an implementer copying the leaf-race pattern will build a false-green test. Add harness instructions to merge stderr for ancestor cases only.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-race-window-audit-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-race-window-audit-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	plan.txt:74-76 scripts/design-log-publish.sh:401-413	Plan-review ancestor harness uses `plan-review/round-1/sub/...`	`rel` like `round-1/sub/file` fails the allowlist at `scripts/design-log-publish.sh:410-413` (`unexpected path under plan-review`) before `design_publish_ancestor_within_root` runs, so Item A is not exercised and the required `plan-review ancestor became a symlink` substring will not appear	Use an allowlisted file directly under `round-1` (e.g. `findings-classification.tsv`); set `ANCESTOR_RACE_PARENT` to the physical `round-1` directory under `pr_root` (swap target outside root), mirroring render-cache `sub/` without an extra disallowed segment
1	in_scope	important	risk-integration	plan.txt:70-76 scripts/test-design-log-publish.sh:972-975	Ancestor cases require ancestor-specific `larch_err` on stderr but the plan does not specify stderr capture	Existing leaf-race neighbors wrap publish with `2>/dev/null` and only grep stdout for `PUBLISH_OK=false`, so the planned substring assertions on ancestor messages would be dropped and could false-green on stdout-only failure	Capture merged output (`2>&1`) or stderr explicitly when asserting `... ancestor became a symlink before staging`; document that requirement in `scripts/test-design-log-publish.md`

1. **[correctness]** `plan.txt:74-76`, `scripts/design-log-publish.sh:401-413` — The proposed plan-review ancestor-directory race layout (`plan-review/round-1/sub/...`) conflicts with the publish allowlist, which only accepts `round-<N>/<basename>` or `round-<N>/revise/<basename>`. The loop fails at lines 410-413 before the new ancestor guard, so the harness cannot prove the TOCTOU backstop for plan-review. **Revision:** swap `ANCESTOR_RACE_PARENT` to the physical `round-1` directory and enumerate an allowlisted file such as `round-1/findings-classification.tsv`.

2. **[risk-integration]** `plan.txt:70-76`, `scripts/test-design-log-publish.sh:972-975` — Item A tests require matching ancestor-specific `larch_err` text (emitted on stderr via `larch_err`), but the plan does not say to change the stdout-only `2>/dev/null` capture pattern used by sibling race cases. **Revision:** assert the ancestor substring on stderr or merged `2>&1` output in both new ancestor-race blocks.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-race-window-audit-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-race-window-audit-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-sanitize-contract-fidelity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-sanitize-contract-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-sanitize-contract-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-sanitize-contract-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-sanitize-contract-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-sanitize-contract-fidelity-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-sanitize-contract-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-sanitize-contract-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-sanitize-contract-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-sanitize-contract-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/ship-pr.sh:889-901	Plan adds Item C coverage in test-ship-pr.sh but does not say how to hit append_tool_failure_local fallback	Default make_repo leaves append-tool-failure.sh executable and IMPLEMENT_TMPDIR set, so a test that only calls ship-pr with a control-byte output_file exercises the --redact success path (append-tool-failure.sh), not the larch_err relay loops being changed	Spell out the fixture: force [ -z "$log_tmpdir" ] or [ ! -x "$SCRIPT_DIR/append-tool-failure.sh" ] (e.g. empty read_state tmpdir or non-executable helper), capture stderr, assert BEL/ESC stripped; mirror test-ci-failed-jobs.sh T8 printf pattern
1	in_scope	important	risk-integration	skills/review/scripts/test-collect-findings.sh:30-37	Plan adds collector/wait log relay assertions but not a stderr capture contract	Harness captures stdout only via out=$(...); collect-findings.sh runs larch_quiet_init and failure relays use larch_err on stderr, so a stdout-only grep can pass while control bytes still appear on stderr	Require merged 2>&1 capture or LARCH_QUIET_DISABLE=1 for the new case(s); assert captured stderr lacks \x07/\x1b while preserving printable text (same pattern as scripts/test-ci-failed-jobs.sh:178-194)

1. **[correctness]** `scripts/ship-pr.sh:889-901` — Item C changes only the `append_tool_failure_local` fallback `larch_err` loops when `log_tmpdir` is empty or `append-tool-failure.sh` is not executable. The plan’s `test-ship-pr.sh` bullet does not say how to force that branch; the default `make_repo` stub always provides an executable helper and a valid tmpdir, so a naive test would exercise the `--redact` success path instead of the sanitized fallback relay.

2. **[risk-integration]** `skills/review/scripts/test-collect-findings.sh:30-37` — New collector/wait relay tests must not follow the existing stdout-only `out=$(...)` pattern. `collect-findings.sh` initializes quiet mode; failure-path `larch_err` lines go to stderr, so control-byte assertions on `out` alone can false-green. Specify merged `2>&1` capture or `LARCH_QUIET_DISABLE=1` for those cases (as the plan already does for ancestor races in `test-design-log-publish.sh`).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

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

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

{"no_issues_found": true}


## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

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
1	in_scope	important	correctness	scripts/test-collect-agent-results.sh:7; skills/review/scripts/test-review-core.sh:5; skills/review/scripts/test-collect-findings.sh:30	Plan treats LARCH_QUIET_DISABLE=1 as an alternative to merged 2>&1 for relay-byte assertions	With quiet disabled, larch_err still writes only to stderr (lib-quiet.sh:127-139); stdout-only out=$(...) or run_core without 2>&1 can pass BEL/ESC grep while never exercising the sanitized relay	Remove the OR wording in Item B harness steps and Failure modes; require merged 2>&1 (or a dedicated stderr capture file) for every new control-byte relay case

1. **correctness** — `scripts/test-collect-agent-results.sh:7`, `skills/review/scripts/test-review-core.sh:5`, `skills/review/scripts/test-collect-findings.sh:30` — The plan lists `merged 2>&1` **or** `LARCH_QUIET_DISABLE=1` as satisfying the Item B/C relay capture contract (Approach, Failure modes, and each new harness section). `LARCH_QUIET_DISABLE` only skips quiet-log redirection (`lib-quiet.md:27-29`, `lib-quiet.sh:43-44`); `larch_err` still goes to stderr, not stdout (`lib-quiet.sh:127-139`). Harnesses that already export `LARCH_QUIET_DISABLE=1` but capture with stdout-only `out=$(...)` can false-green on BEL/ESC absence. **Revision:** Require `2>&1` (or explicit stderr capture, as in `test-collect-findings.sh:84`) for all new relay tests; drop `LARCH_QUIET_DISABLE=1` as a substitute in the plan text.

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

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-harness-fidelity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-harness-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-harness-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-relay-site-coverage-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-relay-site-coverage-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-relay-site-coverage-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-relay-site-coverage-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-relay-site-coverage-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-relay-site-coverage-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-relay-site-coverage-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-relay-site-coverage-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-relay-site-coverage-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-relay-site-coverage-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-ancestor-guard-logic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-ancestor-guard-logic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-ancestor-guard-logic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-ancestor-guard-logic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-ancestor-guard-logic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-ancestor-guard-logic-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-ancestor-guard-logic-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-ancestor-guard-logic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-ancestor-guard-logic-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-ancestor-guard-logic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

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

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	<TMPDIR>/plan.txt:177	Wait-relay harness cites `$REVIEW_TMPDIR/wait.log` but production uses `wait-for-claude-reviewers.log`	Stub or seed writes `wait.log` while `collect-findings.sh` relays `wait_log="$REVIEW_TMPDIR/wait-for-claude-reviewers.log"` (~230); BEL/ESC fixture never hits the changed loops and the wait case false-greens	Use `wait-for-claude-reviewers.log` everywhere in the plan and harness docs; seed the stub’s stderr into that path
2	in_scope	important	correctness	<TMPDIR>/plan.txt:180-183	Failure-relay harness steps omit production entry gates	Collector relay runs only when `EXTERNAL_COUNT>0` (~203); wait relay only when `CLAUDE_COUNT>0` with `.done` sentinels (~227-232). Harness text only says “stub exits non-zero”	New cases never enter the `larch_err` loops being changed; sanitization tests pass without exercising production paths	Collector case: pass `--external-output-files` (dummy file is fine). Wait case: pass `--claude-output-files` plus matching `.done` files, stub `wait-for-reviewers.sh` non-zero, fixture bytes in `wait-for-claude-reviewers.log`

1. **correctness** — `plan.txt:177` (and `skills/review/scripts/collect-findings.sh:230`): Wrong wait log basename (`wait.log` vs `wait-for-claude-reviewers.log`) breaks the wait-relay test contract.

2. **correctness** — `plan.txt:180-183` / `collect-findings.sh:203-246`: Document and implement the `--external-output-files` and `--claude-output-files`+`.done` prerequisites so failure-relay cases actually hit the sanitized loops.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	<TMPDIR>/plan.txt:177	Wait-relay harness cites `$REVIEW_TMPDIR/wait.log` but production uses `wait-for-claude-reviewers.log`	Stub/fixture bytes written to `wait.log` never enter the `$wait_log` relay at `skills/review/scripts/collect-findings.sh:230-243`; merged `2>&1` assertions can false-green	Replace `wait.log` with `wait-for-claude-reviewers.log` everywhere the plan names the wait-relay log path (harness env docs and `test-collect-findings.md`)
1	in_scope	important	correctness	<TMPDIR>/plan.txt:206-212	`test-collect-agent-results.sh` coverage says stub `wait-for-reviewers.sh` but not that `collect-agent-results.sh` hardcodes `"$SCRIPT_DIR/wait-for-reviewers.sh"`	PATH-only or in-repo shadow stubs never hit the WAIT_STDERR relay at `scripts/collect-agent-results.sh:308-311`; BEL/ESC stripping may ship untested	Mirror the collect-findings harness contract: invoke from a minimal tree where `scripts/collect-agent-results.sh` and a stub `scripts/wait-for-reviewers.sh` share the same `SCRIPT_DIR` (copy/symlink real collector + real `lib-quiet.sh`/`redact-secrets.sh` siblings); document that PATH-only stubs are insufficient

1. **correctness** — Plan harness path `wait.log` vs production `wait-for-claude-reviewers.log` (`plan.txt` ~177; production `skills/review/scripts/collect-findings.sh:230`). **Revision:** Use the production basename in all plan/test-doc references.

2. **correctness** — `test-collect-agent-results.sh` plan omits `SCRIPT_DIR`-local stub layout (`plan.txt` ~206-212; production `scripts/collect-agent-results.sh:308`). **Revision:** Add the same explicit “minimal `scripts/` tree + invoke collector from that tree” contract already given for `collect-findings` / `CLAUDE_PLUGIN_ROOT`.

[OUT_OF_SCOPE] `scripts/design-log-publish.sh:271-275` — `design_publish_stage_file` still returns success when the source is missing or a symlink after checks; a post-check TOCTOU on the leaf could skip staging without failing publish. Pre-existing; ancestor guard addresses the scoped parent-directory race only.

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

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-harness-integrity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-harness-integrity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-integrity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-harness-integrity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-integrity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-line-ref-staleness-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-line-ref-staleness-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-line-ref-staleness-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-line-ref-staleness-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-line-ref-staleness-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-line-ref-staleness-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-line-ref-staleness-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-line-ref-staleness-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-line-ref-staleness-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-line-ref-staleness-output-phase3.txt.diag)

  ```
