# Rust CI selector historical classification baseline

This record distinguishes historical classifier replays from the live
observation window that controls non-full Rust CI enforcement. Historical rows
are useful to exercise the final deterministic classifier against immutable
pull-request merge candidates, but they are not live selected-path evidence and
cannot authorize a non-full lane.

## Historical classification baseline

For each row, the current deterministic selector ran with the recorded PR base
and tested merge SHA in a detached worktree. The mode is therefore an
executable classifier result. The linked required full Rust backstop also
completed successfully for every candidate.

The replay command was:

```bash
python3 python/cli.py ci rust-select \
  --event-name pull_request \
  --base-sha <recorded-base> \
  --head-sha <tested-merge-candidate> \
  --repo-root <detached-candidate-worktree>
```

The selector source was the implementation in this change. In CI it executes
from the trusted pull-request base while it reads the candidate worktree as
data. Replaying immutable candidates lets this record compare the final
classifier with exact trees that had a successful full backstop.

| PR | Tested merge candidate | Replayed decision | Proposed scope | Full backstop | Result |
|---|---|---|---|---|---|
| [#8002](https://github.com/character-ai/larch/pull/8002) | `f0c40ddc21ae3e73fce3b0e8308bee41a57c0839` | `partial` | `larch-cli`; format, selected Clippy/tests/doctests, candidate policy and plugin validation | [`rust-coverage`, 230 s](https://github.com/character-ai/larch/actions/runs/30301479391/job/90095217754); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/30301479391/job/90096148397) | full backstop succeeded |
| [#7901](https://github.com/character-ai/larch/pull/7901) | `bdb9900d204c82ed301647d1dfaae607962638a9` | `partial` | `larch-cli`; format, selected Clippy/tests/doctests, candidate policy and plugin validation | [`rust-coverage`, 140 s](https://github.com/character-ai/larch/actions/runs/29796763651/job/88529560397); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/29796763651/job/88529880499) | full backstop succeeded |
| [#7845](https://github.com/character-ai/larch/pull/7845) | `545d81c5fc5b082025413fe7360a16bff182e7a0` | `partial` | `larch-cli`, `larch-lint`; format, selected Clippy/tests/doctests, candidate policy and plugin validation | [`rust-coverage`, 126 s](https://github.com/character-ai/larch/actions/runs/29721888005/job/88286437364); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/29721888005/job/88286756784) | full backstop succeeded |
| [#8039](https://github.com/character-ai/larch/pull/8039) | `60440c1e50e0f359e93e6a75f4425fd18b6edd8d` | `skip` | audited `plugin/`, `python/`, and `skills/` owners; trusted-main policy and plugin validation | [`rust-coverage`, 205 s](https://github.com/character-ai/larch/actions/runs/30849578510/job/91806054206); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/30849578510/job/91806928458) | full backstop succeeded |
| [#8053](https://github.com/character-ai/larch/pull/8053) | `d02eca8726e9f9b6eb8ae86a9903ded1a4ea85dd` | `skip` | audited `agent-lint.toml` owner; trusted-main repository policy | [`rust-coverage`, 206 s](https://github.com/character-ai/larch/actions/runs/30980712688/job/92224321286); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/30980712688/job/92224921450) | full backstop succeeded |
| [#8024](https://github.com/character-ai/larch/pull/8024) | `a216be3438a2ba9dbc4bd3853ca4a6f3f0c9d2e6` | `skip` | audited `plugin/`, `python/`, and `skills/` owners; trusted-main policy and plugin validation | [`rust-coverage`, 204 s](https://github.com/character-ai/larch/actions/runs/30741434838/job/91479479364); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/30741434838/job/91479781196) | full backstop succeeded |

The baseline contains six independent pull requests: three `partial` and three
`skip`. Each replay selects a useful non-full class, and every corresponding
full backstop passed. It records zero historical full-backstop failures for
those classifications.

This is not a claim that the final `rust-partial` or `rust-skip` workflow jobs
executed in those historical runs; they predate this topology. It therefore
does not establish a live selected-path false-safe rate or a post-enforcement
duration. In particular, a local replay of #8002 against its historical CLI
cannot run the final policy command because that historical binary predates the
command surface. The exact command and ownership contracts are covered by
deterministic selector and workflow tests.

## Required live observation window

The live window is open. Both `RUST_CI_PARTIAL_ENFORCEMENT` and
`RUST_CI_SKIP_ENFORCEMENT` remain `false`, so a pull request with a proposed
`partial` or `skip` mode records an observation effective `full` mode and runs
the full backstop. This topology-changing pull request is itself a global
`full` input and cannot be counted.

Before a reviewed workflow change enables either class, append at least three
independent live pull-request rows to this document. Each row must include:

- a distinct pull-request number and tested merge candidate;
- the uploaded `rust-ci-selection` artifact's proposed mode and
  observation-window effective full reason;
- successful `rust-full`, `rust-coverage`, and `rust-gate` job links;
- an explicit false-safe or false-full comparison result; and
- the full-backstop duration plus, when the class is later enabled, the
  selected-path duration on a comparable runner and cache class.

### Live-row collection

Treat each row as evidence from the exact pull-request workflow run, not as a
claim made by its branch. Download that run's `rust-ci-selection` artifact and
record its proposed mode, effective mode, effective-mode reason, and
`observation_only` value. Then record the linked `rust-full`, `rust-coverage`,
and `rust-gate` job results and durations from the same run. Record a rerun or
a job from a different merge candidate separately, but do not let it replace
the original row or satisfy the distinct-pull-request requirement. A
label-forced run is not eligible evidence.

Do not count a label-forced run, selector failure fallback, or a historical
replay as a live observation. A class may be promoted only if every live row
for that class has zero false-safe results. A false-safe result keeps that class
on `full`; a false-full result may improve the classifier but does not justify
promotion. Any selector, ownership, trusted-binary, cache-schema, or workflow
change starts a fresh live window for the affected class.

## Timing interpretation and rollback

The historical full `rust-coverage` samples above are a contextual baseline:
the partial rows have a median of 140 seconds and the skip rows a median of 205
seconds. They are not timings for non-full jobs. Only after a class is enabled
can its `rust-partial` or `rust-skip` duration demonstrate a critical-path
reduction against comparable full-backstop samples.

To roll back selection immediately, apply the `full-rust-ci` label to a pull
request. To roll back a decision class permanently, keep its enforcement value
`false`, remove its audited owner from `rust_ci_selection.py`, or route its
path to a global `full` trigger. A cache miss, schema change, input-identity
mismatch, checksum failure, or provenance failure already falls back to `full`
without an operator action.
