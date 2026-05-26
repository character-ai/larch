# test-render-voter-prompt.sh

Offline regression harness for `skills/shared/scripts/render-voter-prompt.sh`.

## Cases

1. **`case_finding_only`** — `finding-only` + `code`: expects the `[OUT_OF_SCOPE]` OOS clause variant, the shared canonical OOS body substring, `FINDING_N:` examples with forensic axis tokens, the code-review diff/plan verification sentence, and **no** `OOS_N` substring anywhere in the rendered prompt.
2. **`case_finding_oos`** — `finding-oos` + `plan`: expects the plan-review OOS clause lead-in, `OOS_N:` example lines with forensic axis tokens, and the plan/repo silent inspection allowance.
3. **`case_canonical_text_drift_guard`** — greps a hard-coded shared substring (the identical tail of both OOS grammar variants) in `skills/shared/voting-protocol.md`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`, and `skills/design/references/plan-review.md`.
4. **`case_executable_bit`** — asserts `[ -x skills/shared/scripts/render-voter-prompt.sh ]`.
5. **`case_lib_quiet_isolation`** — runs with `LARCH_QUIET_ACTIVE=1` and asserts stdout is non-empty (guards against accidentally sourcing `lib-quiet` and redirecting stdout).
6. **`case_argument_validation`** — asserts exit code `2` for missing `--verification-context` and for invalid `--id-grammar`.

## Invocation

```bash
make test-render-voter-prompt
# or
bash scripts/test-render-voter-prompt.sh
```

Wired into `Makefile` (`test-harnesses-13` shard) per `docs/linting.md`.
