# test-oos-disposition-gate.sh

Delegation smoke for `oos-disposition-gate.sh` and `oos-disposition-checkpoint.sh`. Gate and checkpoint behavior is Rust-owned by `crates/larch-cli/src/oos_commands.rs`, `crates/larch-core/src/issue/oos_disposition.rs`, and `crates/larch-core/src/issue/oos_record.rs`. This smoke must not re-exercise disposition logic.

## Smoke scope (both wrappers)

| Assertion | Coverage |
|-----------|----------|
| `CLAUDE_PLUGIN_ROOT` override selects `$CLAUDE_PLUGIN_ROOT/scripts/larch.sh` | smoke |
| Repo-root fallback when `CLAUDE_PLUGIN_ROOT` is unset | smoke |
| Exact route `scripts/larch.sh oos disposition-gate` | smoke (gate) |
| Exact route `scripts/larch.sh oos disposition-checkpoint` | smoke (checkpoint) |
| Argument forwarding (including multi-arg) | smoke |
| Exit-status forwarding | smoke |
| Stdout / stderr passthrough unchanged | smoke |

## Rust coverage map

| Behavior | Rust authority |
|----------|----------------|
| Gate skip, invalid-input refusal, and command exit mapping | `oos_commands::tests::the_gate_clears_a_fork_and_refuses_an_incomplete_line` |
| Orphan, malformed, or unreadable gate inputs | `oos_commands::tests::the_counters_refuse_an_orphan_batch_and_an_unparseable_one` and `the_counters_refuse_a_directory_and_an_unusable_range` |
| Loose and strict filed-URL evidence | `oos_commands::tests::strict_and_loose_filing_evidence_both_clear_the_gate` |
| Filed, inline, and rejected disposition states | `oos_disposition::tests::the_gate_clears_on_filing_triage_or_explicit_rejection` |
| URL hosts, de-duplication, rejected sections, and strict fields | `oos_disposition::tests` in `crates/larch-core/src/issue/oos_disposition.rs` |
| Canonical, legacy, and security-routed block counting | `oos_record::tests` in `crates/larch-core/src/issue/oos_record.rs` |
| Empty, forked, blocked, security-pending, ambiguous-run, and design-export checkpoints | `oos_commands::tests` from `a_checkpoint_with_nothing_accepted_clears` through `a_checkpoint_line_that_does_not_parse_still_records_where_it_failed` |
| Wrapper plugin root, route, argv, exit, stdout, and stderr | `skills/implement/scripts/test-oos-disposition-gate.sh` |

The former Python `test_disposition_gate_*` names were retired with #8178. Do not restore them as command-behavior authority; retained `python/tests/issue/test_file_oos.py` coverage exercises distinct in-process helpers under receiving umbrella #7680.

## Commands

```text
cargo test --locked --package larch-cli --bin larch oos_commands::tests
cargo test --locked --package larch-core --lib issue::oos_disposition::tests
cargo test --locked --package larch-core --lib issue::oos_record::tests
make oos-disposition-gate-bash-harness
shellcheck skills/implement/scripts/test-oos-disposition-gate.sh
```
