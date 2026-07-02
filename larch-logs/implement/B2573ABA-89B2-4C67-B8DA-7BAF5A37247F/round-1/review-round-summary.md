# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: preserve_temp_root not committed before advertised stdout or post work
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `preserve_temp_root` is only returned to `main()` when `_main_with_temp_root` completes normally. If a `BaseException` occurs after the preserve decision (during `_print_analysis`, plot output, or `_post_report_if_requested`) but before the return tuple reaches `main()`, `main()`'s `finally` still sees `preserve_temp_root=False` and synchronously `rmtree`s `temp_root`. Stdout may already advertise `Cache JSON:` and plot paths while the preserved artifacts are deleted immediately (e.g. `BrokenPipeError` when piping to `head`, `SIGINT`, or a non-`ShipError` from post-issue work).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Commit preserve_temp_root via a mutable holder or inner try/finally before _print_analysis; add a regression test for exception-after-cache-print preserving the root.
  - From cursor-specialist-edge-cases: Propagate preserve to main() before advertised stdout or slow post work via a mutable holder updated at line 145, or relocate synchronous rmtree into _main_with_temp_root finally keyed on that holder.
  - From codex-specialist-edge-cases: Move cleanup into the scope with the updated preserve flag, or update outer preserve state before printing/posting advertised paths.


### FINDING_2: tmpdir redaction hides advertised cache and plot paths
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: important
- **Concern**: Preserved report-token artifact paths are printed through general tmpdir redaction (`redact.redact`), so stdout shows placeholders like `Cache JSON: <TMPDIR>/report-cache.ndjson` instead of the concrete preserved path under `<TMPDIR> That contradicts the readable advertised-path contract: callers cannot open the paths printed on stdout after exit even when the temp root is preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Use secrets-only or dedicated artifact-line redaction that preserves concrete cache and plot paths, and test that advertised stdout paths exist.
  - From codex-specialist-testing: Print artifact paths through an explicit unredacted safe path or revise the contract, and add tests that parse stdout paths and assert those paths exist after main exits.


