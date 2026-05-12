## Goal
Add 3 test cases per harness covering the `--summary` flag mode in `token-report.sh` and `timing-report.sh`.

## Implementation Plan
- `scripts/test-token-report.sh`: 3 summary-mode cases (normal output with vendor breakdown, zero-vendor omitting parenthetical, no-marks unavailable)
- `scripts/test-timing-report.sh`: 3 summary-mode cases (normal output with elapsed + vendor counts, zero-vendor with zeros in parenthetical, no-marks unavailable)

## Test plan
Run both harnesses directly: `bash scripts/test-token-report.sh` and `bash scripts/test-timing-report.sh`.
