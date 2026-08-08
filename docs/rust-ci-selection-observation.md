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

The `partial` live window remains open: `RUST_CI_PARTIAL_ENFORCEMENT` is
`false`, so a proposed `partial` mode records an observation effective `full`
mode and runs the full backstop. `RUST_CI_SKIP_ENFORCEMENT` is `true` after the
completed skip window below. A proposed `skip` mode now executes only after the
trusted-main policy artifact validates; a cache or verification failure remains
`full`. The topology-changing pull request that enables a class is itself a
global `full` input and cannot be counted as that class's selected-path result.

Before a reviewed workflow change enables an unproven class, append at least
three independent live pull-request rows to this document. Each row must
include:

- a distinct pull-request number and tested merge candidate;
- the uploaded `rust-ci-selection` artifact's proposed mode and
  observation-window effective full reason;
- successful `rust-full`, `rust-coverage`, and `rust-gate` job links;
- an explicit false-safe or false-full comparison result; and
- the full-backstop duration plus, when the class is later enabled, the
  selected-path duration with its runner and cache conditions.

### Completed skip observation window

These are three distinct, ordinary docs-only pull requests. The linked
selection job uploaded the listed effective-decision record; every full
backstop in the same run passed.

| PR | Tested merge candidate | Proposed/effective decision | Full backstop | Comparison |
|---|---|---|---|---|
| [#8247](https://github.com/character-ai/larch/pull/8247) | `4d8d98e0a583f00e14aa8064124390289f873cab` | [`rust-ci-selection`](https://github.com/character-ai/larch/actions/runs/31248043914/job/93079779676): `skip` → `full`; `skip-observation-window-open`; `observation_only=true` | [`rust-full`, 345 s](https://github.com/character-ai/larch/actions/runs/31248043914/job/93079841037); [`rust-coverage` success](https://github.com/character-ai/larch/actions/runs/31248043914/job/93080391569); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/31248043914/job/93080402605) | false-safe: none observed; false-full: not assessed while `full` was effective |
| [#8248](https://github.com/character-ai/larch/pull/8248) | `b9f8cad8070535181dc8e369b1f792c8090a1f86` | [`rust-ci-selection`](https://github.com/character-ai/larch/actions/runs/31248368102/job/93080605950): `skip` → `full`; `skip-observation-window-open`; `observation_only=true` | [`rust-full`, 352 s](https://github.com/character-ai/larch/actions/runs/31248368102/job/93080650942); [`rust-coverage` success](https://github.com/character-ai/larch/actions/runs/31248368102/job/93081184191); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/31248368102/job/93081194121) | false-safe: none observed; false-full: not assessed while `full` was effective |
| [#8249](https://github.com/character-ai/larch/pull/8249) | `f3f4e63dd4a9b4ee79fde0abd490f3a2ea760d26` | [`rust-ci-selection`](https://github.com/character-ai/larch/actions/runs/31248773154/job/93081635452): `skip` → `full`; `skip-observation-window-open`; `observation_only=true` | [`rust-full`, 346 s](https://github.com/character-ai/larch/actions/runs/31248773154/job/93081688015); [`rust-coverage` success](https://github.com/character-ai/larch/actions/runs/31248773154/job/93082214841); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/31248773154/job/93082225084) | false-safe: none observed; false-full: not assessed while `full` was effective |

All three runs used `ubuntu-24.04` with the same Rust-input identity. The
Cargo-inputs, cargo-nextest, and cargo-llvm-cov caches were hits in every run;
the coverage-target cache was deliberately disabled. The comparable full-job
durations were 345 seconds, 352 seconds, and 346 seconds (median 346 seconds).
Each full backstop passed, so this window has zero observed false-safe results
for `skip`. A green full backstop is not false-full evidence while the full lane
is intentionally effective.

The reviewed skip promotion that recorded this window was a global `full`
input, so it did not pretend to supply a selected skip duration. The ordinary
eligible pull request below provides that measurement. The partial class remains
in observation until it independently meets the same rule.

### Live-row collection

Treat each row as evidence from the exact pull-request workflow run, not as a
claim made by its branch. Download that run's `rust-ci-selection` artifact and
record its proposed mode, effective mode, effective-mode reason, and
`observation_only` value. Then record the linked `rust-full`, `rust-coverage`,
and `rust-gate` job results and durations from the same run. Record a rerun or
a job from a different merge candidate separately, but do not let it replace
the original row or satisfy the distinct-pull-request requirement. A
label-forced run is not eligible evidence.

### Comparison outcome

For a proposed non-full row, record `false-safe: none observed` only when the
same run's full backstop is green. A full-backstop failure is inconclusive until
its scope is investigated: mark it false-safe when it exposes required work
that the proposed path would omit, and otherwise record the failure without
promoting the class. A green full backstop does not establish a selected-path
duration or turn the row into false-full evidence.

### Timing comparability

Record the runner image, tool and cache class, and the full `rust-full` job
duration for every live row. After a class is enabled, compare its selected-path
duration only with full rows on the same runner image and with the same
Rust-input identity. Distinguish cold from warm runs and explicitly name when
the lanes intentionally use different cache mechanisms, such as Cargo/tool
caches for `full` and a verified trusted-main artifact for `skip`; do not call
those different mechanisms the same cache class. The lightweight aggregate jobs
confirm required dependencies; they do not replace the selected execution-path
duration.

### Enforced skip measurement

| PR | Tested merge candidate | Enforced decision | Selected path and required statuses | Result |
|---|---|---|---|---|
| [#8252](https://github.com/character-ai/larch/pull/8252) | `b98d5e4b2669f79f6f1516ed307afef8c5ad78c4` | [`rust-ci-selection`](https://github.com/character-ai/larch/actions/runs/31249895522/job/93084462058): proposed/effective `skip`; `selector-proposed-skip`; `rollout_state=enforced`; `observation_only=false` | [`rust-skip`, 71 s](https://github.com/character-ai/larch/actions/runs/31249895522/job/93084512640); [`rust-coverage` success](https://github.com/character-ai/larch/actions/runs/31249895522/job/93084626961); [`rust-gate` success](https://github.com/character-ai/larch/actions/runs/31249895522/job/93084645746); [`rust-full` skipped](https://github.com/character-ai/larch/actions/runs/31249895522/job/93084512895) | verified trusted-main artifact, repository policy, and plugin validation all succeeded |

The selected `rust-skip` job completed trusted-main artifact verification,
repository policy, and plugin validation before it succeeded. Its 71-second
duration is the selected execution-path measurement. The required Rust path
from `rust-selection` completion through `rust-gate` completion took 92 seconds.
The comparable full controls were 362 seconds (#8247), 370 seconds (#8248),
and 368 seconds (#8249), for a 368-second median; the enforced skip path is
therefore 276 seconds (75%) shorter on that measured Rust PR critical path.

All four runs used `ubuntu-24.04` and the same Rust-input identity. The full
controls restored warm Cargo-inputs, cargo-nextest, and cargo-llvm-cov caches
with the coverage-target cache disabled. The selected skip lane instead used a
verified trusted-main policy artifact, so this is a class-specific cache
comparison rather than a claim that both lanes restored the same cache. Its
successful repository-policy and plugin-validation step retains the coverage
that makes this skip decision safe.

Do not count a label-forced run, selector failure fallback, or a historical
replay as a live observation. A class may be promoted only if every live row
for that class has zero false-safe results. A false-safe result keeps that class
on `full`; a false-full result may improve the classifier but does not justify
promotion. Any selector, ownership, trusted-binary, cache-schema, or workflow
change that changes selection or the trust contract starts a fresh live window
for the affected class. The reviewed class-specific enforcement toggle that
follows a completed window does not change the classifier or its trusted-input
contract.

## Timing interpretation and rollback

The historical full `rust-coverage` samples above are contextual baselines: the
partial rows have a median of 140 seconds and the skip rows a median of 205
seconds. They are not timings for non-full jobs. The completed live skip window
adds a comparable pre-enforcement full-job control with a median of 346 seconds.
Only after a class is enabled can its `rust-partial` or `rust-skip` duration
demonstrate a critical-path reduction against comparable full-backstop samples.

To roll back selection immediately, apply the `full-rust-ci` label to a pull
request. To roll back a decision class permanently, keep its enforcement value
`false`, remove its audited owner from `rust_ci_selection.py`, or route its
path to a global `full` trigger. A cache miss, schema change, input-identity
mismatch, checksum failure, or provenance failure already falls back to `full`
without an operator action.
