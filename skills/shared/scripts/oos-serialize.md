# oos-serialize.sh Contract

`skills/shared/scripts/oos-serialize.sh` extracts accepted out-of-scope review observations from a ballot file while holding security-tagged observations locally.

Primary caller: `skills/review/scripts/emit-tally.sh`.

Inputs: `--findings-file`, `--output-file`, and optional `--session-env-path`. The serializer scans `### FINDING_N:` blocks tagged `[OUT_OF_SCOPE]` or `[OOS]`, writes only blocks with no `Result=` marker or `Result=accepted`, and rewrites emitted headings to canonical `### OOS_<seq>:`. Blocks with `Result=rejected` are excluded from the accepted sink.

Security holdback recognizes unfenced `focus-area = security`, dedicated line-start `focus-area: security` / `focus-area = security` fields whose label or value may be backtick-wrapped, and explicit heading tags such as `[security]` / `<security>` (also when backtick-wrapped). Ordinary heading prose containing the bare word `security` is not a security-routing signal.

Stdout is `OOS_ACCEPTED` and `OOS_HELD_SECURITY`.

When any tagged OOS block is present, security classification requires a working `python3` interpreter (shared contract with `scripts/lib-vote-tally.sh::is_security_block`). Classifier smoke-test, block read (`OSError`), or routing failures exit **2** and leave `--output-file` empty so callers such as `emit-tally.sh` fail closed instead of emitting a partial public sink.

Harness: `skills/shared/scripts/test-oos-serialize.sh`, wired through `make test-oos-serialize`.
