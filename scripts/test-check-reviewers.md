# scripts/test-check-reviewers.sh — contract

Regression test for `check-reviewers.sh` presence detection.

## What it tests

## Fixture coverage

- **Present**: Codex and Cursor stubs on `PATH` emit `*_PRESENT=true` and `*_AVAILABLE=true`.
- **Absent / skipped**: missing binaries and skip flags emit `*_PRESENT=false` and `*_AVAILABLE=false`.
- **Rejected legacy probe**: `--probe` exits 2 so callers cannot request removed runtime health probing.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/check-reviewers.sh` | Source of truth for the acceptance rule this harness tests |
| `scripts/check-reviewers.md` | Contract for the script under test |
