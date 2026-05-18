### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `scripts/test-harness-timer.sh:1`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-harness-timer.sh:1`      The new Makefile-only harness is not added to `agent-lint.toml`’s dead-script exclusions, so `agent-lint` fails with `G004/dead-script` for `scripts/test-harness-timer.sh`. Concrete failing scenario: the branch adds `Makefile:449-450`, then CI’s `agent-lint` job runs and rejects the PR even though `make test-harness-timer` passes. Add `scripts/test-harness-timer.sh` to the existing Makefile-only harness exclusion block near `scripts/test-harness-shards-coverage.sh` / `scripts/harness-timer.sh`; include `scripts/test-harness-timer.md` too if you want to mirror the adjacent sibling-doc pattern.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:27-33

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Regex ^[12]\.[0-9]{2}s$ rejects durations &gt;= 3.00s. Overloaded CI can report &gt;=3.00s after sleep 2, causing a spurious harness failure. Widen acceptable range or assert min/max with slack.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:27-33

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] `sleep 2` test only accepts 1.xx–2.xx seconds. Heavily loaded CI can report 3.00s+ while timing logic is still correct. Widen the regex upper bound or assert min plus generous max.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## risk-integration: scripts/test-harness-timer.sh:18-25

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] sleep 0.5 upper bound 0.69s is tight vs stated ±100ms slop Reported 0.70s fails the test on rare scheduler delay Allow 0.7xs or use numeric min/max comparison
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/test-harness-timer.sh:27-33

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] sleep 2 assertion only allows 1.xx–2.99s Heavily loaded CI could yield 3.00s+ wall time; harness fails despite valid timer Widen regex or assert min/max duration with slack
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:18-25

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Tight wall-clock window for sleep 0.5. Rare scheduler delays can exceed 0.69s and flake the test. Widen slop or use bounded tolerance logic.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:27-33

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] sleep 2 regex only allows 1.xx-2.xx s Wall time can be 3.00s+ on loaded CI so timing line matches harness but test fails Widen pattern or assert numeric bounds instead of leading digit class
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:53-64

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] false case only asserts non-empty timing token, not shape. Malformed non-empty third field could pass despite invalid duration format. Assert timing matches the same format/regex as other cases or the documented parser contract.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **Important** (`correctness`) — `scripts/test-harness-timer.sh:35-41` — The `sleep 0.5` case caps at **`0.79s`**, but `harness-timer.sh` measures wall time from **after** the first `python3` snapshot through the second snapshot **after** the sleep, so the measured interval includes at least one extra `python3 -c` invocation on the hot path. On cold or overloaded hosts, `sleep 0.5` plus that overhead can exceed **`0.80s`** even when the wrapper is correct, producing **flake failures** on `test-harness-timer` / shard 12. Widen the upper bound, measure overhead separately, or anchor the assertion to the prompt’s regex plus a documented slop policy.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end &lt; start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Latent** (`correctness`) — `scripts/harness-timer.sh:12`, `scripts/harness-timer.md:28-30` — If the wall clock moves backward (`end &lt; start`), Python emits a **negative** fractional string, which **does not** match the published parser token `^[0-9]+(\.[0-9]+)?s$`, so a rare VM/NTP adjustment yields **log lines parsers reject** without any inner harness fault. Clamp elapsed at `0.00s`, or extend the contract to cover negatives and add a test if that is intentional.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 5. **Nit** (`code-quality`) — `scripts/test-harness-timer.sh:61-64` — The `false` case only checks that the timing field is **non-empty**, not that it matches the **`N.NNs`** shape or the public regex. A bogus third column would still pass. Reuse `timing_in_range` with a trivial non-negative window or assert the same regex used elsewhere in the file.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Nit** `code-quality` `scripts/test-harness-timer.sh:44-50`, `scripts/test-harness-timer.md:8` — The new `sleep 0.5` test does not match either the requested assertion (`^0\.[4-6][0-9]s$`) or its sibling doc: the script accepts up to `1.20s`, while the doc says `0.40s-0.79s`. This weakens the regression check and leaves the docs inconsistent. Tighten the assertion to the intended regex, or update both the harness and doc to the same deliberately widened CI range.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/test-harness-timer.sh:44-50`, `scripts/test-harness-timer.md:8` — The new `sleep 0.5` test does not match either the requested assertion (`^0\.[4-6][0-9]s$`) or its sibling doc: the script accepts up to `1.20s`, while the doc says `0.40s-0.79s`. This weakens the regression check and leaves the docs inconsistent. Tighten the assertion to the intended regex, or update both the harness and doc to the same deliberately widened CI range.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.md:6-10

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Doc lists three tests; scripts/test-harness-timer.sh adds a backward-clock case. Contract doc omits exercised behavior. Add a fourth bullet for the backward-clock / clamp test.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.md:8 vs scripts/test-harness-timer.sh:47-50

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sibling doc Test 1 claims 0.40s-0.79s but the harness allows 0.40s-1.20s. Reviewers or future edits trust the .md and ship a mismatching or wrong tightened test. Align scripts/test-harness-timer.md with scripts/test-harness-timer.sh (or change the script to match the doc after conscious choice).
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.md:8 vs scripts/test-harness-timer.sh:47-50

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Sibling doc claims 0.40s-0.79s for sleep 0.5; script enforces 0.40s-1.20s. Triage and reviewers read the wrong acceptance window. Update scripts/test-harness-timer.md or the numeric bounds so they match.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.md:8-9 vs scripts/test-harness-timer.sh:47-48

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Doc says 0.40s-0.79s for test 1; script allows up to 1.20s Readers trust the stub and misjudge what CI enforces. Align ranges (and ideally align both with the feature regex).
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:44-60

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sleep timing assertions use wide numeric windows and a generic two-decimal format check; they do not implement the feature/plan regex contracts (^0.[4-6][0-9]s$ for sleep 0.5, ^[12].[0-9]{2}s$ for sleep 2). A timer bug emitting 3.50s for sleep 2 passes Test 2; 0.79s for sleep 0.5 passes Test 1 though both violate the stated acceptance regexes. Assert timings with =~ or grep -E against the specified regexes (or update the written contract everywhere if intentionally looser).
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:78-99

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Shim matches exact python -c string; harness edits can neuter test silently. Clamp regression may stop running without failing. Document coupling or assert shim invocation via counter/state.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: scripts/test-harness-timer.md:8 vs scripts/test-harness-timer.sh:47-50

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sibling stub doc understates allowed sleep 0.5 timing window vs harness. Readers or future editors trust 0.40s-0.79s while CI accepts up to 1.20s; silent contract drift. Match doc to harness range or narrow harness to match doc; note rationale if intentional.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## risk-integration: scripts/test-harness-timer.sh:76-96;scripts/harness-timer.sh:8-11

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Backward-clock test depends on an exact python3 -c argv match. Rewording the timer’s Python one-liner can make the stub a no-op while the test still passes. Couple the stub to a stable contract (env hook) or assert the mock executed.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## architecture: scripts/test-harness-timer.md:6-10 vs scripts/test-harness-timer.sh:76-108

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing documentation for backward-clock Test 4. Coverage story incomplete for operators scanning only the .md sibling. Add Test 4 description mirroring the shell harness.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: scripts/test-harness-timer.sh:44-51

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] sleep 0.5 assertion uses 0.40-1.20s instead of feature regex ^0\.[4-6][0-9]s$ A timing like 1.10s passes the harness but would fail the specified regex; sub-second shard signal quality regressions could slip through. Match ^0\.[4-6][0-9]s$ (or an equivalent tight numeric band) for the half-second case.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: scripts/test-harness-timer.sh:53-60

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] sleep 2 assertion uses 1.90-4.99s without constraining the leading second digit Values like 3.50s pass but violate ^[12]\.[0-9]{2}s$ from the feature description. Add regex or a range that only allows 1.xx–2.xx (with documented slop), not 3.x–4.x.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/test-harness-timer.sh:60-66

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] sleep 2 assertion only allows 1.xx–2.xx second timings Under load sleep 2 can wall-clock past 3s so timing prints 3.01s and the regex fails despite a correct harness Use a numeric range check or allow a bounded overrun in the pattern
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: scripts/test-harness-timer.sh:8-20

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Counter variable `fail` shares its name with helper `fail()`, diverging from the repo pattern that uses `FAIL` for the counter in accumulating harnesses. Maintenance and future edits to `fail()` risk confusion or subtle mistakes; harder to grep and inconsistent with scripts/test-refresh-run-logs.sh. Rename counter to `FAIL` (and optionally `PASS`/`pass` to `PASS`) following scripts/test-refresh-run-logs.sh:10-14.
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## correctness: scripts/harness-timer.md (Edit-In-Sync); docs/linting.md (absent from branch diff)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Output format for LARCH_HARNESS_TIMING changed to fractional seconds while harness-timer.md still requires a same-PR update to docs/linting.md under "Refreshing harness shard balance." Contributors or checklist-driven review may treat the PR as failing the documented cross-file sync contract even though code and tests are otherwise consistent. Add a minimal same-PR edit to docs/linting.md in that subsection (e.g., state fractional third column and reference scripts/harness-timer.md parser contract) or relax the Edit-In-Sync text if paired updates are no longer required.
- **Suggested revision**: Address the concern above.

