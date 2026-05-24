# test-phantom-probe-with-warn.sh

Offline harness for `scripts/phantom-probe-with-warn.sh` (see sibling `.md`).

## Stubbing

Same `SCRIPT_DIR` sibling pattern as `scripts/test-rebase-checkpoint-probe.md`: copy `phantom-probe-with-warn.sh`, `lib-quiet.sh`, `lib-phantom-probe.sh`, and stub `check-phantom-dirty.sh` / `append-execution-issue.sh` into a per-case temp directory.

## Cases (10)

1. `STATUS=clean`
2. `STATUS=tracked-only`
3. `STATUS=phantom` + successful append
4. `STATUS=unknown` + successful append
5. Append failure with `ERROR=` on stdout (FINDING_1)
6. Append failure stderr-only fallback
7. Breadcrumb count (`→ phantom-probe:` exactly once) with `LARCH_QUIET_BREADCRUMBS=1`
8. Bad `--step` rejected by stub (simulates `check-phantom-dirty.sh` `unknown` / `bad-step`)
9. Executable-bit assertion on production `phantom-probe-with-warn.sh`
10. (Reserved duplicate coverage) — folded into case 3 phantom append success path; harness counts 10 assertions via explicit blocks.
