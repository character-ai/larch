### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: **correctness** `python/ship.py:11` — **[Nit]** `_version_supported` calls `tuple(version_info)` with `# type: ignore[arg-type]` when `sys.version_info` already supports direct tuple comparison: `sys.version_info >= (3, 11)` works without any cast or type ignore. **Suggested fix:** type the parameter as `tuple[int, ...]` (or just inline the guard in the call site as `sys.version_info >= (3, 11)`).
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 6. **correctness** `python/ship.py:11` — **[Nit]** `_version_supported` calls `tuple(version_info)` with `# type: ignore[arg-type]` when `sys.version_info` already supports direct tuple comparison: `sys.version_info >= (3, 11)` works without any cast or type ignore. **Suggested fix:** type the parameter as `tuple[int, ...]` (or just inline the guard in the call site as `sys.version_info >= (3, 11)`). ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: **correctness** `python/ship.py:714-721` — **Latent**: `emit_result()` does not catch I/O errors from `print`/`flush` on the contract stream. If `print(json.dumps(payload, sort_keys=True), file=stream)` or `stream.flush()` raises `BrokenPipeError` or `OSError` (e.g., fd 3 closed by the parent's orchestrator between quiet init and emit, or stdout broken in non-quiet mode), the exception propagates through `emit_result`, bypasses `_persist_stall_metadata_if_needed` (already past), and exits `main()` entirely — leaving the caller with no contract JSON and a non-zero, non-JSON exit. The acceptance criterion "Contract JSON always reaches the caller-visible contract stream" is violated on a broken pipe. **Suggested fix:** Wrap the print+flush in `try/except OSError` (or `Exception`), log the failure to original stderr (fd 4 if quiet), and continue to return the exit code.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **correctness** `python/ship.py:714-721` — **Latent**: `emit_result()` does not catch I/O errors from `print`/`flush` on the contract stream. If `print(json.dumps(payload, sort_keys=True), file=stream)` or `stream.flush()` raises `BrokenPipeError` or `OSError` (e.g., fd 3 closed by the parent's orchestrator between quiet init and emit, or stdout broken in non-quiet mode), the exception propagates through `emit_result`, bypasses `_persist_stall_metadata_if_needed` (already past), and exits `main()` entirely — leaving the caller with no contract JSON and a non-zero, non-JSON exit. The acceptance criterion "Contract JSON always reaches the caller-visible contract stream" is violated on a broken pipe. **Suggested fix:** Wrap the print+flush in `try/except OSError` (or `Exception`), log the failure to original stderr (fd 4 if quiet), and continue to return the exit code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: **Latent** `correctness` `python/finalize.py:334,337` — `shlex.split(value, posix=True)` silently strips backslashes from single-token values (e.g., a bash-written `STALL_STEP=git\-rebase` reads back as `git-rebase`; `VALUE=a\b` reads as `ab`). The fallback `len(parsed) == 1 else value` only protects multi-token inputs. Since `write_finalize_state_merged` never writes backslashes, round-trip is clean for Python-written files, but external `finalize-state.sh` files written by bash scripts using backslash-continuation would silently corrupt on first Python read. **Suggested fix:** Replace shlex with a simple `value.strip("'\"")` parser that mirrors the unquoted-only write format, or at least document the posix-stripping caveat in the function docstring.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Latent** `correctness` `python/finalize.py:334,337` — `shlex.split(value, posix=True)` silently strips backslashes from single-token values (e.g., a bash-written `STALL_STEP=git\-rebase` reads back as `git-rebase`; `VALUE=a\b` reads as `ab`). The fallback `len(parsed) == 1 else value` only protects multi-token inputs. Since `write_finalize_state_merged` never writes backslashes, round-trip is clean for Python-written files, but external `finalize-state.sh` files written by bash scripts using backslash-continuation would silently corrupt on first Python read. **Suggested fix:** Replace shlex with a simple `value.strip("'\"")` parser that mirrors the unquoted-only write format, or at least document the posix-stripping caveat in the function docstring.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

